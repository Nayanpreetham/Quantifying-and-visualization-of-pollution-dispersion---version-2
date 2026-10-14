# Phase 16 — Multi-Year Transport Corridor and Seasonal Climatology Analysis (2019–2024)

**Project**: 2D Grid-to-Grid Pollution Dispersion Model for India  
**Date of Completion**: October 2026  
**Auditor / Science Lead**: Independent Validation & Verification (IV&V) Agent  
**Study Baseline**: 2019–2024 (6 Full Calendar Years / 72 Calendar Months)  
**Milestone Verdict**: **GO** for Final Synthesis & Thesis Reporting  

---

## 1. Executive Summary & Milestone Verdict

Phase 16 executes a multi-year transport corridor and seasonal climatology analysis for the completed 6-year historical baseline (2019–2024). 

Using the 72 monthly transport matrices and 6 annual transport matrices verified in Phases 13 and 15, this analysis quantifies modeled atmospheric source-to-destination pathways, recurring regional transport corridors, seasonal circulation reversals, and interannual stability across the Indian subcontinent.

```mermaid
flowchart TD
    subgraph S1["1. Matrix Input Audit (Task A)"]
        A["72 Monthly Matrices + 6 Annual Matrices<br/>100% Validated (2019–2024)"] --> B["Exact Schema Consistency<br/>100% Probability Closure (Max Err: 6.71e-14)"]
    end

    subgraph S2["2. Step-Weighted Climatology (Task B)"]
        B --> C["24 Yearly Seasonal Matrices<br/>5 Continuous Cross-Year Winters<br/>4 Climatological Baselines (DJF, MAM, JJAS, ON)"]
        C --> D["Step-Weighted Unconditional Pooling<br/>Eliminates Month-Length Weighting Distortion"]
    end

    subgraph S3["3. Corridor Identification & Stability (Tasks C & D)"]
        D --> E["Top-5 Corridors per Source-Window<br/>Threshold Sensitivity: tau in [0.01, 0.02, 0.05, 0.10]"]
        D --> F["Interannual Stability Metrics<br/>Mean Pairwise Cosine Similarity: 0.9625 – 0.9985<br/>Distance Bands: Local, Near-Reg, Reg, Long-Range"]
    end

    subgraph S4["4. Cartography & Ground Truth Separation (Tasks E & F)"]
        E --> G["6 Publication-Ready Cartographic Figures<br/>IGP vs Peninsular Comparison"]
        F --> G
        G --> H["Conservative OpenAQ Separation<br/>2,391 In-Situ Slots (2020/2021)<br/>Physical Climatology vs Ambient AQI Distinguished"]
    end
```

### Milestone Verdict: **GO**
- **Mathematical Rigor**: All seasonal and multi-year matrices pooled via exact step-weighted unconditional aggregation, preserving probability closure to machine precision ($\max |\sum \bar{T} - 1.0| < 2.5 \times 10^{-14}$).
- **Empirical Climatological Stability**: Interannual pairwise cosine similarity of transport probability vectors exceeds **0.96** across all advection windows ($1\text{h}$ to $24\text{h}$), confirming persistent, recurring wind regimes across the subcontinent.
- **Scientific Honesty & Non-Imputation**: Strictly separates unconditioned physical transport climatology from concentration-weighted influence ($I = \bar{T} \cdot C_{\text{src}}$), noting that the 2,391 available observation slots in 2020–2021 support influence estimation while 2019 and 2022–2024 serve as pure physical meteorological climatologies.

---

## 2. Task A — Audit of Analysis Inputs

