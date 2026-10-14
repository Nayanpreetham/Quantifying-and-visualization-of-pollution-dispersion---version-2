# Phase 11 — Multi-Week Pilot Period & Station Selection Report

**Audit Timestamp:** 2026-10-14 22:52 UTC  
**Selection Decision:** 5-Week Continuous Window (September 15 – October 20, 2021)  

---

## 1. Documented Selection Criteria

The multi-week validation study period was selected using four strict objective criteria:
1. **Continuous Duration (4–6 Weeks):** The selected window spans exactly **35.75 days (5 full weeks + 18 hours, 144 synoptic steps)**, satisfying the multi-week protocol.
2. **Climatic Transition Representation:** Spans the critical transition from the **Late Monsoon** (mid-September: frequent rain washout, moist southwesterly/southeasterly flow, lower background aerosols) into the **Post-Monsoon Inversion** (October: dry continental northwesterly flow, thermal trapping, early agricultural residue burning onset).
3. **Geographic Diversity:** Spans 10 stations across 7 major urban nodes covering **North India** (Chandigarh), **West India** (Ahmedabad), the **Indo-Gangetic Corridor** (Agra, Kanpur, Prayagraj, Varanasi), and **Northeast India** (Guwahati).
4. **Real-World Monitoring Asymmetry:** Ingestion explicitly tests model robustness against incomplete ground observation periods (e.g. Guwahati station active through Sep 24, Prayagraj active through Oct 22).

---

## 2. Selected Monitoring Stations

| Station ID | Station Name | City | Geographic Zone | Lat, Lon | Matched Grid ID | Hourly Obs | Completeness | Mean PM2.5 | Max PM2.5 |
|---|---|---|---|---|---|---|---|---|---|
| 42240 | Pan Bazaar, Guwahati - AP | Guwahati | Northeast River Valley | 26.19, 91.74 | `IND_r047_c095` | 214 | 24.9% | 19.8 | 64.8 |
| 227384 | Jhunsi, Prayagraj - UPPCB | Prayagraj | Central/Eastern Ganget | 25.43, 81.92 | `IND_r050_c056` | 491 | 57.2% | 35.6 | 124.3 |
| 227534 | Gyaspur, Ahmedabad - IITM | Ahmedabad | Western Semi-Arid (Guj | 22.98, 72.55 | `IND_r060_c018` | 448 | 52.2% | 61.8 | 1228.7 |
| 227931 | Sector-3B Avas Vikas Colo | Agra | Upper Gangetic Plain ( | 27.19, 77.96 | `IND_r043_c040` | 509 | 59.3% | 44.7 | 323.2 |
| 228297 | SVPI Airport Hansol, Ahme | Ahmedabad | Western Semi-Arid (Guj | 23.08, 72.63 | `IND_r060_c019` | 493 | 57.4% | 61.0 | 1285.6 |
| 228397 | IESD Banaras Hindu Univer | Varanasi | Eastern Gangetic Plain | 25.26, 83.00 | `IND_r051_c060` | 510 | 59.4% | 14.5 | 67.2 |
| 228403 | Bhelupur, Varanasi - UPPC | Varanasi | Eastern Gangetic Plain | 25.30, 83.00 | `IND_r051_c060` | 499 | 58.1% | 18.1 | 77.5 |
| 229252 | NSI Kalyanpur, Kanpur - U | Kanpur | Central Gangetic Plain | 26.51, 80.25 | `IND_r046_c049` | 511 | 59.5% | 23.0 | 134.2 |
| 233415 | Sector 22, Chandigarh - C | Chandigarh | North India (Punjab/Ha | 30.74, 76.78 | `IND_r029_c035` | 478 | 55.6% | 31.3 | 126.0 |
| 234568 | FTI Kidwai Nagar, Kanpur  | Kanpur | Central Gangetic Plain | 26.43, 80.33 | `IND_r046_c049` | 519 | 60.4% | 24.1 | 115.1 |

---

## 3. Meteorological Alignment Summary

- **ERA5 Dataset:** `data/raw/era5/2021/era5_2021_instant.nc`
- **Time Steps:** 144 synoptic steps (every 6 hours: 00:00, 06:00, 12:00, 18:00 UTC) from `2021-09-15 00:00:00` to `2021-10-20 18:00:00`.
- **Expected Simulation Runs:** 10 stations x 144 steps x 5 advection windows = up to 7,200 potential runs (actual valid runs determined by station operational hours).
