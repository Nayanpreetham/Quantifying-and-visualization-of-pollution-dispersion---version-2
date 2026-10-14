"""
REGIONAL VISUALIZATION SUITE (INDO-GANGETIC PLAIN)
===================================================
Generates publication-quality diagnostic maps and figures for the Continuous Regional Dispersion Model:
1. 01_regional_igp_grid_and_stations.png
2. 02_regional_era5_wind_field.png
3. 03_regional_openaq_pm25_timeseries.png
4. 04_regional_dispersion_footprint.png
5. 05_regional_transport_matrix_heatmap.png
6. 06_boundary_loss_vs_time.png
7. 07_transport_fraction_vs_wind_speed.png

Output Directory: results/regional_pilot/figures/
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def generate_all_regional_plots(data_dir="data/regional",
                                results_dir="results/regional_pilot",
                                figures_dir="results/regional_pilot/figures"):
    os.makedirs(figures_dir, exist_ok=True)

    grid_path = os.path.join(data_dir, "igp_025_grid.csv")
    map_path = os.path.join(data_dir, "station_to_grid_mapping_corrected.csv")
    wind_path = os.path.join(data_dir, "era5_wind_regional.csv")
    pol_path = os.path.join(data_dir, "openaq_pm25_regional_sources.csv")
    target_path = os.path.join(results_dir, "transport_targets_regional.csv")
    bnd_path = os.path.join(results_dir, "boundary_loss_statistics.csv")

    grid_df = pd.read_csv(grid_path)
    map_df = pd.read_csv(map_path)
    wind_df = pd.read_csv(wind_path)
    pol_df = pd.read_csv(pol_path)
    df = pd.read_csv(target_path)
    bnd_df = pd.read_csv(bnd_path)

    print("[Regional Plot Generator] Generating regional visualizations...")

    # -------------------------------------------------------------
    # Figure 1: Continuous Regional Grid & Station Spine
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(grid_df["longitude"], grid_df["latitude"], s=4, color="lightgray", alpha=0.5, label="Continuous 0.25° Grid Nodes (1,881 cells)")
    matched = map_df[map_df["match_status"] == "MATCHED"]
    # Plot active corridor stations
    active_st_ids = pol_df["station_id"].unique()
    corridor = matched[matched["station_id"].isin(active_st_ids)]
    ax.scatter(corridor["station_longitude"], corridor["station_latitude"], color="crimson", s=100, zorder=5, label="Active IGP Ground Stations (OpenAQ)")
    for _, r in corridor.iterrows():
        ax.annotate(r["corrected_city"], (r["station_longitude"] + 0.15, r["station_latitude"] + 0.1), fontsize=9, fontweight="bold")
    ax.set_xlim(73.5, 88.5)
    ax.set_ylim(23.5, 32.5)
    ax.set_xlabel("Longitude (°E)", fontsize=11)
    ax.set_ylabel("Latitude (°N)", fontsize=11)
    ax.set_title("Continuous Regional Grid (0.25° x 0.25°) & Corrected Station Locations\nIndo-Gangetic Plain Corridor", fontsize=12, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", framealpha=0.9)
    p1 = os.path.join(figures_dir, "01_regional_igp_grid_and_stations.png")
    fig.savefig(p1, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 2: Regional ERA5 Wind Vector Field
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 6))
    t_sample = "2021-10-16 12:00:00 UTC"
    t_wind = wind_df[wind_df["timestamp_utc"] == t_sample]
    # Subsample vectors for clean display (every 2nd point)
    sub_w = t_wind[(t_wind["row"] % 2 == 0) & (t_wind["column"] % 2 == 0)]
    q = ax.quiver(
        sub_w["longitude"], sub_w["latitude"],
        sub_w["u10"], sub_w["v10"],
        sub_w["wind_speed"],
        cmap="viridis", scale=45, width=0.003
    )
    plt.colorbar(q, label="Wind Speed (m/s)")
    ax.set_xlim(73.5, 88.5)
    ax.set_ylim(23.5, 32.5)
    ax.set_xlabel("Longitude (°E)", fontsize=11)
    ax.set_ylabel("Latitude (°N)", fontsize=11)
    ax.set_title(f"Real ERA5 Surface Wind Vectors (U10, V10) across IGP Corridor\n[{t_sample}]", fontsize=12, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4)
    p2 = os.path.join(figures_dir, "02_regional_era5_wind_field.png")
    fig.savefig(p2, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 3: Regional OpenAQ PM2.5 Time Series
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 5))
    for c_name in pol_df["city"].unique():
        c_sub = pol_df[pol_df["city"] == c_name].groupby("timestamp_utc")["pm25_concentration"].mean()
        # Convert timestamp strings for plotting
        t_plot = [pd.to_datetime(t) for t in c_sub.index]
        ax.plot(t_plot, c_sub.values, marker="o", markersize=4, label=c_name, linewidth=1.8)
    ax.set_ylabel("Observed PM2.5 (µg/m³)", fontsize=11)
    ax.set_xlabel("Time (UTC)", fontsize=11)
    ax.set_title("Ground In-Situ PM2.5 Observations across IGP Spine (Oct 14–20, 2021)", fontsize=12, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper left", ncol=3)
    p3 = os.path.join(figures_dir, "03_regional_openaq_pm25_timeseries.png")
    fig.savefig(p3, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 4: Continuous Regional Dispersion Footprint (Oct 16 12:00 UTC, dt=12h)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 6))
    sample_df = df[(df["timestamp_utc"] == t_sample) & (df["elapsed_time_hours"] == 12.0)]
    # Sum influence from all active regional sources
    grid_footprint = sample_df.groupby(["dest_lat", "dest_lon"])["transport_influence"].sum().reset_index()
    # Scatter heat nodes
    sc = ax.scatter(grid_footprint["dest_lon"], grid_footprint["dest_lat"], c=grid_footprint["transport_influence"], cmap="YlOrRd", s=180, marker="s", edgecolors="none")
    plt.colorbar(sc, label="Transported Influence (µg/m³)")
    # Overlay source stations
    sources = sample_df.groupby(["station_name", "city", "source_lat", "source_lon"]).first().reset_index()
    ax.scatter(sources["source_lon"], sources["source_lat"], color="blue", marker="*", s=220, label="Monitored Ground Sources", zorder=6)
    for _, s in sources.iterrows():
        ax.annotate(s["city"], (s["source_lon"] + 0.15, s["source_lat"] + 0.1), fontsize=9, fontweight="bold")
    ax.set_xlim(74.0, 88.0)
    ax.set_ylim(24.0, 32.0)
    ax.set_xlabel("Longitude (°E)", fontsize=11)
    ax.set_ylabel("Latitude (°N)", fontsize=11)
    ax.set_title(f"Continuous Regional Dispersion Footprint across Indo-Gangetic Plain\n[dt = 12h, Elapsed Window, Valid: {t_sample}] — Zero Edge Clamping", fontsize=11, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper right")
    p4 = os.path.join(figures_dir, "04_regional_dispersion_footprint.png")
    fig.savefig(p4, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 5: Regional Transport Matrix Heatmap (Kanpur Hub)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 6))
    knp_matrix = df[(df["city"] == "Kanpur") & (df["elapsed_time_hours"] == 6.0) & (df["timestamp_utc"] == t_sample)]
    piv = knp_matrix.pivot_table(index="dest_lat", columns="dest_lon", values="transport_fraction", fill_value=0.0).sort_index(ascending=False)
    im = ax.imshow(piv.values, cmap="Blues", extent=[piv.columns.min(), piv.columns.max(), piv.index.min(), piv.index.max()])
    plt.colorbar(im, label="Transport Fraction T[src, dest, t]")
    ax.scatter(knp_matrix["source_lon"].iloc[0], knp_matrix["source_lat"].iloc[0], color="red", marker="*", s=200, label="Kanpur Source Node")
    ax.set_xlabel("Longitude (°E)", fontsize=11)
    ax.set_ylabel("Latitude (°N)", fontsize=11)
    ax.set_title("Source -> Destination Regional Transport Matrix T[src, dest, t]\n(Kanpur Hub, dt=6h on Continuous 0.25° Grid)", fontsize=11, fontweight="bold")
    ax.legend(loc="upper left")
    p5 = os.path.join(figures_dir, "05_regional_transport_matrix_heatmap.png")
    fig.savefig(p5, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 6: Boundary Loss & Mass Conservation Curve
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    loss_summary = bnd_df.groupby("elapsed_time_hours").agg(
        inside_mean=("inside_fraction", "mean"),
        loss_mean=("boundary_loss_fraction", "mean")
    ).reset_index()
    dts = loss_summary["elapsed_time_hours"].values
    ax.plot(dts, loss_summary["inside_mean"] * 100, marker="o", color="forestgreen", linewidth=2.2, label="Inside Regional Domain (%)")
    ax.plot(dts, loss_summary["loss_mean"] * 100, marker="s", color="crimson", linewidth=2.2, linestyle="--", label="Boundary Loss (Exited Domain) (%)")
    ax.set_xlabel("Elapsed Time Window dt (Hours)", fontsize=11)
    ax.set_ylabel("Percentage of Ensemble Mass (%)", fontsize=11)
    ax.set_title("Domain Boundary Retention vs Advection Time (Zero Artificial Clamping)", fontsize=12, fontweight="bold")
    ax.set_xticks(dts)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="center right")
    p6 = os.path.join(figures_dir, "06_boundary_loss_vs_time.png")
    fig.savefig(p6, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 7: Transport Fraction vs Wind Speed (Constraint 3)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    dt6_df = df[df["elapsed_time_hours"] == 6.0]
    sc = ax.scatter(dt6_df["wind_speed"], dt6_df["distance_km"], c=dt6_df["transport_fraction"], cmap="viridis", s=40, alpha=0.7)
    plt.colorbar(sc, label="Transport Fraction T")
    ax.set_xlabel("ERA5 Surface Wind Speed (m/s)", fontsize=11)
    ax.set_ylabel("Advected Distance from Source (km)", fontsize=11)
    ax.set_title("Kinematic Transport Scaling: Advection Distance vs Wind Speed\n(Confirming Positive Advection Sensitivity without Stagnation Bias)", fontsize=11, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    p7 = os.path.join(figures_dir, "07_transport_fraction_vs_wind_speed.png")
    fig.savefig(p7, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"[Regional Plot Generator] Successfully saved 7 figures in: {figures_dir}")


if __name__ == "__main__":
    generate_all_regional_plots()
