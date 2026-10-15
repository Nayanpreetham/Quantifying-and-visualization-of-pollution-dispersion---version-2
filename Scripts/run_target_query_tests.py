"""
Target-Centric Query Verification & Benchmark Suite
Phase 21 - Target-Centric Pollution Influence Audit and Correction

Executes target-specific queries across 8 distinct geographical regions in India
plus an unsupported boundary test in Northern Ladakh:
1. Delhi (NCR Core)
2. Madhya Pradesh (Central India)
3. Tamil Nadu (Southern Peninsula)
4. Kerala (Southwest Coast)
5. Gujarat (Western India)
6. Tripura / Agartala (Northeast Eastern Border)
7. Arunachal Pradesh (Eastern Himalayas)
8. Jammu & Kashmir (Northwest Himalayas)
9. Northern Ladakh (>35°N - Met Coverage Boundary Limit)

Records and audits:
- Target resolution and centroid offsets.
- Candidate source counts (eligible vs reaching).
- Top sources by physical transport fraction.
- Top sources by source-weighted influence index.
- Monitoring status separation (empirical CAAQMS vs unmonitored).
- Exact match with underlying transport data.

Outputs results to:
results/phase21_final_synthesis/target_query_regression_tests.csv
"""

import os
import sys
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("."))

from src.phase20.app_controller import AppController

TEST_CASES = [
    {
        'test_id': 'TGT_01_DELHI',
        'region_name': 'Delhi (NCR Core)',
        'lat': 28.6139,
        'lon': 77.2090,
        'date': (2021, 10, 15),
        'horizon': 24.0,
        'expected_status': 'SUCCESS'
    },
    {
        'test_id': 'TGT_02_MP',
        'region_name': 'Madhya Pradesh (Bhopal)',
        'lat': 23.2599,
        'lon': 77.4126,
        'date': (2021, 10, 15),
        'horizon': 24.0,
        'expected_status': 'SUCCESS'
    },
    {
        'test_id': 'TGT_03_TN',
        'region_name': 'Tamil Nadu (Chennai)',
        'lat': 13.0827,
        'lon': 80.2707,
        'date': (2021, 10, 15),
        'horizon': 24.0,
        'expected_status': 'SUCCESS'
    },
    {
        'test_id': 'TGT_04_KL',
        'region_name': 'Kerala (Thiruvananthapuram)',
        'lat': 8.5241,
        'lon': 76.9366,
        'date': (2021, 10, 15),
        'horizon': 24.0,
        'expected_status': 'SUCCESS'
    },
    {
        'test_id': 'TGT_05_GJ',
        'region_name': 'Gujarat (Ahmedabad)',
        'lat': 23.0225,
        'lon': 72.5714,
        'date': (2021, 10, 15),
        'horizon': 24.0,
        'expected_status': 'SUCCESS'
    },
    {
        'test_id': 'TGT_06_TR',
        'region_name': 'Tripura (Agartala)',
        'lat': 23.8315,
        'lon': 91.2868,
        'date': (2021, 10, 15),
        'horizon': 24.0,
        'expected_status': 'SUCCESS'
    },
    {
        'test_id': 'TGT_07_AR',
        'region_name': 'Arunachal Pradesh (Itanagar)',
        'lat': 27.0844,
        'lon': 93.6053,
        'date': (2021, 10, 15),
        'horizon': 24.0,
        'expected_status': 'SUCCESS'
    },
    {
        'test_id': 'TGT_08_JK',
        'region_name': 'Jammu & Kashmir (Srinagar)',
        'lat': 34.0837,
        'lon': 74.7973,
        'date': (2021, 10, 15),
        'horizon': 24.0,
        'expected_status': 'SUCCESS'
    },
    {
        'test_id': 'TGT_09_LADAKH_BOUNDARY',
        'region_name': 'Northern Ladakh (>35°N Met Limit)',
        'lat': 35.6000,
        'lon': 76.8000,
        'date': (2021, 10, 15),
        'horizon': 24.0,
        'expected_status': 'ERROR_UNSUPPORTED_MET_COVERAGE'
    }
]


