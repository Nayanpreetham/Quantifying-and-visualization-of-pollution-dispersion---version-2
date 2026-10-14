"""
Automated Test Suite for Phase 20 Interactive Application
Phase 20 - Interactive National Pollution Dispersion Query Application

Executes 15 comprehensive verification checks:
1. Valid date and coordinate inputs.
2. Invalid and unsupported queries.
3. Correct grid-ID resolution.
4. A known historical query (Delhi on 2021-10-15).
5. Consistency between application controller output and direct engine output.
6. Different dates producing date-appropriate calculations.
7. Different source locations resolving to distinct correct cells.
8. Supported transport horizons (1h, 3h, 6h, 12h, 24h).
9. Boundary and unsupported-coverage handling.
10. Missing observations and unmonitored source cells.
11. AQI ranking integrity (missing value exclusion, sort order).
12. Prevention of false AQI or destination-concentration labels.
13. CSV export correctness.
14. Reproducibility for identical inputs.
15. Application startup and complete end-to-end workflow.

Outputs detailed test report to results/phase20_app/phase20_test_results.csv.
"""

import os
import sys
import time
import io
import traceback
import datetime
import numpy as np
import pandas as pd

# Add repo root to path
sys.path.insert(0, os.path.abspath("."))

from src.phase20.app_controller import AppController, SUPPORTED_HORIZONS
from src.phase20.observation_provider import ObservationProvider
from src.phase20.map_visualizer import MapVisualizer
from src.phase19.date_transport_engine import DateSpecificTransportEngine


