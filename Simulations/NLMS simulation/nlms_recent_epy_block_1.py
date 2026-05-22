import numpy as np
from gnuradio import gr

class bartlett_doa(gr.decim_block):
    def __init__(self, num_angles=181, num_snapshots=30):
        # We inherit from decim_block and set the decimation factor to num_snapshots
        gr.decim_block.__init__(
            self,
            name='Bartlett DoA',
            in_sig=[np.complex64, np.complex64],
            out_sig=[(np.float32, num_angles)],
            decim=num_snapshots
        )
        self.K = num_angles
        self.N = num_snapshots
        
        # Precompute angles and steering matrix to make the block fast
        self.angles = np.linspace(-90, 90, self.K)
        self.steering_matrix = np.zeros((2, self.K), dtype=np.complex128)
        for k in range(self.K):
            theta = np.deg2rad(self.angles[k])
            # For half-wavelength antenna spacing (d = lambda / 2)
            self.steering_matrix[:, k] = [1.0, np.exp(-1j * np.pi * np.sin(theta))]

    def work(self, input_items, output_items):
        in0 = input_items[0]
        in1 = input_items[1]
        out = output_items[0]
        
        # Determine how many output vectors the scheduler wants us to fill
        n_output = len(out)
        
        for i in range(n_output):
            # Extract the correct window of N snapshots for this output step
            x0 = in0[i*self.N : (i+1)*self.N]
            x1 = in1[i*self.N : (i+1)*self.N]
            
            X = np.vstack([x0, x1]).astype(np.complex128)
            
            # Calculate the Sample Covariance Matrix R
            R = (X @ X.conj().T) / self.N
            
            # Compute Bartlett power spectrum
            powers = np.zeros(self.K, dtype=np.float32)
            for k in range(self.K):
                a = self.steering_matrix[:, k]
                p = np.real(a.conj().T @ R @ a)
                powers[k] = p
            
            # Normalize to 1.0 so the peak matches 0 dB on your plot
            max_p = np.max(powers)
            if max_p > 0:
                powers /= max_p
            
            out[i][:] = powers
            
        # Print the peak from the most recent window to the console
        if n_output > 0:
            max_idx = np.argmax(out[-1])
            print(f"Peak detected at: {self.angles[max_idx]:.1f}°")
            
        return n_output