Prior to computing climatological statistics, all input matrices were inventoried and audited by [`task_a_audit_inputs.py`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/src/phase16/task_a_audit_inputs.py). The audit results are documented in [`input_matrix_audit.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase16_climatology/tables/input_matrix_audit.csv):

| Metric / Audit Parameter | Verified Result | Scientific Interpretation |
|---|---|---|
| **Monthly Matrices Available** | 72 / 72 Files Present (100.0%) | 12 files for 2019 (`results/phase15_six_year/monthly/`), 60 files for 2020–2024 (`results/phase13_six_year/monthly/`) |
| **Annual Matrices Available** | 6 / 6 Files Present (100.0%) | 2019 (`results/phase15_six_year/annual/`), 2020–2024 (`results/phase13_six_year/annual/`) |
| **Schema Compatibility** | 100% Identical Column Names & Types | Exactly 15 columns in monthly CSVs; 15 columns in annual CSVs |
| **Grid Identifier Regex** | 100% Pass (`^IND_r\d{3}_c\d{3}$` or `OUTSIDE_DOMAIN`) | Zero malformed grid strings across 1.1+ million matrix records |
| **Fraction Bounds** | $0.0 \le \bar{T}_{s, d, \Delta t} \le 1.0$ | All fractions strictly bounded; 0 NaNs in transport fractions |
| **Maximum Annual Closure Error** | **$6.71 \times 10^{-14}$** | Full row-sum probability closure verified across all 300 annual source-window groups |
| **Matrix Semantics** | Unconditional Transport Probability | Represents the fraction of Lagrangian ensemble particles transported from source $s$ to destination $d$ over $\Delta t$, averaged unconditionally over all eligible meteorological synoptic steps |
| **Domain Exit Category** | Explicit Boundary Accounting | `OUTSIDE_DOMAIN` accounts for particles exiting the national domain bounds ($6^\circ-35^\circ\text{N}, 68^\circ-97^\circ\text{E}$) |

---

## 3. Task B — Seasonal & Annual Aggregation Methodology

### 3.1 Step-Weighted Unconditional Pooling Formula
A simple unweighted arithmetic mean of monthly transport matrices $\frac{1}{M}\sum \bar{T}_m$ is mathematically invalid because calendar months vary in length (e.g., February has 28 or 29 days / 112 or 116 synoptic steps, while January has 31 days / 124 steps).

Following the Phase 10 unconditional aggregation principle, seasonal and multi-year matrices were computed using **step-weighted pooling**:

$$\bar{T}_{\text{period}}[s, d, \Delta t] = \frac{\sum_{m \in \text{period}} \left( \bar{T}_m[s, d, \Delta t] \cdot N_{\text{met}, m} \right)}{\sum_{m \in \text{period}} N_{\text{met}, m}}$$

where $N_{\text{met}, m}$ is the exact number of eligible synoptic 6-hourly steps in month $m$. This weighting guarantees exact probability closure for any arbitrary seasonal or multi-year period:
$$\sum_{d} \bar{T}_{\text{period}}[s, d, \Delta t] = 1.00000000000000 \pm 10^{-13}$$

### 3.2 Seasonal Grouping & Handling of December
Seasons are defined according to the Indian Meteorological Department (IMD) / WMO meteorological calendar:
1. **Winter (DJF)**: December, January, February.
   - Evaluated as **5 Continuous Cross-Year Winters** (Dec 2019–Feb 2020, Dec 2020–Feb 2021, Dec 2021–Feb 2022, Dec 2022–Feb 2023, Dec 2023–Feb 2024).
   - Also evaluated as calendar-year winters (JF + D within same year) and as a **18-month 6-Year Climatological Winter**.
2. **Pre-monsoon (MAM)**: March, April, May (18 months across 6 years).
3. **Monsoon (JJAS)**: June, July, August, September (24 months across 6 years).
4. **Post-monsoon (ON)**: October, November (12 months across 6 years).

The complete seasonal inventory is stored in [`seasonal_transport_summary.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase16_climatology/tables/seasonal_transport_summary.csv).

| Season Climatology | Months Included | Synoptic Steps | Active Pairs | Mean Boundary Retention | Max Closure Error | Mean Modeled Transport Dist |
|---|---|---|---|---|---|---|
| **Winter (DJF)** | 18 Months (Dec–Feb) | 2,164 | 12,397 | 100.00% | $1.73 \times 10^{-14}$ | 71.3 km |
| **Pre-monsoon (MAM)** | 18 Months (Mar–May) | 2,208 | 17,056 | 100.00% | $2.08 \times 10^{-14}$ | 81.6 km |
| **Monsoon (JJAS)** | 24 Months (Jun–Sep) | 2,928 | 21,676 | 99.98% | $2.31 \times 10^{-14}$ | 84.6 km |
| **Post-monsoon (ON)** | 12 Months (Oct–Nov) | 1,464 | 9,620 | 100.00% | $1.39 \times 10^{-14}$ | 62.6 km |
| **Full 6-Year Baseline** | **All 72 Months** | **8,768** | **24,369** | **100.00%** | **$1.91 \times 10^{-14}$** | **76.9 km** |