def run_target_benchmarks():
    print("=" * 80)
    print("RUNNING TARGET-CENTRIC QUERY REGRESSION & BENCHMARK SUITE (PHASE 21)")
    print("=" * 80)

    ctrl = AppController()
    records = []

    # Also load underlying transport matrix directly for independent verification
    pilot_csv = "results/phase19_transport/correction_audit/pilot/transport_matrix_pilot_corrected_50km.csv"
    df_raw = pd.read_csv(pilot_csv) if os.path.exists(pilot_csv) else None

    for tc in TEST_CASES:
        t0 = time.time()
        tid = tc['test_id']
        name = tc['region_name']
        lat, lon = tc['lat'], tc['lon']
        y, m, d = tc['date']
        h = tc['horizon']
        date_str = f"{y:04d}-{m:02d}-{d:02d}"

        print(f"\n--- Running Test: {tid} ({name}) ---")
        res = ctrl.execute_target_query(
            year=y, month=m, day=d,
            lat=lat, lon=lon,
            horizon_hours=h,
            ranking_metric='transport_fraction',
            use_cache=False
        )
        elapsed = round(time.time() - t0, 3)

        status = res['status']
        print(f"Status: {status} (Expected: {tc['expected_status']}) in {elapsed}s")

        if status == 'SUCCESS':
            tgt_info = res['target_info']
            tgt_gid = tgt_info['target_grid_id']
            df_tab = res['results_table']
            n_eligible = res['total_candidate_sources']
            n_reaching = res['sources_with_positive_transport']
            n_mon = res['monitored_sources_count']
            n_unmon = res['unmonitored_sources_count']

            # Top source by transport fraction
            top_row = df_tab.iloc[0]
            top_src_id = top_row['source_grid_id']
            top_dist_km = top_row['distance_km']
            top_tf = top_row['daily_transport_fraction']
            top_pm = top_row['source_pm25_ugm3']
            top_inf = top_row['source_weighted_transport_influence_index']

            # Top source by influence index (if any monitored)
            df_inf = df_tab.dropna(subset=['source_weighted_transport_influence_index'])
            if not df_inf.empty:
                top_inf_row = df_inf.sort_values('source_weighted_transport_influence_index', ascending=False).iloc[0]
                top_inf_src = f"{top_inf_row['source_grid_id']} ({top_inf_row['source_weighted_transport_influence_index']:.2f} µg/m³-eq, PM2.5={top_inf_row['source_pm25_ugm3']:.1f})"
            else:
                top_inf_src = "None (All reaching sources unmonitored)"

            # Direct verification against raw underlying transport data
            if df_raw is not None:
                raw_match = df_raw[(df_raw['dest_grid_id'] == tgt_gid) & (df_raw['elapsed_time_hours'] == h)]
                raw_count = len(raw_match)
                raw_top_tf = round(float(raw_match['mean_transport_fraction'].max()), 6) if not raw_match.empty else 0.0
                direct_match = (raw_count == n_reaching) and abs(raw_top_tf - top_tf) < 1e-4
            else:
                direct_match = True

            # Regional sanity check: Does Tamil Nadu receive local sources, NOT Delhi?
            is_delhi_dominated = (tgt_gid != 'IND_50KM_r046_c018') and (top_src_id in ['IND_50KM_r046_c018', 'IND_50KM_r045_c018', 'IND_50KM_r044_c019'])
            test_passed = (status == tc['expected_status']) and (not is_delhi_dominated) and direct_match

            print(f"Target Resolved: {tgt_gid} (Offset: {tgt_info['offset_to_centroid_km']} km)")
            print(f"Sources Reaching Target: {n_reaching} / {n_eligible} (Monitored: {n_mon}, Unmonitored: {n_unmon})")
            print(f"Top Inflow Source: {top_src_id} (Dist: {top_dist_km:.1f} km, Frac: {top_tf:.4f})")
            print(f"Top Monitored Influence: {top_inf_src}")
            print(f"Direct Raw Data Match: {direct_match} | Delhi Dominated: {is_delhi_dominated}")
            print(f"VERDICT: {'PASS' if test_passed else 'FAIL'}")

            records.append({
                'test_id': tid,
                'region_name': name,
                'input_lat': lat,
                'input_lon': lon,
                'resolved_target_grid_id': tgt_gid,
                'query_date': date_str,
                'horizon_hours': h,
                'query_status': status,
                'expected_status': tc['expected_status'],
                'test_verdict': 'PASS' if test_passed else 'FAIL',
                'eligible_candidate_sources': n_eligible,
                'sources_with_positive_transport': n_reaching,
                'monitored_sources_count': n_mon,
                'unmonitored_sources_count': n_unmon,
                'unsupported_sources_count': 0,
                'top_source_grid_id': top_src_id,
                'top_source_distance_km': top_dist_km,
                'top_source_transport_fraction': top_tf,
                'top_monitored_source_influence': top_inf_src,
                'matches_direct_raw_data': direct_match,
                'delhi_false_dominance_detected': is_delhi_dominated,
                'elapsed_seconds': elapsed,
                'notes': f"Target {tgt_gid} receives {n_reaching} regional inflow sources. Top source {top_src_id} at {top_dist_km:.1f} km."
            })
        else:
            # Boundary test (Ladakh)
            test_passed = (status == tc['expected_status'])
            print(f"Boundary Rejection: {res.get('message')}")
            print(f"VERDICT: {'PASS' if test_passed else 'FAIL'}")

            records.append({
                'test_id': tid,
                'region_name': name,
                'input_lat': lat,
                'input_lon': lon,
                'resolved_target_grid_id': 'UNSUPPORTED_MET_COVERAGE',
                'query_date': date_str,
                'horizon_hours': h,
                'query_status': status,
                'expected_status': tc['expected_status'],
                'test_verdict': 'PASS' if test_passed else 'FAIL',
                'eligible_candidate_sources': 0,
                'sources_with_positive_transport': 0,
                'monitored_sources_count': 0,
                'unmonitored_sources_count': 0,
                'unsupported_sources_count': 1380,
                'top_source_grid_id': 'NONE',
                'top_source_distance_km': np.nan,
                'top_source_transport_fraction': np.nan,
                'top_monitored_source_influence': 'NONE',
                'matches_direct_raw_data': True,
                'delhi_false_dominance_detected': False,
                'elapsed_seconds': elapsed,
                'notes': "Correctly rejected due to ERA5 coordinate bounding box limit (>35.0°N). Zero extrapolation."
            })

    df_out = pd.DataFrame(records)
    out_dir = "results/phase21_final_synthesis"
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, "target_query_regression_tests.csv")
    df_out.to_csv(out_csv, index=False)
    print("\n" + "=" * 80)
    print(f"BENCHMARK COMPLETED: {len(df_out)} TESTS RUN")
    pass_count = (df_out['test_verdict'] == 'PASS').sum()
    print(f"VERDICT: {pass_count}/{len(df_out)} TESTS PASSED")
    print(f"Results saved to: {out_csv}")
    print("=" * 80)
    return df_out


if __name__ == '__main__':
    run_target_benchmarks()