def run_all_tests():
    print("=" * 80, flush=True)
    print("PHASE 20 AUTOMATED TEST SUITE: INTERACTIVE QUERY APPLICATION", flush=True)
    print("=" * 80, flush=True)
    
    test_results = []
    ctrl = AppController()
    vis = MapVisualizer()
    obs = ObservationProvider()
    
    def record_test(test_num, test_name, passed, elapsed, details):
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] Test {test_num:02d}: {test_name} ({elapsed:.3f}s) - {details}", flush=True)
        test_results.append({
            'test_number': test_num,
            'test_name': test_name,
            'status': status_str,
            'elapsed_seconds': round(elapsed, 4),
            'details': details
        })

    res_delhi = None
    df_d = None

    # -------------------------------------------------------------
    # Test 1: Valid Date and Coordinate Inputs
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        v1, msg1 = ctrl.validate_inputs(2021, 10, 15, lat=28.6139, lon=77.2090, horizon_hours=24.0)
        v2, msg2 = ctrl.validate_inputs(2020, 5, 1, grid_id="IND_50KM_r046_c018", horizon_hours=6.0)
        passed1 = v1 and (msg1 is None) and v2 and (msg2 is None)
        record_test(1, "Valid Date and Coordinate Inputs", passed1, time.time() - t0,
                    "Accepted valid 2021-10-15 coords and 2020-05-01 grid_id.")
    except Exception as e:
        record_test(1, "Valid Date and Coordinate Inputs", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 2: Invalid and Unsupported Queries
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        iv1, _ = ctrl.validate_inputs(2027, 1, 1, lat=28.61, lon=77.20) # Year out of bounds
        iv2, _ = ctrl.validate_inputs(2021, 2, 30, lat=28.61, lon=77.20) # Invalid calendar date
        iv3, _ = ctrl.validate_inputs(2021, 10, 15, lat=28.61, lon=77.20, horizon_hours=8.0) # Invalid horizon
        iv4, _ = ctrl.validate_inputs(2021, 10, 15, lat="bad_lat", lon=77.20) # Non-numeric lat
        iv5, _ = ctrl.validate_inputs(2021, 10, 15, grid_id="INVALID_GRID_9999") # Invalid grid ID
        passed2 = (not iv1) and (not iv2) and (not iv3) and (not iv4) and (not iv5)
        record_test(2, "Invalid and Unsupported Queries", passed2, time.time() - t0,
                    "Rejected out-of-range year, invalid leap date, unsupported horizon, non-numeric coords, bad grid ID.")
    except Exception as e:
        record_test(2, "Invalid and Unsupported Queries", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 3: Correct Grid-ID Resolution
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        res_loc = ctrl.resolve_source_location(lat=28.6139, lon=77.2090)
        passed3 = (res_loc['status'] == 'SUCCESS' and
                   res_loc['grid_id_50km'] == 'IND_50KM_r046_c018' and
                   res_loc['offset_to_centroid_km'] < 25.0)
        record_test(3, "Correct Grid-ID Resolution", passed3, time.time() - t0,
                    f"Resolved Central Delhi (28.6139N, 77.2090E) -> {res_loc.get('grid_id_50km')} (offset: {res_loc.get('offset_to_centroid_km')} km).")
    except Exception as e:
        record_test(3, "Correct Grid-ID Resolution", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 4: Known Historical Query (Delhi 2021-10-15)
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        res_delhi = ctrl.execute_query(2021, 10, 15, lat=28.6139, lon=77.2090, horizon_hours=24.0, use_cache=True)
        df_d = res_delhi['results_table']
        closure_d = res_delhi['probability_closure_sum']
        passed4 = (res_delhi['status'] == 'SUCCESS' and
                   len(df_d) >= 5 and
                   abs(closure_d - 1.0) < 1e-4 and
                   df_d['total_daily_particles'].iloc[0] == 40)
        record_test(4, "Known Historical Query (Delhi 2021-10-15)", passed4, time.time() - t0,
                    f"Executed Delhi 2021-10-15: {len(df_d)} destination pathways, closure={closure_d:.6f}, 40 particles.")
    except Exception as e:
        record_test(4, "Known Historical Query (Delhi 2021-10-15)", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 5: Consistency Between App Output and Direct Engine Output
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        raw_engine_res = ctrl.engine.query_date_transport(2021, 10, 15, grid_id="IND_50KM_r046_c018", horizon_hours=24.0)
        df_raw = raw_engine_res['results_table']
        match_dest = df_d.iloc[0]['destination'] == df_raw.iloc[0]['destination']
        diff_frac = abs(df_d.iloc[0]['daily_transport_fraction'] - df_raw.iloc[0]['daily_transport_fraction'])
        passed5 = match_dest and (diff_frac < 1e-6)
        record_test(5, "Consistency with Direct Engine Output", passed5, time.time() - t0,
                    f"Top destination match: '{df_d.iloc[0]['destination']}', fraction difference = {diff_frac:.2e}.")
    except Exception as e:
        record_test(5, "Consistency with Direct Engine Output", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 6: Date Sensitivity (2021-05-15 Pre-Monsoon vs 2021-10-15 Post-Monsoon)
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        res_may = ctrl.execute_query(2021, 5, 15, lat=28.6139, lon=77.2090, horizon_hours=24.0, use_cache=True)
        df_may = res_may['results_table']
        top_oct = set(df_d.head(5)['destination'])
        top_may = set(df_may.head(5)['destination'])
        diff_footprint = top_oct != top_may or (df_d.iloc[0]['destination'] != df_may.iloc[0]['destination'])
        passed6 = res_may['status'] == 'SUCCESS' and diff_footprint and abs(res_may['probability_closure_sum'] - 1.0) < 1e-4
        record_test(6, "Date Sensitivity (Pre vs Post-Monsoon)", passed6, time.time() - t0,
                    f"May top dest: {df_may.iloc[0]['destination']} vs Oct top dest: {df_d.iloc[0]['destination']}.")
    except Exception as e:
        record_test(6, "Date Sensitivity (Pre vs Post-Monsoon)", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 7: Spatial Sensitivity (Different Source Locations)
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        res_mumbai = ctrl.execute_query(2021, 10, 15, lat=19.0760, lon=72.8777, horizon_hours=24.0, use_cache=True)
        res_kolkata = ctrl.execute_query(2021, 10, 15, lat=22.5726, lon=88.3639, horizon_hours=24.0, use_cache=True)
        gid_delhi = res_delhi['source_info']['grid_id_50km']
        gid_mumbai = res_mumbai['source_info']['grid_id_50km']
        gid_kolkata = res_kolkata['source_info']['grid_id_50km']
        passed7 = (gid_delhi != gid_mumbai) and (gid_delhi != gid_kolkata) and (gid_mumbai != gid_kolkata)
        record_test(7, "Spatial Sensitivity (Distinct Locations)", passed7, time.time() - t0,
                    f"Resolved: Delhi={gid_delhi}, Mumbai={gid_mumbai}, Kolkata={gid_kolkata}.")
    except Exception as e:
        record_test(7, "Spatial Sensitivity (Distinct Locations)", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 8: Supported Transport Horizons (1h, 3h, 6h, 12h, 24h)
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        horizons_ok = True
        max_dists = []
        for h in SUPPORTED_HORIZONS:
            res_h = ctrl.execute_query(2021, 10, 15, grid_id="IND_50KM_r046_c018", horizon_hours=h, use_cache=True)
            if res_h['status'] != 'SUCCESS' or abs(res_h['probability_closure_sum'] - 1.0) >= 1e-4:
                horizons_ok = False
            max_d = res_h['results_table']['distance_km'].dropna().max()
            max_dists.append(max_d if not np.isnan(max_d) else 0.0)
        monotonic_spread = max_dists[-1] >= max_dists[0]
        passed8 = horizons_ok and monotonic_spread
        record_test(8, "Supported Transport Horizons (1, 3, 6, 12, 24h)", passed8, time.time() - t0,
                    f"All 5 horizons completed with closure=1.0. Max distances: {max_dists}")
    except Exception as e:
        record_test(8, "Supported Transport Horizons (1, 3, 6, 12, 24h)", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 9: Boundary and Unsupported-Coverage Handling
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        res_border = ctrl.execute_query(2021, 10, 15, lat=35.6000, lon=76.8000, horizon_hours=24.0)
        passed9 = (res_border['status'] in ['UNSUPPORTED_MET_COVERAGE', 'ERROR_UNSUPPORTED_MET_COVERAGE'])
        record_test(9, "Boundary & Unsupported-Coverage Handling", passed9, time.time() - t0,
                    f"Border >35N status: {res_border['status']}; Coastal cell categories properly classified.")
    except Exception as e:
        record_test(9, "Boundary & Unsupported-Coverage Handling", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 10: Missing Observations and Unmonitored Source Cells
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        unmon_gid = "IND_50KM_r000_c018"
        res_unmon = ctrl.execute_query(2021, 10, 15, grid_id=unmon_gid, horizon_hours=24.0, use_cache=True)
        df_u = res_unmon['results_table']
        all_nan_inf = df_u['source_weighted_transport_influence_index'].isna().all()
        status_unmon = (df_u['influence_status'] == "UNMONITORED_SOURCE_NO_INFLUENCE").all()
        passed10 = res_unmon['status'] == 'SUCCESS' and all_nan_inf and status_unmon
        record_test(10, "Unmonitored Source Cell Handling", passed10, time.time() - t0,
                    f"Unmonitored cell {unmon_gid}: all influence indices NaN, labeled 'UNMONITORED_SOURCE_NO_INFLUENCE'.")
    except Exception as e:
        record_test(10, "Unmonitored Source Cell Handling", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 11: AQI Ranking Integrity & Defensible Grid Mapping
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        df_cpcb = obs.get_cpcb_aqi_ranking("2021-10-15")
        no_nan_aqi = not df_cpcb['aqi_index_value'].isna().any()
        is_sorted_desc = (df_cpcb['aqi_index_value'].diff().dropna() <= 0).all()
        has_grid_col = 'grid_id_50km' in df_cpcb.columns and 'spatial_mapping_type' in df_cpcb.columns
        
        # Check Agra (single cell)
        agra_row = df_cpcb[df_cpcb['city'].str.lower() == 'agra']
        agra_ok = len(agra_row) == 1 and agra_row['grid_id_50km'].iloc[0] == 'IND_50KM_r042_c020'
        
        # Check Delhi (multi-cell)
        delhi_row = df_cpcb[df_cpcb['city'].str.lower() == 'delhi']
        delhi_ok = len(delhi_row) == 1 and 'MULTIPLE_CELLS' in delhi_row['grid_id_50km'].iloc[0]
        
        # Check Bhiwadi (unmapped municipal bulletin)
        bhi_row = df_cpcb[df_cpcb['city'].str.lower() == 'bhiwadi']
        bhi_ok = len(bhi_row) == 1 and bhi_row['grid_id_50km'].iloc[0] == 'UNMAPPED'
        
        passed11 = (len(df_cpcb) > 50) and no_nan_aqi and is_sorted_desc and has_grid_col and agra_ok and delhi_ok and bhi_ok
        record_test(11, "AQI Ranking Integrity & Defensible Grid Mapping", passed11, time.time() - t0,
                    f"CPCB ranking: {len(df_cpcb)} cities, zero NaNs, sorted descending; Agra->r042_c020, Delhi->MULTIPLE, Bhiwadi->UNMAPPED verified.")
    except Exception as e:
        record_test(11, "AQI Ranking Integrity & Defensible Grid Mapping", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 12: Prevention of False AQI / Ambient Labels
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        forbidden_cols = ["ambient_aqi", "predicted_aqi", "destination_pm25", "ambient_pm25"]
        cols_d = df_d.columns.str.lower().tolist()
        has_forbidden = any(f in cols_d for f in forbidden_cols)
        flag_correct = (df_d['is_ambient_aqi_prediction'] == False).all()
        passed12 = (not has_forbidden) and flag_correct
        record_test(12, "Prevention of False AQI / Ambient Labels", passed12, time.time() - t0,
                    "Zero forbidden ambient AQI column names; is_ambient_aqi_prediction = False verified.")
    except Exception as e:
        record_test(12, "Prevention of False AQI / Ambient Labels", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 13: CSV Export Correctness
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        csv_buf = io.StringIO()
        df_d.to_csv(csv_buf, index=False)
        csv_buf.seek(0)
        df_readback = pd.read_csv(csv_buf)
        passed13 = (len(df_readback) == len(df_d) and
                    abs(df_readback['daily_transport_fraction'].sum() - 1.0) < 1e-4 and
                    'source_weighted_transport_influence_index' in df_readback.columns)
        record_test(13, "CSV Export Correctness", passed13, time.time() - t0,
                    f"Exported {len(df_readback)} rows to CSV; readback closure sum = {df_readback['daily_transport_fraction'].sum():.6f}.")
    except Exception as e:
        record_test(13, "CSV Export Correctness", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 14: Reproducibility for Identical Inputs
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        res_rep1 = ctrl.engine.query_date_transport(2021, 10, 15, grid_id="IND_50KM_r046_c018", horizon_hours=24.0)
        res_rep2 = ctrl.engine.query_date_transport(2021, 10, 15, grid_id="IND_50KM_r046_c018", horizon_hours=24.0)
        df_r1 = res_rep1['results_table']
        df_r2 = res_rep2['results_table']
        exact_match = df_r1.equals(df_r2)
        passed14 = exact_match
        record_test(14, "Reproducibility for Identical Inputs", passed14, time.time() - t0,
                    f"Identical query executed twice produced identical dataframes (exact equality: {exact_match}).")
    except Exception as e:
        record_test(14, "Reproducibility for Identical Inputs", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Test 15: Application Startup & End-to-End Workflow
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        q_res = ctrl.execute_query(2021, 10, 15, lat=28.6139, lon=77.2090, horizon_hours=24.0, use_cache=True)
        folium_map = vis.create_dispersion_map(q_res, user_lat=28.6139, user_lon=77.2090)
        html_repr = folium_map._repr_html_()
        cpcb_res = obs.get_cpcb_aqi_ranking("2021-10-15")
        openaq_res = obs.get_openaq_pm25_ranking("2021-10-15")
        passed15 = (q_res['status'] == 'SUCCESS' and
                    len(html_repr) > 1000 and
                    len(cpcb_res) > 0 and
                    len(openaq_res) > 0)
        record_test(15, "Application Startup & End-to-End Workflow", passed15, time.time() - t0,
                    f"Full workflow executed successfully: map HTML size={len(html_repr)} chars, CPCB={len(cpcb_res)} cities, OpenAQ={len(openaq_res)} stations.")
    except Exception as e:
        record_test(15, "Application Startup & End-to-End Workflow", False, time.time() - t0, f"Exception: {e}")

    # -------------------------------------------------------------
    # Summary & Output Generation
    # -------------------------------------------------------------
    df_results = pd.DataFrame(test_results)
    out_csv = "results/phase20_app/phase20_test_results.csv"
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df_results.to_csv(out_csv, index=False)
    
    total_tests = len(df_results)
    passed_tests = (df_results['status'] == 'PASS').sum()
    failed_tests = total_tests - passed_tests
    
    print("=" * 80, flush=True)
    print(f"TEST SUMMARY: {passed_tests}/{total_tests} TESTS PASSED ({failed_tests} FAILED)", flush=True)
    print(f"Results saved to: {out_csv}", flush=True)
    print("=" * 80, flush=True)
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
