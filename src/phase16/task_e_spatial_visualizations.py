"""
PHASE 16 — TASK E: SPATIAL OUTPUTS & CARTOGRAPHIC VISUALIZATIONS
================================================================
Generates 6 publication-ready, geographically referenced figures in results/phase16_climatology/figures/:
1. fig1_six_year_recurring_corridors_composite.png:
   - National domain with 10 source stations and top recurring transport corridor vectors.
2. fig2_seasonal_corridor_shifts_4panel.png:
   - 4-panel seasonal comparison: Winter (DJF), Pre-monsoon (MAM), Monsoon (JJAS), Post-monsoon (ON).
3. fig3_transport_distance_scaling_and_bands.png:
   - 2-panel chart: (a) Mean/median transport distance scaling vs advection window, (b) Stacked distance bands.
4. fig4_interannual_stability_matrix.png:
   - Heatmap of interannual pairwise cosine similarities and Pearson correlations across 2019–2024.
5. fig5_spatial_dispersion_footprint_igp_vs_peninsular.png:
   - Spatial 2D footprint comparing Indo-Gangetic Plain (Kanpur/Varanasi) vs Peninsular India (Visakhapatnam/Ahmedabad).
6. fig6_corridor_persistence_and_threshold_sensitivity.png:
   - Sensitivity curves of persistent corridor count across thresholds tau in [0.01, 0.02, 0.05, 0.10].
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches

WINDOWS = [1.0, 3.0, 6.0, 12.0, 24.0]

def generate_spatial_visualizations(
    base_dir="results/phase16_climatology",
    stations_path="results/phase11_validation/selected_stations.csv",
    grid_path="data/national/india_025_grid.csv"
):
    fig_dir = os.path.join(base_dir, "figures")
    tables_dir = os.path.join(base_dir, "tables")
    os.makedirs(fig_dir, exist_ok=True)

    stations_df = pd.read_csv(stations_path)
    grid_df = pd.read_csv(grid_path)
    grid_lookup = grid_df.set_index("grid_id")[["latitude", "longitude"]].to_dict(orient="index")

    top_corridors_file = os.path.join(tables_dir, "top_transport_corridors.csv")
    stability_file = os.path.join(tables_dir, "interannual_stability.csv")
    pers_file = os.path.join(tables_dir, "corridor_persistence.csv")
    seasonal_summary_file = os.path.join(tables_dir, "seasonal_transport_summary.csv")

    df_top = pd.read_csv(top_corridors_file)
    df_stab = pd.read_csv(stability_file) if os.path.exists(stability_file) else None
    df_pers = pd.read_csv(pers_file) if os.path.exists(pers_file) else None

    # Load 6-year climatological seasonal matrices
    clim_matrices = {}
    for s_name in ["Winter", "Pre-monsoon", "Monsoon", "Post-monsoon"]:
        c_path = os.path.join(base_dir, "matrices", f"transport_matrix_climatology_{s_name}.csv")
        if os.path.exists(c_path):
            clim_matrices[s_name] = pd.read_csv(c_path)

    # -------------------------------------------------------------
    # FIGURE 1: Six-Year Recurring Corridors Composite Map
    # -------------------------------------------------------------
    print("[Task E] Generating Figure 1: Six-Year Recurring Corridors Composite...")
    fig, ax = plt.subplots(figsize=(10, 11), dpi=300)
    ax.set_facecolor("#f8f9fa")

    # Domain bounds
    ax.set_xlim(67.0, 98.0)
    ax.set_ylim(6.0, 36.0)
    ax.set_xlabel("Longitude (°E)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Latitude (°N)", fontsize=11, fontweight="bold")
    ax.set_title("Six-Year National Transport Corridor Climatology (2019–2024)\n"
                 "Recurring 2D Advection Pathways Across 10 Representative Monitoring Hubs",
                 fontsize=12, fontweight="bold", pad=12)

    # Plot national grid outline bounds
    ax.plot([68, 97, 97, 68, 68], [6, 6, 35, 35, 6], color="#6c757d", linestyle="--", linewidth=1.0, label="Computational Domain (0.25°)")

    # Filter corridors for 6h and 24h windows with high persistence (rate >= 0.8)
    corridors_to_plot = df_top[(df_top["annual_persistence_rate"] >= 0.8) & (df_top["destination_grid_id"] != "OUTSIDE_DOMAIN")]

    # Plot vectors
    for _, row in corridors_to_plot.iterrows():
        s_id = row["station_id"]
        d_gid = row["destination_grid_id"]
        dt_h = row["advection_window_hours"]
        mean_t = row["climatological_mean_transport_fraction"]

        st_row = stations_df[stations_df["station_id"] == s_id].iloc[0]
        s_lat, s_lon = float(st_row["station_latitude"]), float(st_row["station_longitude"])

        if d_gid in grid_lookup:
            d_lat = float(grid_lookup[d_gid]["latitude"])
            d_lon = float(grid_lookup[d_gid]["longitude"])
        else:
            continue

        d_km = row["distance_km"]
        if d_km < 15.0:
            continue  # local retention, don't draw tiny vector

        # Color and alpha based on transport window
        color = "#1f77b4" if dt_h <= 6.0 else ("#ff7f0e" if dt_h <= 12.0 else "#d62728")
        alpha = np.clip(mean_t * 5.0, 0.4, 0.9)
        width = max(0.8, min(mean_t * 20.0, 3.5))

        ax.annotate(
            "", xy=(d_lon, d_lat), xytext=(s_lon, s_lat),
            arrowprops=dict(
                arrowstyle="-|>", color=color, lw=width, alpha=alpha,
                shrinkA=3, shrinkB=3, mutation_scale=12
            )
        )

    # Plot stations
    for _, st in stations_df.iterrows():
        s_lat, s_lon = float(st["station_latitude"]), float(st["station_longitude"])
        city = st["corrected_city"]
        ax.plot(s_lon, s_lat, marker="o", color="#212529", markersize=7, markeredgewidth=1.5, markeredgecolor="white", zorder=5)
        ax.text(s_lon + 0.35, s_lat + 0.15, city, fontsize=9, fontweight="bold", color="#212529", zorder=6,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8, edgecolor="#ced4da", lw=0.5))

    # Legend
    p_6h = mpatches.Patch(color="#1f77b4", label="Near-Regional Pathway (dt ≤ 6h)")
    p_12h = mpatches.Patch(color="#ff7f0e", label="Regional Pathway (dt = 12h)")
    p_24h = mpatches.Patch(color="#d62728", label="Long-Range Pathway (dt = 24h)")
    ax.legend(handles=[p_6h, p_12h, p_24h], loc="lower right", framealpha=0.9, fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.6)

    fig1_path = os.path.join(fig_dir, "fig1_six_year_recurring_corridors_composite.png")
    fig.tight_layout()
    fig.savefig(fig1_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved Figure 1: {fig1_path}")

    # -------------------------------------------------------------
    # FIGURE 2: Seasonal Corridor Shifts (4-Panel Subplot)
    # -------------------------------------------------------------
    print("[Task E] Generating Figure 2: Seasonal Corridor Shifts (4-Panel)...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 15), dpi=300)
    seasons = [("Winter", axes[0, 0]), ("Pre-monsoon", axes[0, 1]), ("Monsoon", axes[1, 0]), ("Post-monsoon", axes[1, 1])]

    for s_name, ax in seasons:
        ax.set_facecolor("#f8f9fa")
        ax.set_xlim(67.0, 98.0)
        ax.set_ylim(6.0, 36.0)
        ax.set_title(f"Season: {s_name} (2019–2024 Climatology)", fontsize=11, fontweight="bold")
        ax.set_xlabel("Longitude (°E)", fontsize=9)
        ax.set_ylabel("Latitude (°N)", fontsize=9)
        ax.plot([68, 97, 97, 68, 68], [6, 6, 35, 35, 6], color="#adb5bd", linestyle="--", linewidth=0.8)

        if s_name in clim_matrices:
            df_s = clim_matrices[s_name]
            # Focus on 12h and 24h regional transport
            df_s_reg = df_s[df_s["elapsed_time_hours"].isin([12.0, 24.0])]
            
            # Draw top corridors with fraction >= 0.03
            for _, r in df_s_reg[df_s_reg["mean_transport_fraction"] >= 0.03].iterrows():
                s_id = r["station_id"]
                d_gid = r["dest_grid_id"]
                if d_gid == "OUTSIDE_DOMAIN" or d_gid not in grid_lookup:
                    continue
                st_row = stations_df[stations_df["station_id"] == s_id].iloc[0]
                s_lat, s_lon = float(st_row["station_latitude"]), float(st_row["station_longitude"])
                d_lat, d_lon = float(grid_lookup[d_gid]["latitude"]), float(grid_lookup[d_gid]["longitude"])

                frac = float(r["mean_transport_fraction"])
                lw = max(0.5, min(frac * 15.0, 2.5))
                alpha = np.clip(frac * 4.0, 0.3, 0.8)
                color = "#0077b6" if s_name in ["Winter", "Post-monsoon"] else "#e63946"

                ax.annotate(
                    "", xy=(d_lon, d_lat), xytext=(s_lon, s_lat),
                    arrowprops=dict(
                        arrowstyle="-|>", color=color, lw=lw, alpha=alpha,
                        shrinkA=2, shrinkB=2, mutation_scale=8
                    )
                )

        # Plot stations
        for _, st in stations_df.iterrows():
            ax.plot(st["station_longitude"], st["station_latitude"], marker="o", color="#212529", markersize=4, zorder=5)
            ax.text(st["station_longitude"] + 0.3, st["station_latitude"] + 0.1, st["corrected_city"], fontsize=7.5, color="#343a40")

        ax.grid(True, linestyle=":", alpha=0.5)

    fig2_path = os.path.join(fig_dir, "fig2_seasonal_corridor_shifts_4panel.png")
    fig.tight_layout()
    fig.savefig(fig2_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved Figure 2: {fig2_path}")

    # -------------------------------------------------------------
    # FIGURE 3: Transport Distance Scaling and Distance Bands
    # -------------------------------------------------------------
    print("[Task E] Generating Figure 3: Transport Distance Scaling & Bands...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=300)

    # Panel 1: Scaling curves
    if df_stab is not None:
        for city, grp in df_stab.groupby("city"):
            sorted_grp = grp.sort_values("advection_window_hours")
            ax1.plot(sorted_grp["advection_window_hours"], sorted_grp["six_year_mean_transport_dist_km"], marker="o", lw=1.8, label=city)
        ax1.set_xlabel("Advection Window (Hours)", fontsize=10, fontweight="bold")
        ax1.set_ylabel("Mean Modeled Transport Distance (km)", fontsize=10, fontweight="bold")
        ax1.set_title("(a) Geodesic Transport Distance vs Time Window", fontsize=11, fontweight="bold")
        ax1.set_xticks(WINDOWS)
        ax1.grid(True, linestyle=":", alpha=0.6)
        ax1.legend(loc="upper left", fontsize=8, framealpha=0.9, ncol=2)

        # Panel 2: Stacked Distance Bands by Window
        band_means = df_stab.groupby("advection_window_hours").agg(
            Local=("local_frac_lt_30km", "mean"),
            Near_Regional=("near_regional_frac_30_100km", "mean"),
            Regional=("regional_frac_100_250km", "mean"),
            Long_Range=("long_range_frac_gte_250km", "mean"),
            Domain_Exit=("domain_exit_frac", "mean")
        ) * 100.0

        windows_str = [f"{int(w)}h" for w in WINDOWS]
        bottom = np.zeros(len(WINDOWS))
        colors = ["#2b5c8f", "#4575b4", "#74add1", "#fdae61", "#d73027"]
        labels = ["Local (<30 km)", "Near-Reg (30-100 km)", "Reg (100-250 km)", "Long-Range (≥250 km)", "Domain Exit"]

        for i, col in enumerate(band_means.columns):
            vals = band_means[col].values
            ax2.bar(windows_str, vals, bottom=bottom, label=labels[i], color=colors[i], width=0.55, edgecolor="white", lw=0.5)
            bottom += vals

        ax2.set_xlabel("Advection Window", fontsize=10, fontweight="bold")
        ax2.set_ylabel("Mean Transport Fraction (%)", fontsize=10, fontweight="bold")
        ax2.set_title("(b) Spatial Partitioning Across Distance Bands", fontsize=11, fontweight="bold")
        ax2.set_ylim(0, 105)
        ax2.grid(True, linestyle=":", alpha=0.6, axis="y")
        ax2.legend(loc="lower right", fontsize=8.5, framealpha=0.9)

    fig3_path = os.path.join(fig_dir, "fig3_transport_distance_scaling_and_bands.png")
    fig.tight_layout()
    fig.savefig(fig3_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved Figure 3: {fig3_path}")

    # -------------------------------------------------------------
    # FIGURE 4: Interannual Stability Matrix
    # -------------------------------------------------------------
    print("[Task E] Generating Figure 4: Interannual Stability Analysis...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=300)

    if df_stab is not None:
        # Bar chart of mean cosine similarity by station for dt=6h and dt=24h
        stab_6h = df_stab[df_stab["advection_window_hours"] == 6.0].sort_values("mean_pairwise_cosine_similarity").reset_index(drop=True)
        stab_24h = df_stab[df_stab["advection_window_hours"] == 24.0].set_index("station_id").loc[stab_6h["station_id"]].reset_index()

        y_pos = np.arange(len(stab_6h))
        height = 0.38

        ax1.barh(y_pos - height/2, stab_6h["mean_pairwise_cosine_similarity"], height=height, color="#2b5c8f", label="dt = 6h")
        ax1.barh(y_pos + height/2, stab_24h["mean_pairwise_cosine_similarity"], height=height, color="#d95f02", label="dt = 24h")
        ax1.set_yticks(y_pos)
        st_labels = [f"{r['city']} ({r['station_id']})" for _, r in stab_6h.iterrows()]
        ax1.set_yticklabels(st_labels, fontsize=8.5)
        ax1.set_xlabel("Mean Pairwise Cosine Similarity Across Years", fontsize=10, fontweight="bold")
        ax1.set_title("(a) Interannual Transport Pattern Stability", fontsize=11, fontweight="bold")
        ax1.set_xlim(0.65, 1.0)
        ax1.grid(True, linestyle=":", alpha=0.6, axis="x")
        ax1.legend(loc="lower right", fontsize=9)

        # Spatial concentration (Gini coefficient) vs transport distance
        for dt_h, grp in df_stab.groupby("advection_window_hours"):
            ax2.scatter(grp["six_year_mean_transport_dist_km"], grp["six_year_avg_gini_coefficient"],
                        s=80, alpha=0.8, label=f"dt = {int(dt_h)}h")
        ax2.set_xlabel("Mean Transport Distance (km)", fontsize=10, fontweight="bold")
        ax2.set_ylabel("Gini Coefficient of Destination Fractions", fontsize=10, fontweight="bold")
        ax2.set_title("(b) Dispersion Concentration vs Distance", fontsize=11, fontweight="bold")
        ax2.grid(True, linestyle=":", alpha=0.6)
        ax2.legend(loc="upper right", fontsize=8.5)

    fig4_path = os.path.join(fig_dir, "fig4_interannual_stability_matrix.png")
    fig.tight_layout()
    fig.savefig(fig4_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved Figure 4: {fig4_path}")

    # -------------------------------------------------------------
    # FIGURE 5: Spatial Footprint Comparison (IGP vs Peninsular)
    # -------------------------------------------------------------
    print("[Task E] Generating Figure 5: Spatial Dispersion Footprint Comparison...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7), dpi=300)

    # Kanpur (IGP) vs Ahmedabad (Western India) at dt=12h in Climatological Winter
    if "Winter" in clim_matrices and "Monsoon" in clim_matrices:
        df_win = clim_matrices["Winter"]
        kanpur_win = df_win[(df_win["city"] == "Kanpur") & (df_win["elapsed_time_hours"] == 12.0)]
        ahmed_win = df_win[(df_win["city"] == "Ahmedabad") & (df_win["elapsed_time_hours"] == 12.0)]

        # Plot Kanpur footprint
        ax1.set_facecolor("#f8f9fa")
        ax1.set_xlim(75.0, 86.0)
        ax1.set_ylim(23.0, 30.0)
        ax1.set_title("Kanpur (Indo-Gangetic Plain) — 12h Winter Footprint", fontsize=11, fontweight="bold")
        ax1.set_xlabel("Longitude (°E)", fontsize=9.5)
        ax1.set_ylabel("Latitude (°N)", fontsize=9.5)

        for _, r in kanpur_win.iterrows():
            d_gid = r["dest_grid_id"]
            if d_gid in grid_lookup:
                d_lat = grid_lookup[d_gid]["latitude"]
                d_lon = grid_lookup[d_gid]["longitude"]
                frac = r["mean_transport_fraction"]
                sz = max(10, frac * 2000)
                ax1.scatter(d_lon, d_lat, s=sz, color="#d62728", alpha=0.5, edgecolor="none")

        # Mark Kanpur
        kp_st = stations_df[stations_df["corrected_city"] == "Kanpur"].iloc[0]
        ax1.plot(kp_st["station_longitude"], kp_st["station_latitude"], "ko", markersize=8, markeredgecolor="white")
        ax1.text(kp_st["station_longitude"] + 0.2, kp_st["station_latitude"] + 0.1, "Kanpur Source", fontweight="bold", fontsize=9)
        ax1.grid(True, linestyle=":", alpha=0.5)

        # Plot Ahmedabad footprint
        ax2.set_facecolor("#f8f9fa")
        ax2.set_xlim(68.5, 76.5)
        ax2.set_ylim(19.5, 26.5)
        ax2.set_title("Ahmedabad (Western India) — 12h Winter Footprint", fontsize=11, fontweight="bold")
        ax2.set_xlabel("Longitude (°E)", fontsize=9.5)
        ax2.set_ylabel("Latitude (°N)", fontsize=9.5)

        for _, r in ahmed_win.iterrows():
            d_gid = r["dest_grid_id"]
            if d_gid in grid_lookup:
                d_lat = grid_lookup[d_gid]["latitude"]
                d_lon = grid_lookup[d_gid]["longitude"]
                frac = r["mean_transport_fraction"]
                sz = max(10, frac * 2000)
                ax2.scatter(d_lon, d_lat, s=sz, color="#1f77b4", alpha=0.5, edgecolor="none")

        ah_st = stations_df[stations_df["corrected_city"] == "Ahmedabad"].iloc[0]
        ax2.plot(ah_st["station_longitude"], ah_st["station_latitude"], "ko", markersize=8, markeredgecolor="white")
        ax2.text(ah_st["station_longitude"] + 0.2, ah_st["station_latitude"] + 0.1, "Ahmedabad Source", fontweight="bold", fontsize=9)
        ax2.grid(True, linestyle=":", alpha=0.5)

    fig5_path = os.path.join(fig_dir, "fig5_spatial_dispersion_footprint_igp_vs_peninsular.png")
    fig.tight_layout()
    fig.savefig(fig5_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved Figure 5: {fig5_path}")

    # -------------------------------------------------------------
    # FIGURE 6: Corridor Persistence & Sensitivity
    # -------------------------------------------------------------
    print("[Task E] Generating Figure 6: Threshold Sensitivity Curves...")
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)

    if df_pers is not None:
        taus = [0.01, 0.02, 0.05, 0.10]
        c_3plus = []
        c_5plus = []
        for tau in taus:
            col = f"years_active_tau_{tau:.2f}".replace(".", "_")
            c_3plus.append((df_pers[col] >= 3).sum())
            c_5plus.append((df_pers[col] >= 5).sum())

        ax.plot(taus, c_3plus, marker="s", lw=2.2, color="#2b5c8f", label="Recurring in ≥ 3 of 6 Years (≥ 50%)")
        ax.plot(taus, c_5plus, marker="o", lw=2.2, color="#d95f02", label="Highly Persistent in ≥ 5 of 6 Years (≥ 83%)")
        ax.set_xlabel("Corridor Transport Fraction Threshold (τ)", fontsize=10, fontweight="bold")
        ax.set_ylabel("Number of Transport Corridors", fontsize=10, fontweight="bold")
        ax.set_title("Corridor Recurrence Sensitivity Across Detection Thresholds", fontsize=11, fontweight="bold")
        ax.set_xticks(taus)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="upper right", fontsize=9.5)

    fig6_path = os.path.join(fig_dir, "fig6_corridor_persistence_and_threshold_sensitivity.png")
    fig.tight_layout()
    fig.savefig(fig6_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved Figure 6: {fig6_path}")

    print("\n[Task E] All 6 publication-ready spatial visualizations successfully generated!")

if __name__ == "__main__":
    generate_spatial_visualizations()