---

## 4. Task C — Recurring Transport Corridors & Threshold Sensitivity

### 4.1 Geodesic Distance Bands
Geodesic distances are calculated using the Haversine equation between source coordinates and destination cell centroids, classified into 5 discrete physical regimes:
- **Local / Self-Grid ($d < 30\text{ km}$)**: Immediate plume retention within source cell and adjacent perimeter.
- **Near-Regional ($30 \le d < 100\text{ km}$)**: Intra-basin transport (e.g. Kanpur $\rightarrow$ Lucknow corridor).
- **Regional ($100 \le d < 250\text{ km}$)**: Inter-district transport across regional airsheds (e.g. Agra $\rightarrow$ Delhi or Kanpur $\rightarrow$ Varanasi).
- **Long-Range ($d \ge 250\text{ km}$)**: Inter-state synoptic scale transport.
- **Domain Exit (`OUTSIDE_DOMAIN`)**: Boundary loss.

### 4.2 Top Recurring Corridors
The top 5 destinations per source station and window are recorded in [`top_transport_corridors.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase16_climatology/tables/top_transport_corridors.csv). Key recurring corridors include:
1. **Guwahati Regional Airshed (Assam Valley)**:
   - Primary Corridor: `IND_r047_c095` $\rightarrow$ `IND_r048_c094` (Brahmaputra valley axis, bearing $\sim 19^\circ$, distance 32.1 km).
   - Persistence: Active in **6 of 6 years** (annual persistence $= 1.0$) and **71 of 72 months** (monthly persistence $= 0.986$).
2. **Indo-Gangetic Plain Corridor (Kanpur $\rightarrow$ Down-Valley)**:
   - Dominant axis: Northwest-to-southeast channel aligned with the Himalayan terrain barrier.
   - At $\Delta t = 12\text{h}$, transport to southeastern down-valley cells occurs with annual recurrence in **6 of 6 years**.
3. **Western India Maritime Corridor (Ahmedabad $\rightarrow$ Gulf of Khambhat)**:
   - Reversal axis: Strong southwest monsoon flow in JJAS transitioning to northeast continental outflow in winter.

### 4.3 Pre-Defined Threshold Sensitivity Analysis
To avoid arbitrary cutoff dependence, corridor recurrence was systematically evaluated across four thresholds $\tau \in [0.01, 0.02, 0.05, 0.10]$ in [`corridor_persistence.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase16_climatology/tables/corridor_persistence.csv):

| Threshold ($\tau$) | Meaning | Recurring Links ($\ge 3$ of 6 Years) | Highly Persistent Links ($\ge 5$ of 6 Years) |
|---|---|---|---|
| **$\tau = 0.01$** | $\ge 1\%$ transport probability | 779 links | 669 links (85.9%) |
| **$\tau = 0.02$** | $\ge 2\%$ transport probability | 364 links | 316 links (86.8%) |
| **$\tau = 0.05$ (Primary)** | $\ge 5\%$ transport probability | 152 links | 118 links (77.6%) |
| **$\tau = 0.10$** | $\ge 10\%$ transport probability | 68 links | 54 links (79.4%) |

> [!NOTE]
> Regardless of whether $\tau$ is set to 1%, 2%, 5%, or 10%, between **77% and 87%** of candidate links recur across $\ge 5$ of the 6 years. This proves that modeled corridor recurrence is an intrinsic physical characteristic of the ERA5 synoptic wind field rather than an artifact of threshold selection.

---

## 5. Task D — Seasonal and Interannual Stability Analysis

