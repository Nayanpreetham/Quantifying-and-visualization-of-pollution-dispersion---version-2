"""
PHASE 11 — TASK E: MULTI-WEEK TRANSPORT ROBUSTNESS EVALUATION & DIAGNOSTICS
===========================================================================
Evaluates model behavior and stability across 5 weeks of real meteorological
and pollution observations:
1. Wind regime categorization:
   - Low (Calm/Stagnant): w <= 1.5 m/s
   - Medium (Moderate Advection): 1.5 < w < 3.5 m/s
   - High (Ventilation/Strong Advection): w >= 3.5 m/s
2. Advection scaling verification: haversine distance vs theoretical (w * dt).
3. Plume dilution & footprint spread: peak transport fraction and cell count vs dt.
4. Directional alignment: distribution of destination bearing vs wind flow vector.
5. Boundary retention & loss scaling across time windows.
6. Temporal stability across the 5 evaluation weeks (Sep 15 - Oct 20, 2021).
7. High-resolution diagnostic figures generated and copied to artifact directory.

Outputs:
- results/phase11_validation/transport_robustness_summary.csv
- results/phase11_validation/figures/phase11_01_openaq_pm25_multiweek_timeseries.png
- results/phase11_validation/figures/phase11_02_era5_wind_rose_and_regimes.png
- results/phase11_validation/figures/phase11_03_advection_distance_scaling.png
- results/phase11_validation/figures/phase11_04_plume_decay_and_footprint_spread.png
- results/phase11_validation/figures/phase11_05_directional_alignment_histogram.png
- results/phase11_validation/figures/phase11_06_weekly_transport_stability.png
- results/phase11_validation/figures/phase11_07_spatial_dispersion_footprint_composite.png
"""

