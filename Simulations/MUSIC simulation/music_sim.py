#!/usr/bin/env python3
"""
music_sim.py
------------
Complete GNU Radio MUSIC DOA simulation.

Usage
-----
    python3 music_sim.py

Dependencies
------------
    gnuradio >= 3.9, PyQt5, numpy
    music_doa_block.py  — must be in the same directory

Flowgraph overview
------------------

  sig_source_c ──────────────────────┬──► add1 ─────────────────►┐
  (complex cosine, 3 kHz)            │  ▲                         │
                                     │  noise1                    │
                                     │                            ├─► music_doa ─► vector_sink (spectrum plot)
                                     └──► multiply_const_cc ──► add2 ──────────►┘           │
                                            (spatial phase          ▲             └──► argmax ──► angle display
                                             e^{jπ sin θ})          noise2

The true DOA angle is set by DOA_DEG (default 30°).
The QT slider lets you change it live without restarting.
"""

import sys
import numpy as np
from gnuradio import gr, blocks, analog, qtgui
from PyQt5 import Qt
import sip

# ── local MUSIC block ──────────────────────────────────────────
from music_doa_block import music_doa


# ═══════════════════════════════════════════════════════════════
#  Tunable parameters
# ═══════════════════════════════════════════════════════════════
SAMP_RATE     = 50_000       # Sa/s
SIGNAL_FREQ   =  3_000       # Hz
SIGNAL_AMP    =  0.5         # signal amplitude
NOISE_AMP     =  0.3         # complex noise amplitude  (SNR ≈ 4.4 dB)
DOA_DEG       =  30.0        # initial true angle of arrival (−90 … +90)
NUM_SNAPSHOTS =  100         # covariance estimation window (snapshots)
NUM_ANGLES    =  181         # angle bins: −90°…+90° at 1°/bin
# ═══════════════════════════════════════════════════════════════


