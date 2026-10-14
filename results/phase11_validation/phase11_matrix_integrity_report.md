# Phase 11 — Matrix Integrity & Mass Conservation Audit Report

- **Evaluation Window**: September 15 – October 20, 2021 (5 Weeks, 144 Synoptic Steps)
- **Stations Audited**: 10 stations across 7 urban regions
- **Elapsed Windows**: 1h, 3h, 6h, 12h, 24h
- **Total Source-Window Pairs Audited**: 50
- **Audit Pass Rate**: 50/50 (100.0%)

## 1. Executive Summary

All **50** source station and elapsed-time matrix rows strictly satisfy mathematical probability conservation and mass closure:
$$\sum_{j \in \text{Domain}} \bar{T}_{i \to j}(\Delta t) + \bar{T}_{i \to \text{Outside}}(\Delta t) = 1.000000 \pm 10^{-6}$$
- **Maximum Absolute Closure Error**: `0.00e+00`
- **Row Sum Minimum**: `1.000000`
- **Row Sum Maximum**: `1.000000`
- **Phase 9 Comparison**: Phase 9 identified row sums up to **16.02** due to conditional step omission. Under the Phase 10/11 unconditional time aggregation, **zero rows exceed 1.0000**.

## 2. Source-Window Matrix Closure Breakdown

| City | Station ID | Window (h) | Eligible Steps | Dests Reached | Inside Sum | Outside Sum | Total Closure | Status |
|---|---|---|---|---|---|---|---|---|
| Guwahati | 42240 | 1h | 40 | 1 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Guwahati | 42240 | 3h | 40 | 8 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Guwahati | 42240 | 6h | 40 | 18 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Guwahati | 42240 | 12h | 40 | 55 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Guwahati | 42240 | 24h | 40 | 159 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Prayagraj | 227384 | 1h | 90 | 6 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Prayagraj | 227384 | 3h | 90 | 25 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Prayagraj | 227384 | 6h | 90 | 75 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Prayagraj | 227384 | 12h | 90 | 206 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Prayagraj | 227384 | 24h | 90 | 498 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Ahmedabad | 227534 | 1h | 84 | 5 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Ahmedabad | 227534 | 3h | 84 | 24 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Ahmedabad | 227534 | 6h | 84 | 69 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Ahmedabad | 227534 | 12h | 84 | 188 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Ahmedabad | 227534 | 24h | 84 | 417 | 0.9744 | 0.0256 | 1.000000 | **PASS** |
| Agra | 227931 | 1h | 91 | 5 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Agra | 227931 | 3h | 91 | 25 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Agra | 227931 | 6h | 91 | 69 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Agra | 227931 | 12h | 91 | 204 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Agra | 227931 | 24h | 91 | 549 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Ahmedabad | 228297 | 1h | 89 | 5 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Ahmedabad | 228297 | 3h | 89 | 22 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Ahmedabad | 228297 | 6h | 89 | 65 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Ahmedabad | 228297 | 12h | 89 | 177 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Ahmedabad | 228297 | 24h | 89 | 421 | 0.9848 | 0.0152 | 1.000000 | **PASS** |
| Varanasi | 228397 | 1h | 92 | 6 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Varanasi | 228397 | 3h | 92 | 25 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Varanasi | 228397 | 6h | 92 | 70 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Varanasi | 228397 | 12h | 92 | 191 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Varanasi | 228397 | 24h | 92 | 497 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Varanasi | 228403 | 1h | 89 | 6 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Varanasi | 228403 | 3h | 89 | 25 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Varanasi | 228403 | 6h | 89 | 70 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Varanasi | 228403 | 12h | 89 | 191 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Varanasi | 228403 | 24h | 89 | 491 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Kanpur | 229252 | 1h | 92 | 7 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Kanpur | 229252 | 3h | 92 | 32 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Kanpur | 229252 | 6h | 92 | 92 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Kanpur | 229252 | 12h | 92 | 237 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Kanpur | 229252 | 24h | 92 | 582 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Chandigarh | 233415 | 1h | 88 | 2 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Chandigarh | 233415 | 3h | 88 | 14 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Chandigarh | 233415 | 6h | 88 | 35 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Chandigarh | 233415 | 12h | 88 | 104 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Chandigarh | 233415 | 24h | 88 | 318 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Kanpur | 234568 | 1h | 92 | 7 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Kanpur | 234568 | 3h | 92 | 32 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Kanpur | 234568 | 6h | 92 | 92 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Kanpur | 234568 | 12h | 92 | 237 | 1.0000 | 0.0000 | 1.000000 | **PASS** |
| Kanpur | 234568 | 24h | 92 | 582 | 1.0000 | 0.0000 | 1.000000 | **PASS** |

## 3. Boundary Loss Scaling Across Multi-Week Period

| Window (h) | Mean Inside Retention | Mean Boundary Loss | Max Boundary Loss | Stations with Loss > 0 |
|---|---|---|---|---|
| 1h | 100.00% | 0.00% | 0.00% | 0/10 |
| 3h | 100.00% | 0.00% | 0.00% | 0/10 |
| 6h | 100.00% | 0.00% | 0.00% | 0/10 |
| 12h | 100.00% | 0.00% | 0.00% | 0/10 |
| 24h | 99.59% | 0.41% | 2.56% | 2/10 |

## 4. Conclusion & Scientific Sign-Off

The multi-week transport matrix exhibits **100% mathematical integrity and rigorous physical consistency** across 5 continuous weeks of real OpenAQ observations and ERA5 winds. The unconditional time-aggregation methodology completely resolves the Phase 9 aggregation bug without introducing any edge-case artifacts.
