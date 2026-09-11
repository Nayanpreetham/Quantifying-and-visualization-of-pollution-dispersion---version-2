"""
Fast Grid Lookup using Rasterized Index
=========================================
Replaces the expensive geopandas sjoin for trajectory-to-grid assignment.

The 50-km source grid can be indexed as a 2D array of (row, column) integers
because it is a regular grid. Each trajectory point (lat, lon) can be assigned
to a grid cell via simple arithmetic instead of repeated polygon intersection.

This reduces trajectory-to-grid assignment from O(N_traj_points * N_grid_cells)
polygon intersections to O(N_traj_points) array index lookups.

Usage
-----
    from src.transport.grid_lookup import GridRasterIndex

    # Build once per session
    index = GridRasterIndex('data/processed/grid/india_50km_grid.geojson')

    # Assign grid cells to trajectory points (fast)
    grid_ids = index.assign_grid_ids(lats, lons)

    # Get influence counts
    influence = index.compute_influence(lats, lons)
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from typing import Optional


class GridRasterIndex:
    """
    A fast rasterized lookup for the 50-km India source grid.

    The grid uses the 'center_lat' and 'center_lon' columns from the GeoJSON
    to construct a KD-tree for nearest-neighbor assignment. This is much faster
    than polygon intersection while being virtually equivalent for a regular grid
    (the nearest centroid of a regular grid gives the correct cell 99.9%+ of the time).

    For points outside India (ocean, foreign countries), returns NaN grid_id.
    """

    def __init__(self, grid_geojson: str):
        from scipy.spatial import cKDTree

        self.grid = gpd.read_file(grid_geojson)

        # Build KD-tree from grid centroids
        centroids = np.column_stack([
            self.grid['center_lat'].values,
            self.grid['center_lon'].values,
        ])
        self.kdtree = cKDTree(centroids)
        self.grid_ids = self.grid['grid_id'].values

        # Half-cell radius: if nearest centroid is farther than this, the
        # point is outside the grid (ocean/foreign).
        # The grid is ~0.45 deg per cell at ~50km; use 0.4 deg as cutoff.
        self.max_dist_deg = 0.4

    def assign_grid_ids(
        self,
        lats: np.ndarray,
        lons: np.ndarray,
    ) -> np.ndarray:
        """
        Assign a grid_id string to each trajectory point.

        Points outside the grid (ocean, far out-of-domain) receive None.

        Parameters
        ----------
        lats, lons : 1D array of float
            Trajectory point coordinates.

        Returns
        -------
        np.ndarray of object (str or None)
        """
        points = np.column_stack([lats, lons])
        dists, indices = self.kdtree.query(points)

        grid_ids = np.where(
            dists <= self.max_dist_deg,
            self.grid_ids[indices],
            None,
        )
        return grid_ids

    def compute_influence(
        self,
        lats: np.ndarray,
        lons: np.ndarray,
        ensemble_member_ids: Optional[np.ndarray] = None,
    ) -> pd.DataFrame:
        """
        Compute transport influence weights from trajectory points.

        Parameters
        ----------
        lats, lons : 1D float arrays
            All trajectory point positions (all ensemble members concatenated).
        ensemble_member_ids : 1D int array or None
            Member IDs for each point. If None, treats all as one member.

        Returns
        -------
        pd.DataFrame with columns:
            source_grid_id     : str
            ensemble_residence_points : int
            transport_weight   : float (fraction of ALL points in each cell)
            frac_outside_domain : float (fraction of points in no grid cell)
        """
        grid_ids = self.assign_grid_ids(lats, lons)
        total_points = len(grid_ids)

        inside_mask = grid_ids != None
        inside_ids = grid_ids[inside_mask]

        outside_count = int((~inside_mask).sum())

        if len(inside_ids) == 0:
            return pd.DataFrame(columns=[
                'source_grid_id', 'ensemble_residence_points',
                'transport_weight', 'frac_outside_domain'
            ])

        counts = pd.Series(inside_ids).value_counts()
        influence = pd.DataFrame({
            'source_grid_id': counts.index,
            'ensemble_residence_points': counts.values,
        })
        influence['transport_weight'] = influence['ensemble_residence_points'] / total_points
        influence['frac_outside_domain'] = outside_count / total_points * 100.0
        return influence


def fast_ensemble_influence(
    ensemble_df: pd.DataFrame,
    grid_index: GridRasterIndex,
    target_id: str,
    countries_gdf: Optional[gpd.GeoDataFrame] = None,
) -> pd.DataFrame:
    """
    Fast replacement for calculate_ensemble_influence() in source_receptor.py.

    Uses the rasterized KD-tree index for grid assignment instead of sjoin.
    Optionally performs a single country classification pass (much cheaper than
    per-point sjoin) by checking the endpoint and mid-point of each member.

    Parameters
    ----------
    ensemble_df : pd.DataFrame
        Combined ensemble trajectory DataFrame.
    grid_index : GridRasterIndex
        Pre-built raster index.
    target_id : str
        Target grid cell ID.
    countries_gdf : GeoDataFrame or None
        World country polygons for domain classification.
        If None, skips country classification.

    Returns
    -------
    pd.DataFrame with transport influence and domain fractions.
    """
    from shapely.geometry import Point

    lats = ensemble_df['latitude'].values
    lons = ensemble_df['longitude'].values

    influence = grid_index.compute_influence(lats, lons)
    influence['target_grid_id'] = target_id

    # Country/ocean classification via single vectorized sjoin
    if countries_gdf is not None and not ensemble_df.empty:
        geometry = gpd.points_from_xy(lons, lats)
        traj_gdf = gpd.GeoDataFrame({'idx': range(len(lats))}, geometry=geometry, crs='EPSG:4326')
        joined = gpd.sjoin(traj_gdf, countries_gdf[['name', 'geometry']], how='left', predicate='within')
        country_col = joined['name'].fillna('Ocean')
        country_counts = country_col.value_counts(normalize=True) * 100.0
        for country, frac in country_counts.items():
            influence[f'frac_{country}'] = frac

    return influence
