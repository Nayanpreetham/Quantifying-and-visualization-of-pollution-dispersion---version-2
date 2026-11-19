"""
India National Pollution Transport & Dispersion Explorer
Environmental Intelligence GIS Dashboard (Phases 20 & 21 Final)

A physics-based 2D Lagrangian grid-to-grid atmospheric pollution transport
platform driven by ECMWF ERA5 horizontal reanalysis winds (U10/V10) across
India's 50 km projected national grid (EPSG:7755).

Dual Operational Workflows:
1. Receptor Analysis (Inflow): Answers "Where is pollution in my selected region coming from?"
   Identifies and ranks all contributing candidate source regions across India reaching the target.
2. Source Analysis (Dispersion): Answers "Where does pollution from my selected region travel?"
   Simulates downwind advective plume dispersion across the national terrestrial grid.
"""

import os
import sys
import json
import datetime
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath("."))

from src.phase20.app_controller import AppController, SUPPORTED_YEAR_MIN, SUPPORTED_YEAR_MAX, SUPPORTED_HORIZONS
from src.phase20.map_visualizer import MapVisualizer

# ---------------------------------------------------------
# Page Configuration & Professional Dark Cartographic Theme
# ---------------------------------------------------------
st.set_page_config(
    page_title="India Pollution Transport & Dispersion Explorer",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Dark Cartographic Theme */
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
    }
    
    /* Sleek Top Navigation Header */
    .app-header {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        border-bottom: 1px solid #1e293b;
        padding-bottom: 12px;
        margin-bottom: 16px;
    }
    
    .main-title {
        font-size: 1.85rem;
        font-weight: 750;
        color: #f8fafc;
        letter-spacing: -0.4px;
        margin: 0;
    }
    
    .main-subtitle {
        font-size: 0.90rem;
        color: #94a3b8;
        margin-top: 3px;
    }
    
    .badge-pill {
        display: inline-block;
        background-color: #1e293b;
        color: #38bdf8;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.74rem;
        font-weight: 600;
        margin-right: 6px;
        border: 1px solid #334155;
    }
    
    /* Modern Environmental Intelligence Cards */
    .intel-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 12px 14px;
        text-align: left;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
        transition: border-color 0.15s ease-in-out;
    }
    .intel-card:hover {
        border-color: #374151;
    }
    
    .intel-label {
        font-size: 0.70rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 4px;
    }
    
    .intel-value {
        font-size: 1.28rem;
        font-weight: 700;
        color: #f8fafc;
        line-height: 1.2;
    }
    
    .intel-sub {
        font-size: 0.74rem;
        color: #64748b;
        margin-top: 3px;
    }
    
    .context-bar {
        background: #111827;
        border-left: 4px solid #38bdf8;
        padding: 10px 14px;
        border-radius: 6px;
        margin-bottom: 14px;
        font-size: 0.86rem;
        color: #cbd5e1;
    }
    
    .highlight-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 12px 16px;
        margin-top: 12px;
        margin-bottom: 14px;
        font-size: 0.88rem;
        color: #e2e8f0;
    }
    
    /* Custom Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: 1px solid #1e293b;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 6px 6px 0 0;
        font-weight: 600;
        font-size: 0.88rem;
        color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        color: #38bdf8 !important;
        border-bottom-color: #38bdf8 !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Cache Resources: Controller, Visualizer, District Hierarchy
# ---------------------------------------------------------
@st.cache_resource(show_spinner="Initializing Environmental Intelligence Engine & GIS Hierarchy...")
def load_application_resources():
    ctrl = AppController()
    vis = MapVisualizer()
    
    # Load District & State Hierarchy
    mapping_path = os.path.join("data", "processed", "geography", "district_to_grid_mapping.json")
    if not os.path.exists(mapping_path):
        mapping_path = os.path.join("data", "raw", "geography", "district_to_grid_mapping.json")
    hierarchy = {}
    if os.path.exists(mapping_path):
        with open(mapping_path, 'r', encoding='utf-8') as f:
            hierarchy = json.load(f)
            
    # Load reverse Grid-to-Districts Mapping
    rev_mapping_path = os.path.join("data", "processed", "geography", "grid_to_districts_mapping.json")
    if not os.path.exists(rev_mapping_path):
        rev_mapping_path = os.path.join("data", "raw", "geography", "grid_to_districts_mapping.json")
    grid_to_names = {}
    if os.path.exists(rev_mapping_path):
        with open(rev_mapping_path, 'r', encoding='utf-8') as f:
            grid_to_names = json.load(f)
            
    return ctrl, vis, hierarchy, grid_to_names

controller, visualizer, district_hierarchy, grid_to_names = load_application_resources()

def get_human_region_name(grid_id):
    names = grid_to_names.get(grid_id)
    if names:
        return names[0]
    return grid_id

# ---------------------------------------------------------
# Top Navigation Header
# ---------------------------------------------------------
st.markdown("""
<div class="app-header">
    <div>
        <h1 class="main-title">🇮🇳 India National Pollution Transport & Dispersion Explorer</h1>
        <div class="main-subtitle">
            Understand where atmospheric pollution comes from, where it travels, and which regions are most influenced.
        </div>
    </div>
</div>
<div style="margin-bottom: 14px;">
    <span class="badge-pill">🌐 50 km Equal-Area Grid (EPSG:7755)</span>
    <span class="badge-pill">🌀 ECMWF ERA5 Horizontal Winds (U10/V10)</span>
    <span class="badge-pill">🔬 2D Lagrangian Trajectory Ensembles</span>
    <span class="badge-pill">📅 Historical Reanalysis (2019–2024)</span>
    <span class="badge-pill">🛡️ Strict Probability Closure (100% Mass Balance)</span>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Sidebar: Analysis Configuration Panel
# ---------------------------------------------------------
st.sidebar.markdown("### ⚙️ Analysis Configuration")

# 1. Analysis Type Selector
workflow_mode = st.sidebar.radio(
    "Analysis Type",
    options=[
        "🎯 Receptor Analysis (Where is pollution coming from?)",
        "💨 Source Analysis (Where does pollution travel to?)"
    ],
    index=0,
    help="Receptor Mode identifies contributing upstream sources reaching a region. Source Mode simulates downwind plume advection from a source region."
)
is_target_mode = "Receptor" in workflow_mode

# 2. Pollutant Selector
st.sidebar.selectbox(
    "Target Pollutant",
    options=["PM2.5 (Continuous CAAQMS Ground Truth & ERA5 Advection)"],
    index=0,
    help="Atmospheric transport model operates on fine particulate matter (PM2.5) supported by historical continuous ground sensors."
)

st.sidebar.markdown("---")
st.sidebar.markdown("**📍 Geographical Selection**")

# Quick City Presets
PRESET_CITIES = {
    "Select from major regional hubs or choose State/District below...": None,
    "Varanasi, Uttar Pradesh": (25.3606, 82.8253, "Uttar Pradesh", "Varanasi"),
    "Delhi (NCR Core)": (28.6139, 77.2090, "Delhi", "Delhi"),
    "Bhopal, Madhya Pradesh": (23.2599, 77.4126, "Madhya Pradesh", "Bhopal"),
    "Chennai, Tamil Nadu": (13.0827, 80.2707, "Tamil Nadu", "Chennai"),
    "Mumbai, Maharashtra": (19.0760, 72.8777, "Maharashtra", "Mumbai City"),
    "Kolkata, West Bengal": (22.5726, 88.3639, "West Bengal", "Kolkata"),
    "Bengaluru, Karnataka": (12.9716, 77.5946, "Karnataka", "Bangalore"),
    "Ahmedabad, Gujarat": (23.0225, 72.5714, "Gujarat", "Ahmadabad"),
    "Kanpur, Uttar Pradesh": (26.4499, 80.3319, "Uttar Pradesh", "Kanpur Nagar"),
    "Lucknow, Uttar Pradesh": (26.8467, 80.9462, "Uttar Pradesh", "Lucknow"),
    "Hyderabad, Telangana": (17.3850, 78.4867, "Andhra Pradesh", "Hyderabad"),
    "Agartala, Tripura": (23.8315, 91.2868, "Tripura", "West Tripura"),
    "Itanagar, Arunachal Pradesh": (27.0844, 93.6053, "Arunachal Pradesh", "Papum Pare"),
    "Srinagar, Jammu & Kashmir": (34.0837, 74.7973, "Jammu and Kashmir", "Srinagar"),
    "Thiruvananthapuram, Kerala": (8.5241, 76.9366, "Kerala", "Thiruvananthapuram")
}

selected_preset = st.sidebar.selectbox("Quick Regional Presets", list(PRESET_CITIES.keys()))

# State and District Dropdown Selection
all_states = sorted(list(district_hierarchy.keys())) if district_hierarchy else ["Delhi", "Uttar Pradesh", "Maharashtra"]

# Default State and District
default_state = "Delhi"
default_district = "Delhi"

if selected_preset and PRESET_CITIES[selected_preset] is not None:
    _, _, p_state, p_dist = PRESET_CITIES[selected_preset]
    if p_state in all_states:
        default_state = p_state
        default_district = p_dist

state_idx = all_states.index(default_state) if default_state in all_states else 0
chosen_state = st.sidebar.selectbox("Select State / UT", all_states, index=state_idx)

available_districts = sorted(list(district_hierarchy.get(chosen_state, {}).keys()))
if not available_districts:
    available_districts = ["Central"]

dist_idx = available_districts.index(default_district) if default_district in available_districts else 0
chosen_district = st.sidebar.selectbox("Select District / Administrative Zone", available_districts, index=dist_idx)

# Determine Coordinates from District Centroid
district_info = district_hierarchy.get(chosen_state, {}).get(chosen_district, {})
auto_lat = district_info.get('centroid_lat', 28.6139)
auto_lon = district_info.get('centroid_lon', 77.2090)
mapped_grid_id = district_info.get('grid_id_50km', 'IND_50KM_r046_c018')

# Advanced Coordinate Override
with st.sidebar.expander("⚙️ Advanced Settings (Custom Coordinates & Grid Override)", expanded=False):
    st.caption("Override default district centroid with specific GPS coordinates or raw 50 km grid ID:")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        custom_lat = st.number_input("Latitude (°N)", min_value=0.0, max_value=45.0, value=float(auto_lat), format="%.4f")
    with col_c2:
        custom_lon = st.number_input("Longitude (°E)", min_value=60.0, max_value=105.0, value=float(auto_lon), format="%.4f")
    
    use_custom_coords = (abs(custom_lat - auto_lat) > 0.001) or (abs(custom_lon - auto_lon) > 0.001)
    if use_custom_coords:
        final_lat = custom_lat
        final_lon = custom_lon
        location_display_name = f"Custom Location ({final_lat:.2f}°N, {final_lon:.2f}°E)"
    else:
        final_lat = auto_lat
        final_lon = auto_lon
        location_display_name = f"{chosen_district}, {chosen_state}"

st.sidebar.markdown("---")
st.sidebar.markdown("**📅 Analysis Time Period & Transport Horizon**")

input_date = st.sidebar.date_input(
    "Historical Date (2019–2024)",
    value=datetime.date(2021, 10, 15),
    min_value=datetime.date(SUPPORTED_YEAR_MIN, 1, 1),
    max_value=datetime.date(SUPPORTED_YEAR_MAX, 12, 31),
    help="Select any date within the validated 6-year ERA5 reanalysis period."
)

horizon_choice = st.sidebar.select_slider(
    "Transport Horizon",
    options=[1.0, 3.0, 6.0, 12.0, 24.0],
    value=24.0,
    format_func=lambda x: f"{int(x)} Hours" if x >= 1.0 else f"{x}h",
    help="Lagrangian atmospheric transport duration."
)

if is_target_mode:
    ranking_metric_label = st.sidebar.selectbox(
        "Rank Contributing Sources By",
        options=[
            "Physical Transport Fraction (T_ij)",
            "Source-Weighted Influence Index (I_ij = C_i * T_ij)"
        ],
        index=0,
        help="Transport fraction quantifies advection probability. Influence index weights transport by source ground PM2.5."
    )
    metric_key = "source_weighted_transport_influence_index" if "Source-Weighted" in ranking_metric_label else "transport_fraction"
else:
    metric_key = "transport_fraction"

min_frac_pct = st.sidebar.slider("Min. Display Filter Threshold (%)", 0.0, 5.0, 0.0, step=0.25, help="Filter out negligible peripheral transport fractions.")
min_frac_val = min_frac_pct / 100.0

btn_text = "🎯 Run Receptor Inflow Analysis" if is_target_mode else "💨 Run Source Dispersion Analysis"
run_clicked = st.sidebar.button(btn_text, type="primary", use_container_width=True)

# ---------------------------------------------------------
# Query Execution & State Management
# ---------------------------------------------------------
query_cache_key = (is_target_mode, input_date, final_lat, final_lon, horizon_choice, metric_key)

if run_clicked or 'last_execution_key' not in st.session_state or st.session_state['last_execution_key'] != query_cache_key:
    spinner_msg = (
        f"Evaluating atmospheric transport corridors reaching {location_display_name} on {input_date} ({horizon_choice:g}h)..."
        if is_target_mode else
        f"Simulating atmospheric dispersion from {location_display_name} on {input_date} ({horizon_choice:g}h)..."
    )
    with st.spinner(spinner_msg):
        if is_target_mode:
            query_result = controller.execute_target_query(
                year=input_date.year,
                month=input_date.month,
                day=input_date.day,
                lat=final_lat,
                lon=final_lon,
                horizon_hours=horizon_choice,
                ranking_metric=metric_key,
                use_cache=True
            )
        else:
            query_result = controller.execute_query(
                year=input_date.year,
                month=input_date.month,
                day=input_date.day,
                lat=final_lat,
                lon=final_lon,
                horizon_hours=horizon_choice,
                use_cache=True
            )
        st.session_state['last_query_result'] = query_result
        st.session_state['last_execution_key'] = query_cache_key
        st.session_state['last_location_name'] = location_display_name
else:
    query_result = st.session_state['last_query_result']
    location_display_name = st.session_state.get('last_location_name', location_display_name)

# ---------------------------------------------------------
# Handle Boundary Limits and Errors
# ---------------------------------------------------------
if query_result['status'] != 'SUCCESS':
    if query_result['status'] in ('UNSUPPORTED_MET_COVERAGE', 'ERROR_UNSUPPORTED_MET_COVERAGE'):
        st.warning(f"⚠️ **Meteorological Coverage Boundary Limit:** {query_result.get('message')}")
        st.info("The ERA5 reanalysis domain for this project is bounded by [6.0°N–35.0°N, 68.0°E–97.0°E]. High-altitude peripheral coordinates beyond this box cannot be simulated without unscientific extrapolation.")
    elif query_result['status'] == 'VALIDATION_ERROR':
        st.error(f"❌ **Input Validation Error:** {query_result.get('message')}")
    else:
        st.error(f"❌ **Simulation Error ({query_result['status']}):** {query_result.get('message')}")
    st.stop()

# ---------------------------------------------------------
# Summary Insight Cards (Answering Real Environmental Questions)
# ---------------------------------------------------------
df_table = query_result['results_table']
exec_time = query_result['execution_time_seconds']

if is_target_mode:
    tgt_info = query_result['target_info']
    tgt_mon = query_result['target_monitoring_info']
    
    st.markdown(f"""
    <div class="context-bar">
        <b>🎯 Receptor Inflow Analysis:</b> Identifying all geographical regions contributing atmospheric transport 
        into <b>{location_display_name}</b> (Grid Cell: <code>{tgt_info['target_grid_id']}</code>) on <b>{input_date}</b> over a <b>{horizon_choice:g}-hour</b> window.
    </div>
    """, unsafe_allow_html=True)
    
    # Meaningful Card 1: Selected Region
    # Meaningful Card 2: Local Observed PM2.5 (Ground Truth)
    # Meaningful Card 3: Contributing Source Regions (Count)
    # Meaningful Card 4: Monitored Contributing Sources
    # Meaningful Card 5: Dominant Contributing Source
    # Meaningful Card 6: Transport Window
    
    local_pm_str = f"{tgt_mon['effective_source_pm25_ugm3']:.1f} µg/m³" if not np.isnan(tgt_mon['effective_source_pm25_ugm3']) else "Unmonitored"
    local_pm_sub = f"{tgt_mon['stations_count']} CAAQMS Station(s)" if tgt_mon['stations_count'] > 0 else "No Ground Monitor"
    
    if not df_table.empty:
        top_contrib = df_table.iloc[0]
        top_src_name = get_human_region_name(top_contrib['source_grid_id'])
        top_src_frac = top_contrib['daily_transport_fraction'] * 100
        top_src_dist = top_contrib['distance_km']
        dominant_str = f"{top_src_name}"
        dominant_sub = f"{top_src_frac:.1f}% Inflow ({top_src_dist:.0f} km away)"
    else:
        dominant_str = "None Identified"
        dominant_sub = "Within threshold"
        
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f"""
        <div class="intel-card">
            <div class="intel-label">Selected Receptor</div>
            <div class="intel-value" style="font-size: 1.05rem;">{location_display_name}</div>
            <div class="intel-sub">Cell: {tgt_info['target_grid_id']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="intel-card">
            <div class="intel-label">Local Observed PM2.5</div>
            <div class="intel-value" style="color: #38bdf8;">{local_pm_str}</div>
            <div class="intel-sub">{local_pm_sub}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="intel-card">
            <div class="intel-label">Contributing Regions</div>
            <div class="intel-value">{query_result['sources_with_positive_transport']}</div>
            <div class="intel-sub">Out of 1,380 National Cells</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="intel-card">
            <div class="intel-label">Monitored Contributors</div>
            <div class="intel-value" style="color: #34d399;">{query_result['monitored_sources_count']}</div>
            <div class="intel-sub">With Ground Stations</div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="intel-card">
            <div class="intel-label">Primary Contributor</div>
            <div class="intel-value" style="font-size: 1.0rem; color: #f59e0b;">{dominant_str}</div>
            <div class="intel-sub">{dominant_sub}</div>
        </div>
        """, unsafe_allow_html=True)
    with c6:
        st.markdown(f"""
        <div class="intel-card">
            <div class="intel-label">Transport Window</div>
            <div class="intel-value">{int(horizon_choice)} Hours</div>
            <div class="intel-sub">{input_date.strftime('%d %b %Y')}</div>
        </div>
        """, unsafe_allow_html=True)

else:
    src_info = query_result['source_info']
    mon_info = query_result['monitoring_info']
    cat_counts = query_result['category_counts']
    c_land = cat_counts.get("VALID_LAND_DESTINATION", 0)
    
    st.markdown(f"""
    <div class="context-bar">
        <b>💨 Source Dispersion Analysis:</b> Simulating downwind atmospheric advection dispersing from 
        <b>{location_display_name}</b> (Grid Cell: <code>{src_info['grid_id_50km']}</code>) on <b>{input_date}</b> over a <b>{horizon_choice:g}-hour</b> window.
    </div>
    """, unsafe_allow_html=True)
    
    source_pm_str = f"{mon_info['effective_source_pm25_ugm3']:.1f} µg/m³" if not np.isnan(mon_info['effective_source_pm25_ugm3']) else "Unmonitored"
    source_pm_sub = f"{mon_info['stations_count']} Local Station(s)" if mon_info['stations_count'] > 0 else "No Ground Monitor"
    
    land_dests = df_table[df_table['category'] == 'VALID_LAND_DESTINATION']
    max_reach_km = land_dests['distance_km'].max() if not land_dests.empty else 0.0
    
    if not land_dests.empty:
        top_dest = land_dests.iloc[0]
        top_dest_name = get_human_region_name(str(top_dest['destination']))
        top_dest_frac = top_dest['daily_transport_fraction'] * 100
        corridor_str = f"{top_dest_name}"
        corridor_sub = f"{top_dest_frac:.1f}% Plume Fraction"
    else:
        corridor_str = "Local Retention"
        corridor_sub = "100% within source"
        
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f"""
        <div class="intel-card">
            <div class="intel-label">Selected Source</div>
            <div class="intel-value" style="font-size: 1.05rem;">{location_display_name}</div>
            <div class="intel-sub">Cell: {src_info['grid_id_50km']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="intel-card">
            <div class="intel-label">Source Observed PM2.5</div>
            <div class="intel-value" style="color: #38bdf8;">{source_pm_str}</div>
            <div class="intel-sub">{source_pm_sub}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="intel-card">
            <div class="intel-label">Affected Regions</div>
            <div class="intel-value">{c_land}</div>
            <div class="intel-sub">Terrestrial Cells Reached</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="intel-card">
            <div class="intel-label">Max Transport Reach</div>
            <div class="intel-value" style="color: #34d399;">{max_reach_km:.0f} km</div>
            <div class="intel-sub">Furthest Downwind Land Cell</div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="intel-card">
            <div class="intel-label">Primary Corridor</div>
            <div class="intel-value" style="font-size: 1.0rem; color: #f59e0b;">{corridor_str}</div>
            <div class="intel-sub">{corridor_sub}</div>
        </div>
        """, unsafe_allow_html=True)
    with c6:
        st.markdown(f"""
        <div class="intel-card">
            <div class="intel-label">Transport Window</div>
            <div class="intel-value">{int(horizon_choice)} Hours</div>
            <div class="intel-sub">{input_date.strftime('%d %b %Y')}</div>
        </div>
        """, unsafe_allow_html=True)

st.write("")

# ---------------------------------------------------------
# Main Tabs: Map-First Experience
# ---------------------------------------------------------
tab_map, tab_table, tab_stations, tab_methodology = st.tabs([
    "🗺️ Geographic Explorer",
    "📊 Regional Findings & Matrix",
    "📡 Ground Monitoring & Local Truth",
    "🔬 Model Architecture & Physics"
])

# ---------------------------------------------------------
# Tab 1: Geographic Explorer (The Central Heart of Application)
# ---------------------------------------------------------
with tab_map:
    col_map_opts1, col_map_opts2, col_map_opts3 = st.columns([2, 1, 1])
    with col_map_opts1:
        if is_target_mode:
            st.markdown(f"##### 🎯 Inflow Transport Footprint reaching {location_display_name}")
            st.caption("Interactive Leaflet map showing candidate source regions and atmospheric transport pathways converging on the target receptor.")
        else:
            st.markdown(f"##### 💨 Downwind Dispersion Plume from {location_display_name}")
            st.caption("Interactive Leaflet map showing downwind trajectory dispersion across Indian states and 50 km model grid cells.")
    with col_map_opts2:
        show_pathway_lines = st.checkbox("Show Transport Corridors (Pathways)", value=True)
    with col_map_opts3:
        show_grid_overlay = st.checkbox("Overlay 50 km Model Grid", value=False)
        
    # Generate Map
    if is_target_mode:
        folium_map = visualizer.create_target_influence_map(
            query_result,
            user_lat=final_lat,
            user_lon=final_lon,
            min_fraction=min_frac_val,
            show_pathways=show_pathway_lines,
            show_grid=show_grid_overlay
        )
    else:
        folium_map = visualizer.create_dispersion_map(
            query_result,
            user_lat=final_lat,
            user_lon=final_lon,
            min_fraction=min_frac_val,
            show_pathways=show_pathway_lines,
            show_grid=show_grid_overlay
        )
        
    components.html(folium_map._repr_html_(), height=620, scrolling=False)
    
    # Map Findings Highlight
    if is_target_mode and not df_table.empty:
        st.markdown(f"""
        <div class="highlight-card">
            <b>💡 Key Inflow Finding:</b> 
            Atmospheric transport reaching <b>{location_display_name}</b> on {input_date} is predominantly influenced by 
            <b>{top_src_name}</b> located <b>{top_src_dist:.1f} km</b> away ({top_src_frac:.2f}% modeled inflow transport fraction).
            A total of <b>{len(df_table)} geographical cells</b> have physical transport pathways connecting into this receptor.
        </div>
        """, unsafe_allow_html=True)
    elif not is_target_mode:
        st.markdown(f"""
        <div class="highlight-card">
            <b>💡 Key Dispersion Finding:</b> 
            Air masses leaving <b>{location_display_name}</b> on {input_date} disperse across 
            <b>{c_land} terrestrial land cells</b>, with a maximum travel reach of <b>{max_reach_km:.1f} km</b> over {horizon_choice:g} hours.
            Primary recipient region is <b>{corridor_str}</b>. Total mathematical probability closure: <b>{query_result['probability_closure_sum']:.6f} (100% mass accounting)</b>.
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------
# Tab 2: Regional Findings & Matrix
# ---------------------------------------------------------
with tab_table:
    if is_target_mode:
        st.markdown("#### 📊 Candidate Source Inflow Ranking & Attribution Matrix")
        st.caption("Quantitative ranking of all upstream source regions whose physical transport pathways connect into the selected receptor.")
        
        filtered_df = df_table[df_table['daily_transport_fraction'] >= min_frac_val].copy()
        
        # Add human-friendly region names
        filtered_df['region_name'] = filtered_df['source_grid_id'].apply(get_human_region_name)
        
        # Add transport fraction column formatted
        display_df = filtered_df.copy()
        display_df['transport_fraction_fmt'] = display_df['daily_transport_fraction'].apply(lambda x: f"{x*100:.2f}%")
        display_df['distance_km_fmt'] = display_df['distance_km'].apply(lambda x: f"{x:.1f} km" if not pd.isna(x) else "—")
        display_df['source_pm25_fmt'] = display_df['source_pm25_ugm3'].apply(
            lambda x: f"{x:.1f} µg/m³" if not pd.isna(x) else "Unmonitored"
        )
        display_df['influence_fmt'] = display_df['source_weighted_transport_influence_index'].apply(
            lambda x: f"{x:.2f} µg/m³-eq" if not pd.isna(x) else "Unmonitored (NaN)"
        )
        
        st.dataframe(
            display_df[[
                'rank', 'region_name', 'source_grid_id', 'distance_km_fmt',
                'transport_fraction_fmt', 'source_pm25_fmt', 'influence_fmt', 'source_observation_status'
            ]].rename(columns={
                'rank': 'Rank',
                'region_name': 'Source Region / District',
                'source_grid_id': 'Grid Cell ID',
                'distance_km_fmt': 'Distance to Receptor',
                'transport_fraction_fmt': 'Inflow Transport %',
                'source_pm25_fmt': 'Source Observed PM2.5',
                'influence_fmt': 'Attributed Influence (I_ij = C_i * T_ij)',
                'source_observation_status': 'Monitoring Status'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # Scatter / Decay Plot
        st.markdown("##### 📈 Transport Inflow vs. Distance to Receptor")
        plot_data = filtered_df[['distance_km', 'daily_transport_fraction']].dropna()
        if not plot_data.empty:
            plot_data['transport_fraction_pct'] = plot_data['daily_transport_fraction'] * 100
            st.scatter_chart(
                plot_data,
                x='distance_km',
                y='transport_fraction_pct',
                color='#38bdf8',
                size='transport_fraction_pct'
            )
            
        csv_bytes = df_table.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Quantitative Inflow Matrix (CSV)",
            data=csv_bytes,
            file_name=f"inflow_matrix_{tgt_info['target_grid_id']}_{input_date}_{int(horizon_choice)}h.csv",
            mime="text/csv"
        )
        
    else:
        st.markdown("#### 📊 Downwind Destination Transport Matrix")
        st.caption("Quantitative accounting of destination cells receiving advected air masses from the source region.")
        
        filtered_df = df_table[df_table['daily_transport_fraction'] >= min_frac_val].copy()
        filtered_df['region_name'] = filtered_df['destination'].apply(lambda d: get_human_region_name(str(d)) if str(d).startswith("IND_50KM") else str(d))
        
        display_df = filtered_df.copy()
        display_df['transport_fraction_fmt'] = display_df['daily_transport_fraction'].apply(lambda x: f"{x*100:.2f}%")
        display_df['distance_km_fmt'] = display_df['distance_km'].apply(lambda x: f"{x:.1f} km" if not pd.isna(x) else "—")
        display_df['influence_fmt'] = display_df['source_weighted_transport_influence_index'].apply(
            lambda x: f"{x:.2f} µg/m³-eq" if not pd.isna(x) else "Unmonitored (NaN)"
        )
        
        st.dataframe(
            display_df[[
                'rank', 'region_name', 'destination', 'category',
                'transport_fraction_fmt', 'distance_km_fmt', 'influence_fmt'
            ]].rename(columns={
                'rank': 'Rank',
                'region_name': 'Destination Region',
                'destination': 'Destination Code / Boundary',
                'category': 'Fate Category',
                'transport_fraction_fmt': 'Transport Fraction (T_ij)',
                'distance_km_fmt': 'Distance from Source',
                'influence_fmt': 'Dispersed Influence (I_ij)'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # Dispersion Decay Plot
        st.markdown("##### 📈 Dispersion Transport vs. Distance from Source")
        land_plot = filtered_df[filtered_df['category'] == 'VALID_LAND_DESTINATION'][['distance_km', 'daily_transport_fraction']].dropna()
        if not land_plot.empty:
            land_plot['transport_fraction_pct'] = land_plot['daily_transport_fraction'] * 100
            st.scatter_chart(
                land_plot,
                x='distance_km',
                y='transport_fraction_pct',
                color='#f59e0b',
                size='transport_fraction_pct'
            )
            
        csv_bytes = df_table.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Quantitative Dispersion Matrix (CSV)",
            data=csv_bytes,
            file_name=f"dispersion_matrix_{src_info['grid_id_50km']}_{input_date}_{int(horizon_choice)}h.csv",
            mime="text/csv"
        )

# ---------------------------------------------------------
# Tab 3: Ground Monitoring & Local Truth
# ---------------------------------------------------------
with tab_stations:
    st.markdown("#### 🏢 Regulatory Air Quality Monitoring Ground Truth")
    st.caption("Real-world ground observations from Continuous Ambient Air Quality Monitoring Stations (CAAQMS) operated by CPCB and State Pollution Control Boards.")
    
    local_gid = tgt_info['target_grid_id'] if is_target_mode else src_info['grid_id_50km']
    local_mon = tgt_mon if is_target_mode else mon_info
    loc_role = "Target Receptor" if is_target_mode else "Source Emitter"
    
    col_st1, col_st2 = st.columns([1, 2])
    with col_st1:
        st.markdown(f"##### Local Status: `{local_gid}`")
        st.write(f"- **Monitoring Category:** `{local_mon['monitoring_status']}`")
        st.write(f"- **Active CAAQMS Stations:** `{local_mon['stations_count']}`")
        pm_val = f"{local_mon['effective_source_pm25_ugm3']:.1f} µg/m³" if not np.isnan(local_mon['effective_source_pm25_ugm3']) else "No Station Data"
        st.write(f"- **Observed PM2.5 Level:** `{pm_val}`")
    with col_st2:
        if local_mon['station_names']:
            st.markdown("**Installed Monitoring Stations in this Cell:**")
            for stn in local_mon['station_names']:
                st.markdown(f"- 🏢 `{stn}`")
        else:
            st.info("ℹ️ **Unmonitored Cell:** This 50 km cell has no installed continuous regulatory air-quality monitors. Under our scientific protocol, physical transport fractions ($T_{ij}$) are computed, but concentration influence indices ($I_{ij}$) remain strictly `NaN` rather than inventing synthetic data.")

    st.markdown("---")
    
    if is_target_mode:
        st.markdown("##### Monitored Contributing Sources Reaching this Receptor")
        df_mon_sources = df_table[df_table['source_observation_status'] != 'UNMONITORED_SOURCE'].copy()
        
        if not df_mon_sources.empty:
            df_mon_sources['region_name'] = df_mon_sources['source_grid_id'].apply(get_human_region_name)
            df_mon_disp = df_mon_sources[[
                'rank', 'region_name', 'source_grid_id', 'distance_km',
                'daily_transport_fraction', 'source_pm25_ugm3', 'source_weighted_transport_influence_index'
            ]].copy()
            
            df_mon_disp['daily_transport_fraction'] = df_mon_disp['daily_transport_fraction'].apply(lambda x: f"{x*100:.2f}%")
            df_mon_disp['distance_km'] = df_mon_disp['distance_km'].apply(lambda x: f"{x:.1f} km")
            df_mon_disp['source_pm25_ugm3'] = df_mon_disp['source_pm25_ugm3'].apply(lambda x: f"{x:.1f} µg/m³")
            df_mon_disp['source_weighted_transport_influence_index'] = df_mon_disp['source_weighted_transport_influence_index'].apply(lambda x: f"{x:.2f} µg/m³-eq")
            
            st.dataframe(
                df_mon_disp.rename(columns={
                    'rank': 'Rank',
                    'region_name': 'Contributing Region',
                    'source_grid_id': 'Grid Cell ID',
                    'distance_km': 'Distance',
                    'daily_transport_fraction': 'Inflow Transport %',
                    'source_pm25_ugm3': 'Source Observed PM2.5 (C_i)',
                    'source_weighted_transport_influence_index': 'Influence Index (I_ij = C_i * T_ij)'
                }),
                use_container_width=True,
                hide_index=True
            )
            st.caption("ℹ️ **Scientific Integrity Note:** The influence index $I_{ij} = C_i \\times T_{ij}$ represents source pollution mass arriving at the target in $\\mu\\text{g/m}^3$-equivalent. It is an attribution metric, not the target's measured ambient air quality.")
        else:
            st.info(f"All candidate source cells reaching this receptor are located in unmonitored rural/regional cells. While physical transport pathways are verified, influence indices remain `NaN` due to absence of ground sensors in those source zones.")

    st.markdown("---")
    st.markdown("##### National CAAQMS Ground Truth Coverage Overview")
    st.markdown("""
    - **Total Indian Landmass:** **1,380 grid cells** ($50\\text{ km} \\times 50\\text{ km}$ regular equal-area cells).
    - **Monitored Cells:** **51 cells (3.70%)** contain active regulatory CAAQMS monitors (103 total stations in metropolitan centers).
    - **Unmonitored Cells:** **1,329 cells (96.30%)** have zero ground sensors.
    - **Data Integrity Protocol:** The model quantifies physical atmospheric advection ($T_{ij}$) across the entire country, but strictly reports `NaN` for influence where empirical ground concentrations are absent.
    """)

# ---------------------------------------------------------
# Tab 4: Model Architecture & Physics
# ---------------------------------------------------------
with tab_methodology:
    st.markdown("#### 🔬 Atmospheric Physics & Mathematical Methodology")
    st.caption("Comprehensive physical, mathematical, and computational specifications of the India National Dispersion Framework.")
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("##### 1. Coordinate System & Spatial Grid")
        st.markdown("""
        - **Projection:** Lambert Conformal Conic (`EPSG:7755`, India Unified Coordinate System).
        - **Equal-Area Regular Geometry:** Square $50\\text{ km} \\times 50\\text{ km}$ cells ($2,500\\text{ km}^2$ nominal area).
        - **Terrestrial Scope:** 1,380 sovereign land cells bounded by Survey of India polygons.
        - **Advantage over 0.25° Lat-Lon:** Eliminates 15% meridional area distortion from south to north India.
        """)
        
        st.markdown("##### 2. Meteorological Forcing & Interpolation")
        st.markdown("""
        - **Dataset:** ECMWF ERA5 Atmospheric Reanalysis (2019–2024, 6 full years).
        - **Variables:** Surface horizontal wind components $U_{10}$ (eastward) and $V_{10}$ (northward).
        - **Synoptic Sampling:** 6-hourly time slices ($00:00, 06:00, 12:00, 18:00\\text{ UTC}$).
        - **Interpolation:** Continuous 2D bivariate spline spatial interpolation and linear temporal interpolation between synoptic slices.
        """)
        
    with col_m2:
        st.markdown("##### 3. Lagrangian Trajectory & Ensemble Engine")
        st.markdown(r"""
        - **Numerical Advection:** Euler–Cauchy kinematic time-stepping ($\Delta t = 1.0\text{ hour}$, CFL stability $C \le 1.8$).
        - **Ensemble Configuration:** 10 particles per synoptic release (1 central deterministic + 9 perturbed members).
        - **Turbulent Spread:** $\Delta V \sim \mathcal{N}(0, 0.4\text{ m/s})$, $\Delta \theta \sim \mathcal{N}(0, 12.0^\circ)$.
        - **Daily Integration:** 4 releases $\times$ 10 members = **40 simulated trajectories per source per day**.
        - **Advection Horizons:** 1h, 3h, 6h, 12h, and 24h.
        """)
        
        st.markdown("##### 4. Four-Tier Boundary Fate Accounting")
        st.markdown("""
        All trajectories are classified into four mutually exclusive categories:
        1. `VALID_LAND_DESTINATION`: Terrestrial 50 km cell.
        2. `INTERNAL_UNMODELED_WATER`: Coastal marine water cell.
        3. `DOMAIN_EXIT_EXTERNAL`: International land or open ocean exit.
        4. `UNSUPPORTED_MET_COVERAGE`: Beyond ERA5 bounds ($>35^\\circ\\text{N}$ / $>97^\\circ\\text{E}$).
        $$\\sum T_{ij} = 1.000000 \\quad \\text{(Strict Numerical Closure)}$$
        """)

    st.markdown("---")
    st.markdown("##### 5. Documented Scientific Assumptions & Physical Boundaries")
    st.markdown("""
    1. **Two-Dimensional Surface Transport:** Advection is driven by 10-meter horizontal winds. Upper-level boundary layer shear and convective vertical mixing are excluded due to lack of 3D national reanalysis forcing.
    2. **Passive Conservative Tracer:** Particulate matter is treated as chemically inert without wet scavenging by precipitation or dry gravitational settling.
    3. **Diagnostic Analysis Only:** All simulations are retrospective evaluations against verified historical ERA5 fields (2019–2024). The tool does **not** forecast future air quality or predict prognostic weather.
    4. **Physical Pathways vs. Emissions Inventories:** The model quantifies atmospheric transport connection probabilities between geographic cells; it does **not** attribute pollution to specific industrial or vehicular facilities.
    """)
