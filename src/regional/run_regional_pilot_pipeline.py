"""
MASTER REGIONAL PIPELINE RUNNER (INDO-GANGETIC PLAIN)
======================================================
Executes the full Phase 6 Regional Model:
1. Builds continuous 0.25° grid & corrects station mappings
2. Runs 2D physics ensemble dispersion across the continuous domain
3. Evaluates 10 physical constraints (with boundary-loss verification)
4. Generates 7 regional diagnostic maps and charts
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))

from src.regional.build_regional_grid_and_mapping import run_regional_prep
from src.regional.physics_2d_regional_dispersion import run_regional_dispersion
from src.regional.verify_regional_constraints import verify_regional_constraints
from src.regional.plot_regional_visualizations import generate_all_regional_plots


def run_full_regional_pipeline():
    print("\n" + "=" * 70)
    print("STARTING CONTINUOUS REGIONAL POLLUTION DISPERSION MODEL (IGP)")
    print("=" * 70 + "\n")

    # Step 1: Data prep, continuous grid, corrected mapping
    run_regional_prep()

    # Step 2: 2D physics & ensemble advection across continuous grid
    run_regional_dispersion(
        grid_path="data/regional/igp_025_grid.csv",
        aligned_path="data/regional/openaq_era5_aligned_regional.csv",
        results_dir="results/regional_pilot",
        n_ensemble=20
    )

    # Step 3: Physical constraint verification
    verify_regional_constraints(results_dir="results/regional_pilot")

    # Step 4: Visualizations
    generate_all_regional_plots(
        data_dir="data/regional",
        results_dir="results/regional_pilot",
        figures_dir="results/regional_pilot/figures"
    )

    print("\n" + "=" * 70)
    print("REGIONAL MODEL EXECUTION & VERIFICATION COMPLETE!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_full_regional_pipeline()
