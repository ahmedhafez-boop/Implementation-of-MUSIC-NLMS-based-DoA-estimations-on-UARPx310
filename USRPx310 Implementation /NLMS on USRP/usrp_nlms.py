#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# Author: ahmed
# GNU Radio version: 3.10.9.2

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import analog
from gnuradio import blocks
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time
import math
import sip
import usrp_nlms_epy_block_8 as epy_block_8  # embedded python block



class usrp_nlms(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Not titled yet", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Not titled yet")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("GNU Radio", "usrp_nlms")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)

        ##################################################
        # Variables
        ##################################################
        self.u = u = 0.2
        self.samp_rate = samp_rate = 196000
        self.phase_shift = phase_shift = 38
        self.center_freq = center_freq = 2.4e9
        self.a = a = 0

        ##################################################
        # Blocks
        ##################################################

        self._phase_shift_range = qtgui.Range(-180, 180, 0.1, 38, 200)
        self._phase_shift_win = qtgui.RangeWidget(self._phase_shift_range, self.set_phase_shift, "phase_shift", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._phase_shift_win)
        self._a_range = qtgui.Range(-90, 90, 1, 0, 200)
        self._a_win = qtgui.RangeWidget(self._a_range, self.set_a, "AoA", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._a_win)
        self.uhd_usrp_source_0_0 = uhd.usrp_source(
            ",".join(('addr=192.168.10.2', '')),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,2)),
            ),
        )
        self.uhd_usrp_source_0_0.set_clock_source('internal', 0)
        self.uhd_usrp_source_0_0.set_samp_rate(samp_rate)
        _last_pps_time = self.uhd_usrp_source_0_0.get_time_last_pps().get_real_secs()
        # Poll get_time_last_pps() every 50 ms until a change is seen
        while(self.uhd_usrp_source_0_0.get_time_last_pps().get_real_secs() == _last_pps_time):
            time.sleep(0.05)
        # Set the time to PC time on next PPS
        self.uhd_usrp_source_0_0.set_time_next_pps(uhd.time_spec(int(time.time()) + 1.0))
        # Sleep 1 second to ensure next PPS has come
        time.sleep(1)

        self.uhd_usrp_source_0_0.set_center_freq(2.5e9, 0)
        self.uhd_usrp_source_0_0.set_antenna("RX2", 0)
        self.uhd_usrp_source_0_0.set_bandwidth(10e3, 0)
        self.uhd_usrp_source_0_0.set_gain(14, 0)

        self.uhd_usrp_source_0_0.set_center_freq(2.5e9, 1)
        self.uhd_usrp_source_0_0.set_antenna("RX2", 1)
        self.uhd_usrp_source_0_0.set_bandwidth(10e3, 1)
        self.uhd_usrp_source_0_0.set_gain(14, 1)
        self.uhd_usrp_sink_0_0 = uhd.usrp_sink(
            ",".join(('addr=192.168.10.2', '')),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
            "",
        )
        self.uhd_usrp_sink_0_0.set_clock_source('internal', 0)
        self.uhd_usrp_sink_0_0.set_samp_rate(samp_rate)
        _last_pps_time = self.uhd_usrp_sink_0_0.get_time_last_pps().get_real_secs()
        # Poll get_time_last_pps() every 50 ms until a change is seen
        while(self.uhd_usrp_sink_0_0.get_time_last_pps().get_real_secs() == _last_pps_time):
            time.sleep(0.05)
        # Set the time to PC time on next PPS
        self.uhd_usrp_sink_0_0.set_time_next_pps(uhd.time_spec(int(time.time()) + 1.0))
        # Sleep 1 second to ensure next PPS has come
        time.sleep(1)

        self.uhd_usrp_sink_0_0.set_center_freq(2.5e9, 0)
        self.uhd_usrp_sink_0_0.set_antenna("TX/RX", 0)
        self.uhd_usrp_sink_0_0.set_bandwidth(10e3, 0)
        self.uhd_usrp_sink_0_0.set_gain(13, 0)
        self._u_range = qtgui.Range(0, 1, 0.05, 0.2, 200)
        self._u_win = qtgui.RangeWidget(self._u_range, self.set_u, "u", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._u_win)
        self.qtgui_vector_sink_f_0_1 = qtgui.vector_sink_f(
            91,
            (-90),
            1,
            "x-Axis",
            "y-Axis",
            "",
            1, # Number of inputs
            None # parent
        )
        self.qtgui_vector_sink_f_0_1.set_update_time(0.5)
        self.qtgui_vector_sink_f_0_1.set_y_axis((-140), 10)
        self.qtgui_vector_sink_f_0_1.enable_autoscale(True)
        self.qtgui_vector_sink_f_0_1.enable_grid(False)
        self.qtgui_vector_sink_f_0_1.set_x_axis_units("")
        self.qtgui_vector_sink_f_0_1.set_y_axis_units("")
        self.qtgui_vector_sink_f_0_1.set_ref_level(0)


        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_vector_sink_f_0_1.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_vector_sink_f_0_1.set_line_label(i, labels[i])
            self.qtgui_vector_sink_f_0_1.set_line_width(i, widths[i])
            self.qtgui_vector_sink_f_0_1.set_line_color(i, colors[i])
            self.qtgui_vector_sink_f_0_1.set_line_alpha(i, alphas[i])

        self._qtgui_vector_sink_f_0_1_win = sip.wrapinstance(self.qtgui_vector_sink_f_0_1.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_vector_sink_f_0_1_win)
        self.qtgui_number_sink_0_2 = qtgui.number_sink(
            gr.sizeof_short,
            0,
            qtgui.NUM_GRAPH_HORIZ,
            1,
            None # parent
        )
        self.qtgui_number_sink_0_2.set_update_time(0.01)
        self.qtgui_number_sink_0_2.set_title("")

        labels = ['', '', '', '', '',
            '', '', '', '', '']
        units = ['', '', '', '', '',
            '', '', '', '', '']
        colors = [("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(1):
            self.qtgui_number_sink_0_2.set_min(i, -180)
            self.qtgui_number_sink_0_2.set_max(i, 180)
            self.qtgui_number_sink_0_2.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.qtgui_number_sink_0_2.set_label(i, "Data {0}".format(i))
            else:
                self.qtgui_number_sink_0_2.set_label(i, labels[i])
            self.qtgui_number_sink_0_2.set_unit(i, units[i])
            self.qtgui_number_sink_0_2.set_factor(i, factor[i])

        self.qtgui_number_sink_0_2.enable_autoscale(True)
        self._qtgui_number_sink_0_2_win = sip.wrapinstance(self.qtgui_number_sink_0_2.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_number_sink_0_2_win)
        self.qtgui_compass_0_0 = self._qtgui_compass_0_0_win = qtgui.GrCompass('NLMS AoA', 250, 0.2, True, 0,False,1,"default")
        self._qtgui_compass_0_0_win.setColors("default","red", "black", "black")
        self._qtgui_compass_0_0 = self._qtgui_compass_0_0_win
        self.top_layout.addWidget(self._qtgui_compass_0_0_win)
        self.qtgui_compass_0 = self._qtgui_compass_0_win = qtgui.GrCompass('NLMS AoA', 250, 0.2, True, 0,False,1,"default")
        self._qtgui_compass_0_win.setColors("default","red", "black", "black")
        self._qtgui_compass_0 = self._qtgui_compass_0_win
        self.top_layout.addWidget(self._qtgui_compass_0_win)
        self.epy_block_8 = epy_block_8.nlms_doa(num_angles=91, num_snapshots=30, step_size=0.2, num_passes=3, d_over_lambda=0.5)
        self.blocks_short_to_float_0 = blocks.short_to_float(1, 1)
        self.blocks_phase_shift_0_0_0 = blocks.phase_shift(phase_shift, False)
        self.blocks_argmax_xx_0_1 = blocks.argmax_fs(91)
        self.blocks_add_const_vxx_1 = blocks.add_const_ss((-45))
        self.analog_sig_source_x_0_0_1 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, 3e3, 0.5, 0, 0)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_sig_source_x_0_0_1, 0), (self.uhd_usrp_sink_0_0, 0))
        self.connect((self.blocks_add_const_vxx_1, 0), (self.blocks_short_to_float_0, 0))
        self.connect((self.blocks_argmax_xx_0_1, 0), (self.blocks_add_const_vxx_1, 0))
        self.connect((self.blocks_argmax_xx_0_1, 1), (self.qtgui_number_sink_0_2, 0))
        self.connect((self.blocks_phase_shift_0_0_0, 0), (self.epy_block_8, 1))
        self.connect((self.blocks_short_to_float_0, 0), (self.qtgui_compass_0, 0))
        self.connect((self.epy_block_8, 0), (self.blocks_argmax_xx_0_1, 0))
        self.connect((self.epy_block_8, 1), (self.qtgui_compass_0_0, 0))
        self.connect((self.epy_block_8, 0), (self.qtgui_vector_sink_f_0_1, 0))
        self.connect((self.uhd_usrp_source_0_0, 1), (self.blocks_phase_shift_0_0_0, 0))
        self.connect((self.uhd_usrp_source_0_0, 0), (self.epy_block_8, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "usrp_nlms")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_u(self):
        return self.u

    def set_u(self, u):
        self.u = u

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.analog_sig_source_x_0_0_1.set_sampling_freq(self.samp_rate)
        self.uhd_usrp_sink_0_0.set_samp_rate(self.samp_rate)
        self.uhd_usrp_source_0_0.set_samp_rate(self.samp_rate)

    def get_phase_shift(self):
        return self.phase_shift

    def set_phase_shift(self, phase_shift):
        self.phase_shift = phase_shift
        self.blocks_phase_shift_0_0_0.set_shift(self.phase_shift)

    def get_center_freq(self):
        return self.center_freq

    def set_center_freq(self, center_freq):
        self.center_freq = center_freq

    def get_a(self):
        return self.a

    def set_a(self, a):
        self.a = a




def main(top_block_cls=usrp_nlms, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
