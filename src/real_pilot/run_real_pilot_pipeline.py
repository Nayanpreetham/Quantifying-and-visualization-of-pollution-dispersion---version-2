"""
MASTER REAL PILOT PIPELINE RUNNER
==================================
Executes the full Real-Data 2D Dispersion Pilot Experiment:
1. Runs 2D kinematic advection & ensemble dispersion on real OpenAQ + ERA5 data
2. Evaluates 10 physical constraints on real outputs
3. Generates 8 diagnostic and verification figures
"""

import os
import sys

sys.path.insert(0, os.path.abspath("."))

from src.real_pilot.physics_2d_real_pilot import run_real_dispersion_pilot, benchmark_real_ensemble_stability
from src.real_pilot.verify_real_constraints import run_real_constraint_verification
from src.real_pilot.plot_real_visualizations import generate_all_real_plots


def run_full_real_pilot():
    print("\n" + "=" * 70)
    print("STARTING 2D REAL-DATA POLLUTION DISPERSION PILOT")
    print("=" * 70 + "\n")

    # Step 1: Run physics & ensemble dispersion
    run_real_dispersion_pilot(
        grid_path="data/processed/real_grid.csv",
        aligned_path="data/processed/openaq_era5_aligned.csv",
        results_dir="results/real_pilot",
        n_ensemble=20
    )
    benchmark_real_ensemble_stability(
        grid_path="data/processed/real_grid.csv",
        aligned_path="data/processed/openaq_era5_aligned.csv",
        results_dir="results/real_pilot"
    )

    # Step 2: Physical constraint checks
    run_real_constraint_verification(results_dir="results/real_pilot")

    # Step 3: Visualization suite
    generate_all_real_plots(
        data_dir="data/processed",
        results_dir="results/real_pilot",
        figures_dir="results/real_pilot/figures"
    )

    print("\n" + "=" * 70)
    print("REAL-DATA PILOT PIPELINE SUCCESSFULLY COMPLETED!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_full_real_pilot()
