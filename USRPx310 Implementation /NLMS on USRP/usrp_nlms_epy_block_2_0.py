import numpy as np
from gnuradio import gr

class nlms_doa(gr.decim_block):
    def __init__(self, num_signals=1, num_angles=181, num_snapshots=50, step_size=0.2):
        gr.decim_block.__init__(
            self,
            name='ultra lightweight Block-NLMS for DoA',
            in_sig=[np.complex64, np.complex64],
            out_sig=[(np.float32, num_angles)],
            decim=num_snapshots
        )
        self.M = num_signals
        self.K = num_angles
        self.N = num_snapshots
        self.u = step_size

        # Precompute search angles and steering matrices
        self.angles = np.linspace(-90, 90, self.K)
        self.steering_matrix = np.zeros((2, self.K), dtype=np.complex128)
        for k in range(self.K):
            theta = np.deg2rad(self.angles[k])
            self.steering_matrix[:, k] = [1.0, np.exp(-1j * np.pi * np.sin(theta))]

    def work(self, input_items, output_items):
        in0 = input_items[0]
        in1 = input_items[1]
        out = output_items[0]
        
        n_output = len(out)
        A_H = np.conj(self.steering_matrix).T  # Shape: (K, 2)
        
        for i in range(n_output):
            # Extract the N snapshots for this block
            x0 = in0[i*self.N : (i+1)*self.N]
            x1 = in1[i*self.N : (i+1)*self.N]
            X = np.column_stack([x0, x1]).astype(np.complex128)  # Shape: (N, 2)
            
            # 1. Compute average snapshot power across the entire block instantly
            block_power = np.sum(np.abs(X)**2) / self.N + 1e-10
            
            # 2. Compute the spatial baseline matrix: (K, 2) @ (2, N) -> (K, N)
            D_matrix = A_H @ X.T
            
            # 3. CLOSED-FORM BLOCK UPDATE (Zero Loops!)
            # Instead of stepping snapshot-by-snapshot, we multiply the entire 
            # data matrices together. This maps directly to ultra-fast hardware BLAS.
            # Matrix multiply: (K, N) @ (N, 2) -> Resulting shape is (K, 2)
            W_c = (self.u / block_power) * (D_matrix @ np.conj(X))
            
            # 4. Calculate the spatial spectrum norms directly from W_c
            norms = np.linalg.norm(W_c, axis=1)
                
            out[i][:] = norms
            
        if n_output > 0:
            max_idx = np.argmax(out[-1])
            print(f"Block-NLMS Peak detected at: {self.angles[max_idx]:.1f}°")
            
        return n_output
