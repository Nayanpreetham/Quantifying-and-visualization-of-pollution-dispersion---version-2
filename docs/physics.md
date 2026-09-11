# Physics & Meteorology Formulas

This document outlines the physical derivations used to generate inputs for the Kljun Flux Footprint Prediction model from ERA5 reanalysis data.

## 1. Wind Speed and Direction
ERA5 provides the 10-meter U and V wind components (\u10\, \10\).

**Wind Speed (ws):**
\ws = sqrt(u10^2 + v10^2)\
Units: m/s

**Wind Direction (wd):**
\wd = (270 - (180/pi) * atan2(v10, u10)) % 360\
Units: degrees (meteorological convention, angle from which the wind blows)

## 2. Friction Velocity (u*) and Monin-Obukhov Length (L)
We use the surface sensible heat flux (\sshf\) and surface latent heat flux (\slhf\) from ERA5. By ERA5 convention, downwards fluxes are positive, so heating the atmosphere is negative. We reverse the sign for standard micrometeorological convention (positive = upwards).

**Virtual Heat Flux (H_v):**
Approximated using sensible and latent heat fluxes.
\H = -sshf\
\LE = -slhf\

**Friction Velocity (u*):**
Approximated using a bulk drag formulation or derived from wind speed and surface roughness under neutral conditions, modified by stability. For simplicity in V1 from ERA5:
\u* = ws * k / ln(z / z0)\ (Assuming neutral stability as a first guess)
Where \k = 0.4\ (Von Karman constant), \z = 10m\, \z0 = 0.1m\ (estimated aerodynamic roughness over mixed terrain).

**Monin-Obukhov Length (L):**
\L = - (rho * cp * T_v * u*^3) / (k * g * H_v)\
Where:
- \ho\ = air density (~1.2 kg/m3)
- \cp\ = specific heat capacity (~1005 J/kg/K)
- \T_v\ = virtual temperature (approximated as 2m temperature in Kelvin)
- \g\ = 9.81 m/s2
- \H_v\ = virtual kinematic heat flux

## 3. Lateral Turbulence (sigma_v)
For the Kljun FFP, lateral wind velocity variance (\sigma_v\) is required.
Following standard MOST parameterizations:
- Unstable conditions (\L < 0\): \sigma_v = u* * sqrt(3.6 + 2.0 * (-z/L)^(2/3))\
- Stable conditions (\L > 0\): \sigma_v = u* * 1.9\

## 4. Boundary Layer Height (PBLH)
ERA5 provides boundary layer height (\lh\) directly. We ensure it is strictly positive (clamp minimum to 50m).
