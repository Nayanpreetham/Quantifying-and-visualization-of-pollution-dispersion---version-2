"""
National Pollution Dispersion Query Application
Phase 20 - Interactive User-Facing Web Application
Phase 21 - Target-Centric Pollution Influence Verification & National Query System

A physically rigorous 2D Lagrangian grid-to-grid historical pollution transport
analysis tool driven by ECMWF ERA5 horizontal reanalysis winds (U10/V10) across
India's 50 km projected national grid (EPSG:7755).

Supports Dual Operational Modes:
1. Target Influence Mode (Reverse Query): Given any receptor location in India,
   identifies all eligible candidate source cells whose forward modeled dispersion
   pathways reach the target, ranked by physical transport fraction or source-weighted influence.
2. Source Dispersion Mode (Forward Query): Given any emission source location,
   computes downwind 2D dispersion across the national grid.

Mandatory Scientific Constraints:
- Historical dispersion analysis ONLY (2019-2024).
- Strictly NOT an AQI prediction or forecasting tool (is_ambient_aqi_prediction = False).
- Candidate sources are transport pathway contributors, NOT verified emission inventories.
- Ground observations (CPCB/OpenAQ) are explicitly disaggregated from modeled transport.
- Probability closure and 4-tier boundary separation rigorously enforced.
"""

