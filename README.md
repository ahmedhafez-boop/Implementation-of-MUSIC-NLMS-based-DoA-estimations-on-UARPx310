# Real-Time Direction of Arrival (DoA) Estimation on USRP X310: MUSIC & NLMS

This repository contains a complete, end-to-end implementation and evaluation pipeline for **Direction of Arrival (DoA) estimation** using:

- **MUSIC (Multiple Signal Classification)** — a high-resolution subspace method.
- **NLMS (Normalized Least Mean Squares)** — an adaptive filtering approach inspired by Bakhshi & Shahtalebi (2018).

The project progresses through **three validated stages**:

1. **MATLAB Monte-Carlo simulations** (baseline performance sweeps).
2. **GNU Radio software simulations** (bit-exact verification with controlled phase offsets).
3. **Real-time hardware experiments** on a **two-channel USRP X310 SDR platform**.

The work was prepared as a research-style technical report and includes algorithm derivations, simulation figures, GNU Radio flowgraphs, calibration methodology, and measured results.

---

## Abstract (Project Summary)

This project designs, simulates, and implements real-time DoA estimation using MUSIC and NLMS on a two-channel USRP X310 SDR. A MATLAB Monte-Carlo study sweeps **SNR**, **snapshot count**, and **NLMS step size** to establish baselines. The algorithms are then implemented as GNU Radio flowgraphs to validate signal-chain correctness in a controlled environment. Finally, the system is executed on real hardware and evaluated for true angles from **−60° to +60°**, while documenting practical SDR challenges such as **UHD receive overflows**, **phase-calibration sensitivity**, and **noise coupling artifacts**.

Measured hardware performance:

- **MUSIC:** MAE = **2.45°**, RMSE = **2.91°**
- **NLMS:** MAE = **1.63°**, RMSE = **2.00°**

---

## Repository Contents (High-Level)

Although the repo is implementation-heavy (Python/GNU Radio + MATLAB), the structure typically includes:

- **Python** code for GNU Radio Out-Of-Tree (OOT) / embedded blocks used to compute MUSIC pseudo-spectrum and NLMS updates.
- **MATLAB** scripts for Monte-Carlo sweeps over SNR, snapshot count, and NLMS step size.
- **Report figures** (flowgraphs, outputs, measurement photos, result tables) used in the accompanying IEEE-style report.

> If you are looking for a specific part (MATLAB simulation, GNU Radio flowgraphs, or USRP execution scripts), search the repo for keywords such as `MUSIC`, `NLMS`, `Monte-Carlo`, `UHD`, or `grc`.

---

## System Model

A **two-element Uniform Linear Array (ULA)** with spacing **d** receives a narrowband source from angle **θ**.

Steering vector:

\[
\mathbf{a}(\theta)=\begin{bmatrix}1 & e^{-j\frac{2\pi d}{\lambda}\sin\theta}\end{bmatrix}^T
\]

Snapshot model:

\[
\mathbf{x}_n = \mathbf{a}(\theta)s_n + \mathbf{v}_n
\]

---

## Algorithms

### 1) MUSIC

1. Estimate covariance:

\[
\hat{\mathbf{R}}_{x} = \frac{1}{N}\sum_{n=1}^{N}\mathbf{x}_n\mathbf{x}_n^{H}
\]

2. Eigen-decompose and extract noise subspace **Eₙ**.

3. Evaluate pseudo-spectrum:

\[
P_{\mathrm{MUSIC}}(\theta)=\frac{1}{\mathbf{a}^H(\theta)\mathbf{E}_n\mathbf{E}_n^H\mathbf{a}(\theta)}
\]

4. Choose angle that maximizes \(P_{\mathrm{MUSIC}}(\theta)\).

### 2) NLMS-based DoA (Bakhshi & Shahtalebi-inspired)

For each candidate angle \(\theta^{(k)}\in\Theta\), update a weight vector \(\mathbf{w}_k[n]\):

