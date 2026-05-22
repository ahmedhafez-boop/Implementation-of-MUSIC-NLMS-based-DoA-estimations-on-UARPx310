"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr


class nlms_doa(gr.basic_block):  # other base classes are basic_block, decim_block, interp_block
    """Embedded Python Block example - a simple multiply const"""

    def __init__(self, num_signals = 1, num_angles = 181, num_snapshots=100, step_size = 0.2 ):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.basic_block.__init__(
            self,
            name='NLMS for DoA',   # will show up in GRC
            in_sig=[np.complex64, np.complex64],
            out_sig=[(np.float32, num_angles)],# vector of K floats, not a scalar stream
           
            )
        # if an attribute with the same name as a parameter is found,
        # a callback is registered (properties work, too).
        self.M = num_signals
        self.K = num_angles
        self.N = num_snapshots
        self.u = step_size
        
    def steer(self,theta_deg):
        theta = np.deg2rad(theta_deg)
        
        return np.array([ 1.0, np.exp(-1j * np.pi * np.sin(theta))], dtype=np.complex128)
        
    def general_work(self, input_items, output_items):
        available = min(len(input_items[0]), len(input_items[1]))


        if available < self.N:
            return 0
        X = np.column_stack([
            input_items[0][:self.N].astype(np.complex128),
            input_items[1][:self.N].astype(np.complex128)
            ])
        angles = np.linspace(-90, 90, self.K)   # [-90°, -89°, ..., 90°]
        norms = np.zeros(self.K, dtype=np.float32)
        powers = np.zeros(self.K, dtype=np.float32)
        for k in range(self.K):
            w = np.zeros(2, dtype=np.complex128)
            power_acc = 0.0
            a_k = self.steer(angles[k])
            for n in range(self.N):
                d = np.conj(a_k) @ X[n]  # inner product → scalar ✓  (a^H · x_n)
                y = np.conj(w) @ X[n]
                e = d - y     # scalar error ✓             (d - ŵ^H · x_n)
                xns = np.linalg.norm(X[n])**2 + 1e-10
                w += (self.u/(xns))* (e.conj())* X[n]
                power_acc += np.abs(y)**2
            powers[k] = power_acc / self.N
            '''norms[k] = np.linalg.norm(w)    # real-valued scalar ✓
        output_items[0][0][:] = norms
        print(output_items[0][0][:])'''
                

        print(np.max(powers), np.min(powers))
        print(np.argmax(powers))    
        output_items[0][0][:] = powers
        
        return 1
