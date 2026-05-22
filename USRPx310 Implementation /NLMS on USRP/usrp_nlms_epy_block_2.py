import numpy as np
from gnuradio import gr

class nlms_doa(gr.decim_block):
    def __init__(self, num_signals=1, num_angles=91, num_snapshots=50, step_size=0.2):
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
            
            for n in range(self.N):
                x_n = X[n]               # Shape: (2,)
                x_n_conj = np.conj(x_n)  # Shape: (2,)
                
                # 1. ACTUAL ESTIMATE: y = w^H * x  -> maps to C BLAS: W_c @ x_n
                Y = W_c @ x_n 
                
                # 2. THE ERROR: e = d - y
                E = D_matrix[:, n] - Y
                
                # 3. Input Power: ||x||^2
                xns = np.real(x_n_conj @ x_n) + 1e-10
                
                # 4. WEIGHT UPDATE: w = w + mu * e * x / power
                # Using np.outer(E, x_n_conj) applies this to all 181 angles instantly
                W_c += (self.u / xns) * np.outer(E, x_n_conj)
            
            # Norm of W_c is identical to norm of W
            norms = np.linalg.norm(W_c, axis=1)
                
            out[i][:] = norms
            
        if n_output > 0:
            max_idx = np.argmax(out[-1])
            print(f"NLMS Peak detected at: {self.angles[max_idx]:.1f}°")
            
        return n_output
            
        if n_output > 0:
            max_idx = np.argmax(out[-1])
            print(f"Block-NLMS Peak detected at: {self.angles[max_idx]:.1f}°")
            
        return n_output