class MusicSim(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "MUSIC DOA Simulation")
        Qt.QWidget.__init__(self)
        self.setWindowTitle("MUSIC DOA — GNU Radio Simulation")

        self._doa_deg = float(DOA_DEG)

        # ── signal (complex sinusoid, shared by both array elements) ──
        self.sig = analog.sig_source_c(
            SAMP_RATE, analog.GR_COS_WAVE, SIGNAL_FREQ, SIGNAL_AMP
        )

        # ── element 2 phase shift  exp(j·π·sin θ) ────────────────────
        psi = np.pi * np.sin(np.deg2rad(self._doa_deg))
        self.phase_shift = blocks.multiply_const_cc(np.exp(1j * psi))

        # ── independent complex Gaussian noise ───────────────────────
        self.n1 = analog.noise_source_c(analog.GR_GAUSSIAN, NOISE_AMP, seed=42)
        self.n2 = analog.noise_source_c(analog.GR_GAUSSIAN, NOISE_AMP, seed=99)

        # ── combine signal + noise for each element ───────────────────
        self.add1 = blocks.add_cc()   # element 1 :  s(t) + n1(t)
        self.add2 = blocks.add_cc()   # element 2 :  s(t)·e^{jψ} + n2(t)

        # ── MUSIC estimator ───────────────────────────────────────────
        self.music = music_doa(
            num_snapshots=NUM_SNAPSHOTS,
            num_signals=1,
            num_angles=NUM_ANGLES,
        )

        # ── argmax → estimated angle ──────────────────────────────────
        self.argmax  = blocks.argmax_fs(NUM_ANGLES)   # output: index (short)
        self.s2f     = blocks.short_to_float(1, 1.0)  # short → float
        self.ang_off = blocks.add_const_ff(-90.0)     # index → angle (°)
        # null-sink the unused second argmax output
        self.null    = blocks.null_sink(gr.sizeof_short)

        # ── QT GUI: MUSIC spectrum plot ───────────────────────────────
        self.vec_sink = qtgui.vector_sink_f(
            NUM_ANGLES,               # vector length
            -90,                      # x-axis start (degrees)
            1,                        # x-axis step  (1°/bin)
            "Angle (°)",             # x-axis label
            "Pseudospectrum power",   # y-axis label
            "MUSIC Spectrum",         # plot title
            1,                        # number of inputs
            None,                     # parent widget
        )
        self.vec_sink.enable_autoscale(True)
        self.vec_sink.set_line_label(0, "P(θ)")
        self.vec_sink.set_line_width(0, 2)

        # ── QT GUI: estimated DOA number ──────────────────────────────
        self.num_sink = qtgui.number_sink(
            gr.sizeof_float,
            0.0,
            qtgui.NUM_GRAPH_HORIZ,
            1,
            None,
        )
        self.num_sink.set_update_time(0.10)
        self.num_sink.set_title(0, f"Estimated DOA (°)   [true = {DOA_DEG}°]")
        self.num_sink.set_min(0, -90)
        self.num_sink.set_max(0,  90)

        # ── QT layout ─────────────────────────────────────────────────
        self._build_gui()

        # ── connect the flowgraph ─────────────────────────────────────
        self._connect()

    # ------------------------------------------------------------------
    def _build_gui(self):
        """Assemble the Qt window: slider + spectrum + angle readout."""
        vec_w = sip.wrapinstance(self.vec_sink.pyqwidget(), Qt.QWidget)
        num_w = sip.wrapinstance(self.num_sink.pyqwidget(), Qt.QWidget)

        # ── DOA slider ────────────────────────────────────────────────
        slider_label = Qt.QLabel(f"True DOA Angle: {int(DOA_DEG)}°")
        slider_label.setAlignment(Qt.Qt.AlignCenter)

        self._slider_label = slider_label

        slider = Qt.QSlider(Qt.Qt.Horizontal)
        slider.setMinimum(-90)
        slider.setMaximum( 90)
        slider.setValue(int(DOA_DEG))
        slider.setTickInterval(10)
        slider.setTickPosition(Qt.QSlider.TicksBelow)
        slider.valueChanged.connect(self._on_angle_changed)

        slider_row = Qt.QHBoxLayout()
        slider_row.addWidget(Qt.QLabel("-90°"))
        slider_row.addWidget(slider)
        slider_row.addWidget(Qt.QLabel("+90°"))

        layout = Qt.QVBoxLayout()
        layout.addWidget(slider_label)
        layout.addLayout(slider_row)
        layout.addWidget(vec_w, stretch=4)
        layout.addWidget(num_w, stretch=1)
        self.setLayout(layout)
        self.resize(900, 700)

    # ------------------------------------------------------------------
    def _connect(self):
        """Wire up all GNU Radio blocks."""
        # element 1:  sig + n1
        self.connect(self.sig,  (self.add1, 0))
        self.connect(self.n1,   (self.add1, 1))

        # element 2:  sig → phase shift → add; noise → add
        self.connect(self.sig,         self.phase_shift)
        self.connect(self.phase_shift, (self.add2, 0))
        self.connect(self.n2,          (self.add2, 1))

        # MUSIC: element 0 → in0,  element 1 → in1
        self.connect(self.add1, (self.music, 0))
        self.connect(self.add2, (self.music, 1))

        # MUSIC output → spectrum plot
        self.connect(self.music, self.vec_sink)

        # MUSIC output → argmax → float → offset → angle display
        self.connect(self.music,          self.argmax)
        self.connect((self.argmax, 0),    self.s2f)
        self.connect(self.s2f,            self.ang_off)
        self.connect(self.ang_off,        self.num_sink)

        # sink the unused argmax port 1
        self.connect((self.argmax, 1), self.null)

    # ------------------------------------------------------------------
    def _on_angle_changed(self, angle_deg: int):
        """Qt slot: update spatial phase when slider moves."""
        self._doa_deg = float(angle_deg)
        self._slider_label.setText(f"True DOA Angle: {angle_deg}°")
        psi = np.pi * np.sin(np.deg2rad(self._doa_deg))
        self.phase_shift.set_k(np.exp(1j * psi))


# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = Qt.QApplication(sys.argv)
    tb  = MusicSim()
    tb.show()
    tb.start()
    try:
        app.exec_()
    finally:
        tb.stop()
        tb.wait()
