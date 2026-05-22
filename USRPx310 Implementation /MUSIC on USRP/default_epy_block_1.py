"""
music_doa_block.py
------------------
MUSIC Direction-of-Arrival embedded Python block for GNU Radio.

Signal model — 2-element ULA, d = λ/2 spacing:
    x1(t) = s(t) + n1(t)
    x2(t) = s(t)·exp(j·π·sin θ) + n2(t)

Steering vector:  a(θ) = [1,  exp(j·π·sin θ)]ᵀ

MUSIC pseudospectrum:
    P(θ) = 1 / ( aᴴ(θ) · Eₙ · Eₙᴴ · a(θ) )

The peak of P(θ) is the estimated angle of arrival.

Place this file in the same directory as music_sim.py.
"""

import numpy as np
from gnuradio import gr


class music_doa(gr.basic_block):
    """
    MUSIC DOA Estimator — 2-element ULA

    Ports
    -----
    in0  : complex64   — element 1 received signal
    in1  : complex64   — element 2 received signal
    out0 : float32[num_angles] — MUSIC pseudospectrum  (−90° … +90°)

    Parameters
    ----------
    num_snapshots : int   — samples per covariance estimate  (default 100)
    num_signals   : int   — number of signal sources         (default 1)
    num_angles    : int   — angular grid points              (default 181 → 1°/bin)
    """

    def __init__(self, num_snapshots: int = 100,
                       num_signals:   int = 1,
                       num_angles:    int = 181):

        gr.basic_block.__init__(
            self,
            name="MUSIC DOA",
            in_sig=[np.complex64, np.complex64],
            out_sig=[(np.float32, num_angles)],
        )

        self.N = num_snapshots   # snapshot count
        self.K = num_signals     # number of sources  (must be < 2)
        self.L = num_angles

        # ── Pre-compute steering matrix  A : (2, L) ────────────────
        # a(θ) = [1,  exp(j·π·sinθ)]
        angles_rad = np.deg2rad(np.linspace(-90, 90, num_angles))
        self.A = np.vstack([
            np.ones(num_angles, dtype=np.complex128),
            np.exp(1j * np.pi * np.sin(angles_rad)),
        ])  # shape (2, L)

    # ----------------------------------------------------------------
    def general_work(self, input_items, output_items):
        n_in  = min(len(input_items[0]), len(input_items[1]))
        n_out = len(output_items[0])

        # How many full spectrum vectors can we produce?
        n_produce = min(n_out, n_in // self.N)
        if n_produce == 0:
            return 0

        for i in range(n_produce):
            s = i * self.N

            # ── 1. Data matrix  X : (2, N) ──────────────────────────
            X = np.vstack([
                input_items[0][s : s + self.N],
                input_items[1][s : s + self.N],
            ]).astype(np.complex128)

            # ── 2. Sample covariance matrix  R : (2, 2) ─────────────
            R = (X @ X.conj().T) / self.N

            # ── 3. Eigendecomposition  (eigh → ascending order) ──────
            _, V = np.linalg.eigh(R)

            # ── 4. Noise subspace  Eₙ : (2, 2−K) ────────────────────
            En = V[:, : 2 - self.K]

            # ── 5. MUSIC pseudospectrum  (vectorised over all angles) ─
            #   G  = Eₙ Eₙᴴ                     (2×2 noise projector)
            #   denom[l] = aᴴ(θₗ) G a(θₗ)      (real scalar per angle)
            G     = En @ En.conj().T                     # (2, 2)
            AG    = self.A.conj().T @ G                  # (L, 2)
            denom = np.real(np.einsum("la,al->l", AG, self.A))  # (L,)
            P     = (1.0 / np.maximum(denom, 1e-10)).astype(np.float32)

            output_items[0][i] = P

        self.consume_each(n_produce * self.N)
        return n_produce