import os
import sys
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
# Page Configuration & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="India National Pollution Dispersion Model",
    page_icon="🌬️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e3d59;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 1rem;
    }
    .disclaimer-card {
        background-color: #fff8e7;
        border-left: 5px solid #ffb03b;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 1.5rem;
        font-size: 0.9rem;
        color: #6a4900;
    }
    .target-mode-banner {
        background-color: #ebf5fb;
        border-left: 5px solid #2980b9;
        padding: 10px 14px;
        border-radius: 4px;
        margin-bottom: 1rem;
        font-size: 0.88rem;
        color: #1b4f72;
    }
    .metric-container {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 6px;
        padding: 10px 14px;
        text-align: center;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.25rem;
        font-weight: 600;
        color: #212529;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Cache Resource: Controller & Visualizer
# ---------------------------------------------------------
@st.cache_resource(show_spinner="Initializing Dispersion Engine and 50 km National Grid...")
def load_application_resources():
    ctrl = AppController()
    vis = MapVisualizer()
    return ctrl, vis

controller, visualizer = load_application_resources()

# ---------------------------------------------------------
# Header & Scientific Notice
# ---------------------------------------------------------
st.markdown('<div class="main-header">🌬️ India National 2D Pollution Dispersion Model</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Lagrangian Dynamic Trajectory Grid-to-Grid Transport Analysis | 50 km Resolution</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="disclaimer-card">
    <b>Scientific Integrity Notice:</b> This physical transport analysis system is driven by 
    ECMWF ERA5 horizontal winds (U10/V10) across India's 50 km projected grid. It quantifies the <i>physical probability</i> of pollutant transport 
    between source and destination cells. It does <b>NOT</b> forecast ambient AQI, simulate 
    chemical transformation, or estimate emission source inventories. Ground observations are independent 
    empirical benchmarks displayed for regional context.
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Sidebar: Query Mode & Simulation Parameters
# ---------------------------------------------------------
st.sidebar.header("🕹️ Query Configuration")

query_mode = st.sidebar.radio(
    "Operational Mode",
    options=[
        "🎯 Target Influence Mode (Identify incoming sources for a target)",
        "🚀 Source Dispersion Mode (Simulate forward downwind dispersion from a source)"
    ],
    index=0
)
is_target_mode = "Target Influence" in query_mode

# Presets covering all national regions
PRESETS = {
    "Select a preset location or enter custom coords...": None,
    "🏛️ Delhi (NCR Core) [28.614°N, 77.209°E]": (28.6139, 77.2090),
    "🏛️ Madhya Pradesh (Bhopal) [23.260°N, 77.413°E]": (23.2599, 77.4126),
    "🌊 Tamil Nadu (Chennai) [13.083°N, 80.271°E]": (13.0827, 80.2707),
    "🌴 Kerala (Thiruvananthapuram) [8.524°N, 76.937°E]": (8.5241, 76.9366),
    "🏭 Gujarat (Ahmedabad) [23.023°N, 72.571°E]": (23.0225, 72.5714),
    "🌿 Tripura (Agartala) [23.832°N, 91.287°E]": (23.8315, 91.2868),
    "⛰️ Arunachal Pradesh (Itanagar) [27.084°N, 93.605°E]": (27.0844, 93.6053),
    "❄️ Jammu & Kashmir (Srinagar) [34.084°N, 74.797°E]": (34.0837, 74.7973),
    "🏔️ Northern Ladakh (>35°N - Met Limit Boundary)": (35.6000, 76.8000),
    "🏭 Kanpur (Indo-Gangetic Plain) [26.450°N, 80.332°E]": (26.4499, 80.3319),
    "🌊 Mumbai (West Coast) [19.076°N, 72.878°E]": (19.0760, 72.8777),
    "🌿 Kolkata (East Delta) [22.573°N, 88.364°E]": (22.5726, 88.3639),
    "💻 Bengaluru (Deccan Plateau) [12.972°N, 77.595°E]": (12.9716, 77.5946),
    "🌾 Unmonitored Rural Cell (Central India)": (20.5000, 78.5000)
}

selected_preset = st.sidebar.selectbox("Quick Preset Locations", list(PRESETS.keys()))

# Manage session state coordinates cleanly to prevent accidental resets
if 'user_coords' not in st.session_state:
    st.session_state['user_coords'] = (28.6139, 77.2090)
    st.session_state['selected_preset_prev'] = selected_preset

# If preset selection changed, update coordinates
if selected_preset != st.session_state.get('selected_preset_prev'):
    st.session_state['selected_preset_prev'] = selected_preset
    if selected_preset and PRESETS[selected_preset] is not None:
        st.session_state['user_coords'] = PRESETS[selected_preset]

curr_lat, curr_lon = st.session_state['user_coords']

loc_label = "Target Receptor Coordinates" if is_target_mode else "Source Emitter Coordinates"
st.sidebar.subheader(f"📍 {loc_label}")
col_lat, col_lon = st.sidebar.columns(2)
with col_lat:
    input_lat = st.number_input("Latitude (°N)", min_value=0.0, max_value=45.0, value=curr_lat, step=0.01, format="%.4f")
with col_lon:
    input_lon = st.number_input("Longitude (°E)", min_value=60.0, max_value=105.0, value=curr_lon, step=0.01, format="%.4f")

st.session_state['user_coords'] = (input_lat, input_lon)

# Date Selector
st.sidebar.subheader("📅 Historical Date")
default_date = datetime.date(2021, 10, 15) # Default: National pilot post-monsoon benchmark
input_date = st.sidebar.date_input(
    "Query Date (2019-2024)",
    value=default_date,
    min_value=datetime.date(SUPPORTED_YEAR_MIN, 1, 1),
    max_value=datetime.date(SUPPORTED_YEAR_MAX, 12, 31)
)

# Transport Horizon Selector
st.sidebar.subheader("⏱️ Transport Horizon")
horizon_choice = st.sidebar.select_slider(
    "Advection Duration (Hours)",
    options=[1.0, 3.0, 6.0, 12.0, 24.0],
    value=24.0,
    format_func=lambda x: f"{int(x)}h" if x >= 1.0 else f"{x}h"
)

# Mode-Specific Sidebar Controls
if is_target_mode:
    st.sidebar.subheader("📊 Source Ranking Metric")
    ranking_choice = st.sidebar.selectbox(
        "Rank Candidate Sources By",
        options=[
            "Physical Transport Fraction (T_ij)",
            "Source-Weighted Influence Index (I_ij = C_i * T_ij)"
        ],
        index=0
    )
    metric_key = "source_weighted_transport_influence_index" if "Source-Weighted" in ranking_choice else "transport_fraction"
else:
    metric_key = "transport_fraction"

# Display Filters
st.sidebar.subheader("🔍 Display Filters")
min_frac_pct = st.sidebar.slider("Min. Transport Fraction Filter (%)", 0.0, 10.0, 0.0, step=0.5)
min_frac_val = min_frac_pct / 100.0

if not is_target_mode:
    category_filter = st.sidebar.multiselect(
        "Destination Categories",
        options=["VALID_LAND_DESTINATION", "INTERNAL_UNMODELED_WATER", "DOMAIN_EXIT_EXTERNAL", "UNSUPPORTED_MET_COVERAGE"],
        default=["VALID_LAND_DESTINATION", "INTERNAL_UNMODELED_WATER", "DOMAIN_EXIT_EXTERNAL", "UNSUPPORTED_MET_COVERAGE"]
    )

# Execution trigger
btn_label = "🎯 Run Target Inflow Query" if is_target_mode else "▶️ Run Source Dispersion Simulation"
run_clicked = st.sidebar.button(btn_label, type="primary", use_container_width=True)

# Determine whether to execute new query
query_cache_key = (is_target_mode, input_date, input_lat, input_lon, horizon_choice, metric_key)

if run_clicked or 'last_execution_key' not in st.session_state or st.session_state['last_execution_key'] != query_cache_key:
    spinner_msg = (
        f"Identifying candidate sources reaching ({input_lat:.3f}°N, {input_lon:.3f}°E) on {input_date} ({horizon_choice:g}h)..."
        if is_target_mode else
        f"Computing dynamic Lagrangian dispersion from ({input_lat:.3f}°N, {input_lon:.3f}°E) on {input_date} ({horizon_choice:g}h)..."
    )
    with st.spinner(spinner_msg):
        if is_target_mode:
            query_result = controller.execute_target_query(
                year=input_date.year,
                month=input_date.month,
                day=input_date.day,
                lat=input_lat,
                lon=input_lon,
                horizon_hours=horizon_choice,
                ranking_metric=metric_key,
                use_cache=True
            )
        else:
            query_result = controller.execute_query(
                year=input_date.year,
                month=input_date.month,
                day=input_date.day,
                lat=input_lat,
                lon=input_lon,
                horizon_hours=horizon_choice,
                use_cache=True
            )
        st.session_state['last_query_result'] = query_result
        st.session_state['last_execution_key'] = query_cache_key
else:
    query_result = st.session_state['last_query_result']

# ---------------------------------------------------------
# Handle Boundary / Validation Errors
# ---------------------------------------------------------
if query_result['status'] != 'SUCCESS':
    if query_result['status'] in ('UNSUPPORTED_MET_COVERAGE', 'ERROR_UNSUPPORTED_MET_COVERAGE'):
        st.warning(f"⚠️ **Meteorological Coverage Boundary Exceeded:** {query_result.get('message')}")
        st.info("The ERA5 reanalysis domain for this project is bounded by [6.0°N–35.0°N, 68.0°E–97.0°E]. Peripheral cells beyond this bounding box cannot be simulated without unscientific extrapolation.")
    elif query_result['status'] == 'VALIDATION_ERROR':
        st.error(f"❌ **Input Validation Error:** {query_result.get('message')}")
    else:
        st.error(f"❌ **Simulation Error ({query_result['status']}):** {query_result.get('message')}")
    st.stop()

# ---------------------------------------------------------
# Diagnostic Summary Banner (KPI Cards)
# ---------------------------------------------------------
df_table = query_result['results_table']
exec_time = query_result['execution_time_seconds']
is_cached = query_result['cache_hit']
cache_badge = " (Cached)" if is_cached else ""

if is_target_mode:
    tgt_info = query_result['target_info']
    tgt_mon = query_result['target_monitoring_info']
    
    st.markdown(f"""
    <div class="target-mode-banner">
        <b>🎯 Target-Centric Influence Analysis:</b> Reversing query orientation to evaluate all 1,380 national 50 km cells 
        and identify candidate source cells whose forward physical transport pathways reach target cell <b>{tgt_info['target_grid_id']}</b>.
    </div>
    """, unsafe_allow_html=True)
    
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    with kpi1:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Target Grid ID</div>
            <div class="metric-value">{tgt_info['target_grid_id']}</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi2:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Target Offset</div>
            <div class="metric-value">{tgt_info['offset_to_centroid_km']} km</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi3:
        status_label = "Active CAAQMS" if tgt_mon['has_date_matched_obs'] else ("Baseline Only" if tgt_mon['has_historical_baseline'] else "Unmonitored")
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Target Monitoring</div>
            <div class="metric-value">{status_label}</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi4:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Contributing Sources</div>
            <div class="metric-value">{query_result['sources_with_positive_transport']} / 1380</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi5:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Monitored Sources</div>
            <div class="metric-value">{query_result['monitored_sources_count']}</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi6:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Runtime</div>
            <div class="metric-value">{exec_time:.2f}s{cache_badge}</div>
        </div>
        """, unsafe_allow_html=True)

else:
    # Forward source dispersion KPI banner
    src_info = query_result['source_info']
    mon_info = query_result['monitoring_info']
    
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    with kpi1:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Source Grid ID</div>
            <div class="metric-value">{src_info['grid_id_50km']}</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi2:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Grid Offset</div>
            <div class="metric-value">{src_info['offset_to_centroid_km']} km</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi3:
        status_label = "Active CAAQMS" if mon_info['has_date_matched_obs'] else ("Baseline Only" if mon_info['has_historical_baseline'] else "Unmonitored")
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Monitoring Status</div>
            <div class="metric-value">{status_label}</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi4:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Synoptic Releases</div>
            <div class="metric-value">4 daily (00-18Z)</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi5:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Total Trajectories</div>
            <div class="metric-value">{query_result['total_ensemble_particles']}</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi6:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Runtime</div>
            <div class="metric-value">{exec_time:.2f}s{cache_badge}</div>
        </div>
        """, unsafe_allow_html=True)

st.write("")

# ---------------------------------------------------------
# Main Panel Tabs
# ---------------------------------------------------------
tab_map, tab_table, tab_obs, tab_diagnostics = st.tabs([
    "🗺️ Geospatial Map",
    "📊 Quantitative Results Table",
    "📈 Empirical Ground Air Quality",
    "🔬 Scientific Integrity & Model Diagnostics"
])

# ---------------------------------------------------------
# Tab 1: Geospatial Map
# ---------------------------------------------------------
with tab_map:
    if is_target_mode:
        st.subheader(f"Target Inflow Footprint ({horizon_choice:g}h Transport Horizon)")
        st.caption(f"Showing candidate source cells whose modeled transport pathways reach target cell {tgt_info['target_grid_id']} on {input_date}.")
        
        folium_map = visualizer.create_target_influence_map(
            query_result,
            user_lat=input_lat,
            user_lon=input_lon,
            min_fraction=min_frac_val
        )
        components.html(folium_map._repr_html_(), height=650, scrolling=False)
        
        n_reach = query_result['sources_with_positive_transport']
        n_mon = query_result['monitored_sources_count']
        n_unmon = query_result['unmonitored_sources_count']
        top_src = df_table.iloc[0]['source_grid_id'] if not df_table.empty else "None"
        top_frac = df_table.iloc[0]['daily_transport_fraction'] if not df_table.empty else 0.0
        
        st.markdown(
            f"**Candidate Sources Reaching Target:** **{n_reach}** (Monitored: **{n_mon}**, Unmonitored: **{n_unmon}**) | "
            f"**Top Candidate Source:** `{top_src}` (Transport Fraction: **{top_frac*100:.2f}%**) | "
            f"**Evaluated National Candidates:** 1,380 terrestrial cells"
        )
    else:
        st.subheader(f"Geospatial Dispersion Footprint ({horizon_choice:g}h Advection Horizon)")
        st.caption(f"Showing modeled downwind footprint from source {src_info['grid_id_50km']} on {input_date}. Destination polygons colored by transport fraction.")
        
        folium_map = visualizer.create_dispersion_map(
            query_result,
            user_lat=input_lat,
            user_lon=input_lon,
            min_fraction=min_frac_val
        )
        components.html(folium_map._repr_html_(), height=650, scrolling=False)
        
        cat_counts = query_result['category_counts']
        c_land = cat_counts.get("VALID_LAND_DESTINATION", 0)
        c_water = cat_counts.get("INTERNAL_UNMODELED_WATER", 0)
        c_exit = cat_counts.get("DOMAIN_EXIT_EXTERNAL", 0)
        c_unsupp = cat_counts.get("UNSUPPORTED_MET_COVERAGE", 0)
        
        st.markdown(
            f"**Destination Pathways Reached:** Terrestrial Land Cells: **{c_land}** | "
            f"Internal Unmodeled Water: **{c_water}** | Domain Exits: **{c_exit}** | "
            f"Unsupported Met: **{c_unsupp}** | Total Probability Closure: **{query_result['probability_closure_sum']:.4f}**"
        )

# ---------------------------------------------------------
# Tab 2: Quantitative Results Table
# ---------------------------------------------------------
with tab_table:
    if is_target_mode:
        st.subheader("Quantitative Candidate Source Inflow Table")
        st.caption(
            "Sortable table of candidate source cells whose modeled forward transport pathways arrive at the selected target. "
            "Transport fractions represent physical dispersion probability. Influence index (ug/m3-equiv) is computed only when source ground PM2.5 is available."
        )
        
        filtered_df = df_table[df_table['daily_transport_fraction'] >= min_frac_val].copy()
        
        display_df = filtered_df.copy()
        display_df['daily_transport_fraction'] = display_df['daily_transport_fraction'].apply(lambda x: f"{x:.4f} ({x*100:.2f}%)")
        display_df['distance_km'] = display_df['distance_km'].apply(lambda x: f"{x:.1f} km" if not pd.isna(x) else "—")
        display_df['source_pm25_ugm3'] = display_df['source_pm25_ugm3'].apply(
            lambda x: f"{x:.1f} µg/m³" if not pd.isna(x) else "Unmonitored"
        )
        display_df['source_weighted_transport_influence_index'] = display_df['source_weighted_transport_influence_index'].apply(
            lambda x: f"{x:.2f} µg/m³-equiv" if not pd.isna(x) else "Unmonitored"
        )
        
        st.dataframe(
            display_df[[
                'rank', 'source_grid_id', 'distance_km', 'daily_transport_fraction',
                'particles_count', 'source_pm25_ugm3',
                'source_weighted_transport_influence_index', 'source_observation_status'
            ]],
            use_container_width=True,
            hide_index=True
        )
        
        csv_bytes = df_table.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Complete Target Inflow Results (CSV)",
            data=csv_bytes,
            file_name=f"target_inflow_{tgt_info['target_grid_id']}_{input_date}_{int(horizon_choice)}h.csv",
            mime="text/csv"
        )
    else:
        st.subheader("Quantitative Destination Transport Table")
        st.caption("Sortable matrix of destination cells with transport probabilities, distance from source, and source-weighted influence indices.")
        
        filtered_df = df_table[
            (df_table['daily_transport_fraction'] >= min_frac_val) &
            (df_table['category'].isin(category_filter))
        ].copy()
        
        display_df = filtered_df.copy()
        display_df['daily_transport_fraction'] = display_df['daily_transport_fraction'].apply(lambda x: f"{x:.4f} ({x*100:.1f}%)")
        display_df['distance_km'] = display_df['distance_km'].apply(lambda x: f"{x:.1f} km" if not pd.isna(x) else "—")
        display_df['source_weighted_transport_influence_index'] = display_df['source_weighted_transport_influence_index'].apply(
            lambda x: f"{x:.2f} µg/m³-equiv" if not pd.isna(x) else "Unmonitored"
        )
        
        st.dataframe(
            display_df[[
                'rank', 'destination', 'category', 'daily_transport_fraction',
                'particles_count', 'distance_km', 'source_weighted_transport_influence_index',
                'influence_status'
            ]],
            use_container_width=True,
            hide_index=True
        )
        
        csv_bytes = df_table.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Complete Query Results (CSV)",
            data=csv_bytes,
            file_name=f"dispersion_{src_info['grid_id_50km']}_{input_date}_{int(horizon_choice)}h.csv",
            mime="text/csv"
        )

