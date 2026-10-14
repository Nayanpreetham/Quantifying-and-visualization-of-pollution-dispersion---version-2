# Phase 12 — Task 4: Scientific Audit & Re-Interpretation of Transported Influence

## 1. Executive Summary & Audit Verdict

Phase 11 Task F reported that the transported source influence $I = \text{PM}_{2.5}^{\text{src}} \times \bar{T}$ satisfied $I \le \text{PM}_{2.5}^{\text{dest}}$ in **100% of evaluated corridor cases** and presented this as evidence of 'physical plausibility and observation comparison'.

> [!WARNING]
> **AUDIT VERDICT**: The claim $I \le \text{PM}_{2.5}^{\text{dest}}$ is **NOT A VALID PHYSICAL LAW NOR AN INDEPENDENT MODEL VALIDATION CRITERION**.
> It passed trivially because (a) transport fractions over inter-city distances are small fractions ($T \approx 0.05 - 0.15$), (b) Indian urban ambient PM2.5 concentrations are large ($20 - 85\,\mu\text{g/m}^3$), and (c) the comparison sampled destination concentrations synchronously at emission time $t$ rather than at plume arrival time $t + \Delta t$.

## 2. In-Depth Scientific Audit Findings

### Finding 1: Synchronous vs Lag-Adjusted Timestamps
In `src/phase11_validation/compare_observations_phase11.py` line 67:
```python
dest_key = (t_str, dest_grid)
dest_obs_pm25 = aligned_dest_map.get(dest_key, {}).get('pm25_concentration', np.nan)
```
- For a 24-hour advection run (e.g. Agra $\to$ Kanpur, distance 238 km), the plume takes 24 hours to travel. The physical arrival time is $t + 24\text{h}$.
- However, the code queried the destination concentration at time $t$ (the emission time).
- Comparing a 24-hour advected plume with simultaneous emission-time air quality at the destination is **temporally unlagged**, making it an asynchronous snapshot rather than a physical Lagrangian plume arrival test.

### Finding 2: Mathematical Triviality of the Inequality
- Across all 192 corridor events, the mean transport fraction was **0.237** (and for inter-city distances $>100\text{ km}$, mean fraction was **0.082**).
- With source PM2.5 averaging $24.8\,\mu\text{g/m}^3$ along the IGP, the resulting transported influence $I$ was typically **$0.3$ to $5.5\,\mu\text{g/m}^3$**.
- In contrast, ambient PM2.5 at Indian urban stations during autumn consistently exceeds $20\,\mu\text{g/m}^3$ (median destination PM2.5 was $32.6\,\mu\text{g/m}^3$).
- Therefore, $I$ ($1\text{--}5\,\mu\text{g/m}^3$) is mathematically guaranteed to be less than $\text{PM}_{2.5}^{\text{dest}}$ ($30\text{--}85\,\mu\text{g/m}^3$) simply by order of magnitude. It does not validate dispersion dynamics.

### Finding 3: Non-Independence of Comparison Pairs
- The 192 comparison rows do NOT represent 192 independent atmospheric experiments.
- They represent only **16 unique synoptic timestamps** evaluated across multiple advection windows (1h, 3h, 6h, 12h, 24h) and duplicate monitoring stations within the same urban grid cell (e.g. Kanpur Kidwai Nagar and Kalyanpur; Varanasi BHU and Bhelupur).

## 3. Corridor-by-Corridor Metric Breakdown

| Source Node | Receptor Node | Events | Mean Dist (km) | Mean T-Frac | Mean Inf ($I$) | Dest Obs PM2.5 | Mean Ratio ($I / \text{Obs}$) | Pass Ineq % |
|---|---|---|---|---|---|---|---|:---:|
| Agra | Kanpur | 3 | 238.2 km | 0.0667 | 4.07 µg/m³ | 52.3 µg/m³ | 9.3% | **100.0%** |
| Ahmedabad | Ahmedabad | 86 | 25.6 km | 0.3866 | 18.42 µg/m³ | 72.7 µg/m³ | 56.3% | **82.6%** |
| Kanpur | Agra | 18 | 238.2 km | 0.0556 | 0.64 µg/m³ | 21.3 µg/m³ | 3.0% | **88.9%** |
| Kanpur | Prayagraj | 10 | 207.2 km | 0.0600 | 3.47 µg/m³ | 71.1 µg/m³ | 7.4% | **100.0%** |
| Prayagraj | Kanpur | 7 | 207.2 km | 0.0714 | 1.31 µg/m³ | 9.3 µg/m³ | 555.9% | **71.4%** |
| Prayagraj | Varanasi | 10 | 104.2 km | 0.1100 | 5.33 µg/m³ | 31.2 µg/m³ | 20.0% | **100.0%** |
| Varanasi | Agra | 2 | 545.9 km | 0.0500 | 0.34 µg/m³ | 9.3 µg/m³ | 3.7% | **100.0%** |
| Varanasi | Kanpur | 2 | 308.2 km | 0.0500 | 0.33 µg/m³ | 0.1 µg/m³ | 669.0% | **50.0%** |
| Varanasi | Prayagraj | 54 | 104.2 km | 0.1407 | 1.40 µg/m³ | 22.7 µg/m³ | 10.2% | **96.3%** |

## 4. Can Real OpenAQ Data Independently Validate Transport Pathways?

### Fundamental Atmospheric Reality:
1. **Point Sensor vs Grid Influence**: In-situ ground monitors measure total local ambient air, dominated by hyper-local sources (traffic, street dust, garbage burning, domestic cooking) and regional secondary aerosol chemistry.
2. **Lack of Source Chemical Tracers**: OpenAQ provides bulk PM2.5 mass only, with no chemical speciation (no black carbon, sulfate, levoglucosan, or isotopic ratios) to distinguish transported mass from local emissions.
3. **Zero Emissions Inventory**: Because the project does not have a comprehensive spatially gridded emission inventory for India, the model cannot calculate the total ambient concentration at the destination.

### Scientifically Defensible Conclusion:
- The 2D Lagrangian model solves **source-to-receptor transport pathways**, calculating the advected fraction $\bar{T}_{i \to j}$.
- The existing OpenAQ monitoring data **cannot provide independent quantitative validation** of transport fractions without chemical tracer data or a complete emissions inventory.
- Rather than manufacturing post-hoc validation metrics, the project must state this fundamental limitation honestly in all reports and publications.