"""
Map Visualizer for Phase 20 Interactive Application
Phase 20 - Interactive National Pollution Dispersion Query Application

Renders interactive geospatial Folium maps of 50 km grid-to-grid pollution dispersion:
- Highlights the selected source location and source grid cell.
- Renders reached destination polygons color-coded by transport fraction.
- Clearly delineates the 4 categories:
    1. Valid Terrestrial Land Destination ('IND_50KM_rXXX_cYYY')
    2. Internal Unmodeled Water ('INTERNAL_UNMODELED_WATER')
    3. External Domain Exit ('DOMAIN_EXIT_EXTERNAL')
    4. Unsupported Meteorological Coverage ('UNSUPPORTED_MET_COVERAGE')
- Distinguishes user-clicked coordinates from grid cell centroid.
- Adds rich interactive tooltips and custom HTML legend.
- Strictly displays modeled transport probability, NOT destination ambient AQI.
"""

import os
import json
import folium
from folium import plugins
import branca.colormap as cm
import pandas as pd
import numpy as np

GRID_GEOJSON_PATH = "results/phase18_grid_audit/india_50km_grid.geojson"


class MapVisualizer:
    def __init__(self, geojson_path=GRID_GEOJSON_PATH):
        self.geojson_path = geojson_path
        self.features_by_id = {}
        self._load_features()

    def _load_features(self):
        """Loads and indexes the 1,380 grid cell geometries by grid_id_50km."""
        if os.path.exists(self.geojson_path):
            with open(self.geojson_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for feat in data.get('features', []):
                    gid = feat['properties'].get('grid_id_50km')
                    if gid:
                        self.features_by_id[gid] = feat

    def create_dispersion_map(self, query_result, user_lat=None, user_lon=None, min_fraction=0.0):
        """
        Creates an interactive Folium map representing the dispersion query.
        
        Args:
            query_result (dict): Output dictionary from DateSpecificTransportEngine or AppController.
            user_lat (float, optional): User-specified latitude.
            user_lon (float, optional): User-specified longitude.
            min_fraction (float): Filter threshold for display.
            
        Returns:
            folium.Map: Configured interactive Leaflet map.
        """
        src_lat = query_result.get('source_latitude', 22.0)
        src_lon = query_result.get('source_longitude', 79.0)
        src_gid = query_result.get('source_grid_id', 'UNKNOWN')
        query_date = query_result.get('query_date', '')
        horizon_hours = query_result.get('horizon_hours', 24.0)
        
        # Initialize Folium Map centered on source
        m = folium.Map(
            location=[src_lat, src_lon],
            zoom_start=6,
            tiles="CartoDB positron",
            control_scale=True
        )
        
        # Color palette for transport fractions (0.0 to max_fraction)
        df_results = query_result.get('results_table', pd.DataFrame())
        max_frac = df_results['daily_transport_fraction'].max() if not df_results.empty else 1.0
        max_frac = max(0.05, float(max_frac))
        
        colormap = cm.LinearColormap(
            colors=['#fee5d9', '#fcae91', '#fb6a4a', '#de2d26', '#a50f15'],
            vmin=0.0,
            vmax=max_frac,
            caption=f"Modeled Transport Fraction ({horizon_hours:g}h Horizon)"
        )
        
        # Layer 1: Destination Grid Polygons (Terrestrial)
        dest_fg = folium.FeatureGroup(name="Modeled Destination Cells (Terrestrial)")
        
        marine_water_fraction = 0.0
        domain_exit_fraction = 0.0
        unsupported_met_fraction = 0.0
        
        for _, row in df_results.iterrows():
            d_id = str(row['destination'])
            frac = float(row['daily_transport_fraction'])
            cat = str(row['category'])
            dist_km = row.get('distance_km', np.nan)
            inf_idx = row.get('source_weighted_transport_influence_index', np.nan)
            
            if frac < min_fraction:
                continue
                
            if cat == "INTERNAL_UNMODELED_WATER":
                marine_water_fraction += frac
                continue
            elif cat == "DOMAIN_EXIT_EXTERNAL":
                domain_exit_fraction += frac
                continue
            elif cat == "UNSUPPORTED_MET_COVERAGE":
                unsupported_met_fraction += frac
                continue
                
            # Valid Land Destination
            feat = self.features_by_id.get(d_id)
            if feat is not None:
                fill_color = colormap(frac)
                
                # Format tooltip HTML
                dist_str = f"{dist_km:.1f} km" if not pd.isna(dist_km) else "N/A"
                inf_str = f"{inf_idx:.2f} ug/m3-equiv" if not pd.isna(inf_idx) else "Unmonitored"
                
                popup_html = f"""
                <div style="font-family: Arial, sans-serif; font-size: 12px; min-width: 200px;">
                    <b style="color: #2b5c8f;">Destination: {d_id}</b><br/>
                    <hr style="margin: 4px 0;"/>
                    <b>Category:</b> {cat}<br/>
                    <b>Transport Fraction:</b> {frac*100:.1f}% ({frac:.4f})<br/>
                    <b>Distance from Source:</b> {dist_str}<br/>
                    <b>Source-Weighted Influence:</b> {inf_str}<br/>
                    <i style="color: #666; font-size: 10px;">Physical dispersion probability only. Not ambient AQI.</i>
                </div>
                """
                
                geo_json = folium.GeoJson(
                    feat,
                    style_function=lambda x, fc=fill_color: {
                        'fillColor': fc,
                        'color': '#555555',
                        'weight': 1,
                        'fillOpacity': 0.65
                    },
                    highlight_function=lambda x: {
                        'weight': 3,
                        'color': '#000000',
                        'fillOpacity': 0.85
                    },
                    tooltip=folium.Tooltip(f"{d_id}: {frac*100:.1f}% transport ({dist_str})"),
                    popup=folium.Popup(popup_html, max_width=300)
                )
                geo_json.add_to(dest_fg)
                
        dest_fg.add_to(m)
        
        # Layer 2: Source Cell Highlight
        src_fg = folium.FeatureGroup(name="Source Grid Cell")
        src_feat = self.features_by_id.get(src_gid)
        if src_feat is not None:
            folium.GeoJson(
                src_feat,
                style_function=lambda x: {
                    'fillColor': '#9b59b6',
                    'color': '#8e44ad',
                    'weight': 3,
                    'fillOpacity': 0.45
                },
                tooltip=f"SOURCE CELL: {src_gid}",
                popup=folium.Popup(f"<b>SOURCE CELL: {src_gid}</b><br/>Center: ({src_lat:.4f}, {src_lon:.4f})", max_width=250)
            ).add_to(src_fg)
            
        # Source centroid marker
        folium.CircleMarker(
            location=[src_lat, src_lon],
            radius=6,
            color='#8e44ad',
            fill=True,
            fill_color='#8e44ad',
            fill_opacity=0.9,
            tooltip=f"Source Centroid: {src_gid} ({src_lat:.3f}, {src_lon:.3f})"
        ).add_to(src_fg)
        
        # User coordinate marker (if distinct)
        if user_lat is not None and user_lon is not None:
            dist_user_center = np.sqrt((user_lat - src_lat)**2 + (user_lon - src_lon)**2) * 111.0
            folium.Marker(
                location=[user_lat, user_lon],
                icon=folium.Icon(color="blue", icon="info-sign"),
                tooltip=f"Selected Input Point: ({user_lat:.4f}, {user_lon:.4f})",
                popup=folium.Popup(f"<b>User Selected Point</b><br/>Lat: {user_lat:.4f}<br/>Lon: {user_lon:.4f}<br/>Resolved Cell: {src_gid}<br/>Offset to Center: {dist_user_center:.1f} km", max_width=250)
            ).add_to(src_fg)
            
        src_fg.add_to(m)
        
        # Non-terrestrial categories summary box in map HTML
        non_terr_items = []
        if marine_water_fraction > 0:
            non_terr_items.append(f"<li><span style='color: #2980b9;'>&#9632;</span> <b>Internal Unmodeled Water:</b> {marine_water_fraction*100:.1f}%</li>")
        if domain_exit_fraction > 0:
            non_terr_items.append(f"<li><span style='color: #e67e22;'>&#9632;</span> <b>Domain Exit (International):</b> {domain_exit_fraction*100:.1f}%</li>")
        if unsupported_met_fraction > 0:
            non_terr_items.append(f"<li><span style='color: #7f8c8d;'>&#9632;</span> <b>Unsupported Met Coverage:</b> {unsupported_met_fraction*100:.1f}%</li>")
            
        non_terr_html = ""
        if non_terr_items:
            non_terr_html = f"""
            <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid #ccc; font-size: 11px;">
                <b>Boundary / Non-Land Partition:</b>
                <ul style="margin: 4px 0; padding-left: 18px;">
                    {''.join(non_terr_items)}
                </ul>
            </div>
            """

        # Custom Floating Legend
        legend_html = f"""
        <div style="
            position: fixed; 
            bottom: 30px; 
            right: 30px; 
            width: 260px; 
            background-color: white; 
            z-index: 9999; 
            font-size: 12px; 
            font-family: Arial, sans-serif;
            border: 2px solid #bbb; 
            border-radius: 6px;
            box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
            padding: 10px;
            opacity: 0.95;
        ">
            <h4 style="margin: 0 0 6px 0; font-size: 13px; color: #2c3e50;">Dispersion Footprint ({horizon_hours:g}h)</h4>
            <div style="font-size: 11px; margin-bottom: 6px;">
                <b>Source:</b> {src_gid}<br/>
                <b>Date:</b> {query_date}
            </div>
            <div>
                <span style="display: inline-block; width: 14px; height: 14px; background: #8e44ad; vertical-align: middle; margin-right: 6px;"></span> Source Grid Cell
            </div>
            <div style="margin-top: 4px;">
                <span style="display: inline-block; width: 14px; height: 14px; background: #a50f15; vertical-align: middle; margin-right: 6px;"></span> High Transport (> {max_frac*0.6*100:.0f}%)
            </div>
            <div style="margin-top: 4px;">
                <span style="display: inline-block; width: 14px; height: 14px; background: #fcae91; vertical-align: middle; margin-right: 6px;"></span> Moderate Transport
            </div>
            <div style="margin-top: 4px;">
                <span style="display: inline-block; width: 14px; height: 14px; background: #fee5d9; vertical-align: middle; margin-right: 6px;"></span> Low Transport (< {max_frac*0.2*100:.1f}%)
            </div>
            {non_terr_html}
            <div style="margin-top: 8px; font-size: 10px; color: #7f8c8d; line-height: 1.2;">
                *Strictly 2D physical transport probability. Does NOT represent destination ambient air quality or AQI.
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
        
        folium.LayerControl(collapsed=False).add_to(m)
        return m

    def save_map_html(self, folium_map, out_path):
        """Saves folium map to HTML file."""
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        folium_map.save(out_path)
