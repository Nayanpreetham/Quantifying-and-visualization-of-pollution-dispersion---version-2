"""
Generate Visual Map of the 50 km x 50 km National Grid and Station Mappings
Phase 18 — National 50 km x 50 km Grid Design and Coverage Audit
"""

import os
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import geopandas as gpd
import pandas as pd

def main():
    print("=== Generating 50 km Grid and Station Mapping Figure ===")
    out_dir = "results/phase18_grid_audit"
    fig_path = os.path.join(out_dir, "fig_50km_grid_and_stations.png")
    
    # Load 50km grid geojson
    grid_gdf = gpd.read_file(os.path.join(out_dir, "india_50km_grid.geojson"))
    
    # Load stations
    st_df = pd.read_csv(os.path.join(out_dir, "station_to_50km_grid_mapping.csv"))
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 9), dpi=300)
    
    # Panel A: 50 km Grid by Retention Policy / Land Fraction
    ax1.set_facecolor("#eef2f5")
    ax1.set_xlim(67.0, 98.0)
    ax1.set_ylim(7.0, 36.5)
    ax1.set_xlabel("Longitude (°E)", fontsize=10.5, fontweight='bold')
    ax1.set_ylabel("Latitude (°N)", fontsize=10.5, fontweight='bold')
    ax1.set_title("Panel A: National 50 km × 50 km Terrestrial Grid (EPSG:7755)\n1,380 Cells Intersecting Sovereign Land Boundary",
                  fontsize=11.5, fontweight='bold', pad=10)
    
    color_map = {
        'CORE_INTERIOR': '#2b83ba',
        'MAJORITY_LAND': '#abdda4',
        'COASTAL_BORDER_SIGNIFICANT': '#fdae61',
        'COASTAL_BORDER_SLIGHT': '#d7191c'
    }
    
    for pol, col in color_map.items():
        sub = grid_gdf[grid_gdf['retention_policy'] == pol]
        sub.boundary.plot(ax=ax1, color="#6c757d", linewidth=0.3, alpha=0.6)
        sub.plot(ax=ax1, color=col, alpha=0.75)
        
    patches = [
        mpatches.Patch(color='#2b83ba', label='Core Interior (>=99.9% land, n=1,071)'),
        mpatches.Patch(color='#abdda4', label='Majority Land (50-99.9% land, n=153)'),
        mpatches.Patch(color='#fdae61', label='Coastal/Border (10-50% land, n=94)'),
        mpatches.Patch(color='#d7191c', label='Border Fringe (<10% land, n=62)')
    ]
    ax1.legend(handles=patches, loc='lower right', fontsize=8.5, framealpha=0.95)
    ax1.grid(True, linestyle=":", alpha=0.5)
    
    # Panel B: Station Distribution across 50 km Grid
    ax2.set_facecolor("#eef2f5")
    ax2.set_xlim(67.0, 98.0)
    ax2.set_ylim(7.0, 36.5)
    ax2.set_xlabel("Longitude (°E)", fontsize=10.5, fontweight='bold')
    ax2.set_ylabel("Latitude (°N)", fontsize=10.5, fontweight='bold')
    ax2.set_title("Panel B: Observational Ground Network Co-Location\n103 Stations in 51 Cells (1,329 Cells Unmonitored)",
                  fontsize=11.5, fontweight='bold', pad=10)
    
    # Background 50km cells
    grid_gdf.boundary.plot(ax=ax2, color="#ced4da", linewidth=0.4, alpha=0.7)
    
    # Highlight cells containing stations
    cells_with_st = st_df['grid_id_50km'].unique()
    grid_st_cells = grid_gdf[grid_gdf['grid_id_50km'].isin(cells_with_st)]
    grid_st_cells.plot(ax=ax2, color="#ffe8cc", edgecolor="#fd7e14", linewidth=0.8, alpha=0.85)
    
    # Plot all 103 stations
    all_non_core = st_df[~st_df['is_core_10_pilot_station']]
    ax2.scatter(all_non_core['station_longitude'], all_non_core['station_latitude'],
                s=25, color="#1f77b4", edgecolors="white", linewidth=0.5, label="Monitoring Stations (n=93)", zorder=5)
                
    # Plot 10 core pilot stations
    core_st = st_df[st_df['is_core_10_pilot_station']]
    ax2.scatter(core_st['station_longitude'], core_st['station_latitude'],
                s=90, color="#d62728", marker="*", edgecolors="black", linewidth=0.8, label="Core Pilot Stations (n=10)", zorder=6)
                
    for _, r in core_st.iterrows():
        ax2.text(r['station_longitude'] + 0.35, r['station_latitude'] + 0.15,
                 r['corrected_city'], fontsize=8, fontweight='bold',
                 bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85, edgecolor="#d62728", lw=0.8),
                 zorder=7)
                 
    p_st = [
        mpatches.Patch(color='#ffe8cc', label='Monitored 50 km Cells (n=51, 3.7%)'),
        mpatches.Patch(color='#eef2f5', label='Unmonitored 50 km Cells (n=1,329, 96.3%)'),
        mpatches.Patch(color='#1f77b4', label='Active OpenAQ Stations (n=93)'),
        mpatches.Patch(color='#d62728', label='Core Pilot Hubs (n=10)')
    ]
    ax2.legend(handles=p_st, loc='lower right', fontsize=8.5, framealpha=0.95)
    ax2.grid(True, linestyle=":", alpha=0.5)
    
    fig.suptitle("Phase 18 — National 50 km × 50 km Grid Architecture and Observational Coverage",
                 fontsize=13.5, fontweight='bold', y=0.98)
    fig.tight_layout()
    fig.savefig(fig_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved Figure: {fig_path}")

if __name__ == '__main__':
    main()
