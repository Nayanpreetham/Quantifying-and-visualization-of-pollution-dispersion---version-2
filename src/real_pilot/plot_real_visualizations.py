"""
REAL PILOT VISUALIZATION SUITE
==============================
Generates diagnostic maps and charts for the Real-Data 2D Dispersion Pilot:
1. 01_real_pilot_cities_map.png
2. 02_real_era5_wind_field.png
3. 03_real_openaq_pm25_map.png
4. 04_real_physics_dispersion_map.png
5. 05_real_transport_matrix.png
6. 06_real_dispersion_vs_distance.png
7. 07_real_downwind_vs_upwind.png
8. 08_real_ensemble_stability.png

Output Directory: results/real_pilot/figures/
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def generate_all_real_plots(data_dir="data/processed",
                            results_dir="results/real_pilot",
                            figures_dir="results/real_pilot/figures"):
    os.makedirs(figures_dir, exist_ok=True)

    grid_path = os.path.join(data_dir, "real_grid.csv")
    aligned_path = os.path.join(data_dir, "openaq_era5_aligned.csv")
    target_path = os.path.join(results_dir, "transport_targets.csv")
    stab_path = os.path.join(results_dir, "ensemble_stability_benchmark.csv")

    grid_df = pd.read_csv(grid_path)
    aligned_df = pd.read_csv(aligned_path)
    df = pd.read_csv(target_path)

    print("[Plot Generator] Generating real pilot visualizations...")

    # -------------------------------------------------------------
    # Figure 1: Pilot Cities Geographic Distribution
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 6))
    centers = grid_df[grid_df["is_city_center"] == True]
    ax.scatter(centers["longitude"], centers["latitude"], color="crimson", s=120, zorder=5, label="Pilot City Centers")
    for _, r in centers.iterrows():
        ax.annotate(r["city_name"], (r["longitude"] + 0.2, r["latitude"] + 0.1), fontsize=11, fontweight="bold")
    ax.set_xlim(70, 86)
    ax.set_ylim(21, 33)
    ax.set_xlabel("Longitude (°E)", fontsize=11)
    ax.set_ylabel("Latitude (°N)", fontsize=11)
    ax.set_title("Real Data Pilot — 5 Selected Indian Monitoring Hubs", fontsize=13, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper left")
    p1 = os.path.join(figures_dir, "01_real_pilot_cities_map.png")
    fig.savefig(p1, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 2: Real ERA5 Wind Vector Field
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 6))
    # Sample timestamp: 2021-09-23 06:00:00 UTC
    t_sample = "2021-09-23 06:00:00 UTC"
    t_wind = aligned_df[aligned_df["timestamp_utc"] == t_sample]
    q = ax.quiver(
        t_wind["longitude"], t_wind["latitude"],
        t_wind["u10"], t_wind["v10"],
        t_wind["wind_speed"],
        cmap="viridis", scale=60, width=0.003
    )
    plt.colorbar(q, label="Wind Speed (m/s)")
    ax.set_xlabel("Longitude (°E)", fontsize=11)
    ax.set_ylabel("Latitude (°N)", fontsize=11)
    ax.set_title(f"Real ERA5 Surface Wind Vectors (U10, V10)\n[{t_sample}]", fontsize=12, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    p2 = os.path.join(figures_dir, "02_real_era5_wind_field.png")
    fig.savefig(p2, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 3: OpenAQ Observed PM2.5 Concentrations
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    monitored = aligned_df[aligned_df["is_monitored_cell"] == True]
    city_pm = monitored.groupby("city_name")["pm25_concentration"].mean().sort_values(ascending=False)
    bars = ax.bar(city_pm.index, city_pm.values, color="royalblue", edgecolor="black", alpha=0.85)
    for b in bars:
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.5, f"{b.get_height():.1f}", ha="center", fontsize=10, fontweight="bold")
    ax.set_ylabel("Mean PM2.5 (µg/m³)", fontsize=11)
    ax.set_title("OpenAQ Real Station Observed PM2.5 (Sep 23–25, 2021)", fontsize=12, fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    p3 = os.path.join(figures_dir, "03_real_openaq_pm25_map.png")
    fig.savefig(p3, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 4: Real Physics Dispersion Map (Kanpur, dt=3h)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 6))
    knp_sub = df[(df["city_id"] == "KNP") & (df["elapsed_time_hours"] == 3.0) & (df["timestamp_utc"] == t_sample)]
    piv = knp_sub.pivot(index="dest_lat", columns="dest_lon", values="transport_influence").sort_index(ascending=False)
    im = ax.imshow(piv.values, cmap="YlOrRd", extent=[knp_sub["dest_lon"].min(), knp_sub["dest_lon"].max(), knp_sub["dest_lat"].min(), knp_sub["dest_lat"].max()])
    plt.colorbar(im, label="Transport Influence (µg/m³)")
    # Mark source
    src_pt = knp_sub.iloc[0]
    ax.scatter(src_pt["source_lon"], src_pt["source_lat"], color="blue", marker="*", s=250, label="Source Station (Kanpur)")
    ax.set_xlabel("Longitude (°E)", fontsize=11)
    ax.set_ylabel("Latitude (°N)", fontsize=11)
    ax.set_title(f"Real 2D Dispersion Heatmap — Kanpur (dt=3h)\nERA5 Wind: {src_pt['wind_speed']} m/s, Dir: {src_pt['wind_direction_deg']}°", fontsize=11, fontweight="bold")
    ax.legend(loc="upper left")
    p4 = os.path.join(figures_dir, "04_real_physics_dispersion_map.png")
    fig.savefig(p4, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 5: Transport Matrix Heatmap (Source to Destination)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 6))
    # 7x7 destination grid transport fractions for Kanpur center
    piv_mat = knp_sub.pivot(index="rel_dy", columns="rel_dx", values="transport_fraction").sort_index(ascending=False)
    im_mat = ax.imshow(piv_mat.values, cmap="Blues", extent=[-0.35, 0.35, -0.35, 0.35])
    plt.colorbar(im_mat, label="Transport Fraction T[src, dest, t]")
    ax.set_xlabel("Relative Longitude Offset (°)", fontsize=11)
    ax.set_ylabel("Relative Latitude Offset (°)", fontsize=11)
    ax.set_title("Source -> Destination Transport Matrix T[src, dest, t]\n(Kanpur Hub, dt=3h)", fontsize=12, fontweight="bold")
    p5 = os.path.join(figures_dir, "05_real_transport_matrix.png")
    fig.savefig(p5, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 6: Dispersion vs Distance Decay
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    dt1 = df[df["elapsed_time_hours"] == 1.0]
    dt3 = df[df["elapsed_time_hours"] == 3.0]
    dt6 = df[df["elapsed_time_hours"] == 6.0]
    ax.scatter(dt1["distance_km"], dt1["transport_influence"], alpha=0.3, color="teal", label="dt = 1h")
    ax.scatter(dt3["distance_km"], dt3["transport_influence"], alpha=0.3, color="coral", label="dt = 3h")
    ax.scatter(dt6["distance_km"], dt6["transport_influence"], alpha=0.3, color="purple", label="dt = 6h")
    ax.set_xlabel("Distance from Source Grid (km)", fontsize=11)
    ax.set_ylabel("Transported Influence (µg/m³)", fontsize=11)
    ax.set_title("Transported Pollution Influence vs Distance under Real ERA5 Winds", fontsize=12, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper right")
    p6 = os.path.join(figures_dir, "06_real_dispersion_vs_distance.png")
    fig.savefig(p6, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 7: Downwind vs Upwind Comparison
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 5))
    down = df[df["rel_angle_to_wind_deg"] <= 45.0]["transport_influence"]
    cross = df[(df["rel_angle_to_wind_deg"] > 45.0) & (df["rel_angle_to_wind_deg"] < 135.0)]["transport_influence"]
    up = df[df["rel_angle_to_wind_deg"] >= 135.0]["transport_influence"]
    means = [down.mean(), cross.mean(), up.mean()]
    labels = ["Downwind (<=45°)", "Crosswind (45°-135°)", "Upwind (>=135°)"]
    colors = ["forestgreen", "gold", "tomato"]
    bars = ax.bar(labels, means, color=colors, edgecolor="black", alpha=0.85)
    for b in bars:
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.1, f"{b.get_height():.2f}", ha="center", fontsize=10, fontweight="bold")
    ax.set_ylabel("Mean Transport Influence (µg/m³)", fontsize=11)
    ax.set_title("Physical Verification — Downwind vs Upwind Transport Under Real Winds", fontsize=11, fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    p7 = os.path.join(figures_dir, "07_real_downwind_vs_upwind.png")
    fig.savefig(p7, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 8: Ensemble Stability Benchmark (N=5, 10, 20)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if os.path.exists(stab_path):
        s_df = pd.read_csv(stab_path)
        bars = ax.bar(s_df["ensemble_comparison"], s_df["mae_fraction_diff"], color=["skyblue", "navy"], edgecolor="black")
        for b in bars:
            ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.002, f"MAE: {b.get_height():.4f}", ha="center", fontsize=10, fontweight="bold")
        ax.axhline(0.10, color="red", linestyle="--", label="N=5 Acceptance Limit (0.10)")
        ax.axhline(0.05, color="orange", linestyle="--", label="N=10 Acceptance Limit (0.05)")
    ax.set_ylabel("MAE Fraction Difference", fontsize=11)
    ax.set_title("Ensemble Numerical Stability Benchmark (Real Winds)", fontsize=12, fontweight="bold")
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    p8 = os.path.join(figures_dir, "08_real_ensemble_stability.png")
    fig.savefig(p8, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"[Plot Generator] All 8 figures successfully generated in: {figures_dir}")


if __name__ == "__main__":
    generate_all_real_plots()
