"""
Map Visualizer for Phase 20/21 Environmental Intelligence Explorer
Renders interactive geospatial Leaflet/Folium maps for India-wide 2D pollution dispersion:
- Complete Velvet Palette:
    Primary (60%): Charcoal Black (#232528)
    Secondary (30%): Dark Beige (#B6A38E)
    Accent (10%): Velvet Red (#6B1B1E)
- Multi-level geographical hierarchy:
    Level 1: Asian continent with international borders.
    Level 2: Indian State and Union Territory boundaries in Dark Beige (#B6A38E).
    Level 3: District boundaries (with district and state hover tooltips).
    Level 4: Toggleable 50 km model grid overlay (EPSG:7755).
- Dual analysis visualization:
    1. Receptor Inflow Analysis: Highlighted target receptor in Velvet Red (#6B1B1E),
       incoming contributing source cells in harmonious beige-to-crimson gradient,
       flow pathways in Dark Beige (#B6A38E), and source-weighted influence.
    2. Source Dispersion Analysis: Highlighted source cell in Velvet Red (#6B1B1E),
       downwind transport footprint, dispersion pathways, and boundary partitions.
- Modern floating dark-glass cartographic legend with Velvet Palette styling.
"""

import os
import json
import folium
from folium import plugins
import branca.colormap as cm
import pandas as pd
import numpy as np

GRID_GEOJSON_PATH = "results/phase18_grid_audit/india_50km_grid.geojson"
ASIA_GEOJSON_PATH = "data/processed/geography/asia_countries.geojson" if os.path.exists("data/processed/geography/asia_countries.geojson") else "data/raw/geography/asia_countries.geojson"
NATIONAL_GEOJSON_PATH = "data/processed/geography/india_national_web.geojson" if os.path.exists("data/processed/geography/india_national_web.geojson") else "data/raw/geography/india_national_web.geojson"
STATES_GEOJSON_PATH = "data/processed/geography/india_states_web.geojson" if os.path.exists("data/processed/geography/india_states_web.geojson") else "data/raw/geography/india_states_web.geojson"
DISTRICTS_GEOJSON_PATH = "data/processed/geography/india_districts_web.geojson" if os.path.exists("data/processed/geography/india_districts_web.geojson") else "data/raw/geography/india_districts_web.geojson"
GRID_TO_DISTRICTS_PATH = "data/processed/geography/grid_to_districts_mapping.json" if os.path.exists("data/processed/geography/grid_to_districts_mapping.json") else "data/raw/geography/grid_to_districts_mapping.json"


