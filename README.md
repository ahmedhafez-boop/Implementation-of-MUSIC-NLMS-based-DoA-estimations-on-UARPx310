# Direction of Arrival (DoA) Estimation on USRP X310 (MUSIC & NLMS)

This repository documents and implements an end-to-end, **research-oriented** workflow for **real-time Direction of Arrival (DoA)** estimation using a **two-channel USRP X310** and a **two-element antenna array**.

The work compares two families of DoA estimators:

- **MUSIC (Multiple Signal Classification)**: a classic high-resolution method based on estimating a covariance matrix and separating “signal” vs “noise” structure.
- **NLMS (Normalized Least Mean Squares)**: an adaptive method that updates weights sample-by-sample and can be attractive for real-time SDR use due to lower computational overhead.

The emphasis of this project is not only algorithm implementation, but also the **practical engineering details** that determine whether DoA estimation works reliably on real hardware: phase calibration, overflow events, simulation pitfalls, and the trade-offs between accuracy and real-time constraints.

---

## What problem is being solved?

When a radio signal arrives at two spatially separated antennas, it reaches one antenna slightly before the other. For narrowband signals, that time delay is usually observed as a **phase difference** between the two received channels.

If you know the antenna spacing and the carrier wavelength, that phase difference can be mapped to an **Angle of Arrival / Direction of Arrival (DoA)**.

In practice, real systems are messy:

- Hardware channels may have unknown **static phase offsets**.
- Streaming can drop samples due to host/transport limitations (e.g., **UHD overflows**).
- Indoor reflections create **multipath**, distorting the ideal two-antenna phase relationship.

This repo is built around addressing these realities, not just running textbook simulations.

---

## Project pipeline (three-stage validation)

This work follows a research-style validation pipeline:

### 1) MATLAB Monte‑Carlo baseline
Before running anything on SDR hardware, the algorithms are tested in MATLAB using Monte‑Carlo trials.

The purpose of this stage is to establish “expected behavior” under controlled assumptions (ideal array model, AWGN, controllable SNR).

Key sweeps include:

- **SNR sweep**: how performance improves as noise decreases.
- **Snapshot count sweep (N)**: how performance improves when you average more data.
- **NLMS step-size sweep (μ)**: how stability and accuracy depend on adaptation aggressiveness.

This stage answers: *“Under ideal conditions, should this algorithm work, and what parameters matter most?”*

### 2) GNU Radio software simulation (signal-chain verification)
After MATLAB, the estimators are re-implemented as GNU Radio flowgraphs.

This step is crucial because it verifies the **real signal-chain implementation** (vectorization, buffering, windowing, data types, rate handling) before any hardware is involved.

A controlled test signal is split into two channels and a known phase offset is introduced so the “true” DoA is known. AWGN is then added.

**Important pitfall documented in this project:**

- If you reuse the **same noise source** in both channels during simulation, the noise becomes correlated.
- MUSIC relies heavily on correct “noise behavior” assumptions; correlated noise can artificially improve/ruin results and lead to misleading conclusions.

This stage answers: *“Is the SDR-style implementation correct before plugging in the USRP?”*

### 3) USRP X310 hardware experiment (real-time measurement)
Finally, the same flowgraphs are run on live USRP X310 samples.

This stage captures real-world issues and measures end-to-end DoA accuracy for true angles spanning approximately **−60° to +60°**.

It also documents and discusses the dominant hardware limitations encountered.

This stage answers: *“Does it still work on real hardware, and why does it fail when it fails?”*

---

## Intuition: how the estimators behave

### MUSIC (high resolution, but needs good statistics)
Think of MUSIC as a method that tries to learn the “shape” of the data by averaging snapshots into a covariance matrix.

- With **more snapshots**, the covariance estimate becomes more reliable.
- With **higher SNR**, the separation between the signal structure and the noise structure becomes clearer.

MUSIC can give very sharp peaks (high angular resolution), but it is sensitive to:

- poor covariance estimates (too few snapshots),
- channel mismatch / phase calibration errors,
- assumptions violated in practice (correlated noise, multipath, dropped samples).

### NLMS (adaptive and lightweight)
NLMS is an adaptive approach that updates a weight vector iteratively.

- It is naturally “streaming-friendly” because it processes samples/snapshots sequentially.
- It depends strongly on the **step size μ**: too small → slow convergence; too large → instability or jitter.

In this project’s measured trials, NLMS showed slightly better average error than MUSIC, suggesting it may be less fragile under certain hardware impairments.

---

## Hardware calibration (why it matters)

DoA depends on **relative phase** between channels. The USRP X310 has two receiver chains that can introduce a fixed, unknown phase offset between channels.

A practical calibration approach used here is:

1. Feed the *same* reference tone to both channels (splitter).
2. Measure the channel-to-channel complex ratio.
3. Save it as a correction factor and apply it to subsequent measurements.

**Key insight:** even small residual phase errors can translate directly into degrees of DoA bias—especially near broadside (around 0°), where the mapping can be very sensitive.

---

## Practical challenges observed (and why they matter)

### 1) UHD Receive overflow (“O” events)
An overflow means the host did not keep up with the incoming stream, so samples are dropped.

Why this hurts DoA estimation:

- Dropped samples break the continuity of the buffer used for estimation.
- Phase relationships can appear to “jump,” corrupting the measured inter-channel phase.

Mitigations used in this work include:

- reducing sample rate,
- reducing the number of snapshots per estimate,
- reducing the angle search grid size,
- discarding buffers/windows that contain overflow indicators.

### 2) Noise coupling in simulation
A single shared AWGN source for both channels creates artificial correlation and can bias MUSIC results. The fix is simply to use **independent noise sources per channel**.

### 3) Indoor multipath
Reflections create multiple arriving paths, so the “single plane wave” model becomes imperfect. This typically increases error and can produce outliers.

---

## Summary of measured results (USRP X310)

Using true angles spanning approximately **−60° to +60°**:

- **MUSIC:** MAE ≈ **2.45°**, RMSE ≈ **2.91°**
- **NLMS:** MAE ≈ **1.63°**, RMSE ≈ **2.00°**

A notable NLMS outlier occurred near **30°**, suspected to coincide with an overflow event during that run.

---

## Reproducibility notes

To reproduce similar experiments you typically need:

- **MATLAB** (for the Monte‑Carlo baseline).
- **GNU Radio + Python** (for simulations and algorithm blocks).
- **UHD drivers + USRP X310** (for hardware runs).

Real-time stability depends strongly on your host machine, OS scheduling, transport (1GbE vs 10GbE), and buffer settings. If you see frequent overflows, reduce sample rate and processing load first.

---

## References

- R. O. Schmidt, “Multiple emitter location and signal parameter estimation,” *IEEE Transactions on Antennas and Propagation*, 1986.  
- G. Bakhshi and K. Shahtalebi, “Role of the NLMS Algorithm in Direction of Arrival Estimation for Antenna Arrays,” *IEEE Communications Letters*, 2018.

---

## License

No license file is currently included. If you plan to share or reuse the code broadly, consider adding a license (e.g., MIT, BSD-3-Clause, GPLv3) that matches your intended usage.