Dispersion stability was quantified across all 50 source-window groups in [`interannual_stability.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase16_climatology/tables/interannual_stability.csv).

| Advection Window ($\Delta t$) | Mean Transport Distance | Local Fraction ($< 30$ km) | Regional Fraction ($30 - 250$ km) | Long-Range ($\ge 250$ km) | Mean Pairwise Cosine Similarity | Stability Rating |
|---|---|---|---|---|---|---|
| **1.0 hour** | 9.9 km | 99.2% | 0.8% | 0.0% | **0.9985** | Very High |
| **3.0 hours** | 26.4 km | 66.0% | 34.1% | 0.0% | **0.9891** | Very High |
| **6.0 hours** | 50.3 km | 23.5% | 76.5% | 0.0% | **0.9812** | Very High |
| **12.0 hours** | 99.4 km | 6.6% | 92.0% | 1.5% | **0.9738** | Very High |
| **24.0 hours** | 198.4 km | 2.4% | 72.2% | 25.4% | **0.9625** | Very High |

### Physical Interpretations
1. **Linear Distance Scaling**: Modeled transport distance scales almost perfectly linearly with advection window:
   $$\bar{d}(\Delta t) \approx 8.25\,\text{km/h} \times \Delta t$$
   reflecting a consistent mean surface advection speed of $\approx 2.3\,\text{m s}^{-1}$ across the Indian domain.
2. **High Interannual Pattern Fidelity**: Pairwise cosine similarity between years exceeds **0.96** even at 24 hours advection. Year-to-year variation in seasonal circulation is dominated by modest variations in wind speed rather than major shifts in prevailing corridor orientation.
3. **Dispersion Concentration**: Local self-retention drops from 99.2% at 1h to 2.4% at 24h, with 97.6% of mass entering regional and long-range transport pathways by 24h.

---

## 6. Task E — Cartographic Visualizations

All six publication-grade spatial maps and diagnostic charts were generated and saved to `results/phase16_climatology/figures/`:

### Figure 1: Six-Year National Recurring Transport Corridors Composite
![Figure 1: Six-Year Recurring Corridors Composite](file:///C:/Users/Nayan%20preetham/.gemini/antigravity/brain/03c22f0a-5ded-4938-bf05-6a8d57692603/fig1_six_year_recurring_corridors_composite.png)
*Figure 1: Composite national transport map (2019–2024) showing recurring advection vectors for 6h (blue), 12h (orange), and 24h (red) windows across 10 monitoring hubs.*

### Figure 2: Four-Panel Seasonal Corridor Shifts
![Figure 2: Seasonal Corridor Shifts](file:///C:/Users/Nayan%20preetham/.gemini/antigravity/brain/03c22f0a-5ded-4938-bf05-6a8d57692603/fig2_seasonal_corridor_shifts_4panel.png)
*Figure 2: Seasonal transport pattern shifts across Winter (DJF), Pre-monsoon (MAM), Monsoon (JJAS), and Post-monsoon (ON). Illustrates down-valley northwest flow in winter vs southwesterly maritime inflow during monsoon.*

### Figure 3: Transport Distance Scaling and Spatial Partitioning
![Figure 3: Transport Distance Scaling and Bands](file:///C:/Users/Nayan%20preetham/.gemini/antigravity/brain/03c22f0a-5ded-4938-bf05-6a8d57692603/fig3_transport_distance_scaling_and_bands.png)
*Figure 3: (a) Geodesic transport distance vs advection window across 10 stations; (b) Stacked distance band distribution demonstrating regional transition from 1h to 24h.*

### Figure 4: Interannual Stability and Dispersion Concentration
![Figure 4: Interannual Stability Matrix](file:///C:/Users/Nayan%20preetham/.gemini/antigravity/brain/03c22f0a-5ded-4938-bf05-6a8d57692603/fig4_interannual_stability_matrix.png)
*Figure 4: (a) Mean pairwise cosine similarity across all pairs of years (2019–2024) per station; (b) Gini concentration coefficient vs modeled transport distance.*

### Figure 5: Spatial Dispersion Footprint Comparison (IGP vs Peninsular)
![Figure 5: Spatial Footprint Comparison](file:///C:/Users/Nayan%20preetham/.gemini/antigravity/brain/03c22f0a-5ded-4938-bf05-6a8d57692603/fig5_spatial_dispersion_footprint_igp_vs_peninsular.png)
*Figure 5: 12-hour winter dispersion footprint comparing Kanpur (Indo-Gangetic Plain channel flow) vs Ahmedabad (Western India semi-arid dispersal).*

### Figure 6: Threshold Sensitivity Curves
![Figure 6: Threshold Sensitivity Curves](file:///C:/Users/Nayan%20preetham/.gemini/antigravity/brain/03c22f0a-5ded-4938-bf05-6a8d57692603/fig6_corridor_persistence_and_threshold_sensitivity.png)
*Figure 6: Number of recurring corridors (active in $\ge 3$ and $\ge 5$ years) as a function of detection threshold $\tau \in [0.01, 0.10]$.*

---

## 7. Task F — Conservative Handling of OpenAQ Observations

A rigorous audit of observational grounding was conducted in [`openaq_comparison_coverage.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase16_climatology/tables/openaq_comparison_coverage.csv):

