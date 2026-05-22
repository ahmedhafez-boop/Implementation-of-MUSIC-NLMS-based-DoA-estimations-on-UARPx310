import numpy as np
from gnuradio import gr

class nlms_doa(gr.decim_block):
    def __init__(self, num_signals=1, num_angles=181, num_snapshots=100, step_size=0.2):
        gr.decim_block.__init__(
            self,
            name='New NLMS for DoA',
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
        
        for i in range(n_output):
            # Extract N snapshots for this block processing step 
            x0 = in0[i*self.N : (i+1)*self.N]
            x1 = in1[i*self.N : (i+1)*self.N]
            
            # Stack into an (N, 2) array so X[n] gives a 2-element row snapshot vector
            X = np.column_stack([x0, x1]).astype(np.complex128)
            
            norms = np.zeros(self.K, dtype=np.float32)
            
            # Outer loop over the elements of searching set Theta 
            for k in range(self.K):
                w = np.zeros(2, dtype=np.complex128)  # Initialization of weights to 0 
                a_k = self.steering_matrix[:, k]
                
                # Inner loop over snapshots
                for n in range(self.N):
                    x_n = X[n]
                    
                    # Target steering calculation: d = a^H * X_n 
                    d = np.conj(a_k) @ x_n
                    
                    # Filter output: y = w^H * X_n
                    y = np.conj(w) @ x_n
                    
                    # Scalar error calculation
                    e = d - y
                    
                    # Squared norm of the input vector: ||X_n||^2
                    xns = np.sum(np.abs(x_n)**2) + 1e-10
                    
                    # NLMS Weight Update formula 
                    w += (self.u / xns) * np.conj(e) * x_n
                
                # Store Euclidean norm of final weights for this angle
                norms[k] = np.linalg.norm(w)
            
            # Optional: Normalize the spectrum so the peak equals 1.0 (0 dB)
            max_norm = np.max(norms)
            if max_norm > 0:
                norms /= max_norm
                
            out[i][:] = norms
            
        if n_output > 0:
            max_idx = np.argmax(out[-1])
            print(f"NLMS Peak detected at: {self.angles[max_idx]:.1f}°")
            
        return n_output