\[
\mathbf{w}_k[n]=\mathbf{w}_k[n-1]+\frac{\mu}{\epsilon+\|\mathbf{x}_n\|_2^2}\mathbf{x}_n e_{k,n}^*
\]

After \(N\) snapshots, the DoA is estimated by:

\[
\hat{\theta}=\arg\max_{\theta^{(k)}\in\Theta}\|\mathbf{w}_k[N]\|_2
\]

---

## Performance Metrics

Across repeated trials, the following metrics are used:

- **RMSE:** \(\sqrt{\frac{1}{T}\sum_{t=1}^{T}(\hat\theta_t-\theta_0)^2}\)
- **MAE:** \(\frac{1}{T}\sum_{t=1}^{T}|\hat\theta_t-\theta_0|\)
- **Probability of Resolution (Pres):** fraction of trials with error < tolerance (e.g., 1°)

---

## MATLAB Monte-Carlo Study

A baseline Monte-Carlo evaluation was performed with **T = 500 trials** per operating point. The sweeps include:

- **SNR sweep** (e.g., MUSIC approaches sub-degree RMSE at sufficiently high SNR).
- **Snapshot count sweep** (MUSIC improves strongly with N due to covariance estimation; NLMS improves with more adaptation steps).
- **Step-size sweep** for NLMS (bowl-shaped stability/accuracy behavior).

Key observation from the study:

- Effective NLMS step sizes under tested conditions: approximately **μ ∈ [0.01, 0.1]**.

---

## GNU Radio Simulation (Software Validation)

Before running on hardware, the estimators were re-implemented in GNU Radio.

- A tone source is split into two channels.
- One channel is phase-shifted by:

\[
\psi_{\mathrm{sim}}=\frac{2\pi d}{\lambda}\sin\theta_{\mathrm{true}}
\]

- Independent AWGN sources are added to each channel.

**Important implementation note:**

- Using a *single shared noise source* across both channels creates artificial correlation and biases MUSIC by collapsing the noise subspace. Always use **independent noise sources** per channel in simulations.

---

## USRP X310 Hardware Implementation

### Calibration

The USRP X310 dual-channel front-end can introduce unknown static inter-channel phase offsets. A calibration tone is split and fed to both channels; the measured complex ratio is stored as a correction phasor and applied to subsequent receive buffers.

### Practical challenges observed

- **UHD receive overflow (“O” events):** corrupts snapshot windows and introduces phase discontinuities.
- **Phase-calibration sensitivity:** even small residual phase error can translate into angular bias.
- **Multipath reflections** in indoor environments.

Mitigations applied:

- Reduced sample rate (e.g., **5 MS/s → 1 MS/s**).
- Reduced search grid size (e.g., **181 → 91 points**).
- Discarded snapshot windows containing overflow markers.

---

## Measured Hardware Results (USRP X310)

True AoA span: **−60° to +60°**.

### MUSIC

- **MAE:** 2.45°
- **RMSE:** 2.91°

### NLMS

- **MAE:** 1.63°
- **RMSE:** 2.00°

NLMS achieved slightly lower MAE despite lower complexity; an outlier at 30° was likely associated with an overflow event.

---

## How to Cite / References

If you use or build upon this work, please cite the underlying methods:

- R. O. Schmidt, “Multiple emitter location and signal parameter estimation,” *IEEE Trans. Antennas Propag.*, 1986.
- G. Bakhshi and K. Shahtalebi, “Role of the NLMS Algorithm in Direction of Arrival Estimation for Antenna Arrays,” *IEEE Communications Letters*, 2018.

---

## Notes / Reproducibility

To reproduce results, you typically need:

- MATLAB for the Monte-Carlo sweeps.
- GNU Radio (with Python) for flowgraph execution.
- UHD drivers and a USRP X310 for hardware measurements.

Because GNU Radio + USRP setups vary across machines, you may need to adjust sample rates, buffer sizes, and CPU scheduling to avoid overflows.

---

## License

No explicit license file is currently included. If you intend others to reuse this work, consider adding an OSI-approved license (e.g., MIT, BSD-3-Clause, GPLv3) depending on your intended usage.
