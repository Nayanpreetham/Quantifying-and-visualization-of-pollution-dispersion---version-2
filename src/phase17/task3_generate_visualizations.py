"""
Task 3: Generate Spatial Visualizations and Quantitative Analytical Figures
Phase 17 — AQI-Ranked Source-to-Neighbor Pollution Transport

Generates 5 publication-ready (300 DPI) figures:
1. fig1_aqi_ranked_eligible_source_zones.png
2. fig2_source_to_neighbor_transport_corridors.png
3. fig3_destination_rankings_and_transport_decay.png
4. fig4_transported_influence_vs_geographic_distance.png
5. fig5_seasonal_comparison_worst_aqi_zone.png
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from shapely.geometry import shape

def plot_india_background(ax):
    """Draws India boundary from geojson."""
    boundary_path = "data/raw/geography/india_boundary.geojson"
    if os.path.exists(boundary_path):
        with open(boundary_path, 'r') as f:
            geo = json.load(f)
        geom = shape(geo['features'][0]['geometry'])
        if geom.geom_type == 'Polygon':
            x, y = geom.exterior.xy
            ax.plot(x, y, color="#adb5bd", linewidth=1.2, zorder=2)
            ax.fill(x, y, color="#f8f9fa", alpha=1.0, zorder=1)
        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                x, y = poly.exterior.xy
                ax.plot(x, y, color="#adb5bd", linewidth=1.2, zorder=2)
                ax.fill(x, y, color="#f8f9fa", alpha=1.0, zorder=1)
    else:
        # Fallback domain bounds box
        ax.plot([68, 97, 97, 68, 68], [6, 6, 35, 35, 6], color="#adb5bd", linestyle="--", linewidth=1.0)


def main():
    print("=== Phase 17 Task 3: Generate Visualizations ===")
    out_dir = "results/phase17_target_zones/figures"
    os.makedirs(out_dir, exist_ok=True)
    
    # Load required data
    df_src = pd.read_csv("results/phase17_target_zones/source_zones_ranked_by_aqi.csv")
    df_dest = pd.read_csv("results/phase17_target_zones/destination_zones_by_transport_fraction.csv")
    df_infl = pd.read_csv("results/phase17_target_zones/transported_influence_estimates.csv")
    
    grid_path = "data/national/india_025_grid.csv"
    df_grid = pd.read_csv(grid_path)[['grid_id', 'latitude', 'longitude']]
    grid_coords = dict(zip(df_grid['grid_id'], zip(df_grid['latitude'], df_grid['longitude'])))

    # -------------------------------------------------------------
    # FIGURE 1: AQI-Ranked Eligible Source Zones Map
    # -------------------------------------------------------------
    print("Generating Figure 1: AQI-Ranked Eligible Source Zones Map...")
    fig, ax = plt.subplots(figsize=(11, 11), dpi=300)
    ax.set_facecolor("#eef2f5")
    plot_india_background(ax)
    
    ax.set_xlim(67.0, 98.0)
    ax.set_ylim(7.0, 36.5)
    ax.set_xlabel("Longitude (°E)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Latitude (°N)", fontsize=11, fontweight="bold")
    ax.set_title("Phase 17 — AQI-Ranked Eligible Source Zones across India\n"
                 "Evaluated via CPCB NAQI (2014) 24-Hour PM2.5 Regulatory Standard",
                 fontsize=13, fontweight="bold", pad=12)
    
    # Category color mapping
    cat_colors = {
        'Moderate': '#ff7f0e',      # Orange (AQI 101-200)
        'Satisfactory': '#2ca02c',  # Green (AQI 51-100)
        'Good': '#1f77b4'           # Blue (AQI 0-50)
    }
    
    for _, row in df_src.iterrows():
        lat = row['station_latitude']
        lon = row['station_longitude']
        rank = int(row['aqi_rank'])
        city = row['city']
        aqi_val = row['regulatory_24h_aqi_mean']
        cat = row['aqi_category_mean']
        c = cat_colors.get(cat, '#6c757d')
        
        # Plot marker
        ax.scatter(lon, lat, s=280, color=c, edgecolors='white', linewidth=2.0, zorder=6)
        # Plot rank badge inside marker
        ax.text(lon, lat, str(rank), color='white', fontsize=10, fontweight='bold',
                ha='center', va='center', zorder=7)
        # Label offset
        offset_x = 0.45
        offset_y = 0.25 if rank % 2 == 1 else -0.45
        if city == 'Guwahati':
            offset_x = -3.2
        label_text = f"#{rank} {city}\nAQI: {aqi_val:.1f} ({cat})"
        ax.text(lon + offset_x, lat + offset_y, label_text, fontsize=8.5, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.9, edgecolor=c, lw=1.2),
                zorder=8)

    # Inset Legend
    patches = [
        mpatches.Patch(color='#ff7f0e', label='Moderate AQI (101–200)'),
        mpatches.Patch(color='#2ca02c', label='Satisfactory AQI (51–100)'),
        mpatches.Patch(color='#1f77b4', label='Good AQI (0–50)')
    ]
    ax.legend(handles=patches, loc='lower right', framealpha=0.95, fontsize=9.5, title="CPCB NAQI Category", title_fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.5)
    
    fig1_path = os.path.join(out_dir, "fig1_aqi_ranked_eligible_source_zones.png")
    fig.tight_layout()
    fig.savefig(fig1_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved Figure 1: {fig1_path}")

    # -------------------------------------------------------------
    # FIGURE 2: Source-to-Neighbor Transport Corridors (4-Panel Map)
    # -------------------------------------------------------------
    print("Generating Figure 2: Source-to-Neighbor Transport Corridors (4-Panel)...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 13), dpi=300)
    axes = axes.flatten()
    
    panels_info = [
        {'title': 'Panel A: Rank #1 Ahmedabad (Gyaspur - IND_r060_c018)\nAQI: 128.7 (Moderate) | PM2.5: 62.3 µg/m³', 'st_id': 227534, 'xlim': (69.5, 75.5), 'ylim': (20.5, 25.5)},
        {'title': 'Panel B: Rank #3 Agra (Avas Vikas - IND_r043_c040)\nAQI: 87.5 (Satisfactory) | PM2.5: 45.5 µg/m³', 'st_id': 227931, 'xlim': (75.5, 81.5), 'ylim': (25.0, 29.5)},
        {'title': 'Panel C: Rank #4 Prayagraj (Jhunsi - IND_r050_c056)\nAQI: 64.0 (Satisfactory) | PM2.5: 35.7 µg/m³', 'st_id': 227384, 'xlim': (79.5, 85.5), 'ylim': (23.5, 28.0)},
        {'title': 'Panel D: Rank #6 Kanpur (Kidwai Nagar - IND_r046_c049)\nAQI: 40.6 (Good) | PM2.5: 24.3 µg/m³', 'st_id': 234568, 'xlim': (78.0, 84.0), 'ylim': (24.5, 28.5)}
    ]
    
    for i, p_info in enumerate(panels_info):
        ax = axes[i]
        ax.set_facecolor("#f8f9fa")
        plot_india_background(ax)
        ax.set_xlim(p_info['xlim'])
        ax.set_ylim(p_info['ylim'])
        ax.set_title(p_info['title'], fontsize=10.5, fontweight='bold', pad=8)
        ax.set_xlabel("Longitude (°E)", fontsize=9)
        ax.set_ylabel("Latitude (°N)", fontsize=9)
        ax.grid(True, linestyle=":", alpha=0.5)
        
        st_id = p_info['st_id']
        st_info = df_src[df_src['station_id'] == st_id].iloc[0]
        s_lat, s_lon = st_info['station_latitude'], st_info['station_longitude']
        
        # Plot source station
        ax.plot(s_lon, s_lat, marker='*', markersize=14, color='#d62728', markeredgecolor='black', zorder=10)
        ax.text(s_lon, s_lat + 0.15, f"SOURCE\n{st_info['city']}", fontsize=8, fontweight='bold', ha='center',
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.9, edgecolor="#d62728"), zorder=11)
        
        # Plot 6h and 24h destination links
        for w, col, lw_base in [(6.0, '#1f77b4', 2.0), (24.0, '#ff7f0e', 1.2)]:
            sub_dest = df_dest[
                (df_dest['station_id'] == st_id) &
                (df_dest['elapsed_time_hours'] == w) &
                (df_dest['dest_grid_id'] != 'OUTSIDE_DOMAIN')
            ].head(6)
            
            for _, d_row in sub_dest.iterrows():
                d_lat = d_row['dest_latitude']
                d_lon = d_row['dest_longitude']
                frac = d_row['mean_transport_fraction']
                rank_d = int(d_row['dest_rank'])
                
                if pd.isna(d_lat) or pd.isna(d_lon):
                    continue
                if d_row['distance_km'] < 10.0:
                    continue
                    
                width = max(0.8, frac * 20.0 * lw_base)
                alpha = np.clip(frac * 6.0, 0.4, 0.9)
                
                ax.annotate(
                    "", xy=(d_lon, d_lat), xytext=(s_lon, s_lat),
                    arrowprops=dict(
                        arrowstyle="-|>", color=col, lw=width, alpha=alpha,
                        shrinkA=3, shrinkB=4, mutation_scale=10
                    ), zorder=5
                )
                if w == 6.0 and rank_d <= 3:
                    ax.scatter(d_lon, d_lat, s=40, color=col, edgecolors='black', zorder=7)
                    ax.text(d_lon + 0.08, d_lat + 0.05, f"D#{rank_d} ({frac*100:.1f}%)",
                            fontsize=7.5, fontweight='bold', color=col, zorder=8)

        # Legend on each panel
        p1 = mpatches.Patch(color='#1f77b4', label='6h Advection Vector')
        p2 = mpatches.Patch(color='#ff7f0e', label='24h Advection Vector')
        ax.legend(handles=[p1, p2], loc='lower right', fontsize=8, framealpha=0.9)
        
    fig.suptitle("Source-to-Neighbor Modeled Transport Vectors for Priority AQI Source Zones",
                 fontsize=13, fontweight='bold', y=0.995)
    fig2_path = os.path.join(out_dir, "fig2_source_to_neighbor_transport_corridors.png")
    fig.tight_layout()
    fig.savefig(fig2_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved Figure 2: {fig2_path}")

    # -------------------------------------------------------------
    # FIGURE 3: Destination Rankings and Transport Decay Curves
    # -------------------------------------------------------------
    print("Generating Figure 3: Destination Rankings and Transport Decay...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=300)
    
    # Palette for windows
    win_colors = {
        1.0: '#1f77b4',
        3.0: '#2ca02c',
        6.0: '#ff7f0e',
        12.0: '#9467bd',
        24.0: '#d62728'
    }
    
    # Average across all 10 stations for clean general decay profile
    for w in [1.0, 3.0, 6.0, 12.0, 24.0]:
        sub_w = df_dest[
            (df_dest['elapsed_time_hours'] == w) &
            (df_dest['dest_grid_id'] != 'OUTSIDE_DOMAIN') &
            (df_dest['dest_rank'] <= 25)
        ]
        mean_by_rank = sub_w.groupby('dest_rank')['mean_transport_fraction'].mean()
        cum_by_rank = mean_by_rank.cumsum()
        
        ax1.plot(mean_by_rank.index, mean_by_rank.values, marker='o', markersize=4,
                 linewidth=2.0, color=win_colors[w], label=f'{int(w)}h Window')
        ax2.plot(cum_by_rank.index, cum_by_rank.values, marker='s', markersize=4,
                 linewidth=2.0, color=win_colors[w], label=f'{int(w)}h Window')
        
    ax1.set_xlabel("Destination Zone Rank (Descending Transport Fraction)", fontsize=10.5, fontweight='bold')
    ax1.set_ylabel("Mean Transport Fraction (T)", fontsize=10.5, fontweight='bold')
    ax1.set_title("Panel A: Plume Dispersion & Spatial Fraction Decay", fontsize=11, fontweight='bold')
    ax1.set_xlim(1, 25)
    ax1.set_ylim(0, 0.45)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc='upper right', fontsize=9)
    
    ax2.set_xlabel("Destination Zone Rank (Descending Transport Fraction)", fontsize=10.5, fontweight='bold')
    ax2.set_ylabel("Cumulative Transport Fraction (Σ T)", fontsize=10.5, fontweight='bold')
    ax2.set_title("Panel B: Cumulative Plume Coverage Across Top Destinations", fontsize=11, fontweight='bold')
    ax2.set_xlim(1, 25)
    ax2.set_ylim(0, 1.05)
    ax2.axhline(1.0, color='gray', linestyle='--', alpha=0.6, label='100% Probability Closure')
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc='lower right', fontsize=9)
    
    fig.suptitle("Spatial Transport Fraction Concentration vs Destination Zone Rank across Advection Windows",
                 fontsize=12.5, fontweight='bold', y=0.98)
    fig3_path = os.path.join(out_dir, "fig3_destination_rankings_and_transport_decay.png")
    fig.tight_layout()
    fig.savefig(fig3_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved Figure 3: {fig3_path}")

    # -------------------------------------------------------------
    # FIGURE 4: Transported Influence vs Geographic Distance
    # -------------------------------------------------------------
    print("Generating Figure 4: Transported Influence vs Distance...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=300)
    
    # 6h and 24h panels
    for ax, w, title in [(ax1, 6.0, 'Panel A: 6-Hour Horizon (Near-Regional Dispersion)'),
                         (ax2, 24.0, 'Panel B: 24-Hour Horizon (Regional / Long-Range Transport)')]:
        sub_infl = df_infl[
            (df_infl['elapsed_time_hours'] == w) &
            (df_infl['dest_grid_id'] != 'OUTSIDE_DOMAIN') &
            (df_infl['mean_transported_influence_ugm3'] > 0.05)
        ]
        
        # Color by source AQI rank
        scatter = ax.scatter(
            sub_infl['distance_km'], sub_infl['mean_transported_influence_ugm3'],
            c=sub_infl['source_aqi_rank'], cmap='viridis_r', s=45,
            edgecolors='black', linewidth=0.5, alpha=0.85, zorder=5
        )
        
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_xlabel("Geographic Distance to Destination (km)", fontsize=10.5, fontweight='bold')
        ax.set_ylabel("Modeled Transported Influence I (µg/m³)", fontsize=10.5, fontweight='bold')
        ax.grid(True, linestyle=":", alpha=0.6)
        
        # Add distance band vertical lines
        ax.axvline(30, color='#6c757d', linestyle=':', alpha=0.7)
        ax.axvline(100, color='#6c757d', linestyle=':', alpha=0.7)
        if w == 24.0:
            ax.axvline(250, color='#6c757d', linestyle=':', alpha=0.7)
            ax.text(15, ax.get_ylim()[1]*0.9, "Local\n<30km", fontsize=8, color='#495057', ha='center')
            ax.text(65, ax.get_ylim()[1]*0.9, "Near-Reg\n30-100km", fontsize=8, color='#495057', ha='center')
            ax.text(175, ax.get_ylim()[1]*0.9, "Regional\n100-250km", fontsize=8, color='#495057', ha='center')
            ax.text(285, ax.get_ylim()[1]*0.9, "Long-Range\n>=250km", fontsize=8, color='#495057', ha='center')
            
    cbar = fig.colorbar(scatter, ax=[ax1, ax2], orientation='horizontal', fraction=0.06, pad=0.15)
    cbar.set_label("Source Zone AQI Rank (1 = Highest AQI / Worst Air Quality: Ahmedabad)", fontsize=10, fontweight='bold')
    cbar.set_ticks(range(1, 11))
    
    # Prominent Disclaimer Box
    fig.text(0.5, 0.02,
             "SCIENTIFIC HONESTY NOTE: Transported Influence I = C_src × T represents modeled 2D advective dispersion.\n"
             "It is NOT measured destination ambient concentration, NOT total destination PM2.5, and NOT an AQI prediction.",
             ha='center', fontsize=8.5, style='italic', color='#842029',
             bbox=dict(boxstyle="square,pad=0.4", facecolor="#f8d7da", edgecolor="#f5c2c7", lw=1.0))

    fig.suptitle("Modeled Transported PM2.5 Influence vs Source-to-Destination Distance across AQI-Ranked Zones",
                 fontsize=12.5, fontweight='bold', y=0.98)
    fig4_path = os.path.join(out_dir, "fig4_transported_influence_vs_geographic_distance.png")
    fig.tight_layout(rect=[0, 0.08, 1, 0.95])
    fig.savefig(fig4_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved Figure 4: {fig4_path}")

    # -------------------------------------------------------------
    # FIGURE 5: Seasonal Transport Comparison for Highest AQI Zone
    # -------------------------------------------------------------
    print("Generating Figure 5: Seasonal Comparison for Worst AQI Zone...")
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 6), dpi=300)
    
    top_st_id = 227534  # Ahmedabad Gyaspur
    top_s_lat, top_s_lon = 22.98, 72.58
    
    # 1. Validation Pilot (Post-monsoon Autumn 2021)
    # 2. Winter (DJF Climatology)
    # 3. Monsoon (JJAS Climatology)
    seasons_meta = [
        ('Validation Pilot (Autumn 2021)', ax1, df_dest[(df_dest['station_id'] == top_st_id) & (df_dest['elapsed_time_hours'] == 24.0)]),
    ]
    
    # Load seasonal climatologies from Phase 16 if available
    winter_path = "results/phase16_climatology/matrices/transport_matrix_climatology_Winter.csv"
    monsoon_path = "results/phase16_climatology/matrices/transport_matrix_climatology_Monsoon.csv"
    
    df_winter = pd.read_csv(winter_path) if os.path.exists(winter_path) else None
    df_monsoon = pd.read_csv(monsoon_path) if os.path.exists(monsoon_path) else None
    
    if df_winter is not None:
        sub_w = df_winter[(df_winter['station_id'] == top_st_id) & (df_winter['elapsed_time_hours'] == 24.0)].copy()
        seasons_meta.append(('Climatological Winter (DJF 2019–2024)', ax2, sub_w))
    if df_monsoon is not None:
        sub_m = df_monsoon[(df_monsoon['station_id'] == top_st_id) & (df_monsoon['elapsed_time_hours'] == 24.0)].copy()
        seasons_meta.append(('Climatological Monsoon (JJAS 2019–2024)', ax3, sub_m))
        
    for title, ax, sub_df in seasons_meta:
        ax.set_facecolor("#f8f9fa")
        plot_india_background(ax)
        ax.set_xlim(68.0, 78.0)
        ax.set_ylim(19.0, 27.0)
        ax.set_title(title, fontsize=10.5, fontweight='bold', pad=8)
        ax.set_xlabel("Longitude (°E)", fontsize=9)
        ax.set_ylabel("Latitude (°N)", fontsize=9)
        ax.grid(True, linestyle=":", alpha=0.5)
        
        # Plot source
        ax.plot(top_s_lon, top_s_lat, marker='*', markersize=13, color='#d62728', markeredgecolor='black', zorder=10)
        ax.text(top_s_lon, top_s_lat + 0.25, "Ahmedabad", fontsize=8.5, fontweight='bold', ha='center',
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.9, edgecolor="#d62728"), zorder=11)
        
        # Plot top 15 vectors at 24h
        top_dest_rows = sub_df[sub_df['dest_grid_id'] != 'OUTSIDE_DOMAIN'].sort_values(
            by='mean_transport_fraction', ascending=False
        ).head(12)
        
        for _, r in top_dest_rows.iterrows():
            d_gid = r['dest_grid_id']
            frac = r['mean_transport_fraction']
            if d_gid in grid_coords:
                d_lat, d_lon = grid_coords[d_gid]
            else:
                continue
            dist_km = r.get('distance_km', 0.0)
            if dist_km < 15.0:
                continue
                
            ax.annotate(
                "", xy=(d_lon, d_lat), xytext=(top_s_lon, top_s_lat),
                arrowprops=dict(
                    arrowstyle="-|>", color='#1f77b4', lw=max(0.8, frac * 30.0),
                    alpha=np.clip(frac * 8.0, 0.4, 0.85), shrinkA=2, shrinkB=3, mutation_scale=9
                ), zorder=5
            )
            ax.scatter(d_lon, d_lat, s=25, color='#1f77b4', edgecolors='black', linewidth=0.5, zorder=6)

    fig.suptitle("Seasonal Circulation Differences for Worst-AQI Source Zone (Ahmedabad — Rank #1, 24h Window)",
                 fontsize=12.5, fontweight='bold', y=0.98)
    fig5_path = os.path.join(out_dir, "fig5_seasonal_comparison_worst_aqi_zone.png")
    fig.tight_layout()
    fig.savefig(fig5_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved Figure 5: {fig5_path}")
    
    print("\nAll 5 figures successfully created in results/phase17_target_zones/figures/!")


if __name__ == '__main__':
    main()
