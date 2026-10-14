"""
SEASONAL REGIONAL ROBUSTNESS TEST: EARLY WINTER / DIWALI INVERSION
===================================================================
Phase 7 Step 5: Evaluates the continuous 0.25° regional dispersion model
under an extreme contrasting meteorological and pollution regime:
- Period: November 01, 2021 00:00 UTC to November 04, 2021 18:00 UTC (16 synoptic steps).
- Atmospheric Regime: Severe post-monsoon winter boundary-layer trapping & Diwali episodic peaks.
- Observed PM2.5: Kanpur (mean 136 µg/m³, max >1000 µg/m³), Varanasi (mean 88 µg/m³, max >1400 µg/m³),
  Chandigarh (mean 71 µg/m³).
- Preserves all original October 2021 outputs untouched.

Outputs:
- data/regional/seasonal_winter/era5_wind_winter.nc
- data/regional/seasonal_winter/era5_wind_winter.csv
- data/regional/seasonal_winter/openaq_era5_aligned_winter.csv
- results/regional_seasonal_winter/transport_targets_winter.csv
- results/regional_seasonal_winter/transport_matrix_winter.csv
- results/regional_seasonal_winter/boundary_loss_statistics_winter.csv
- results/regional_seasonal_winter/winter_dispersion_summary.csv
- results/regional_seasonal_winter/figures/
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.synthetic.physics_2d_dispersion import (
    run_ensemble_dispersion,
    calculate_bearing_deg,
    calculate_haversine_distance_km
)
from src.regional.physics_2d_regional_dispersion import map_particle_to_continuous_grid

DATA_LABEL = "REGIONAL SEASONAL TEST — WINTER INVERSION (NOV 2021)"

START_TIME = "2021-11-01 00:00"
END_TIME = "2021-11-04 18:00"
LAT_MAX = 32.0
LAT_MIN = 24.0
LON_MIN = 74.0
LON_MAX = 88.0
GRID_RES = 0.25


def run_winter_seasonal_pipeline(data_out_dir="data/regional/seasonal_winter",
                                results_dir="results/regional_seasonal_winter"):
    os.makedirs(data_out_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    figures_dir = os.path.join(results_dir, "figures")
    os.makedirs(figures_dir, exist_ok=True)

    print("=" * 70)
    print("STARTING REGIONAL SEASONAL TEST: EARLY WINTER / DIWALI INVERSION (NOV 2021)")
    print("=" * 70)

    # 1. Load continuous regional grid & corrected station mapping
    grid_df = pd.read_csv("data/regional/igp_025_grid.csv")
    map_df = pd.read_csv("data/regional/station_to_grid_mapping_corrected.csv")
    matched_stations = map_df[map_df["match_status"] == "MATCHED"].copy()

    # 2. Extract ERA5 wind for November 01-04, 2021
    raw_nc = "data/raw/era5/2021/era5_2021_instant.nc"
    print(f"[Winter Test] Opening raw ERA5: {raw_nc}")
    ds = xr.open_dataset(raw_nc)
    t_coord = "valid_time" if "valid_time" in ds.coords else "time"

    ds_slice = ds[["u10", "v10"]].sel({t_coord: slice(START_TIME, END_TIME)})
    ds_sub = ds_slice.sel(latitude=slice(LAT_MAX, LAT_MIN), longitude=slice(LON_MIN, LON_MAX))
    nc_out = os.path.join(data_out_dir, "era5_wind_winter.nc")
    ds_sub.to_netcdf(nc_out)
    print(f"[Winter Test] Saved winter ERA5 NetCDF: {nc_out}")

    times = ds_sub[t_coord].values
    wind_records = []
    for t_idx, t in enumerate(times):
        t_dt = pd.to_datetime(t)
        t_str = t_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        ds_t = ds_sub.sel({t_coord: t})

        u_grid = ds_t["u10"].values
        v_grid = ds_t["v10"].values

        for _, g in grid_df.iterrows():
            r = int(g["row"])
            c = int(g["column"])
            u = float(u_grid[r, c])
            v = float(v_grid[r, c])
            w_speed = float(np.sqrt(u**2 + v**2))
            w_dir = float((270.0 - np.degrees(np.arctan2(v, u))) % 360.0)

            wind_records.append({
                "timestamp_utc": t_str,
                "synoptic_step": t_idx,
                "grid_id": g["grid_id"],
                "row": r,
                "column": c,
                "latitude": g["latitude"],
                "longitude": g["longitude"],
                "u10": round(u, 3),
                "v10": round(v, 3),
                "wind_speed": round(w_speed, 3),
                "wind_direction_deg": round(w_dir, 1),
                "data_label": DATA_LABEL
            })
    df_wind = pd.DataFrame(wind_records)
    csv_wind_out = os.path.join(data_out_dir, "era5_wind_winter.csv")
    df_wind.to_csv(csv_wind_out, index=False)
    print(f"[Winter Test] Saved winter tabular winds: {csv_wind_out} ({len(df_wind)} records)")
    ds.close()

    # 3. Ingest OpenAQ observations for November 01-04, 2021
    obs_df = pd.read_csv("data/real/openaq/pm25_observations.csv")
    obs_df["dt"] = pd.to_datetime(obs_df["timestamp_utc"]).dt.tz_localize(None)
    sub_obs = obs_df[(obs_df["station_id"].isin(matched_stations["station_id"])) & (obs_df["dt"] >= START_TIME) & (obs_df["dt"] <= END_TIME)].copy()

    merged = sub_obs.merge(
        matched_stations[["station_id", "matched_grid_id", "corrected_city"]],
        on="station_id",
        how="inner"
    )

    synoptic_times = pd.date_range(START_TIME, END_TIME, freq="6h")
    pol_records = []
    for t_idx, t in enumerate(synoptic_times):
        t_str = pd.to_datetime(t).strftime("%Y-%m-%d %H:%M:%S UTC")
        t_low = t - pd.Timedelta(hours=1)
        t_high = t + pd.Timedelta(hours=1)
        t_win = merged[(merged["dt"] >= t_low) & (merged["dt"] <= t_high)]

        grouped = t_win.groupby(["matched_grid_id", "station_id", "station_name", "corrected_city"]).agg(
            pm25_mean=("pm25", "mean"),
            sample_count=("pm25", "count")
        ).reset_index()

        for _, row in grouped.iterrows():
            grid_info = grid_df[grid_df["grid_id"] == row["matched_grid_id"]].iloc[0]
            pol_records.append({
                "timestamp_utc": t_str,
                "synoptic_step": t_idx,
                "grid_id": row["matched_grid_id"],
                "station_id": int(row["station_id"]),
                "station_name": row["station_name"],
                "city": row["corrected_city"],
                "grid_latitude": grid_info["latitude"],
                "grid_longitude": grid_info["longitude"],
                "pm25_concentration": round(float(row["pm25_mean"]), 2),
                "hourly_samples": int(row["sample_count"]),
                "is_source_grid": True,
                "data_label": DATA_LABEL
            })

    df_pol = pd.DataFrame(pol_records)
    print(f"[Winter Test] Extracted active winter source observations: {len(df_pol)} station-step records")

    # 4. Align observations with grid wind
    aligned = pd.merge(
        df_pol,
        df_wind[["timestamp_utc", "grid_id", "u10", "v10", "wind_speed", "wind_direction_deg"]],
        on=["timestamp_utc", "grid_id"],
        how="inner"
    )
    aligned_out = os.path.join(data_out_dir, "openaq_era5_aligned_winter.csv")
    aligned.to_csv(aligned_out, index=False)
    print(f"[Winter Test] Saved aligned dataset: {aligned_out} ({len(aligned)} records across {len(aligned['station_id'].unique())} stations)")

    # 5. Run 2D Physics Ensemble Dispersion
    n_ensemble = 20
    elapsed_time_windows = [1.0, 3.0, 6.0, 12.0, 24.0]
    records = []
    boundary_stats = []
    grid_lookup = grid_df.set_index("grid_id")[["latitude", "longitude"]].to_dict(orient="index")

    for _, src_row in aligned.iterrows():
        s_id = int(src_row["station_id"])
        s_name = str(src_row["station_name"])
        s_city = str(src_row["city"])
        src_grid_id = str(src_row["grid_id"])
        src_lat = float(src_row["grid_latitude"])
        src_lon = float(src_row["grid_longitude"])
        t_str = str(src_row["timestamp_utc"])
        step_idx = int(src_row["synoptic_step"])

        u10 = float(src_row["u10"])
        v10 = float(src_row["v10"])
        w_speed = float(src_row["wind_speed"])
        w_dir = float(src_row["wind_direction_deg"])
        src_pm25 = float(src_row["pm25_concentration"])
        wind_flow_dir = (90.0 - np.degrees(np.arctan2(v10, u10))) % 360.0

        for dt_h in elapsed_time_windows:
            particles = run_ensemble_dispersion(
                src_lat, src_lon, u10, v10, dt_h,
                n_ensemble=n_ensemble,
                random_seed=42 + step_idx * 100 + int(dt_h)
            )

            dest_counts = {}
            outside_count = 0

            for p_lat, p_lon in particles:
                dest_id, is_inside, _, _ = map_particle_to_continuous_grid(p_lat, p_lon)
                if is_inside:
                    dest_counts[dest_id] = dest_counts.get(dest_id, 0) + 1
                else:
                    outside_count += 1

            inside_count = sum(dest_counts.values())
            inside_fraction = float(inside_count) / float(n_ensemble)
            boundary_loss_fraction = float(outside_count) / float(n_ensemble)

            boundary_stats.append({
                "timestamp_utc": t_str,
                "synoptic_step": step_idx,
                "station_id": s_id,
                "station_name": s_name,
                "city": s_city,
                "source_grid_id": src_grid_id,
                "elapsed_time_hours": dt_h,
                "wind_speed": w_speed,
                "ensemble_n": n_ensemble,
                "particles_inside": inside_count,
                "particles_outside": outside_count,
                "inside_fraction": round(inside_fraction, 4),
                "boundary_loss_fraction": round(boundary_loss_fraction, 4),
                "mass_conservation_sum": round(inside_fraction + boundary_loss_fraction, 4),
                "data_label": DATA_LABEL
            })

            # Record non-zero active destination cells
            for dest_id, count in dest_counts.items():
                dest_info = grid_lookup[dest_id]
                dest_lat = dest_info["latitude"]
                dest_lon = dest_info["longitude"]

                t_frac = float(count) / float(n_ensemble)
                t_influence = round(src_pm25 * t_frac, 3)

                rel_dx = round(dest_lon - src_lon, 4)
                rel_dy = round(dest_lat - src_lat, 4)
                dist_km = round(calculate_haversine_distance_km(src_lat, src_lon, dest_lat, dest_lon), 2)

                if dist_km > 0.1:
                    dest_bearing = calculate_bearing_deg(src_lat, src_lon, dest_lat, dest_lon)
                    rel_angle = abs((dest_bearing - wind_flow_dir + 180.0) % 360.0 - 180.0)
                else:
                    dest_bearing = wind_flow_dir
                    rel_angle = 0.0

                records.append({
                    "timestamp_utc": t_str,
                    "synoptic_step": step_idx,
                    "station_id": s_id,
                    "station_name": s_name,
                    "city": s_city,
                    "source_grid_id": src_grid_id,
                    "dest_grid_id": dest_id,
                    "source_lat": src_lat,
                    "source_lon": src_lon,
                    "dest_lat": dest_lat,
                    "dest_lon": dest_lon,
                    "elapsed_time_hours": dt_h,
                    "rel_dx": rel_dx,
                    "rel_dy": rel_dy,
                    "distance_km": dist_km,
                    "u10": u10,
                    "v10": v10,
                    "wind_speed": w_speed,
                    "wind_direction_deg": w_dir,
                    "wind_flow_dir_deg": round(wind_flow_dir, 1),
                    "dest_bearing_deg": round(dest_bearing, 1),
                    "rel_angle_to_wind_deg": round(rel_angle, 1),
                    "source_pm25": src_pm25,
                    "particle_count": count,
                    "ensemble_n": n_ensemble,
                    "transport_fraction": round(t_frac, 4),
                    "transport_influence": t_influence,
                    "data_label": DATA_LABEL
                })

    df_out = pd.DataFrame(records)
    target_path = os.path.join(results_dir, "transport_targets_winter.csv")
    df_out.to_csv(target_path, index=False)
    print(f"[Winter Test] Saved winter transport targets: {target_path} ({len(df_out)} active pairs)")

    df_bnd = pd.DataFrame(boundary_stats)
    bnd_path = os.path.join(results_dir, "boundary_loss_statistics_winter.csv")
    df_bnd.to_csv(bnd_path, index=False)
    print(f"[Winter Test] Saved winter boundary statistics: {bnd_path} ({len(df_bnd)} runs)")

    matrix_df = df_out.groupby(["station_id", "station_name", "city", "source_grid_id", "dest_grid_id", "elapsed_time_hours"]).agg(
        mean_transport_fraction=("transport_fraction", "mean"),
        max_transport_fraction=("transport_fraction", "max"),
        mean_transport_influence=("transport_influence", "mean"),
        max_transport_influence=("transport_influence", "max"),
        distance_km=("distance_km", "first")
    ).reset_index()
    matrix_path = os.path.join(results_dir, "transport_matrix_winter.csv")
    matrix_df.to_csv(matrix_path, index=False)
    print(f"[Winter Test] Saved aggregated winter matrix: {matrix_path} ({len(matrix_df)} matrix pairs)")

    # 6. Generate Comparison Figures
    # Figure: Winter PM2.5 Inversion Spike vs Dispersion Footprint
    fig, ax = plt.subplots(figsize=(10, 5))
    for c_name in df_pol["city"].unique():
        c_sub = df_pol[df_pol["city"] == c_name].groupby("timestamp_utc")["pm25_concentration"].mean()
        t_plot = [pd.to_datetime(t) for t in c_sub.index]
        ax.plot(t_plot, c_sub.values, marker="s", label=c_name, linewidth=2)
    ax.set_ylabel("Observed PM2.5 (µg/m³)", fontsize=11)
    ax.set_xlabel("Time (UTC)", fontsize=11)
    ax.set_title("Early Winter / Diwali Episodic PM2.5 Peaks (Nov 01–04, 2021)\nIndo-Gangetic Plain Stations", fontsize=12, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.savefig(os.path.join(figures_dir, "01_winter_pm25_timeseries.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    # Figure: Winter Footprint under Stagnant Wind
    fig, ax = plt.subplots(figsize=(10, 6))
    sample_t = "2021-11-04 12:00:00 UTC"  # Diwali day synoptic step
    sub_foot = df_out[(df_out["timestamp_utc"] == sample_t) & (df_out["elapsed_time_hours"] == 12.0)]
    sc = ax.scatter(sub_foot["dest_lon"], sub_foot["dest_lat"], c=sub_foot["transport_influence"], cmap="hot_r", s=180, marker="s")
    plt.colorbar(sc, label="Transport Influence (µg/m³)")
    ax.scatter(sub_foot["source_lon"], sub_foot["source_lat"], color="blue", marker="*", s=220, label="Diwali Source Stations", zorder=5)
    for _, s in sub_foot.groupby("city").first().reset_index().iterrows():
        ax.annotate(f"{s['city']} ({s['source_pm25']:.0f} µg/m³)", (s["source_lon"] + 0.15, s["source_lat"] + 0.1), fontsize=9, fontweight="bold")
    ax.set_xlim(74.0, 88.0)
    ax.set_ylim(24.0, 32.0)
    ax.set_xlabel("Longitude (°E)", fontsize=11)
    ax.set_ylabel("Latitude (°N)", fontsize=11)
    ax.set_title(f"Winter Inversion Pollution Footprint on Continuous 0.25° Grid\n[Diwali Episode: {sample_t}, dt=12h]", fontsize=11, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper right")
    fig.savefig(os.path.join(figures_dir, "02_winter_diwali_dispersion_footprint.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"[Winter Test] Visualizations saved in: {figures_dir}")
    print("=" * 70)
    print("SEASONAL TEST PIPELINE COMPLETE!")
    print("=" * 70)
    return df_out, df_bnd


if __name__ == "__main__":
    run_winter_seasonal_pipeline()
