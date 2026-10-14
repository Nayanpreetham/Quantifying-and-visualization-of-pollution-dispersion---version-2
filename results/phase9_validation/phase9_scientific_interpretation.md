# Phase 9 — Scientific Interpretation of Model Outputs & Theoretical Limitations

**Document Reference:** `results/phase9_validation/phase9_scientific_interpretation.md`  
**Project:** 2D Grid-to-Grid Pollution Dispersion Model for India  
**Auditor:** Independent Scientific Audit Agent (Phase 9)  
**Date:** 2026-10-14  

---

## 1. Fundamental Distinction Between Key Model Quantities

To maintain scientific integrity and prevent misleading environmental claims, three distinct mathematical quantities produced by this system must never be conflated:

```
+-----------------------------------------------------------------------------------------------------------------------+
|                                        THREE TIERS OF MODEL VARIABLES                                                 |
+-------------------+----------------------------+-----------------+----------------------------------------------------+
| Tier / Quantity   | Mathematical Symbol        | Physical Units  | Scientific Meaning                                 |
+-------------------+----------------------------+-----------------+----------------------------------------------------+
| 1. Ground Ambient | PM2.5_obs(s, t)            | µg/m³           | In-situ ground measurement at an official station. |
|    Observation    |                            |                 | Real, empirical physical data.                     |
+-------------------+----------------------------+-----------------+----------------------------------------------------+
| 2. Transport      | T(src, dest, t, dt)        | Dimensionless   | Kinematic fraction of Lagrangian ensemble parcels  |
|    Fraction       |                            | (0.0 to 1.0)    | originating at source and arriving in dest cell.   |
+-------------------+----------------------------+-----------------+----------------------------------------------------+
| 3. Transported    | I = PM2.5_src * T          | µg/m³           | Advective source-weighted potential contribution.  |
|    Influence      |                            | (Equivalent)    | NOT destination ambient concentration!             |
+-------------------+----------------------------+-----------------+----------------------------------------------------+
```

### Critical Scientific Principle:
> [!CAUTION]
> **Transported Pollution Influence ($I$) MUST NEVER be reported as predicted or validated destination $\text{PM}_{2.5}$ ambient concentration.**  
> 
> A destination grid cell (e.g. in rural Bihar or Uttar Pradesh) has its own complex local emission sources (traffic, crop burning, domestic cooking stoves, brick kilns) and background regional loading.  
> The quantity $I = \text{PM}_{2.5}^{\text{src}} \times T$ represents **ONLY the theoretical parcel of mass advected from that specific monitored source node**. It does not represent total ambient air quality at the receptor.

---

## 2. Core Physics Assumptions and Boundary Limitations

### 1. Pure 2D Horizontal Surface Kinematics
* **Implementation:** Trajectories are integrated using ECMWF ERA5 10-meter horizontal wind components ($U_{10}, V_{10}$).
* **Limitation:** The real atmosphere is 3-dimensional. Pollutants are subject to vertical wind shear, convective updrafts, nocturnal surface inversions, and planetary boundary layer height (PBLH) compression.
* **Implication:** The 2D surface model assumes the pollution remains well-mixed within the surface layer and follows surface streamlines. It cannot capture elevated plume transport above the boundary layer or vertical subsidence.

### 2. Stochastic Ensemble Perturbations as Sub-Grid Eddy Diffusion
* **Implementation:** An ensemble of $N=20$ members is generated with Gaussian velocity perturbations ($\sigma_w = 0.4\text{ m/s}$, $\sigma_\theta = 12^\circ$) and a lower bound $\max(0.2, w_{\text{pert}})$.
* **Limitation:** This is a simplified parametric representation of turbulent dispersion. It does not solve Monin-Obukhov surface-layer similarity theory or calculate Pasquill-Gifford atmospheric stability classes.
* **Implication:** The ensemble provides an envelope of plausible horizontal transport pathways, but does not capture localized micro-meteorological eddies or building wake effects.

### 3. Coarse Spatial Discretization (0.25° Regular Grid)
* **Implementation:** The computational domain is discretized into regular $0.25^\circ \times 0.25^\circ$ cells ($\approx 27.8\text{ km}$ north-south, $\approx 24.5\text{--}27.5\text{ km}$ east-west).
* **Limitation:** Spatial variations smaller than $\sim 25\text{ km}$ (e.g. roadside gradients, industrial stack plumes, urban vs rural contrasts) are averaged across the containing grid cell.
* **Implication:** Small displacements ($< 13\text{ km}$) snap to the home cell node. Transport matrices reflect regional corridor exchange rather than intra-urban dispersion.

### 4. Sparse Ground Monitoring Network
* **Implementation:** Pilot simulations utilize 10 ground monitoring stations active in the selected temporal window.
* **Limitation:** India has over 16,000 grid cells, of which only a small fraction contain active monitoring stations. Large areas between urban centers act as receptor cells but lack monitored source terms.
* **Implication:** Source-to-destination transport matrices currently map known monitored urban nodes to receptor cells. They do not constitute an India-wide comprehensive emissions inventory.

### 5. Absence of Chemical Transformation and Deposition
* **Implementation:** The model treats $\text{PM}_{2.5}$ mass as a conservative, passive tracer.
* **Limitation:** In the real atmosphere:
  * Aerosols undergo chemical reactions (gas-to-particle conversion, secondary sulfate/nitrate formation).
  * Particles undergo dry deposition (gravitational settling, surface impaction) and wet deposition (scavenging by rainfall).
  * Particulate lifetime in the boundary layer typically ranges from 24 to 72 hours.
* **Implication:** Over 24-hour windows, the model represents the *potential kinematic reach* of emissions. In areas of heavy precipitation or high deposition, actual transported mass would be lower than the purely kinematic estimate.

---

## 3. Clear Boundaries: What the Model Can and Cannot Conclude

```
+-----------------------------------------------------------------------------------------------------------------------+
|                                         MODEL CAPABILITIES & STRICT BOUNDARIES                                        |
+-------------------------------------------------------+---------------------------------------------------------------+
| VALID SCIENTIFIC APPLICATIONS                         | INVALID / UNSUPPORTED CLAIMS                                  |
+-------------------------------------------------------+---------------------------------------------------------------+
| Identifying downwind regional transport corridors     | Forecasting ambient AQI or PM2.5 for unmonitored citizens     |
| Calculating directional source-to-receptor fractions  | Attributing total ambient pollution to a single source city   |
| Evaluating kinematic plume reach across time windows  | Claiming real-world predictive accuracy without receptor val  |
| Quantifying regional transboundary connectivity       | Modeling chemical transformation or secondary aerosol mass    |
+-------------------------------------------------------+---------------------------------------------------------------+
```

---

## 4. Summary for Decision-Makers

The 2D Grid-to-Grid Pollution Dispersion Model is a **computational transport-pathway analysis tool**, not an air quality forecasting system. Its outputs must be communicated strictly as **kinematic source-receptor transport matrices** and **source-weighted transport footprints**.
