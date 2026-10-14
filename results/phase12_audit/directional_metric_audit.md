# Phase 12 — Task 3: Audit of Directional Alignment Metric

## 1. Executive Summary & Scientific Re-Classification

Phase 11 reported a median directional alignment error of **14.2°** and a 90th-percentile error of **26.8°** between transport destination cells and wind vectors.

> [!CAUTION]
> **SCIENTIFIC CLASSIFICATION VERDICT**: This metric is an **INTERNAL CODE CONSISTENCY DIAGNOSTIC** (software verification check), **NOT AN INDEPENDENT VALIDATION** of real-world atmospheric accuracy.

### Rationale:
1. **The Reference Direction is NOT Independent**: The comparison evaluates the particle destination bearing against the **exact same ERA5 U10/V10 horizontal wind field** that was fed into the advection equations to move the particles.
2. **Circular Reasoning Warning**: Claiming that particle trajectories align with the driving wind field as evidence of 'model accuracy' merely confirms that the computer code executed $x_{t+\Delta t} = x_t + u\Delta t$ without numerical sign inversions. It provides zero evidence regarding whether the real atmosphere dispersed pollution along that pathway.
3. **Origin of Residual Angular Differences**: The observed deviation (median 14.2°) is entirely caused by:
   - **Isotropic Gaussian Diffusion**: Stochastic perturbations added to simulate ensemble spread ($N=20$).
   - **Grid Cell Quantization**: Particles are mapped to discrete $0.25^\circ \times 0.25^\circ$ (~27 km) cell centroids rather than continuous coordinates.

## 2. Mathematical Definition of Compared Quantities

In `src/phase11_validation/run_multiweek_dispersion.py`:
1. **Driving Wind Flow Vector (Vector B)**:
$$\theta_{\text{flow}} = \left(90^\circ - \text{atan2}(v_{10}, u_{10}) \times \frac{180}{\pi}\right) \pmod{360}$$
   This represents the meteorological direction towards which the ERA5 surface wind is blowing.
2. **Destination Grid Bearing (Vector A)**:
$$\theta_{\text{dest}} = \text{bearing}(\text{lat}_{\text{src}}, \text{lon}_{\text{src}}, \text{lat}_{\text{dest}}, \text{lon}_{\text{dest}})$$
   This represents the great-circle azimuth from the source monitor to the centroid of the destination grid cell.
3. **Relative Angular Deviation**:
$$\Delta \theta = \left|\left(\theta_{\text{dest}} - \theta_{\text{flow}} + 180^\circ\right) \pmod{360} - 180^\circ\right|$$

## 3. Discretization and Distance Dependence Analysis

| Distance Bin | Records | Median Deviation (°) | Mean Deviation (°) | 90th %ile Deviation (°) | Physical Cause of Deviation |
|---|---|---|---|---|---|
| Collocated (0 km) | 1509 | **0.0°** | 0.0° | 0.0° | Identical cell (d=0), delta=0 by definition |
| Local Grid (10-25 km) | 683 | **22.7°** | 24.08° | 47.12° | Grid quantization dominant |
| Sub-Regional (25-50 km) | 2929 | **19.9°** | 21.65° | 41.6° | Gaussian ensemble spread |
| Regional (50-100 km) | 5474 | **12.75°** | 14.46° | 28.4° | Gaussian ensemble spread |
| Long-Range (>100 km) | 15269 | **9.2°** | 10.65° | 22.1° | Gaussian ensemble spread |

## 4. Proper Framing for Production Documentation

For Phase 12 and future production reporting, the directional metric must be documented as:
- **Metric Name**: *Advective-Kinematic Vector Consistency Diagnostic*.
- **Purpose**: Software unit check to ensure that (a) the numerical RK4/Euler advection step correctly respects wind vector signs, (b) grid mapping preserves quadrant orientation, and (c) Gaussian diffusion does not overwhelm mean advective displacement.
- **Disallowed Claim**: Must never be described as 'validation against real-world plume observations'.