import numpy as np
from gnuradio import gr

class nlms_doa(gr.decim_block):
    """
    Ultra-Optimized Batch Block-NLMS DoA for USRP X310.
    Processes all available blocks in a single call to eliminate 
    Python context-switching overhead and prevent Overflows (OO).
    """
    def __init__(self, num_angles=91, num_snapshots=30,
                 step_size=0.2, num_passes=3):
        gr.decim_block.__init__(
            self,
            name='Block-NLMS DOA Optimized',
            in_sig=[np.complex64, np.complex64],
            out_sig=[(np.float32, num_angles)],
            decim=num_snapshots
        )
        self.K   = num_angles
        self.N   = num_snapshots
        self.mu  = np.float32(step_size)
        self.P   = num_passes
        self._cnt = 0

        # Steering matrix A_H: (K, 2) complex64 — computed once at startup
        theta    = np.deg2rad(np.linspace(-90.0, 90.0, self.K))
        A        = np.ones((2, self.K), dtype=np.complex64)
        A[1]     = np.exp(-1j * np.pi * np.sin(theta)).astype(np.complex64)
        self.A_H = np.ascontiguousarray(np.conj(A).T)   # (K, 2)
        self.ang = np.linspace(-90.0, 90.0, self.K)

        # Pre-allocated single-block buffers to eliminate garbage collection
        self.X    = np.zeros((self.N, 2),       dtype=np.complex64)
        self.X_c  = np.zeros((self.N, 2),       dtype=np.complex64)
        self.D    = np.zeros((self.K, self.N),  dtype=np.complex64)
        self.W    = np.zeros((self.K, 2),       dtype=np.complex64)
        self.Y    = np.zeros((self.K, self.N),  dtype=np.complex64)
        self.E    = np.zeros((self.K, self.N),  dtype=np.complex64)
        self.dW   = np.zeros((self.K, 2),       dtype=np.complex64)
        self.nsq  = np.zeros(self.K,            dtype=np.float32)

        kb = sum(a.nbytes for a in [self.A_H, self.X, self.X_c, self.D,
                  self.W, self.Y, self.E, self.dW, self.nsq]) / 1024
        print(f"[Block-NLMS] K={self.K} N={self.N} passes={self.P} | {kb:.1f} KB Buffers Pre-allocated")

    def work(self, input_items, output_items):
        in0 = input_items[0]
        in1 = input_items[1]
        out = output_items[0]
        
        # Determine how many output blocks GNU Radio wants us to produce
        n_output = len(out)
        
        # Process each block sequentially inside this fast loop
        for i in range(n_output):
            start = i * self.N
            end = start + self.N
            
            # 1. Slice items directly without reallocation
            self.X[:, 0] = in0[start:end]
            self.X[:, 1] = in1[start:end]
            np.conj(self.X, out=self.X_c)

            # 2. Fast C-level array power calculation (Re^2 + Im^2)
            power = np.sum(self.X.real**2 + self.X.imag**2) / self.N + 1e-6
            scale = self.mu / (np.float32(self.P) * power)

            # 3. Reference Spatial Baseline: (K,2) @ (2,N) -> (K,N)
            np.dot(self.A_H, self.X.T, out=self.D)

            # 4. Multi-pass Block-NLMS core feedback loop
            self.W[:] = 0.0
            for _ in range(self.P):
                np.dot(self.W, self.X.T, out=self.Y)            # Y = W @ X^T
                np.subtract(self.D, self.Y, out=self.E)         # E = D - Y (Error feedback)
                np.dot(self.E, self.X_c, out=self.dW)          # dW = E @ X*
                self.dW *= scale
                self.W  += self.dW

            # 5. Fast Euclidean norm calculation written directly to GNU Radio's output buffer
            np.sum(self.W.real**2 + self.W.imag**2, axis=1, out=self.nsq)
            np.sqrt(self.nsq, out=out[i])

        # Periodically log findings to terminal to minimize print statements
        self._cnt += n_output
        if self._cnt >= 500:
            self._cnt = 0
            max_idx = np.argmax(out[-1])
            print(f"[NLMS] Peak detected at: {self.ang[max_idx]:.1f}°")

        return n_output
