import numpy as np
from gnuradio import gr

class nlms_doa(gr.decim_block):
    """
    Dual-Output Block-NLMS DOA with Physical Antenna Spacing Calibration.
    Port 0: 91-element Spatial Spectrum Vector
    Port 1: Clean Scalar Peak Angle (Degrees) for Compass/Number Sinks
    """
    def __init__(self, num_angles=91, num_snapshots=30,
                 step_size=0.2, num_passes=3, d_over_lambda=0.41): # Adjusted calibration factor
        gr.decim_block.__init__(
            self,
            name='Calibrated NLMS DOA',
            in_sig=[np.complex64, np.complex64],
            # Port 0 is a vector of size 91, Port 1 is a single scalar float
            out_sig=[(np.float32, num_angles), np.float32], 
            decim=num_snapshots
        )
        self.K   = num_angles
        self.N   = num_snapshots
        self.mu  = np.float32(step_size)
        self.P   = num_passes
        self.d_l = np.float32(d_over_lambda)
        self._cnt = 0

        # Steering matrix A_H with customizable antenna spacing
        self.ang = np.linspace(-90.0, 90.0, self.K)
        theta    = np.deg2rad(self.ang)
        A        = np.ones((2, self.K), dtype=np.complex64)
        # Standard: -1j * pi * sin(theta) -> Calibrated: -1j * 2 * pi * d_over_lambda * sin(theta)
        A[1]     = np.exp(-2j * np.pi * self.d_l * np.sin(theta)).astype(np.complex64)
        self.A_H = np.ascontiguousarray(np.conj(A).T)

        # Pre-allocated single-block buffers
        self.X    = np.zeros((self.N, 2),       dtype=np.complex64)
        self.X_c  = np.zeros((self.N, 2),       dtype=np.complex64)
        self.D    = np.zeros((self.K, self.N),  dtype=np.complex64)
        self.W    = np.zeros((self.K, 2),       dtype=np.complex64)
        self.Y    = np.zeros((self.K, self.N),  dtype=np.complex64)
        self.E    = np.zeros((self.K, self.N),  dtype=np.complex64)
        self.dW   = np.zeros((self.K, 2),       dtype=np.complex64)
        self.nsq  = np.zeros(self.K,            dtype=np.float32)

    def work(self, input_items, output_items):
        in0 = input_items[0]
        in1 = input_items[1]
        out_vector = output_items[0]
        out_scalar = output_items[1]
        
        n_output = len(out_vector)
        
        for i in range(n_output):
            start = i * self.N
            end = start + self.N
            
            self.X[:, 0] = in0[start:end]
            self.X[:, 1] = in1[start:end]
            np.conj(self.X, out=self.X_c)

            power = np.sum(self.X.real**2 + self.X.imag**2) / self.N + 1e-6
            scale = self.mu / (np.float32(self.P) * power)

            np.dot(self.A_H, self.X.T, out=self.D)

            self.W[:] = 0.0
            for _ in range(self.P):
                np.dot(self.W, self.X.T, out=self.Y)
                np.subtract(self.D, self.Y, out=self.E)
                np.dot(self.E, self.X_c, out=self.dW)
                self.dW *= scale
                self.W  += self.dW

            # Calculate norms and write directly to the spectrum vector output
            np.sum(self.W.real**2 + self.W.imag**2, axis=1, out=self.nsq)
            np.sqrt(self.nsq, out=out_vector[i])

            # Extract peak angle and assign it to the scalar output port
            max_idx = np.argmax(out_vector[i])
            peak_deg = self.ang[max_idx]
            out_scalar[i] = peak_deg  # Sends precise float degree (e.g., 30.0)

        self._cnt += n_output
        if self._cnt >= 500:
            self._cnt = 0
            print(f"[NLMS Terminal] Calibrated Peak: {out_scalar[-1]:.1f}°")

        return n_output
