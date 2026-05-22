import numpy as np
from gnuradio import gr

class nlms_doa(gr.decim_block):
    def __init__(self, num_signals=1, num_angles=181, num_snapshots=100, step_size=0.2):
        gr.decim_block.__init__(
            self,
            name='optimized code NLMS for DoA',
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
        
        # Precompute Hermitian (conjugate transpose) of the steering matrix
        # steering_matrix is (2, K), so A_H becomes (K, 2)
        A_H = np.conj(self.steering_matrix).T
        
        for i in range(n_output):
            # Extract N snapshots for this block processing step 
            x0 = in0[i*self.N : (i+1)*self.N]
            x1 = in1[i*self.N : (i+1)*self.N]
            
            # Stack into an (N, 2) matrix
            X = np.column_stack([x0, x1]).astype(np.complex128)
            
            # Initialize weight vectors for ALL K angles simultaneously: shape (K, 2)
            W = np.zeros((self.K, 2), dtype=np.complex128)
            
            # Precompute desired signal 'd' for all angles across all snapshots
            # Matrix multiply: (K, 2) x (2, N) -> Resulting shape is (K, N)
            D_matrix = A_H @ X.T
            
            # Loop ONLY over the snapshots (100 steps instead of 18,100!)
            for n in range(self.N):
                x_n = X[n]  # Current 2-element snapshot vector: shape (2,)
                
                # Compute filter output y = w^H * x_n for all K angles simultaneously
                # Row-wise dot product via broadcasting and summing along columns
                Y = np.sum(np.conj(W) * x_n, axis=1)  # shape (K,)
                
                # Extract desired signal vector for this snapshot step
                D = D_matrix[:, n]  # shape (K,)
                
                # Scalar error for all angles
                E = D - Y  # shape (K,)
                
                # Squared norm of the input vector (scalar, identical across all angles)
                xns = np.sum(np.abs(x_n)**2) + 1e-10
                
                # Fully vectorized NLMS weight update rule across all angles
                # (K, 1) matrix multiplied by (1, 2) matrix updates the (K, 2) weight matrix instantly
                W += (self.u / xns) * (np.conj(E)[:, None] * x_n[None, :])
            
            # Compute Euclidean norm of final weights for each angle out of the loop
            norms = np.linalg.norm(W, axis=1)
            
            # Normalize the spectrum so the peak equals 1.0 (0 dB)
            '''max_norm = np.max(norms)
            if max_norm > 0:
                norms /= max_norm'''
                
            out[i][:] = norms
            
        if n_output > 0:
            max_idx = np.argmax(out[-1])
            print(f"NLMS Peak detected at: {self.angles[max_idx]:.1f}°")
            
        return n_output
