# Final Methodology — India AQI Source-Influence Framework
*Physics-Based Lagrangian Transport-Influence Model*

---

## Scope

This is a TRANSPORT-ONLY Lagrangian source-influence model.

It answers:
"For a target location and time, which geographic source regions have the
strongest transport-pathway influence on the observed pollution signal?"

It does NOT claim to be:
- A chemical transport model (no aerosol chemistry, deposition, or lifetime)
- A mass-conserving pollution model
- A validated PM2.5 concentration predictor

---

## Mathematical Definitions

### Step 1: Backward Lagrangian Trajectory

For target (x_T, z_T, t_T), integrate backward in time using ERA5 winds:
  dx/dt = -u(x,z,t)
  dy/dt = -v(x,z,t)
  dp/dt = -omega(x,z,t)   [pressure coordinates, Pa/s]

Integration: RK4, dt=1800s (30 min), 3D pressure coordinates
Vertical levels: 500/700/850/925/1000 hPa from ERA5
AGL to pressure: ISA barometric formula (atmosphere.py)
Terrain masking: p capped at surface pressure sp at each point

### Step 2: Ensemble Trajectories

For each target/time, generate N ensemble members via perturbations:
  Spatial: 5 positions (+/-10km N/S/E/W + center)
  Vertical: 4 AGL heights (50, 100, 300, 500 m)
  Total members: up to N=20

Convergence threshold: Top-5 source ranking stable between N=10 and N=20

### Step 3: Transport Influence

T(target, source_i, t) = count(ensemble_points in source_i) / count(all_points)

This is the TRAJECTORY-BASED TRANSPORT INFLUENCE fraction.
It is NOT pollution contribution. It represents the physical transport pathway.

Normalization: sum_i T_i + T_outside_domain = 1.0

### Step 4: Periodic Disturbance Factor

D(t) = clip(
    1 + A_annual * sin(2*pi*t/P_annual + phi_annual)
      + A_diurnal * sin(2*pi*t/P_diurnal + phi_diurnal)
      + A_weekly * sin(2*pi*t/P_weekly + phi_weekly)
      + event_perturbation(t),
    D_min, D_max
)

Parameters (calibration targets, not validated):
  A_annual=0.30, phi_annual=3.665 rad (winter peak)
  A_diurnal=0.15, phi_diurnal=5.760 rad (morning peak)
  A_weekly=0.05
  D_min=0.5, D_max=2.5
  event_perturbation=0.5 during Diwali window (+/-24h)

D(t) is UNIFORM across source cells for a given target/time.
It modulates overall signal magnitude, not spatial distribution.

### Step 5: Source-Category Weighting (TRANSPORT_ONLY until emissions loaded)

When emissions data E(source_i, category, t) are available:

  SourceInfluenceIndex(target, source_i, t) =
      T(target, source_i, t) * sum_c E(source_i, c, t) * D(t)

  source_influence_fraction_i = SourceInfluenceIndex_i / sum_j SourceInfluenceIndex_j

When emissions unavailable (current state):
  source_influence_index = T(target, source_i, t)  [TRANSPORT_ONLY]

### Step 6: Domain Classification

For every trajectory point:
  - Assign to nearest 50-km grid cell (KD-tree, cutoff 0.4 deg)
  - Points beyond cutoff: classified as outside_domain
  - Country classification via world.geo.json polygon lookup

Report separately:
  India fraction, Ocean fraction, Pakistan fraction, Bangladesh fraction

A trajectory fraction in Pakistan does NOT mean Pakistan caused the pollution.
It means the air mass traveled through that region.

### Step 7: Source Ranking

For each target/time, rank all source grid cells by source_influence_index.
Report Top-1, Top-3, Top-5 with influence fractions.

---

## Limitations (to be stated in all publications)

1. Transport-only: No chemical transformation, deposition, or aerosol formation.
2. Kinematic only: No turbulent diffusion beyond initial-condition ensemble spread.
3. ERA5 resolution: ~31 km; trajectory position uncertainty ~31 km.
4. Pressure-coordinate terrain: underground masking via surface pressure, not true orography.
5. Ensemble spread represents initial-condition uncertainty, not full stochastic dispersion.
6. Emission inventory: currently unavailable; output is TRANSPORT_ONLY mode.
7. AQI data: city-level daily index; not hourly station PM2.5.
8. Periodic disturbance parameters: illustrative defaults; require calibration.
