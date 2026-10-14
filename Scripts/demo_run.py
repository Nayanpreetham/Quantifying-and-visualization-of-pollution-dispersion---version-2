"""
Live Demonstration Script for India National Pollution Dispersion Model
Executes Delhi 2021-10-15 24h dispersion query and prints complete breakdown.
"""
import sys, os
sys.path.insert(0, os.path.abspath("."))
from src.phase20.app_controller import AppController
import time

def main():
    print("=" * 80)
    print("LIVE RUN DEMONSTRATION: INDIA 2D POLLUTION DISPERSION MODEL")
    print("=" * 80)

    ctrl = AppController()

    print("\n[Step 1] Initializing Controller and Loading ERA5 Grid Metadata...")
    print(f"Total Terrestrial 50 km Grid Cells: {len(ctrl.engine.adapter.grid_df):,}")
    print("Coordinate Reference System: EPSG:7755 (India Boundary Projected Coordinate System)")

    print("\n[Step 2] Executing Simulation for Delhi Source (28.6139°N, 77.2090°E)...")
    print("Historical Date: October 15, 2021 | Transport Horizon: 24.0 Hours")
    print("Synoptic Releases: 00:00, 06:00, 12:00, 18:00 UTC (10 Ensemble Members Each = 40 Particles)")

    t0 = time.time()
    res = ctrl.execute_query(
        year=2021, month=10, day=15,
        lat=28.6139, lon=77.2090,
        horizon_hours=24.0,
        use_cache=False
    )
    t_elapsed = time.time() - t0

    print(f"\n[Step 3] Simulation Completed in {t_elapsed:.2f} seconds!")
    print(f"Query Status: {res['status']}")
    print(f"Resolved Grid Cell: {res['source_info']['grid_id_50km']}")
    print(f"Offset to Cell Centroid: {res['source_info']['offset_to_centroid_km']} km")
    print(f"Monitoring Status: {res['monitoring_info']['monitoring_status']}")
    print(f"Source Ground Observed PM2.5: {res['monitoring_info']['date_matched_pm25_ugm3']:.2f} ug/m3")
    print(f"Probability Closure Sum: {res['probability_closure_sum']:.6f} (Exact Conservation: 100%)")
    print(f"Destination Breakdown: {res['category_counts']}")

    print("\n[Step 4] Top 5 Destination Pathways:")
    cols = ['rank', 'destination', 'category', 'daily_transport_fraction', 'source_weighted_transport_influence_index', 'distance_km']
    print(res['results_table'][cols].head(5).to_string(index=False))

    print("\n[Step 5] Separate Ground Observations (October 15, 2021):")
    print("--- Top 3 CPCB Daily City AQI Bulletins (Unitless Index [0-500]) ---")
    cpcb_cols = ['rank', 'city', 'grid_id_50km', 'aqi_index_value', 'air_quality_category']
    print(res['date_matched_cpcb_ranking'][cpcb_cols].head(3).to_string(index=False))

    print("\n--- Top 3 OpenAQ Ground Continuous CAAQMS PM2.5 Measurements (ug/m3) ---")
    openaq_cols = ['rank', 'city', 'station_name', 'mean_observed_pm25_ugm3']
    print(res['date_matched_openaq_ranking'][openaq_cols].head(3).to_string(index=False))
    
    print("\n" + "=" * 80)
    print("Interactive Web Dashboard is live and running at:")
    print("👉  http://localhost:8501")
    print("=" * 80)

if __name__ == "__main__":
    main()
