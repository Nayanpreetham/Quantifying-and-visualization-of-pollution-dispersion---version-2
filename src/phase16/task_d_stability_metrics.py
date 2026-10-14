"""
PHASE 16 — TASK D: SEASONAL & INTERANNUAL STABILITY METRICS
===========================================================
Calculates quantitative dispersion stability, spatial concentration,
distance scaling, and interannual similarity:
1. Spatial concentration metrics per source station:
   - Normalized Herfindahl-Hirschman Index (HHI*)
   - Gini coefficient of destination transport probabilities
   - Shannon spatial entropy (bits)
2. Mean and median transport distance (km) across advection windows.
3. Distance band distribution:
   - Local (< 30 km)
   - Near-regional (30–100 km)
   - Regional (100–250 km)
   - Long-range (>= 250 km)
   - Boundary exit (OUTSIDE_DOMAIN)
4. Interannual pairwise cosine similarity & Pearson correlation of transport vectors.
5. Outputs:
   - results/phase16_climatology/tables/interannual_stability.csv
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import numpy as np
import pandas as pd
from scipy.spatial.distance import cosine

WINDOWS = [1.0, 3.0, 6.0, 12.0, 24.0]

def compute_hhi_norm(probs):
    """Normalized HHI in [0, 1]"""
    probs = np.array(probs)
    probs = probs[probs > 0]
    n = len(probs)
    if n <= 1:
        return 1.0
    hhi = np.sum(probs**2)
    hhi_norm = (hhi - 1.0 / n) / (1.0 - 1.0 / n)
    return float(np.clip(hhi_norm, 0.0, 1.0))

def compute_gini(probs):
    """Gini coefficient of transport probabilities"""
    probs = np.sort(np.array(probs))
    n = len(probs)
    if n <= 1 or np.sum(probs) == 0:
        return 0.0
    index = np.arange(1, n + 1)
    return float(((np.sum((2 * index - n - 1) * probs)) / (n * np.sum(probs))))

def compute_entropy(probs):
    """Shannon entropy in bits"""
    probs = np.array(probs)
    probs = probs[probs > 0]
    if len(probs) == 0:
        return 0.0
    return float(-np.sum(probs * np.log2(probs)))

def compute_stability_metrics(out_dir="results/phase16_climatology/tables"):
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, "interannual_stability.csv")

    years = list(range(2019, 2025))
    annual_matrices = {}

    for y in years:
        fpath = f"results/phase16_climatology/matrices/transport_matrix_annual_{y}.csv"
        annual_matrices[y] = pd.read_csv(fpath)

    stations = annual_matrices[2019][["station_id", "station_name", "city", "source_grid_id"]].drop_duplicates()

    records = []
    print("[Task D] Calculating spatial concentration, distance distributions & interannual stability...")

    for _, st in stations.iterrows():
        s_id = int(st["station_id"])
        s_name = st["station_name"]
        city = st["city"]
        src_gid = st["source_grid_id"]

        for dt_h in WINDOWS:
            # 1. Year-by-year metrics
            yr_metrics = {}
            dest_vectors = {}

            for y in years:
                df_y = annual_matrices[y]
                sub = df_y[(df_y["station_id"] == s_id) & (df_y["elapsed_time_hours"] == dt_h)]

                # Build full destination probability dictionary
                vec = dict(zip(sub["dest_grid_id"], sub["mean_transport_fraction"]))
                dest_vectors[y] = vec

                # Inside vs outside
                sub_in = sub[sub["dest_grid_id"] != "OUTSIDE_DOMAIN"]
                sub_out = sub[sub["dest_grid_id"] == "OUTSIDE_DOMAIN"]
                out_frac = float(sub_out["mean_transport_fraction"].iloc[0]) if len(sub_out) > 0 else 0.0

                probs = sub["mean_transport_fraction"].values
                hhi = compute_hhi_norm(probs)
                gini = compute_gini(probs)
                entropy = compute_entropy(probs)

                # Distance metrics
                if len(sub_in) > 0:
                    dists = sub_in["distance_km"].values
                    weights = sub_in["mean_transport_fraction"].values
                    mean_dist = float(np.sum(dists * weights) / np.sum(weights)) if np.sum(weights) > 0 else 0.0

                    # Weighted median
                    sorted_idx = np.argsort(dists)
                    cum_w = np.cumsum(weights[sorted_idx]) / np.sum(weights)
                    med_idx = np.searchsorted(cum_w, 0.5)
                    median_dist = float(dists[sorted_idx[min(med_idx, len(dists)-1)]])

                    # Distance bands
                    local_frac = float(sub_in[sub_in["distance_km"] < 30.0]["mean_transport_fraction"].sum())
                    near_reg_frac = float(sub_in[(sub_in["distance_km"] >= 30.0) & (sub_in["distance_km"] < 100.0)]["mean_transport_fraction"].sum())
                    reg_frac = float(sub_in[(sub_in["distance_km"] >= 100.0) & (sub_in["distance_km"] < 250.0)]["mean_transport_fraction"].sum())
                    long_frac = float(sub_in[sub_in["distance_km"] >= 250.0]["mean_transport_fraction"].sum())
                else:
                    mean_dist = 0.0
                    median_dist = 0.0
                    local_frac, near_reg_frac, reg_frac, long_frac = 0.0, 0.0, 0.0, 0.0

                yr_metrics[y] = {
                    "hhi": hhi,
                    "gini": gini,
                    "entropy": entropy,
                    "mean_dist": mean_dist,
                    "median_dist": median_dist,
                    "local_frac": local_frac,
                    "near_reg_frac": near_reg_frac,
                    "reg_frac": reg_frac,
                    "long_frac": long_frac,
                    "out_frac": out_frac
                }

            # 2. Pairwise Interannual Similarity (Consecutive years & all pairs)
            all_dests = set()
            for y in years:
                all_dests.update(dest_vectors[y].keys())
            sorted_all_dests = sorted(list(all_dests))

            vec_arrays = {}
            for y in years:
                arr = np.array([dest_vectors[y].get(d, 0.0) for d in sorted_all_dests])
                vec_arrays[y] = arr

            # Calculate pairwise cosine similarities
            cos_sims = []
            pearson_corrs = []
            for i in range(len(years)):
                for j in range(i + 1, len(years)):
                    y1, y2 = years[i], years[j]
                    u, v = vec_arrays[y1], vec_arrays[y2]
                    dot_uv = np.dot(u, v)
                    norm_u = np.linalg.norm(u)
                    norm_v = np.linalg.norm(v)
                    cos_sim = float(dot_uv / (norm_u * norm_v)) if (norm_u > 0 and norm_v > 0) else 0.0
                    cos_sims.append(cos_sim)

                    # Pearson r
                    if np.std(u) > 0 and np.std(v) > 0:
                        r = float(np.corrcoef(u, v)[0, 1])
                    else:
                        r = 0.0
                    pearson_corrs.append(r)

            mean_cos_sim = float(np.mean(cos_sims))
            min_cos_sim = float(np.min(cos_sims))
            mean_pearson_r = float(np.mean(pearson_corrs))

            # Multi-year averages
            avg_mean_dist = float(np.mean([yr_metrics[y]["mean_dist"] for y in years]))
            avg_median_dist = float(np.mean([yr_metrics[y]["median_dist"] for y in years]))
            avg_hhi = float(np.mean([yr_metrics[y]["hhi"] for y in years]))
            avg_gini = float(np.mean([yr_metrics[y]["gini"] for y in years]))
            avg_local = float(np.mean([yr_metrics[y]["local_frac"] for y in years]))
            avg_near_reg = float(np.mean([yr_metrics[y]["near_reg_frac"] for y in years]))
            avg_reg = float(np.mean([yr_metrics[y]["reg_frac"] for y in years]))
            avg_long = float(np.mean([yr_metrics[y]["long_frac"] for y in years]))
            avg_out = float(np.mean([yr_metrics[y]["out_frac"] for y in years]))

            records.append({
                "station_id": s_id,
                "station_name": s_name,
                "city": city,
                "source_grid_id": src_gid,
                "advection_window_hours": dt_h,
                "six_year_mean_transport_dist_km": round(avg_mean_dist, 2),
                "six_year_median_transport_dist_km": round(avg_median_dist, 2),
                "six_year_avg_hhi_normalized": round(avg_hhi, 4),
                "six_year_avg_gini_coefficient": round(avg_gini, 4),
                "local_frac_lt_30km": round(avg_local, 4),
                "near_regional_frac_30_100km": round(avg_near_reg, 4),
                "regional_frac_100_250km": round(avg_reg, 4),
                "long_range_frac_gte_250km": round(avg_long, 4),
                "domain_exit_frac": round(avg_out, 4),
                "mean_pairwise_cosine_similarity": round(mean_cos_sim, 4),
                "min_pairwise_cosine_similarity": round(min_cos_sim, 4),
                "mean_pairwise_pearson_r": round(mean_pearson_r, 4),
                "interannual_stability_rating": (
                    "VERY_HIGH" if mean_cos_sim >= 0.90 else
                    ("HIGH" if mean_cos_sim >= 0.80 else
                    ("MODERATE" if mean_cos_sim >= 0.70 else "VARIABLE"))
                )
            })

    df_res = pd.DataFrame(records)
    df_res.to_csv(out_csv, index=False)
    print(f"[Task D] Saved interannual stability metrics: {out_csv} ({len(df_res)} source-window groups)")

    print("\n=== INTERANNUAL STABILITY SUMMARY BY ADVECTION WINDOW ===")
    for dt_h, grp in df_res.groupby("advection_window_hours"):
        m_cos = grp["mean_pairwise_cosine_similarity"].mean()
        m_dist = grp["six_year_mean_transport_dist_km"].mean()
        m_loc = grp["local_frac_lt_30km"].mean() * 100.0
        m_reg = (grp["near_regional_frac_30_100km"] + grp["regional_frac_100_250km"]).mean() * 100.0
        m_long = grp["long_range_frac_gte_250km"].mean() * 100.0
        print(f"Window {dt_h:4.1f}h: Dist={m_dist:5.1f} km | Local={m_loc:4.1f}% | Reg={m_reg:4.1f}% | Long={m_long:4.1f}% | Pairwise Cosine Sim={m_cos:.4f}")

    return df_res

if __name__ == "__main__":
    compute_stability_metrics()