1. **Exact In-Situ Availability**:
   - Total Synoptic Time Slots across 10 Stations $\times$ 6 Years: **87,680 slots**.
   - Valid Ground PM2.5 Slots: **2,391 slots** (2.73% of total domain).
     - **2020**: 14 slots (Guwahati only; mean PM2.5 $= 127.3\,\mu\text{g m}^{-3}$).
     - **2021**: 2,377 slots (All 10 stations active; mean PM2.5 $= 68.4\,\mu\text{g m}^{-3}$).
     - **2019, 2022, 2023, 2024**: 0 slots for these 10 stations.
2. **Strict Separation of Output Families**:
   - **Family 1 — Meteorological Transport Climatology ($\bar{T}$)**: Unitless fraction in $[0, 1]$. Valid across all 8,768 synoptic steps and all 6 years. Measures where air masses physically travel.
   - **Family 2 — Transported Influence ($I = \bar{T} \cdot C_{\text{src}}$)**: Expressed in $\mu\text{g m}^{-3}$. Strictly calculated only for the 2,391 time steps where $C_{\text{src}}$ was observed. Missing PM2.5 observations are **never** imputed as zero.
3. **Scientific Limits on Ambient Predictions**:
   - The model computes *advected source influence*, not total ambient destination AQI.
   - It does not account for chemical secondary aerosol formation, wet scavenging, boundary layer height diurnal compression, or unmonitored local destination emissions.
   - Destination observations at arrival time cannot be directly equated with source-time PM2.5 without complete emission inventories.

---

## 8. Master Climatology Tables Summary

| Table Output File | Primary Content | Record Count |
|---|---|---|
| [`input_matrix_audit.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase16_climatology/tables/input_matrix_audit.csv) | Audit of all 72 monthly + 6 annual matrices | 78 rows |
| [`annual_transport_summary.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase16_climatology/tables/annual_transport_summary.csv) | Year-by-year distance, retention, closure metrics | 6 rows |
| [`seasonal_transport_summary.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase16_climatology/tables/seasonal_transport_summary.csv) | 24 yearly seasons + 5 cross-year winters + 4 climatologies | 33 rows |
| [`top_transport_corridors.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase16_climatology/tables/top_transport_corridors.csv) | Top-5 destination cells per station and window | 250 rows |
| [`corridor_persistence.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase16_climatology/tables/corridor_persistence.csv) | Multi-year persistence and threshold sensitivity | 24,369 rows |
| [`interannual_stability.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase16_climatology/tables/interannual_stability.csv) | HHI, Gini, distance scaling, and pairwise cosine similarities | 50 rows |
| [`openaq_comparison_coverage.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase16_climatology/tables/openaq_comparison_coverage.csv) | Station-year observation audit and family separation | 60 rows |

---

## 9. Conclusion & Project Synthesis Readiness

Phase 16 concludes the substantive modeling and climatological analysis of the 2D Grid-to-Grid Pollution Dispersion Project for India. 

The project has achieved:
1. Complete 6-year national physical transport baseline (2019–2024, 72 months, 8,768 synoptic steps, 438,400 Lagrangian ensemble runs).
2. Machine-precision mathematical conservation across all monthly, annual, and climatological matrices.
3. Quantified seasonal wind reversal dynamics and recurring transport corridors.
4. Publication-grade cartographic figures and documented data provenance.

The codebase and data tables are fully prepared for academic thesis compilation and presentation.
