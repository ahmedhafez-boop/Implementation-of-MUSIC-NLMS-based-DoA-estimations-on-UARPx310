import numpy as np
from gnuradio import gr

class nlms_doa(gr.decim_block):
    """
    Block-NLMS DOA — proper error feedback, no inner N-loop.

    Previous code:  W = (μ/P·pwr)·D·X*          (y=0 assumed, error missing)
    This code:      for P passes: E = D − W·X^T   (true error each pass)
                                  W += (μ/P·pwr)·E·X*
    Same matrix structure, same speed, correct NLMS.
    """
    def __init__(self, num_angles=91, num_snapshots=30,
                 step_size=0.2, num_passes=3):
        gr.decim_block.__init__(
            self,
            name='Block-NLMS DOA',
            in_sig=[np.complex64, np.complex64],
            out_sig=[(np.float32, num_angles)],
            decim=num_snapshots
        )
        self.K   = num_angles
        self.N   = num_snapshots
        self.mu  = np.float32(step_size)
        self.P   = num_passes
        self._cnt = 0
        self.set_max_noutput_items(1)

        # Steering matrix A_H: (K, 2) complex64 — computed once, never again
        theta    = np.deg2rad(np.linspace(-90.0, 90.0, self.K))
        A        = np.ones((2, self.K), dtype=np.complex64)
        A[1]     = np.exp(-1j * np.pi * np.sin(theta)).astype(np.complex64)
        self.A_H = np.ascontiguousarray(np.conj(A).T)   # (K, 2)
        self.ang = np.linspace(-90.0, 90.0, self.K)

        # Pre-allocate every buffer — zero malloc in work()
        self.X    = np.zeros((self.N, 2),       dtype=np.complex64)  # snapshots
        self.X_c  = np.zeros((self.N, 2),       dtype=np.complex64)  # conj(X)
        self.D    = np.zeros((self.K, self.N),  dtype=np.complex64)  # desired
        self.W    = np.zeros((self.K, 2),       dtype=np.complex64)  # weights
        self.Y    = np.zeros((self.K, self.N),  dtype=np.complex64)  # filter out
        self.E    = np.zeros((self.K, self.N),  dtype=np.complex64)  # error
        self.dW   = np.zeros((self.K, 2),       dtype=np.complex64)  # weight Δ
        self.nsq  = np.zeros(self.K,            dtype=np.float32)
        self.norms= np.zeros(self.K,            dtype=np.float32)

        kb = sum(a.nbytes for a in [self.A_H, self.X, self.X_c, self.D,
                  self.W, self.Y, self.E, self.dW, self.nsq, self.norms]) / 1024
        print(f"[Block-NLMS] K={self.K} N={self.N} "
              f"passes={self.P} mu={step_size} | {kb:.0f} KB fixed")

    def work(self, input_items, output_items):

        # ── 1. Load snapshots ─────────────────────────────────────────────────
        self.X[:, 0] = input_items[0][:self.N]
        self.X[:, 1] = input_items[1][:self.N]
        np.conj(self.X, out=self.X_c)

        # ── 2. Average block power (scalar, no allocation) ───────────────────
        X_f   = self.X.view(np.float32).reshape(self.N, 4)
        power = np.float32(np.einsum('ni,ni->', X_f, X_f) / self.N + 1e-6)

        # Step size split across P passes so total step ≈ μ/power
        scale = self.mu / (np.float32(self.P) * power)

        # ── 3. D = A_H @ X.T : (K,2)@(2,N) → (K,N) — one BLAS call ────────
        np.dot(self.A_H, self.X.T, out=self.D)

        # ── 4. Block-NLMS: P passes, proper error each time ──────────────────
        #
        #   pass 1:  W=0  →  Y=0  →  E=D          (same as old code)
        #   pass 2:  Y=W₁·Xᵀ  →  E=D−Y₁  ← ERROR TERM NOW CORRECT
        #   pass 3:  Y=W₂·Xᵀ  →  E=D−Y₂  ← refines further
        #
        self.W[:] = 0.0

        for _ in range(self.P):
            np.dot(self.W, self.X.T, out=self.Y)        # Y  = W·X^T   (K,N)
            np.subtract(self.D, self.Y, out=self.E)     # E  = D − Y   (K,N) ← error
            np.dot(self.E, self.X_c,    out=self.dW)    # dW = E·X*    (K,2)
            self.dW *= scale                             # scale in-place
            self.W  += self.dW                           # W += dW      in-place

        # ── 5. Norms via float32 view — zero allocation ───────────────────────
        W_f = self.W.view(np.float32).reshape(self.K, 4)
        np.einsum('ki,ki->k', W_f, W_f, out=self.nsq)
        np.sqrt(self.nsq, out=self.norms)

        output_items[0][0][:] = self.norms

        self._cnt += 1
        if self._cnt % 500 == 0:
            print(f"[NLMS] {self.ang[np.argmax(self.norms)]:.1f}°")

        return 1
