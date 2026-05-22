import numpy as np
from gnuradio import gr

# ── Numba kernel: compiled once, then runs at near-C speed on all cores ────────
try:
    from numba import njit, prange

    @njit(parallel=True, cache=True, fastmath=True)
    def _nlms_kernel(A_H, X, mu):
        """
        Each angle k runs on a separate CPU core (prange).
        No heap, no GIL, no Python — pure native code after first JIT call.
        A_H : (K, 2) complex64  — conjugated steering matrix
        X   : (N, 2) complex64  — snapshot block
        mu  : float32           — step size
        """
        K      = A_H.shape[0]
        N      = X.shape[0]
        norms  = np.zeros(K, dtype=np.float32)

        for k in prange(K):                    # ← all K angles in parallel
            w0 = np.complex64(0.0)
            w1 = np.complex64(0.0)
            a0 = A_H[k, 0]                     # desired filter target, element 0
            a1 = A_H[k, 1]                     # desired filter target, element 1

            for n in range(N):                 # ← sequential (NLMS recurrence)
                x0   = X[n, 0]
                x1   = X[n, 1]
                xns  = (x0.real*x0.real + x0.imag*x0.imag +
                        x1.real*x1.real + x1.imag*x1.imag +
                        np.float32(1e-6))       # ||x_n||²
                d    = a0*x0 + a1*x1           # desired  :  a^H · x_n
                y    = w0*x0 + w1*x1           # output   :  ŵ^H · x_n
                e    = d - y                   # error
                s    = mu / xns               # NLMS step size
                w0  += s * e * np.conj(x0)    # weight update (conj stored)
                w1  += s * e * np.conj(x1)

            norms[k] = np.sqrt(w0.real*w0.real + w0.imag*w0.imag +
                               w1.real*w1.real + w1.imag*w1.imag)
        return norms

    _NUMBA = True
    print("[NLMS DOA] Numba found — parallel JIT mode active")

except ImportError:
    _NUMBA = False
    print("[NLMS DOA] Numba not found — falling back to numpy")


class nlms_doa(gr.decim_block):
    """
    NLMS DOA for USRP X310, 2-element ULA.
    With Numba:    runs K=181, N=100 comfortably at 500 kHz
    Without Numba: use K=61, N=30, samp_rate ≤ 100 kHz
    """
    def __init__(self, num_angles=91, num_snapshots=10, step_size=0.2):
        gr.decim_block.__init__(
            self,
            name='NLMS DOA',
            in_sig=[np.complex64, np.complex64],
            out_sig=[(np.float32, num_angles)],
            decim=num_snapshots
        )
        self.K   = num_angles
        self.N   = num_snapshots
        self.mu  = np.float32(step_size)
        self._t  = 0                           # throttle print counter

        # One block per work() → GIL held for one block at a time only
        self.set_max_noutput_items(1)

        # Steering matrix: (2, K) complex64, precomputed once
        theta    = np.deg2rad(np.linspace(-90.0, 90.0, self.K))
        A        = np.ones((2, self.K), dtype=np.complex64)
        A[1]     = np.exp(-1j * np.pi * np.sin(theta)).astype(np.complex64)
        self.A_H = np.ascontiguousarray(np.conj(A).T)   # (K, 2), C-contiguous
        self.ang = np.linspace(-90.0, 90.0, self.K)

        # Numpy-fallback buffers (only used when Numba is absent)
        self.X     = np.zeros((self.N, 2),      dtype=np.complex64)
        self.W     = np.zeros((self.K, 2),      dtype=np.complex64)
        self.D     = np.zeros((self.K, self.N), dtype=np.complex64)
        self.Y     = np.zeros(self.K,           dtype=np.complex64)
        self.E     = np.zeros(self.K,           dtype=np.complex64)
        self.dW    = np.zeros((self.K, 2),      dtype=np.complex64)
        self.x_c   = np.zeros(2,               dtype=np.complex64)
        self.nsq   = np.zeros(self.K,           dtype=np.float32)
        self.norms = np.zeros(self.K,           dtype=np.float32)

        mode = "Numba parallel" if _NUMBA else "numpy (install numba for 50× speedup)"
        print(f"[NLMS DOA] K={self.K}  N={self.N}  mu={step_size}  | {mode}")

    # ── Numpy fallback (preallocated, zero-alloc in loop) ──────────────────────
    def _nlms_numpy(self):
        np.dot(self.A_H, self.X.T, out=self.D)
        self.W[:] = 0.0
        for n in range(self.N):
            x_n  = self.X[n]
            xns  = np.float32(x_n.real @ x_n.real
                            + x_n.imag @ x_n.imag + 1e-6)
            np.conj(x_n, out=self.x_c)
            np.dot(self.W, x_n, out=self.Y)
            np.subtract(self.D[:, n], self.Y, out=self.E)
            np.multiply(self.E[:, None], self.x_c[None, :], out=self.dW)
            self.dW *= (self.mu / xns)
            self.W  += self.dW
        W_f = self.W.view(np.float32).reshape(self.K, 4)
        np.einsum('ki,ki->k', W_f, W_f, out=self.nsq)
        np.sqrt(self.nsq, out=self.norms)
        return self.norms

    # ── work() ─────────────────────────────────────────────────────────────────
    def work(self, input_items, output_items):
        self.X[:, 0] = input_items[0][:self.N]
        self.X[:, 1] = input_items[1][:self.N]

        if _NUMBA:
            norms = _nlms_kernel(self.A_H, self.X, self.mu)
        else:
            norms = self._nlms_numpy()

        output_items[0][0][:] = norms

        self._t += 1
        if self._t % 500 == 0:
            print(f"[NLMS] {self.ang[np.argmax(norms)]:.1f}°")

        return 1