import os
import sys
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def evaluate_multiweek_robustness(
    aligned_path="data/national/openaq_era5_aligned_phase11.csv",
    targets_path="results/phase11_validation/transport_targets_phase11.csv",
    bnd_path="results/phase11_validation/boundary_statistics_phase11.csv",
    matrix_path="results/phase11_validation/transport_matrix_phase11.csv",
    grid_path="data/national/india_025_grid.csv",
    fig_dir="results/phase11_validation/figures",
    out_dir="results/phase11_validation",
    artifact_dir=r"C:\Users\Nayan preetham\.gemini\antigravity\brain\03c22f0a-5ded-4938-bf05-6a8d57692603"
):
    os.makedirs(fig_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    if os.path.exists(artifact_dir):
        os.makedirs(artifact_dir, exist_ok=True)

    print("[Phase 11 Robustness] Loading datasets...")
    df_aligned = pd.read_csv(aligned_path)
    df_targets = pd.read_csv(targets_path)
    df_bnd = pd.read_csv(bnd_path)
    df_matrix = pd.read_csv(matrix_path)
    df_grid = pd.read_csv(grid_path)

    df_aligned["dt"] = pd.to_datetime(df_aligned["timestamp_utc"]).dt.tz_localize(None)
    df_targets["dt"] = pd.to_datetime(df_targets["timestamp_utc"]).dt.tz_localize(None)
    df_bnd["dt"] = pd.to_datetime(df_bnd["timestamp_utc"]).dt.tz_localize(None)

    # 1. Wind regime categorization
    def categorize_wind(w):
        if w <= 1.5:
            return "Low (<=1.5 m/s)"
        elif w < 3.5:
            return "Medium (1.5-3.5 m/s)"
        else:
            return "High (>=3.5 m/s)"

    df_aligned["wind_regime"] = df_aligned["wind_speed"].apply(categorize_wind)
    df_targets["wind_regime"] = df_targets["wind_speed"].apply(categorize_wind)
    df_bnd["wind_regime"] = df_bnd["wind_speed"].apply(categorize_wind)

    # Assign evaluation week
    min_date = df_aligned["dt"].min()
    df_aligned["week_num"] = ((df_aligned["dt"] - min_date).dt.days // 7) + 1
    df_targets["week_num"] = ((df_targets["dt"] - min_date).dt.days // 7) + 1
    df_bnd["week_num"] = ((df_bnd["dt"] - min_date).dt.days // 7) + 1

    # Clamp week 6 steps into week 5 (35.75 days total)
    df_aligned["week_num"] = df_aligned["week_num"].clip(1, 5)
    df_targets["week_num"] = df_targets["week_num"].clip(1, 5)
    df_bnd["week_num"] = df_bnd["week_num"].clip(1, 5)

    print("[Phase 11 Robustness] Computing robustness summary metrics...")
    
    # Summary by Wind Regime
    regime_summary = []
    for regime in ["Low (<=1.5 m/s)", "Medium (1.5-3.5 m/s)", "High (>=3.5 m/s)"]:
        sub_aligned = df_aligned[df_aligned["wind_regime"] == regime]
        sub_targets = df_targets[df_targets["wind_regime"] == regime]
        sub_bnd = df_bnd[df_bnd["wind_regime"] == regime]

        n_slices = len(sub_aligned)
        mean_ws = sub_aligned["wind_speed"].mean() if n_slices > 0 else 0.0
        mean_pm = sub_aligned["pm25_concentration"].mean() if n_slices > 0 else 0.0

        for dt_h in [1.0, 3.0, 6.0, 12.0, 24.0]:
            tgt_dt = sub_targets[sub_targets["elapsed_time_hours"] == dt_h]
            bnd_dt = sub_bnd[sub_bnd["elapsed_time_hours"] == dt_h]

            mean_dist = tgt_dt["distance_km"].mean() if len(tgt_dt) > 0 else 0.0
            max_dist = tgt_dt["distance_km"].max() if len(tgt_dt) > 0 else 0.0
            mean_angle_err = tgt_dt["rel_angle_to_wind_deg"].mean() if len(tgt_dt) > 0 else 0.0
            mean_peak_frac = tgt_dt.groupby(["timestamp_utc", "station_id"])["transport_fraction"].max().mean() if len(tgt_dt) > 0 else 0.0
            mean_cells = tgt_dt.groupby(["timestamp_utc", "station_id"])["dest_grid_id"].count().mean() if len(tgt_dt) > 0 else 0.0
            bnd_loss = bnd_dt["boundary_loss_fraction"].mean() if len(bnd_dt) > 0 else 0.0

            regime_summary.append({
                "category_type": "WIND_REGIME",
                "category_name": regime,
                "elapsed_time_hours": dt_h,
                "station_step_slices": n_slices,
                "mean_wind_speed_ms": round(mean_ws, 2),
                "mean_pm25_ugm3": round(mean_pm, 2),
                "mean_advection_distance_km": round(mean_dist, 2),
                "max_advection_distance_km": round(max_dist, 2),
                "mean_angle_to_wind_deg": round(mean_angle_err, 2),
                "mean_peak_transport_fraction": round(mean_peak_frac, 4),
                "mean_cells_visited_per_plume": round(mean_cells, 2),
                "mean_boundary_loss_fraction": round(bnd_loss, 4),
                "retention_fraction": round(1.0 - bnd_loss, 4)
            })

    # Summary by Week
    week_names = {
        1: "Week 1 (Sep 15 - Sep 21)",
        2: "Week 2 (Sep 22 - Sep 28)",
        3: "Week 3 (Sep 29 - Oct 05)",
        4: "Week 4 (Oct 06 - Oct 12)",
        5: "Week 5 (Oct 13 - Oct 20)"
    }
    for w_idx in range(1, 6):
        sub_aligned = df_aligned[df_aligned["week_num"] == w_idx]
        sub_targets = df_targets[df_targets["week_num"] == w_idx]
        sub_bnd = df_bnd[df_bnd["week_num"] == w_idx]

        n_slices = len(sub_aligned)
        mean_ws = sub_aligned["wind_speed"].mean() if n_slices > 0 else 0.0
        mean_pm = sub_aligned["pm25_concentration"].mean() if n_slices > 0 else 0.0

        for dt_h in [6.0, 24.0]: # key synoptic windows for week summary
            tgt_dt = sub_targets[sub_targets["elapsed_time_hours"] == dt_h]
            bnd_dt = sub_bnd[sub_bnd["elapsed_time_hours"] == dt_h]

            mean_dist = tgt_dt["distance_km"].mean() if len(tgt_dt) > 0 else 0.0
            max_dist = tgt_dt["distance_km"].max() if len(tgt_dt) > 0 else 0.0
            mean_angle_err = tgt_dt["rel_angle_to_wind_deg"].mean() if len(tgt_dt) > 0 else 0.0
            mean_peak_frac = tgt_dt.groupby(["timestamp_utc", "station_id"])["transport_fraction"].max().mean() if len(tgt_dt) > 0 else 0.0
            mean_cells = tgt_dt.groupby(["timestamp_utc", "station_id"])["dest_grid_id"].count().mean() if len(tgt_dt) > 0 else 0.0
            bnd_loss = bnd_dt["boundary_loss_fraction"].mean() if len(bnd_dt) > 0 else 0.0

            regime_summary.append({
                "category_type": "TEMPORAL_WEEK",
                "category_name": week_names[w_idx],
                "elapsed_time_hours": dt_h,
                "station_step_slices": n_slices,
                "mean_wind_speed_ms": round(mean_ws, 2),
                "mean_pm25_ugm3": round(mean_pm, 2),
                "mean_advection_distance_km": round(mean_dist, 2),
                "max_advection_distance_km": round(max_dist, 2),
                "mean_angle_to_wind_deg": round(mean_angle_err, 2),
                "mean_peak_transport_fraction": round(mean_peak_frac, 4),
                "mean_cells_visited_per_plume": round(mean_cells, 2),
                "mean_boundary_loss_fraction": round(bnd_loss, 4),
                "retention_fraction": round(1.0 - bnd_loss, 4)
            })

    df_robustness = pd.DataFrame(regime_summary)
    rob_csv = os.path.join(out_dir, "transport_robustness_summary.csv")
    df_robustness.to_csv(rob_csv, index=False)
    print(f"[Phase 11 Robustness] Saved robustness summary: {rob_csv} ({len(df_robustness)} rows)")

    # -------------------------------------------------------------
    # GENERATE 7 PUBLICATION FIGURES
    # -------------------------------------------------------------
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig_paths = []

    # Fig 1: Multi-week PM2.5 Time Series across representative stations
    fig1_path = os.path.join(fig_dir, "phase11_01_openaq_pm25_multiweek_timeseries.png")
    fig, ax = plt.subplots(figsize=(14, 6), dpi=150)
    rep_stations = [227931, 229252, 228403, 227534, 233415]
    colors = ["#d95f02", "#7570b3", "#1b9e77", "#e7298a", "#66a61e"]
    for s_id, col in zip(rep_stations, colors):
        sub = df_aligned[df_aligned["station_id"] == s_id].sort_values("dt")
        if len(sub) > 0:
            st_name = sub["station_name"].iloc[0]
            city = sub["city"].iloc[0]
            ax.plot(sub["dt"], sub["pm25_concentration"], marker="o", markersize=3, alpha=0.75, color=col, label=f"{city} ({s_id})")
    ax.axhline(60, color="red", linestyle="--", alpha=0.7, label="India 24h NAAQS Standard (60 µg/m³)")
    ax.set_title("Figure 1: Multi-Week Real PM2.5 In-Situ Observations Across Indian Nodes\n(September 15 – October 20, 2021, 5-Week Pilot)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Date (UTC)", fontsize=11)
    ax.set_ylabel("PM2.5 Concentration (µg/m³)", fontsize=11)
    ax.legend(loc="upper right", frameon=True, fontsize=9)
    plt.tight_layout()
    plt.savefig(fig1_path)
    plt.close()
    fig_paths.append(fig1_path)
    print(f"[Phase 11 Figures] Generated Fig 1: {fig1_path}")

    # Fig 2: ERA5 Wind Speed Distribution & Regimes
    fig2_path = os.path.join(fig_dir, "phase11_02_era5_wind_rose_and_regimes.png")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)
    # Histogram of wind speed
    ws = df_aligned["wind_speed"]
    ax1.hist(ws, bins=25, color="#2b83ba", edgecolor="black", alpha=0.7)
    ax1.axvline(1.5, color="#d7191c", linestyle="--", linewidth=1.5, label="Calm Boundary (1.5 m/s)")
    ax1.axvline(3.5, color="#fdae61", linestyle="--", linewidth=1.5, label="High Wind Boundary (3.5 m/s)")
    ax1.set_title("ERA5 Surface Wind Speed Distribution (N=847 Slices)", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Wind Speed (m/s)", fontsize=10)
    ax1.set_ylabel("Frequency", fontsize=10)
    ax1.legend(loc="upper right", frameon=True)

    # Bar chart of regime proportions
    regime_counts = df_aligned["wind_regime"].value_counts()
    regime_order = ["Low (<=1.5 m/s)", "Medium (1.5-3.5 m/s)", "High (>=3.5 m/s)"]
    counts = [regime_counts.get(r, 0) for r in regime_order]
    bar_cols = ["#d7191c", "#abd9e9", "#2c7bb6"]
    bars = ax2.bar(regime_order, counts, color=bar_cols, edgecolor="black", alpha=0.85)
    for b in bars:
        h = b.get_height()
        pct = (h / len(df_aligned)) * 100
        ax2.annotate(f"{h}\n({pct:.1f}%)", xy=(b.get_x() + b.get_width() / 2, h / 2),
                     xytext=(0, 0), textcoords="offset points", ha="center", va="center", fontsize=10, fontweight="bold", color="white")
    ax2.set_title("Categorized Wind Regimes Proportions", fontsize=12, fontweight="bold")
    ax2.set_ylabel("Number of Synoptic Slices", fontsize=10)
    plt.suptitle("Figure 2: Multi-Week Meteorological Wind Forcing Distribution", fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(fig2_path)
    plt.close()
    fig_paths.append(fig2_path)
    print(f"[Phase 11 Figures] Generated Fig 2: {fig2_path}")

    # Fig 3: Advection Distance Scaling (Theory vs Actual)
    fig3_path = os.path.join(fig_dir, "phase11_03_advection_distance_scaling.png")
    fig, ax = plt.subplots(figsize=(9, 6), dpi=150)
    reg_colors = {"Low (<=1.5 m/s)": "#d7191c", "Medium (1.5-3.5 m/s)": "#2b83ba", "High (>=3.5 m/s)": "#1a9641"}
    windows = [1.0, 3.0, 6.0, 12.0, 24.0]
    for regime, col in reg_colors.items():
        sub_reg = [r for r in regime_summary if r["category_type"] == "WIND_REGIME" and r["category_name"] == regime]
        dists = [r["mean_advection_distance_km"] for r in sub_reg]
        ws_val = sub_reg[0]["mean_wind_speed_ms"]
        ax.plot(windows, dists, marker="o", linewidth=2, color=col, label=f"{regime} (mean w={ws_val} m/s)")
        # Plot theoretical line
        theory_dists = [ws_val * 3.6 * dt for dt in windows]
        ax.plot(windows, theory_dists, linestyle=":", color=col, alpha=0.6)
    ax.set_title("Figure 3: Advection Distance Scaling vs Elapsed Time by Wind Regime\n(Solid = Observed Model Trajectory Distance, Dotted = Kinematic Theory $d = w \\cdot \\Delta t$)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Elapsed Time Window (Hours)", fontsize=11)
    ax.set_ylabel("Mean Advection Distance (km)", fontsize=11)
    ax.set_xticks(windows)
    ax.legend(loc="upper left", frameon=True)
    plt.tight_layout()
    plt.savefig(fig3_path)
    plt.close()
    fig_paths.append(fig3_path)
    print(f"[Phase 11 Figures] Generated Fig 3: {fig3_path}")

    # Fig 4: Plume Dilution & Footprint Spread
    fig4_path = os.path.join(fig_dir, "phase11_04_plume_decay_and_footprint_spread.png")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)
    for regime, col in reg_colors.items():
        sub_reg = [r for r in regime_summary if r["category_type"] == "WIND_REGIME" and r["category_name"] == regime]
        peaks = [r["mean_peak_transport_fraction"] for r in sub_reg]
        cells = [r["mean_cells_visited_per_plume"] for r in sub_reg]
        ax1.plot(windows, peaks, marker="s", linewidth=2, color=col, label=regime)
        ax2.plot(windows, cells, marker="^", linewidth=2, color=col, label=regime)
    ax1.set_title("Peak Transport Fraction Decay ($T_{max}$)", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Elapsed Time Window (Hours)", fontsize=10)
    ax1.set_ylabel("Peak Fraction $T_{max}$", fontsize=10)
    ax1.set_xticks(windows)
    ax1.legend(loc="upper right", frameon=True)

    ax2.set_title("Spatial Footprint Spread (Grid Cells Visited)", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Elapsed Time Window (Hours)", fontsize=10)
    ax2.set_ylabel("Mean Visited Grid Cells ($0.25^\\circ$)", fontsize=10)
    ax2.set_xticks(windows)
    ax2.legend(loc="upper left", frameon=True)

    plt.suptitle("Figure 4: Gaussian Ensemble Plume Diffusion & Spatial Dilution Dynamics", fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(fig4_path)
    plt.close()
    fig_paths.append(fig4_path)
    print(f"[Phase 11 Figures] Generated Fig 4: {fig4_path}")

    # Fig 5: Directional Alignment Histogram
    fig5_path = os.path.join(fig_dir, "phase11_05_directional_alignment_histogram.png")
    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    # Significant transport records: distance > 20 km to avoid collocated roundoff
    sig_tgt = df_targets[df_targets["distance_km"] >= 20.0]
    ax.hist(sig_tgt["rel_angle_to_wind_deg"], bins=36, color="#41b6c4", edgecolor="black", alpha=0.8)
    median_angle = sig_tgt["rel_angle_to_wind_deg"].median()
    mean_angle = sig_tgt["rel_angle_to_wind_deg"].mean()
    p90_angle = sig_tgt["rel_angle_to_wind_deg"].quantile(0.90)
    ax.axvline(median_angle, color="#d95f02", linestyle="-", linewidth=2, label=f"Median Error ({median_angle:.1f}°)")
    ax.axvline(p90_angle, color="#e7298a", linestyle="--", linewidth=1.5, label=f"90th Percentile ({p90_angle:.1f}°)")
    ax.set_title("Figure 5: Physical Vector Alignment Between Wind Flow & Transport Destination\n(N=22,468 Non-Collocated Transport Slices, d >= 20 km)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Relative Angular Deviation from Wind Vector (°)", fontsize=11)
    ax.set_ylabel("Transport Target Count", fontsize=11)
    ax.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    plt.savefig(fig5_path)
    plt.close()
    fig_paths.append(fig5_path)
    print(f"[Phase 11 Figures] Generated Fig 5: {fig5_path}")

    # Fig 6: Weekly Transport Stability (5 Weeks)
    fig6_path = os.path.join(fig_dir, "phase11_06_weekly_transport_stability.png")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)
    w_labels = [f"W{i}" for i in range(1, 6)]
    # 6h distance across weeks
    sub_w_6h = [r for r in regime_summary if r["category_type"] == "TEMPORAL_WEEK" and r["elapsed_time_hours"] == 6.0]
    w_dists_6h = [r["mean_advection_distance_km"] for r in sub_w_6h]
    w_pm = [r["mean_pm25_ugm3"] for r in sub_w_6h]
    w_ws = [r["mean_wind_speed_ms"] for r in sub_w_6h]

    ax1.plot(w_labels, w_dists_6h, marker="o", color="#2c7bb6", linewidth=2, label="6h Advection Distance (km)")
    ax1.set_title("6-Hour Mean Advection Distance Across 5 Weeks", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Pilot Week (Sep 15 - Oct 20, 2021)", fontsize=10)
    ax1.set_ylabel("Distance (km)", fontsize=10)
    ax1.legend(loc="upper right", frameon=True)

    ax2.plot(w_labels, w_ws, marker="s", color="#fdae61", linewidth=2, label="Mean Wind Speed (m/s)")
    ax2_twin = ax2.twinx()
    ax2_twin.plot(w_labels, w_pm, marker="^", color="#d7191c", linewidth=2, linestyle="--", label="Mean PM2.5 (µg/m³)")
    ax2.set_title("Meteorology vs Pollution Evolution", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Pilot Week (Sep 15 - Oct 20, 2021)", fontsize=10)
    ax2.set_ylabel("Wind Speed (m/s)", fontsize=10)
    ax2_twin.set_ylabel("PM2.5 (µg/m³)", fontsize=10)
    ax2.legend(loc="upper left", frameon=True)
    ax2_twin.legend(loc="upper right", frameon=True)

    plt.suptitle("Figure 6: Multi-Week Temporal Stability & Monsoon-Postmonsoon Transition", fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(fig6_path)
    plt.close()
    fig_paths.append(fig6_path)
    print(f"[Phase 11 Figures] Generated Fig 6: {fig6_path}")

    # Fig 7: Spatial Dispersion Footprint Composite
    fig7_path = os.path.join(fig_dir, "phase11_07_spatial_dispersion_footprint_composite.png")
    fig, ax = plt.subplots(figsize=(12, 10), dpi=150)
    # Background national grid points
    ax.scatter(df_grid["longitude"], df_grid["latitude"], s=1, color="lightgray", alpha=0.3, label="National 0.25° Domain")

    # Aggregate 6h transport influence across the entire 5 weeks
    m_6h = df_matrix[(df_matrix["elapsed_time_hours"] == 6.0) & (df_matrix["dest_grid_id"] != "OUTSIDE_DOMAIN")]
    dest_grouped = m_6h.groupby("dest_grid_id").agg(
        total_influence=("mean_transport_influence", "sum"),
        dest_visited=("visited_steps_count", "sum")
    ).reset_index()

    dest_merged = pd.merge(dest_grouped, df_grid, left_on="dest_grid_id", right_on="grid_id", how="inner")
    sc = ax.scatter(
        dest_merged["longitude"], dest_merged["latitude"],
        c=dest_merged["total_influence"], cmap="YlOrRd", s=25, alpha=0.85,
        edgecolor="none"
    )
    cbar = plt.colorbar(sc, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Multi-Week Cumulative 6-Hour Transported Influence (µg/m³)", fontsize=10)

    # Plot source station locations
    st_info = df_aligned.groupby(["station_id", "city", "latitude", "longitude"]).size().reset_index()
    ax.scatter(st_info["longitude"], st_info["latitude"], marker="*", s=120, color="blue", edgecolor="black", zorder=5, label="Source Monitoring Stations")
    for _, st in st_info.iterrows():
        ax.annotate(f"{st['city']}", xy=(st["longitude"], st["latitude"]), xytext=(5, 5), textcoords="offset points", fontsize=9, fontweight="bold", color="darkblue")

    ax.set_title("Figure 7: Multi-Week Cumulative 6-Hour Dispersion Footprint Across India\n(September 15 – October 20, 2021, Continuous 5-Week Pilot)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Longitude (°E)", fontsize=11)
    ax.set_ylabel("Latitude (°N)", fontsize=11)
    ax.set_xlim(68, 97)
    ax.set_ylim(8, 36)
    ax.legend(loc="lower left", frameon=True)
    plt.tight_layout()
    plt.savefig(fig7_path)
    plt.close()
    fig_paths.append(fig7_path)
    print(f"[Phase 11 Figures] Generated Fig 7: {fig7_path}")

    # Copy all figures to artifact directory
    if os.path.exists(artifact_dir):
        print(f"[Phase 11 Figures] Copying {len(fig_paths)} figures to artifact directory: {artifact_dir}")
        for fp in fig_paths:
            dst = os.path.join(artifact_dir, os.path.basename(fp))
            shutil.copyfile(fp, dst)
            print(f"  -> Copied {os.path.basename(fp)}")

    return df_robustness

if __name__ == "__main__":
    evaluate_multiweek_robustness()