class MapVisualizer:
    def __init__(self, geojson_path=GRID_GEOJSON_PATH):
        self.geojson_path = geojson_path
        self.features_by_id = {}
        self.grid_to_regions = {}
        self._asia_geojson = None
        self._national_geojson = None
        self._states_geojson = None
        self._districts_geojson = None
        
        self._load_features()
        self._load_administrative_boundaries()

    def _load_features(self):
        """Loads and indexes the 1,380 50 km grid cell geometries by grid_id_50km."""
        if os.path.exists(self.geojson_path):
            with open(self.geojson_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for feat in data.get('features', []):
                    gid = feat['properties'].get('grid_id_50km')
                    if gid:
                        self.features_by_id[gid] = feat
                        
        if os.path.exists(GRID_TO_DISTRICTS_PATH):
            try:
                with open(GRID_TO_DISTRICTS_PATH, 'r', encoding='utf-8') as f:
                    self.grid_to_regions = json.load(f)
            except Exception:
                self.grid_to_regions = {}

    def _load_administrative_boundaries(self):
        """Loads optional simplified GeoJSON layers for Asian context, Sovereign India, States, and Districts."""
        if os.path.exists(ASIA_GEOJSON_PATH):
            try:
                with open(ASIA_GEOJSON_PATH, 'r', encoding='utf-8') as f:
                    self._asia_geojson = json.load(f)
            except Exception:
                self._asia_geojson = None

        if os.path.exists(NATIONAL_GEOJSON_PATH):
            try:
                with open(NATIONAL_GEOJSON_PATH, 'r', encoding='utf-8') as f:
                    self._national_geojson = json.load(f)
            except Exception:
                self._national_geojson = None

        if os.path.exists(STATES_GEOJSON_PATH):
            try:
                with open(STATES_GEOJSON_PATH, 'r', encoding='utf-8') as f:
                    self._states_geojson = json.load(f)
            except Exception:
                self._states_geojson = None

    def get_region_name(self, grid_id):
        """Returns human-friendly region names associated with a 50 km grid cell."""
        regions = self.grid_to_regions.get(grid_id)
        if regions:
            return ", ".join(regions[:2])
        return grid_id

    def create_dispersion_map(self, query_result, user_lat=None, user_lon=None, min_fraction=0.0,
                              show_pathways=True, show_states=True, show_grid=False):
        """
        Creates an interactive Folium dark-cartographic map for Source Dispersion Analysis
        styled with the 60-30-10 Velvet Palette (#232528 Charcoal, #B6A38E Dark Beige, #6B1B1E Velvet Red).
        """
        src_lat = query_result.get('source_latitude', 22.0)
        src_lon = query_result.get('source_longitude', 79.0)
        src_gid = query_result.get('source_grid_id', 'UNKNOWN')
        query_date = query_result.get('query_date', '')
        horizon_hours = query_result.get('horizon_hours', 24.0)
        src_region_name = self.get_region_name(src_gid)
        
        # Center map on source location with dark cartographic tiles
        m = folium.Map(
            location=[src_lat, src_lon],
            zoom_start=6,
            tiles="CartoDB dark_matter",
            control_scale=True
        )
        
        # Base Layer 1: Asian Regional Context
        if self._asia_geojson is not None:
            asia_fg = folium.FeatureGroup(name="Asian Context & Neighbors (Level 1)", show=True)
            folium.GeoJson(
                self._asia_geojson,
                style_function=lambda x: {
                    'fillColor': '#1A1C1E',
                    'color': '#33363B',
                    'weight': 1.0,
                    'fillOpacity': 0.30
                },
                tooltip=folium.GeoJsonTooltip(fields=['name'], aliases=['Country:'])
            ).add_to(asia_fg)
            asia_fg.add_to(m)

        # Base Layer 2: Indian State Boundaries (Dark Beige: #B6A38E)
        if self._states_geojson is not None:
            states_fg = folium.FeatureGroup(name="Indian States & UTs (Level 2)", show=show_states)
            folium.GeoJson(
                self._states_geojson,
                style_function=lambda x: {
                    'fillColor': '#232528',
                    'color': '#B6A38E',
                    'weight': 1.2,
                    'fillOpacity': 0.08
                },
                highlight_function=lambda x: {
                    'color': '#EAE5DE',
                    'weight': 2.0,
                    'fillOpacity': 0.2
                },
                tooltip=folium.GeoJsonTooltip(fields=['NAME_1'], aliases=['State:'])
            ).add_to(states_fg)
            states_fg.add_to(m)

        # Base Layer 2b: Indian Sovereign Boundary Outline (Complete National Extent)
        if self._national_geojson is not None:
            national_fg = folium.FeatureGroup(name="India Sovereign Boundary (Complete National Extent)", show=True)
            folium.GeoJson(
                self._national_geojson,
                style_function=lambda x: {
                    'fillColor': 'transparent',
                    'color': '#B6A38E',
                    'weight': 2.0,
                    'fillOpacity': 0.0
                },
                tooltip=folium.Tooltip("Republic of India — Sovereign National Territory")
            ).add_to(national_fg)
            national_fg.add_to(m)

        # Layer 3: 50 km Model Grid Overlay
        if show_grid or self.geojson_path:
            grid_fg = folium.FeatureGroup(name="50 km Atmospheric Model Grid (EPSG:7755)", show=show_grid)
            sample_feats = list(self.features_by_id.values())[::2]
            folium.GeoJson(
                {"type": "FeatureCollection", "features": sample_feats},
                style_function=lambda x: {
                    'fillColor': 'transparent',
                    'color': '#4A4742',
                    'weight': 0.7,
                    'fillOpacity': 0.0
                },
                tooltip=folium.Tooltip("50 km Model Grid Cell (EPSG:7755)")
            ).add_to(grid_fg)
            grid_fg.add_to(m)

        # Color palette for transport fractions: Beige to Terracotta to Velvet Red
        df_results = query_result.get('results_table', pd.DataFrame())
        max_frac = df_results['daily_transport_fraction'].max() if not df_results.empty else 1.0
        max_frac = max(0.05, float(max_frac))
        
        colormap = cm.LinearColormap(
            colors=['#EAE5DE', '#D4A373', '#BC4749', '#6B1B1E'],
            vmin=0.0,
            vmax=max_frac,
            caption=f"Downwind Transport Fraction ({horizon_hours:g}h Horizon)"
        )
        
        # Layer 4: Destination Grid Polygons
        dest_fg = folium.FeatureGroup(name="Downwind Destination Footprint", show=True)
        pathways_fg = folium.FeatureGroup(name="Dispersion Transport Pathways", show=show_pathways)
        
        marine_water_fraction = 0.0
        domain_exit_fraction = 0.0
        unsupported_met_fraction = 0.0
        
        for _, row in df_results.iterrows():
            d_id = str(row['destination'])
            frac = float(row['daily_transport_fraction'])
            cat = str(row['category'])
            dist_km = row.get('distance_km', np.nan)
            inf_idx = row.get('source_weighted_transport_influence_index', np.nan)
            dest_name = self.get_region_name(d_id)
            
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
                
            feat = self.features_by_id.get(d_id)
            if feat is not None:
                fill_color = colormap(frac)
                dist_str = f"{dist_km:.1f} km" if not pd.isna(dist_km) else "N/A"
                inf_str = f"{inf_idx:.2f} ug/m3-eq" if not pd.isna(inf_idx) else "Unmonitored"
                
                popup_html = f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 12px; min-width: 230px; background: #232528; color: #EAE5DE; padding: 12px; border-radius: 6px; border: 1px solid #B6A38E;">
                    <div style="font-size: 13px; font-weight: 700; color: #B6A38E; margin-bottom: 4px;">{dest_name}</div>
                    <div style="font-size: 10px; color: #A0988E; margin-bottom: 6px;">Grid Cell: {d_id} ({cat})</div>
                    <div style="height: 1px; background: rgba(182, 163, 142, 0.3); margin: 6px 0;"></div>
                    <div><b>Downwind Transport:</b> <span style="color: #EAE5DE; font-weight: 600;">{frac*100:.2f}%</span> ({frac:.4f})</div>
                    <div><b>Distance from Source:</b> {dist_str}</div>
                    <div><b>Source-Weighted Influence:</b> <span style="color: #B6A38E;">{inf_str}</span></div>
                    <div style="margin-top: 6px; font-size: 10px; color: #A0988E; font-style: italic;">
                        Physical transport probability only. Not ambient AQI.
                    </div>
                </div>
                """
                
                folium.GeoJson(
                    feat,
                    style_function=lambda x, fc=fill_color: {
                        'fillColor': fc,
                        'color': '#B6A38E',
                        'weight': 1.0,
                        'fillOpacity': 0.65
                    },
                    highlight_function=lambda x: {
                        'weight': 2.5,
                        'color': '#FFFFFF',
                        'fillOpacity': 0.85
                    },
                    tooltip=folium.Tooltip(f"{dest_name} ({d_id}): {frac*100:.1f}% transport ({dist_str})"),
                    popup=folium.Popup(popup_html, max_width=320)
                ).add_to(dest_fg)
                
                # Draw pathway connector in Dark Beige (#B6A38E)
                if show_pathways and frac >= 0.03:
                    d_props = feat.get('properties', {})
                    d_lat = d_props.get('center_latitude_deg')
                    d_lon = d_props.get('center_longitude_deg')
                    if d_lat and d_lon and (d_lat != src_lat or d_lon != src_lon):
                        line_weight = max(1.5, min(4.0, frac * 18.0))
                        folium.PolyLine(
                            locations=[[src_lat, src_lon], [d_lat, d_lon]],
                            color='#B6A38E',
                            weight=line_weight,
                            opacity=0.75,
                            dash_array='4, 6',
                            tooltip=f"Path to {dest_name}: {frac*100:.1f}%"
                        ).add_to(pathways_fg)
                        
        dest_fg.add_to(m)
        pathways_fg.add_to(m)
        
        # Layer 5: Source Cell Highlight in Velvet Red (#6B1B1E)
        src_fg = folium.FeatureGroup(name="Source Region & Centroid", show=True)
        src_feat = self.features_by_id.get(src_gid)
        if src_feat is not None:
            folium.GeoJson(
                src_feat,
                style_function=lambda x: {
                    'fillColor': '#6B1B1E',
                    'color': '#B6A38E',
                    'weight': 3.5,
                    'fillOpacity': 0.50
                },
                tooltip=f"SOURCE: {src_region_name} ({src_gid})",
                popup=folium.Popup(f"<b>SOURCE REGION: {src_region_name}</b><br/>Cell: {src_gid}<br/>Centroid: ({src_lat:.4f}, {src_lon:.4f})", max_width=250)
            ).add_to(src_fg)
            
        # Source centroid marker in Velvet Red
        folium.CircleMarker(
            location=[src_lat, src_lon],
            radius=8,
            color='#B6A38E',
            fill=True,
            fill_color='#6B1B1E',
            fill_opacity=0.95,
            tooltip=f"Source Centroid: {src_region_name} ({src_lat:.3f}, {src_lon:.3f})"
        ).add_to(src_fg)
        
        # User input coordinates marker
        if user_lat is not None and user_lon is not None:
            dist_user_center = np.sqrt((user_lat - src_lat)**2 + (user_lon - src_lon)**2) * 111.0
            folium.Marker(
                location=[user_lat, user_lon],
                icon=folium.Icon(color="red", icon="screenshot", prefix="glyphicon"),
                tooltip=f"Selected Location: ({user_lat:.4f}, {user_lon:.4f})",
                popup=folium.Popup(f"<b>Selected Location</b><br/>Lat: {user_lat:.4f}, Lon: {user_lon:.4f}<br/>Resolved Grid: {src_gid}<br/>Offset: {dist_user_center:.1f} km", max_width=250)
            ).add_to(src_fg)
            
        src_fg.add_to(m)
        
        # Non-terrestrial categories
        non_terr_items = []
        if marine_water_fraction > 0:
            non_terr_items.append(f"<li><span style='color: #B6A38E;'>&#9632;</span> <b>Coastal / Marine Water:</b> {marine_water_fraction*100:.1f}%</li>")
        if domain_exit_fraction > 0:
            non_terr_items.append(f"<li><span style='color: #BC4749;'>&#9632;</span> <b>Domain Exit (Cross-Border):</b> {domain_exit_fraction*100:.1f}%</li>")
        if unsupported_met_fraction > 0:
            non_terr_items.append(f"<li><span style='color: #A0988E;'>&#9632;</span> <b>Unsupported Met Bounds:</b> {unsupported_met_fraction*100:.1f}%</li>")
            
        non_terr_html = ""
        if non_terr_items:
            non_terr_html = f"""
            <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid rgba(182,163,142,0.3); font-size: 11px;">
                <b>Boundary / Domain Exits:</b>
                <ul style="margin: 4px 0; padding-left: 16px;">
                    {''.join(non_terr_items)}
                </ul>
            </div>
            """

        # Floating Velvet Palette Legend
        legend_html = f"""
        <div style="
            position: fixed; 
            bottom: 25px; 
            right: 25px; 
            width: 280px; 
            background: rgba(35, 37, 40, 0.96); 
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1px solid #B6A38E;
            border-radius: 8px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
            color: #EAE5DE;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 12px 14px;
            z-index: 9999;
            font-size: 11px;
        ">
            <div style="font-size: 13px; font-weight: 700; color: #EAE5DE; margin-bottom: 2px;">Dispersion Footprint</div>
            <div style="font-size: 11px; color: #B6A38E; margin-bottom: 8px;">
                <b>Source:</b> {src_region_name} · {horizon_hours:g}h window
            </div>
            <div style="margin-bottom: 4px;">
                <span style="display: inline-block; width: 12px; height: 12px; background: #6B1B1E; border: 1px solid #B6A38E; border-radius: 2px; vertical-align: middle; margin-right: 6px;"></span>
                <b>Source Region</b> ({src_gid})
            </div>
            <div style="margin-bottom: 4px;">
                <span style="display: inline-block; width: 12px; height: 12px; background: #BC4749; border-radius: 2px; vertical-align: middle; margin-right: 6px;"></span>
                <b>High Transport Reach</b> (> {max_frac*0.6*100:.1f}%)
            </div>
            <div style="margin-bottom: 4px;">
                <span style="display: inline-block; width: 12px; height: 12px; background: #D4A373; border-radius: 2px; vertical-align: middle; margin-right: 6px;"></span>
                <b>Moderate Transport Reach</b>
            </div>
            <div style="margin-bottom: 4px;">
                <span style="display: inline-block; width: 12px; height: 12px; background: #EAE5DE; border-radius: 2px; vertical-align: middle; margin-right: 6px;"></span>
                <b>Peripheral Reach</b> (< {max_frac*0.2*100:.1f}%)
            </div>
            {non_terr_html}
            <div style="margin-top: 8px; font-size: 9.5px; color: #A0988E; line-height: 1.25;">
                *Strictly 2D physical transport probability. Does not calculate ambient AQI or stack emissions.
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
        folium.LayerControl(collapsed=True).add_to(m)
        return m

    def create_target_influence_map(self, query_result, user_lat=None, user_lon=None, min_fraction=0.0,
                                    show_pathways=True, show_states=True, show_grid=False):
        """
        Creates an interactive Folium dark-cartographic map for Receptor Inflow Analysis
        styled with the 60-30-10 Velvet Palette (#232528 Charcoal, #B6A38E Dark Beige, #6B1B1E Velvet Red).
        """
        target_info = query_result.get('target_info', {})
        target_lat = target_info.get('target_latitude', 22.0)
        target_lon = target_info.get('target_longitude', 79.0)
        target_gid = target_info.get('target_grid_id', 'UNKNOWN')
        query_date = query_result.get('query_date', '')
        horizon_hours = query_result.get('horizon_hours', 24.0)
        target_region_name = self.get_region_name(target_gid)
        
        # Center map on target receptor location
        m = folium.Map(
            location=[target_lat, target_lon],
            zoom_start=6,
            tiles="CartoDB dark_matter",
            control_scale=True
        )
        
        # Base Layer 1: Asian Regional Context
        if self._asia_geojson is not None:
            asia_fg = folium.FeatureGroup(name="Asian Context & Neighbors (Level 1)", show=True)
            folium.GeoJson(
                self._asia_geojson,
                style_function=lambda x: {
                    'fillColor': '#1A1C1E',
                    'color': '#33363B',
                    'weight': 1.0,
                    'fillOpacity': 0.30
                },
                tooltip=folium.GeoJsonTooltip(fields=['name'], aliases=['Country:'])
            ).add_to(asia_fg)
            asia_fg.add_to(m)

        # Base Layer 2: Indian State Boundaries in Dark Beige (#B6A38E)
        if self._states_geojson is not None:
            states_fg = folium.FeatureGroup(name="Indian States & UTs (Level 2)", show=show_states)
            folium.GeoJson(
                self._states_geojson,
                style_function=lambda x: {
                    'fillColor': '#232528',
                    'color': '#B6A38E',
                    'weight': 1.2,
                    'fillOpacity': 0.08
                },
                highlight_function=lambda x: {
                    'color': '#EAE5DE',
                    'weight': 2.0,
                    'fillOpacity': 0.2
                },
                tooltip=folium.GeoJsonTooltip(fields=['NAME_1'], aliases=['State:'])
            ).add_to(states_fg)
            states_fg.add_to(m)

        # Base Layer 2b: Indian Sovereign Boundary Outline (Complete National Extent)
        if self._national_geojson is not None:
            national_fg = folium.FeatureGroup(name="India Sovereign Boundary (Complete National Extent)", show=True)
            folium.GeoJson(
                self._national_geojson,
                style_function=lambda x: {
                    'fillColor': 'transparent',
                    'color': '#B6A38E',
                    'weight': 2.0,
                    'fillOpacity': 0.0
                },
                tooltip=folium.Tooltip("Republic of India — Sovereign National Territory")
            ).add_to(national_fg)
            national_fg.add_to(m)

        # Layer 3: 50 km Model Grid Overlay
        if show_grid or self.geojson_path:
            grid_fg = folium.FeatureGroup(name="50 km Atmospheric Model Grid (EPSG:7755)", show=show_grid)
            sample_feats = list(self.features_by_id.values())[::2]
            folium.GeoJson(
                {"type": "FeatureCollection", "features": sample_feats},
                style_function=lambda x: {
                    'fillColor': 'transparent',
                    'color': '#4A4742',
                    'weight': 0.7,
                    'fillOpacity': 0.0
                },
                tooltip=folium.Tooltip("50 km Model Grid Cell (EPSG:7755)")
            ).add_to(grid_fg)
            grid_fg.add_to(m)

        df_results = query_result.get('results_table', pd.DataFrame())
        max_frac = df_results['daily_transport_fraction'].max() if not df_results.empty else 1.0
        max_frac = max(0.05, float(max_frac))
        
        colormap = cm.LinearColormap(
            colors=['#EAE5DE', '#D4A373', '#BC4749', '#6B1B1E'],
            vmin=0.0,
            vmax=max_frac,
            caption=f"Inflow Transport Fraction ({horizon_hours:g}h Horizon)"
        )
        
        # Layer 4: Contributing Source Grid Cells
        sources_fg = folium.FeatureGroup(name="Contributing Source Regions (Inflow)", show=True)
        pathways_fg = folium.FeatureGroup(name="Inflow Transport Pathways", show=show_pathways)
        
        if not df_results.empty:
            for _, row in df_results.iterrows():
                src_id = str(row['source_grid_id'])
                frac = float(row['daily_transport_fraction'])
                dist_km = row.get('distance_km', np.nan)
                src_pm25 = row.get('source_pm25_ugm3', np.nan)
                inf_idx = row.get('source_weighted_transport_influence_index', np.nan)
                obs_status = row.get('source_observation_status', 'UNMONITORED')
                src_region_name = self.get_region_name(src_id)
                
                if frac < min_fraction:
                    continue
                    
                feat = self.features_by_id.get(src_id)
                if feat is not None:
                    fill_color = colormap(frac)
                    dist_str = f"{dist_km:.1f} km" if not pd.isna(dist_km) else "N/A"
                    pm_str = f"{src_pm25:.1f} ug/m3" if not pd.isna(src_pm25) else "Unmonitored"
                    inf_str = f"{inf_idx:.2f} ug/m3-eq" if not pd.isna(inf_idx) else "Unmonitored"
                    
                    popup_html = f"""
                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 12px; min-width: 230px; background: #232528; color: #EAE5DE; padding: 12px; border-radius: 6px; border: 1px solid #B6A38E;">
                        <div style="font-size: 13px; font-weight: 700; color: #B6A38E; margin-bottom: 4px;">{src_region_name}</div>
                        <div style="font-size: 10px; color: #A0988E; margin-bottom: 6px;">Source Cell: {src_id}</div>
                        <div style="height: 1px; background: rgba(182, 163, 142, 0.3); margin: 6px 0;"></div>
                        <div><b>Transport to Target:</b> <span style="color: #EAE5DE; font-weight: 600;">{frac*100:.2f}%</span> ({frac:.4f})</div>
                        <div><b>Distance:</b> {dist_str}</div>
                        <div><b>Source Observed PM2.5:</b> {pm_str}</div>
                        <div><b>Source-Weighted Influence:</b> <span style="color: #B6A38E;">{inf_str}</span></div>
                        <div style="margin-top: 6px; font-size: 10px; color: #A0988E; font-style: italic;">
                            Candidate transport pathway reaching target. Not verified emissions.
                        </div>
                    </div>
                    """
                    
                    folium.GeoJson(
                        feat,
                        style_function=lambda x, fc=fill_color: {
                            'fillColor': fc,
                            'color': '#B6A38E',
                            'weight': 1.0,
                            'fillOpacity': 0.60
                        },
                        highlight_function=lambda x: {
                            'weight': 2.5,
                            'color': '#FFFFFF',
                            'fillOpacity': 0.85
                        },
                        tooltip=folium.Tooltip(f"{src_region_name} ({src_id}): {frac*100:.2f}% inflow ({dist_str})"),
                        popup=folium.Popup(popup_html, max_width=320)
                    ).add_to(sources_fg)
                    
                    # Draw pathway connector from source centroid to target centroid in Dark Beige (#B6A38E)
                    if show_pathways and frac >= 0.02:
                        s_props = feat.get('properties', {})
                        s_lat = s_props.get('center_latitude_deg')
                        s_lon = s_props.get('center_longitude_deg')
                        if s_lat and s_lon and (s_lat != target_lat or s_lon != target_lon):
                            line_weight = max(1.5, min(4.0, frac * 18.0))
                            folium.PolyLine(
                                locations=[[s_lat, s_lon], [target_lat, target_lon]],
                                color='#B6A38E',
                                weight=line_weight,
                                opacity=0.75,
                                dash_array='4, 6',
                                tooltip=f"Inflow from {src_region_name}: {frac*100:.1f}%"
                            ).add_to(pathways_fg)
                            
        sources_fg.add_to(m)
        pathways_fg.add_to(m)
        
        # Layer 5: Target Receptor Grid Cell Highlight in Velvet Red (#6B1B1E)
        target_fg = folium.FeatureGroup(name="Target Receptor Region", show=True)
        tgt_feat = self.features_by_id.get(target_gid)
        if tgt_feat is not None:
            folium.GeoJson(
                tgt_feat,
                style_function=lambda x: {
                    'fillColor': '#6B1B1E',
                    'color': '#B6A38E',
                    'weight': 3.5,
                    'fillOpacity': 0.50
                },
                tooltip=f"TARGET RECEPTOR: {target_region_name} ({target_gid})",
                popup=folium.Popup(f"<b>TARGET RECEPTOR: {target_region_name}</b><br/>Cell: {target_gid}<br/>Center: ({target_lat:.4f}, {target_lon:.4f})", max_width=250)
            ).add_to(target_fg)
            
        # Target centroid marker in Velvet Red
        folium.CircleMarker(
            location=[target_lat, target_lon],
            radius=8,
            color='#B6A38E',
            fill=True,
            fill_color='#6B1B1E',
            fill_opacity=0.95,
            tooltip=f"Target Centroid: {target_region_name} ({target_lat:.3f}, {target_lon:.3f})"
        ).add_to(target_fg)
        
        # User coordinate marker (if distinct from target centroid)
        if user_lat is not None and user_lon is not None:
            dist_user_center = np.sqrt((user_lat - target_lat)**2 + (user_lon - target_lon)**2) * 111.0
            folium.Marker(
                location=[user_lat, user_lon],
                icon=folium.Icon(color="red", icon="screenshot", prefix="glyphicon"),
                tooltip=f"Selected Target Location: ({user_lat:.4f}, {user_lon:.4f})",
                popup=folium.Popup(f"<b>Selected Target Point</b><br/>Lat: {user_lat:.4f}, Lon: {user_lon:.4f}<br/>Resolved Cell: {target_gid}<br/>Offset: {dist_user_center:.1f} km", max_width=250)
            ).add_to(target_fg)
            
        target_fg.add_to(m)
        
        # Modern Floating Velvet-Palette Legend
        legend_html = f"""
        <div style="
            position: fixed; 
            bottom: 25px; 
            right: 25px; 
            width: 280px; 
            background: rgba(35, 37, 40, 0.96); 
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1px solid #B6A38E;
            border-radius: 8px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
            color: #EAE5DE;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 12px 14px;
            z-index: 9999;
            font-size: 11px;
        ">
            <div style="font-size: 13px; font-weight: 700; color: #EAE5DE; margin-bottom: 2px;">Inflow Intelligence</div>
            <div style="font-size: 11px; color: #B6A38E; margin-bottom: 8px;">
                <b>Target:</b> {target_region_name} · {horizon_hours:g}h window
            </div>
            <div style="margin-bottom: 4px;">
                <span style="display: inline-block; width: 12px; height: 12px; background: #6B1B1E; border: 1px solid #B6A38E; border-radius: 2px; vertical-align: middle; margin-right: 6px;"></span>
                <b>Target Receptor</b> ({target_gid})
            </div>
            <div style="margin-bottom: 4px;">
                <span style="display: inline-block; width: 12px; height: 12px; background: #BC4749; border-radius: 2px; vertical-align: middle; margin-right: 6px;"></span>
                <b>High Inflow Contributor</b> (> {max_frac*0.6*100:.1f}%)
            </div>
            <div style="margin-bottom: 4px;">
                <span style="display: inline-block; width: 12px; height: 12px; background: #D4A373; border-radius: 2px; vertical-align: middle; margin-right: 6px;"></span>
                <b>Moderate Contributor</b>
            </div>
            <div style="margin-bottom: 4px;">
                <span style="display: inline-block; width: 12px; height: 12px; background: #EAE5DE; border-radius: 2px; vertical-align: middle; margin-right: 6px;"></span>
                <b>Minor Inflow Pathway</b> (< {max_frac*0.2*100:.1f}%)
            </div>
            <div style="margin-top: 8px; font-size: 9.5px; color: #A0988E; line-height: 1.25;">
                *Identifies candidate source cells whose physical transport pathways reach this target. Does not represent emission inventories.
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
        folium.LayerControl(collapsed=True).add_to(m)
        return m

    def save_map_html(self, folium_map, out_path):
        """Saves folium map to HTML file."""
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        folium_map.save(out_path)
