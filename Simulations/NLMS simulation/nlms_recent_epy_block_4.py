import numpy as np
from gnuradio import gr

class nlms_doa(gr.decim_block):
    def __init__(self, num_angles=181, num_snapshots=50, step_size=0.2):
        gr.decim_block.__init__(
            self,
            name='claude NLMS DOA',
            in_sig=[np.complex64, np.complex64],
            out_sig=[(np.float32, num_angles)],
            decim=num_snapshots
        )
        self.K   = num_angles
        self.N   = num_snapshots
        self.mu  = np.float32(step_size)
        self._n  = 0  # call counter for throttled print

        # One block per work() call — keeps GIL held for <1 ms
        self.set_max_noutput_items(1)

        # ── Steering matrix: precomputed once, never touched again ───────────
        theta = np.deg2rad(np.linspace(-90.0, 90.0, self.K))
        A = np.ones((2, self.K), dtype=np.complex64)
        A[1] = np.exp(-1j * np.pi * np.sin(theta)).astype(np.complex64)
        # A_H: (K, 2) conjugate-transpose, C-contiguous for fast BLAS
        self.A_H    = np.ascontiguousarray(np.conj(A).T)
        self.angles = np.linspace(-90.0, 90.0, self.K)

        # ── Preallocate every buffer — work() will NEVER call malloc ─────────
        self.X     = np.zeros((self.N, 2),      dtype=np.complex64)
        self.W     = np.zeros((self.K, 2),      dtype=np.complex64)
        self.D     = np.zeros((self.K, self.N), dtype=np.complex64)
        self.Y     = np.zeros(self.K,           dtype=np.complex64)
        self.E     = np.zeros(self.K,           dtype=np.complex64)
        self.dW    = np.zeros((self.K, 2),      dtype=np.complex64)
        self.x_c   = np.zeros(2,               dtype=np.complex64)
        self.nsq   = np.zeros(self.K,           dtype=np.float32)
        self.norms = np.zeros(self.K,           dtype=np.float32)

        kb = sum(a.nbytes for a in [self.A_H, self.X, self.W, self.D,
                  self.Y, self.E, self.dW, self.x_c, self.nsq, self.norms]) / 1024
        print(f"[NLMS DOA] K={self.K}  N={self.N}  mu={step_size}  | {kb:.0f} KB fixed")

    def work(self, input_items, output_items):
        # ── Load snapshots into preallocated X: (N, 2) ──────────────────────
        self.X[:, 0] = input_items[0][:self.N]
        self.X[:, 1] = input_items[1][:self.N]

        # ── D = A_H @ X.T → (K, N): all desired signals, one BLAS call ─────
        np.dot(self.A_H, self.X.T, out=self.D)

        # ── Reset weights ────────────────────────────────────────────────────
        self.W[:] = 0.0

        # ── NLMS: K angles in parallel, loop only over N snapshots ──────────
        for n in range(self.N):
            x_n = self.X[n]  # (2,) view — no copy

            # ||x_n||² as float32 scalar
            xns = np.float32(x_n.real @ x_n.real
                           + x_n.imag @ x_n.imag) + np.float32(1e-6)

            np.conj(x_n, out=self.x_c)               # x_c = conj(x_n)
            np.dot(self.W, x_n, out=self.Y)           # Y = W·x  (= w^H·x)
            np.subtract(self.D[:, n], self.Y, out=self.E)  # E = d - y

            # dW = outer(E, x_c), then W += (mu/||x||²)·dW  — all in-place
            np.multiply(self.E[:, None], self.x_c[None, :], out=self.dW)
            self.dW *= (self.mu / xns)
            self.W  += self.dW

        # ── ||w_k|| with zero allocation: view complex64 as float32 ─────────
        W_f = self.W.view(np.float32).reshape(self.K, 4)
        np.einsum('ki,ki->k', W_f, W_f, out=self.nsq)  # squared norms
        np.sqrt(self.nsq, out=self.norms)               # final norms

        output_items[0][0][:] = self.norms

        # Print ~4×/sec — not every call (would slow work() significantly)
        self._n += 1
        if self._n % 1000 == 0:
            print(f"[NLMS] Peak → {self.angles[np.argmax(self.norms)]:.1f}°")

        return 1
