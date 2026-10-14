"""
MASTER RUNNER: PHASE 8 NATIONAL PILOT PIPELINE
===============================================
Executes the complete India-wide 2D Grid-to-Grid Pollution Dispersion Pilot:
1. Builds continuous 0.25° national grid (16,093 cells) and maps 103 OpenAQ stations.
2. Extracts native ERA5 horizontal surface wind slices (U10, V10).
3. Ingests and aligns OpenAQ PM2.5 ground observations across pilot stations.
4. Executes the 2D Lagrangian ensemble dispersion engine across all time windows.
5. Verifies all 10 physical and numerical constraints.
6. Generates publication-quality diagnostic figures.
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath("."))

from src.national.build_national_grid_and_mapping import run_national_prep
from src.national.physics_2d_national_dispersion import run_national_dispersion
from src.national.verify_national_constraints import verify_national_constraints
from src.national.plot_national_visualizations import generate_all_national_plots

def run_entire_national_pilot():
    start_total = time.time()
    print("=" * 80)
    print("STARTING PHASE 8: INDIA-WIDE 2D GRID-TO-GRID DISPERSION PILOT")
    print("=" * 80)

    # Step 1: National Grid, Station Mapping, ERA5 Extraction, and Alignment
    print("\n[STEP 1/4] Constructing National Grid & Aligning Real Data...")
    run_national_prep()

    # Step 2: 2D Lagrangian Ensemble Dispersion Engine
    print("\n[STEP 2/4] Executing 2D Ensemble Dispersion Engine on National Grid...")
    run_national_dispersion()

    # Step 3: Physical Constraints Audit
    print("\n[STEP 3/4] Auditing 10 Physical and Numerical Constraints...")
    verify_national_constraints()

    # Step 4: Diagnostic Plots & Visualizations
    print("\n[STEP 4/4] Generating Publication Diagnostic Visualizations...")
    generate_all_national_plots()

    elapsed = time.time() - start_total
    print("\n" + "=" * 80)
    print(f"PHASE 8 NATIONAL PILOT COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS!")
    print("=" * 80)

if __name__ == "__main__":
    run_entire_national_pilot()