# ---------------------------------------------------------
# Tab 3: Empirical Ground Air Quality
# ---------------------------------------------------------
with tab_obs:
    st.subheader(f"Observed Ground Air Quality on {input_date}")
    
    # Target / Source Local Air Quality Callout
    local_gid = tgt_info['target_grid_id'] if is_target_mode else src_info['grid_id_50km']
    local_mon = tgt_mon if is_target_mode else mon_info
    loc_role = "Target Receptor" if is_target_mode else "Source Emitter"
    
    st.markdown(f"#### 📍 Local Ground Air Quality at {loc_role} Cell `{local_gid}`")
    col_l1, col_l2, col_l3 = st.columns(3)
    with col_l1:
        st.write(f"- **Monitoring Status:** `{local_mon['monitoring_status']}`")
        st.write(f"- **Reporting Stations:** {local_mon['stations_count']}")
    with col_l2:
        pm_val = f"{local_mon['effective_source_pm25_ugm3']:.1f} µg/m³" if not np.isnan(local_mon['effective_source_pm25_ugm3']) else "No Station Data"
        st.write(f"- **Effective PM2.5:** `{pm_val}`")
        st.write(f"- **Cities Represented:** {', '.join(local_mon['cities']) if local_mon['cities'] else 'None'}")
    with col_l3:
        st.write(f"- **Station Details:** {', '.join(local_mon['station_names'][:3]) if local_mon['station_names'] else 'Unmonitored terrestrial cell'}")
    
    st.markdown("---")
    st.markdown("#### 🏛️ Nationwide Empirical Regulatory Context (CPCB & OpenAQ)")
    st.info(
        "ℹ️ **Nationwide Context Notice:** The tables below display regulatory air quality records collected across India on this date. "
        "These independent measurements provide broad regional context across Indian cities and are **NOT** contributing source zones or model predictions."
    )
    
    subtab_cpcb, subtab_openaq = st.tabs(["🏛️ CPCB Daily AQI Bulletins", "🔬 OpenAQ Measured PM2.5 Concentrations"])
    
    with subtab_cpcb:
        df_cpcb = query_result.get('date_matched_cpcb_ranking', pd.DataFrame())
        if df_cpcb is not None and not df_cpcb.empty:
            st.markdown(f"**Found {len(df_cpcb)} cities reporting CPCB Official AQI Bulletins on {input_date}:**")
            st.dataframe(
                df_cpcb[['rank', 'city', 'grid_id_50km', 'spatial_mapping_type', 'aqi_index_value', 'air_quality_category', 'prominent_pollutant', 'no_stations_reporting']],
                use_container_width=True,
                hide_index=True
            )
            st.caption("ℹ️ Spatial Mapping Rule: Cities whose monitoring stations fall strictly within a single 50 km cell are assigned their exact Grid ID (SINGLE_50KM_CELL). Large metropolitan areas spanning multiple cells are labeled MULTIPLE_CELLS. Municipal bulletins without CAAQMS station coordinates are preserved as UNMAPPED (CITY_LEVEL_REGULATORY_BULLETIN).")
            cpcb_csv = df_cpcb.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CPCB Bulletins CSV", cpcb_csv, f"cpcb_aqi_{input_date}.csv", mime="text/csv")
        else:
            st.info(f"No CPCB city-level AQI bulletins are recorded for {input_date} in the repository archive.")

    with subtab_openaq:
        df_openaq = query_result.get('date_matched_openaq_ranking', pd.DataFrame())
        if df_openaq is not None and not df_openaq.empty:
            st.markdown(f"**Found {len(df_openaq)} ground CAAQMS stations reporting PM2.5 on {input_date}:**")
            st.dataframe(
                df_openaq[['rank', 'city', 'station_name', 'grid_id_50km', 'mean_observed_pm25_ugm3', 'observation_samples']],
                use_container_width=True,
                hide_index=True
            )
            openaq_csv = df_openaq.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download OpenAQ PM2.5 CSV", openaq_csv, f"openaq_pm25_{input_date}.csv", mime="text/csv")
        else:
            st.info(f"No active station-level OpenAQ PM2.5 hourly observations found for {input_date} in the repository archive.")

