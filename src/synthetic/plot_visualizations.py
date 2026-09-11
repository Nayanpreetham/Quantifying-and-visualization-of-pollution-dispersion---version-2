"""
VISUALIZATION GENERATOR
=======================
Generates 10 figures in results/figures/:
1. 01_source_location_map.png (Map/grid showing synthetic source location)
2. 02_wind_vector_field.png (Wind vector field)
3. 03_physics_dispersion_map.png (Physics-derived dispersion map)
4. 04_ml_predicted_dispersion_map.png (ML-predicted dispersion map)
5. 05_physics_vs_ml_error_map.png (Physics vs ML difference/error map)
6. 06_transport_matrix.png (Source -> destination transport matrix)
7. 07_dispersion_vs_distance.png (Plot showing dispersion influence vs distance)
8. 08_downwind_vs_upwind.png (Plot showing downwind vs upwind transport)
9. 09_ensemble_stability_N5_10_20.png (Plot showing ensemble stability for N=5,10,20)
10. 10_ml_feature_importance.png (ML feature importance plot)
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

DISCLAIMER = "SYNTHETIC DATA — PIPELINE/CONSTRAINT VERIFICATION ONLY"


def generate_all_plots(data_dir="data/synthetic", ml_results_dir="results/ml", figures_dir="results/figures"):
    os.makedirs(figures_dir, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # Load data
    pred_path = os.path.join(ml_results_dir, "predictions_full_dataset.csv")
    if not os.path.exists(pred_path):
        raise FileNotFoundError(f"Missing predictions file at {pred_path}")

    df = pd.read_csv(pred_path)
    grid_df = pd.read_csv(os.path.join(data_dir, "grid.csv"))

    # Select Delhi case for spatial grid maps
    del_df = df[(df["city_name"] == "Delhi") & (df["timestamp_hour"] == 0) & (df["elapsed_time_hours"] == 3.0)].copy()

    # Pivot 7x7 grid values for heatmap
    phys_grid = del_df.pivot(index="dest_lat", columns="dest_lon", values="transport_influence").sort_index(ascending=False)
    ml_grid = del_df.pivot(index="dest_lat", columns="dest_lon", values="ml_predicted_influence").sort_index(ascending=False)
    error_grid = (ml_grid - phys_grid)

    src_lat = del_df["source_lat"].iloc[0]
    src_lon = del_df["source_lon"].iloc[0]

    print("[Visualizer] Generating 10 synthetic verification plots...")

    # -------------------------------------------------------------------------
    # 1. Source Location Map
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 6))
    grid_delhi = grid_df[grid_df["city_name"] == "Delhi"]
    ax.scatter(grid_delhi["longitude"], grid_delhi["latitude"], c="lightblue", s=300, edgecolors="gray", label="Grid Cells")
    ax.scatter([src_lon], [src_lat], c="red", s=500, marker="*", label="Source Grid (DEL_r3_c3)")
    ax.set_title(f"01. Synthetic Source Grid Location (Delhi)\n[{DISCLAIMER}]", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "01_source_location_map.png"), dpi=150)
    plt.close()

    # -------------------------------------------------------------------------
    # 2. Wind Vector Field
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 6))
    X_mesh, Y_mesh = np.meshgrid(grid_delhi["longitude"].unique(), grid_delhi["latitude"].unique())
    u10 = del_df["u10"].iloc[0]
    v10 = del_df["v10"].iloc[0]
    U_field = np.full_like(X_mesh, u10)
    V_field = np.full_like(Y_mesh, v10)

    ax.quiver(X_mesh, Y_mesh, U_field, V_field, color="navy", scale=30)
    ax.scatter([src_lon], [src_lat], c="red", s=200, marker="*", label="Source")
    ax.set_title(f"02. ERA5-Like 2D Horizontal Wind Field (U10={u10} m/s, V10={v10} m/s)\n[{DISCLAIMER}]", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "02_wind_vector_field.png"), dpi=150)
    plt.close()

    # -------------------------------------------------------------------------
    # 3. Physics-Derived Dispersion Map
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(phys_grid, cmap="YlOrRd", annot=True, fmt=".1f", ax=ax, cbar_kws={"label": "Transport Influence"})
    ax.set_title(f"03. Physics-Derived Dispersion Map (t=3h)\n[{DISCLAIMER}]", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "03_physics_dispersion_map.png"), dpi=150)
    plt.close()

    # -------------------------------------------------------------------------
    # 4. ML-Predicted Dispersion Map
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(ml_grid, cmap="YlOrRd", annot=True, fmt=".1f", ax=ax, cbar_kws={"label": "ML Predicted Influence"})
    ax.set_title(f"04. ML-Predicted Dispersion Map (t=3h)\n[{DISCLAIMER}]", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "04_ml_predicted_dispersion_map.png"), dpi=150)
    plt.close()

    # -------------------------------------------------------------------------
    # 5. Physics vs ML Error Map
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(error_grid, cmap="coolwarm", annot=True, fmt=".1f", center=0, ax=ax, cbar_kws={"label": "Difference (ML - Physics)"})
    ax.set_title(f"05. Physics vs. ML Difference/Error Map\n[{DISCLAIMER}]", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "05_physics_vs_ml_error_map.png"), dpi=150)
    plt.close()

    # -------------------------------------------------------------------------
    # 6. Source -> Destination Transport Matrix
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 6))
    matrix_df = del_df.pivot(index="source_grid_id", columns="dest_grid_id", values="transport_fraction").fillna(0)
    # Subset to top 15 destination columns for visualization clarity
    cols_sub = matrix_df.sum().sort_values(ascending=False).head(15).index
    sns.heatmap(matrix_df[cols_sub], cmap="Blues", annot=True, fmt=".2f", ax=ax, cbar_kws={"label": "Transport Fraction T[src,dest,t]"})
    ax.set_title(f"06. Grid-to-Grid Transport Matrix T[A, B, t]\n[{DISCLAIMER}]", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Destination Grid ID")
    ax.set_ylabel("Source Grid ID")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "06_transport_matrix.png"), dpi=150)
    plt.close()

    # -------------------------------------------------------------------------
    # 7. Dispersion Influence vs Distance
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(df["distance_km"], df["transport_influence"], alpha=0.5, color="blue", label="Physics Target", s=20)
    ax.scatter(df["distance_km"], df["ml_predicted_influence"], alpha=0.3, color="orange", label="ML Prediction", s=15)
    ax.set_title(f"07. Dispersion Influence vs. Distance\n[{DISCLAIMER}]", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Distance from Source (km)")
    ax.set_ylabel("Transported Pollution Influence")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "07_dispersion_vs_distance.png"), dpi=150)
    plt.close()

    # -------------------------------------------------------------------------
    # 8. Downwind vs Upwind Transport
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 5))
    downwind_pts = df[df["rel_angle_to_wind_deg"] <= 45.0]
    upwind_pts = df[df["rel_angle_to_wind_deg"] >= 135.0]

    ax.scatter(downwind_pts["distance_km"], downwind_pts["transport_influence"], color="green", alpha=0.6, label="Downwind Sector (<=45°)")
    ax.scatter(upwind_pts["distance_km"], upwind_pts["transport_influence"], color="red", alpha=0.6, label="Upwind Sector (>=135°)")
    ax.set_title(f"08. Downwind vs. Upwind Transport Preference\n[{DISCLAIMER}]", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Distance from Source (km)")
    ax.set_ylabel("Transported Pollution Influence")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "08_downwind_vs_upwind.png"), dpi=150)
    plt.close()

    # -------------------------------------------------------------------------
    # 9. Ensemble Stability Benchmark Plot (N=5, 10, 20)
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 5))
    ensemble_sizes = [5, 10, 20]
    # Re-run quick 1D slice comparison for plotting
    from src.synthetic.physics_2d_dispersion import benchmark_ensemble_stability
    stab_df = benchmark_ensemble_stability(data_dir=data_dir)

    bars = ax.bar(stab_df["ensemble_comparison"], stab_df["mae_fraction_diff"] * 100, color=["coral", "teal"], width=0.4)
    ax.axhline(5.0, color="red", linestyle="--", label="5% Stability Threshold")
    ax.set_title(f"09. Ensemble Stability Benchmark (N=5, 10, 20)\n[{DISCLAIMER}]", fontsize=11, fontweight="bold", pad=10)
    ax.set_ylabel("Mean Absolute Difference (%)")
    ax.legend()
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 0.2, f"{yval:.2f}%", ha="center", va="bottom", fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "09_ensemble_stability_N5_10_20.png"), dpi=150)
    plt.close()

    # -------------------------------------------------------------------------
    # 10. ML Feature Importance
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 5))
    feat_imp_path = os.path.join(ml_results_dir, "feature_importances.csv")
    if os.path.exists(feat_imp_path):
        f_df = pd.read_csv(feat_imp_path).head(10)
        sns.barplot(data=f_df, x="importance", y="feature", palette="viridis", ax=ax)
        ax.set_title(f"10. ML Surrogate Feature Importance\n[{DISCLAIMER}]", fontsize=11, fontweight="bold", pad=10)
        ax.set_xlabel("Relative Feature Importance")
        ax.set_ylabel("Feature Name")
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "10_ml_feature_importance.png"), dpi=150)
    plt.close()

    print(f"[Visualizer] Saved all 10 verification figures to: {figures_dir}")


if __name__ == "__main__":
    generate_all_plots()