# ---------------------------------------------------------
# Tab 4: Scientific Integrity & Diagnostics
# ---------------------------------------------------------
with tab_diagnostics:
    st.subheader("Model Diagnostics & Scientific Integrity")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown("#### Simulation Provenance")
        st.write(f"- **Operational Mode:** `{'Target Inflow Query' if is_target_mode else 'Source Dispersion'}`")
        st.write(f"- **Query Date:** `{input_date}`")
        if is_target_mode:
            st.write(f"- **Target Grid Cell:** `{tgt_info['target_grid_id']}` (Row: {tgt_info['row']}, Col: {tgt_info['column']})")
            st.write(f"- **Target Centroid:** `({tgt_info['target_latitude']:.4f}°N, {tgt_info['target_longitude']:.4f}°E)`")
            st.write(f"- **User Coordinates:** `({tgt_info['user_latitude']:.4f}°N, {tgt_info['user_longitude']:.4f}°E)`")
            st.write(f"- **Centroid Offset:** `{tgt_info['offset_to_centroid_km']} km`")
            st.write(f"- **Matrix Source:** `{query_result.get('matrix_source', 'Monthly Matrix')}`")
            st.write(f"- **Ranking Metric:** `{metric_key}`")
        else:
            st.write(f"- **Source Grid Cell:** `{src_info['grid_id_50km']}` (Row: {src_info['row']}, Col: {src_info['column']})")
            st.write(f"- **Grid Centroid:** `({src_info['source_latitude']:.4f}°N, {src_info['source_longitude']:.4f}°E)`")
            st.write(f"- **User Coordinates:** `({src_info['user_latitude']:.4f}°N, {src_info['user_longitude']:.4f}°E)`")
            st.write(f"- **Geodetic Offset:** `{src_info['offset_to_centroid_km']} km`")
        st.write(f"- **Advection Duration:** `{horizon_choice} hours`")
        
    with col_d2:
        st.markdown("#### Spatial Coverage & Candidate Sources")
        if is_target_mode:
            st.write(f"- **National Grid Scope:** `1,380 terrestrial 50 km cells (EPSG:7755)`")
            st.write(f"- **Candidate Sources Evaluated:** `{query_result['total_candidate_sources']} cells`")
            st.write(f"- **Sources with Inflow Pathways:** `{query_result['sources_with_positive_transport']} cells`")
            st.write(f"- **Monitored Candidate Sources:** `{query_result['monitored_sources_count']} cells`")
            st.write(f"- **Unmonitored Candidate Sources:** `{query_result['unmonitored_sources_count']} cells`")
            st.write(f"- **Target Ground Truth Status:** `{tgt_mon['monitoring_status']}`")
        else:
            st.write(f"- **Terrestrial Land Destinations:** `{c_land} cells`")
            st.write(f"- **Internal Unmodeled Water:** `{c_water} pathways`")
            st.write(f"- **Domain Exit (International):** `{c_exit} pathways`")
            st.write(f"- **Unsupported Met Coverage:** `{c_unsupp} pathways`")
            st.write(f"- **Probability Sum:** `{query_result['probability_closure_sum']:.6f}`")
            st.write(f"- **Source Ground Truth Status:** `{mon_info['monitoring_status']}`")

    st.markdown("---")
    st.markdown("#### Methodological Limitations & Explicit Disclaimers")
    st.markdown(r"""
    1. **Strictly 2D Horizontal Transport:** The model advects air parcels using ERA5 10-meter horizontal winds (U10, V10). It does not include vertical wind shear, convective updrafts, or boundary layer entrainment/detrainment.
    2. **Zero Chemical Depletion:** Particulate matter is treated as a passive conservative tracer without wet deposition (scavenging by precipitation), dry deposition (gravitational settling), or secondary aerosol chemistry.
    3. **Zero Forecasting Capability:** All simulations are retrospective evaluations against historical ERA5 reanalysis fields (2019–2024). No prognostic weather or AQI forecasting is performed.
    4. **Candidate Source Transport vs. Emission Inventories:** The target query identifies candidate source cells whose physical atmospheric transport pathways connect to the receptor cell. It does **NOT** represent an emission inventory or source apportionment study.
    5. **Source Influence Metric Definition:** The metric `source_weighted_transport_influence_index` is computed as $I_{ij} = C_i \times T_{ij}$, where $C_i$ is the empirical ground PM2.5 concentration at source cell $i$, and $T_{ij}$ is the transport fraction to destination $j$. It represents the dispersed source concentration in $\mu\text{g/m}^3$-equivalent, **NOT** the ambient air quality or total PM2.5 measured at destination $j$.
    6. **Unmonitored Sources:** For the 1,329 unmonitored grid cells across India lacking air-quality monitoring stations, the transport fraction $T_{ij}$ is physically evaluated, but the influence index is strictly reported as `NaN` (Unmonitored). Concentration values are never fabricated.
    """)
