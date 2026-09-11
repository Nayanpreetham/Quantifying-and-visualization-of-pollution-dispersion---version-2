"""
Source Category Weighting Interface
=====================================
Provides the framework for weighting transport influence by source category.

This module defines the interface for source-category data and implements the
source-influence index calculation:

    SourceInfluence(target, source, t) =
        TransportFootprint(target, source, t)   [from ensemble trajectories]
        * SourceStrength(source, category, t)    [from emissions inventory]
        * PeriodicDisturbance(t)                 [from periodic_disturbance.py]

IMPORTANT: The source-category emissions inventory is NOT currently available
in this repository. The functions in this module will work correctly only if
emissions data are provided in the required format.

If emissions data are unavailable, the system falls back to TRANSPORT-ONLY mode,
meaning the output represents trajectory-based transport influence only, NOT
emission-weighted source influence.

Required emissions format
--------------------------
A CSV or NetCDF file with columns:
    grid_id        : 50-km grid cell identifier (e.g. 'IND_047_021')
    category       : source category name (see CATEGORIES below)
    year           : integer year
    month          : integer month (1-12) or None for annual
    value          : emission rate in µg/m2/s or similar consistent unit
    unit           : string describing the unit
    pollutant      : e.g. 'PM2.5', 'PM10'

Recommended data sources (NOT yet downloaded):
    - IIASA GAINS India inventory (https://gains.iiasa.ac.at)
    - CAMS-REG / CAMS-GLOB inventory
    - EDGAR v7 (https://edgar.jrc.ec.europa.eu)
    - India NATCOM emission inventories

Current status: PLACEHOLDER INTERFACE ONLY.
"""

import pandas as pd
import numpy as np
import os
from typing import Optional, Dict

# Canonical source category names
CATEGORIES = [
    'power_generation',
    'industry',
    'transport',
    'residential',
    'agriculture',
    'crop_residue_burning',
    'waste_burning',
    'dust',
    'other',
]

# Default equal weights (used when no emissions data are available)
UNIFORM_WEIGHTS = {cat: 1.0 / len(CATEGORIES) for cat in CATEGORIES}


class SourceCategoryWeighter:
    """
    Manages source-category emission strength data and applies it to
    transport influence estimates.

    In the absence of emissions data, operates in TRANSPORT_ONLY mode.
    """

    def __init__(self, emissions_file: Optional[str] = None):
        self.mode = 'TRANSPORT_ONLY'
        self.emissions: Optional[pd.DataFrame] = None

        if emissions_file and os.path.exists(emissions_file):
            self._load_emissions(emissions_file)
        else:
            print(
                "[SourceCategoryWeighter] WARNING: No emissions file provided or found. "
                "Operating in TRANSPORT_ONLY mode. Output represents transport influence "
                "only, NOT emission-weighted source influence."
            )

    def _load_emissions(self, path: str):
        required_cols = {'grid_id', 'category', 'value', 'pollutant'}
        if path.endswith('.csv'):
            df = pd.read_csv(path)
        elif path.endswith(('.nc', '.netcdf')):
            import xarray as xr
            df = xr.open_dataset(path).to_dataframe().reset_index()
        else:
            raise ValueError(f"Unsupported emissions file format: {path}")

        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Emissions file missing required columns: {missing}")

        # Validate categories
        unknown = set(df['category'].unique()) - set(CATEGORIES)
        if unknown:
            print(f"[SourceCategoryWeighter] Unknown categories in emissions file: {unknown}")

        self.emissions = df
        self.mode = 'EMISSION_WEIGHTED'
        print(
            f"[SourceCategoryWeighter] Loaded emissions: {len(df)} records, "
            f"pollutants: {df['pollutant'].unique().tolist()}, "
            f"categories: {df['category'].unique().tolist()}"
        )

    def get_grid_emission_strength(
        self,
        grid_id: str,
        pollutant: str = 'PM2.5',
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Returns emission strength by category for a given grid cell.

        Parameters
        ----------
        grid_id : str
            50-km grid cell identifier.
        pollutant : str
            Pollutant name.
        year, month : int or None
            Temporal filter. If None, uses annual average.

        Returns
        -------
        dict
            {category_name: emission_value} for all categories.
            Returns zeros for missing categories.
            In TRANSPORT_ONLY mode, returns a dict of uniform NaN values
            to signal that weighting cannot be applied.
        """
        if self.mode == 'TRANSPORT_ONLY':
            return {cat: float('nan') for cat in CATEGORIES}

        mask = (self.emissions['grid_id'] == grid_id) & \
               (self.emissions['pollutant'] == pollutant)
        if year is not None and 'year' in self.emissions.columns:
            mask &= (self.emissions['year'] == year)
        if month is not None and 'month' in self.emissions.columns:
            mask &= (self.emissions['month'] == month)

        sub = self.emissions[mask]
        result = {cat: 0.0 for cat in CATEGORIES}
        for _, row in sub.iterrows():
            cat = row['category']
            if cat in result:
                result[cat] = float(row['value'])
        return result

    def apply_emission_weighting(
        self,
        influence_df: pd.DataFrame,
        pollutant: str = 'PM2.5',
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Apply source-category emission weighting to a transport influence DataFrame.

        In TRANSPORT_ONLY mode, adds 'emission_mode' = 'TRANSPORT_ONLY' and
        'source_influence_index' = transport_weight (no emission multiplication).

        In EMISSION_WEIGHTED mode, adds per-category columns and computes:
            source_influence_index = transport_weight * total_emission_strength

        Parameters
        ----------
        influence_df : pd.DataFrame
            Output of calculate_ensemble_influence(). Must have 'source_grid_id'
            and 'transport_weight'.

        Returns
        -------
        pd.DataFrame with additional columns.
        """
        if influence_df.empty:
            return influence_df

        out = influence_df.copy()
        out['emission_mode'] = self.mode

        if self.mode == 'TRANSPORT_ONLY':
            # Source influence index equals transport weight only.
            # This is transport influence, NOT emission-weighted source influence.
            out['source_influence_index'] = out['transport_weight']
            for cat in CATEGORIES:
                out[f'emission_{cat}'] = float('nan')
            return out

        # Emission-weighted mode
        emission_rows = []
        for _, row in out.iterrows():
            gid = row['source_grid_id']
            em = self.get_grid_emission_strength(gid, pollutant, year, month)
            emission_rows.append(em)

        em_df = pd.DataFrame(emission_rows, index=out.index)
        for cat in CATEGORIES:
            out[f'emission_{cat}'] = em_df.get(cat, 0.0)

        out['total_emission_strength'] = em_df.sum(axis=1)
        out['source_influence_index'] = out['transport_weight'] * out['total_emission_strength']

        # Normalize to sum to 1 over source cells
        total = out['source_influence_index'].sum()
        if total > 0:
            out['source_influence_fraction'] = out['source_influence_index'] / total
        else:
            out['source_influence_fraction'] = 0.0

        return out


def compute_source_influence_report(
    target_id: str,
    timestamp: pd.Timestamp,
    influence_df: pd.DataFrame,
    weighter: SourceCategoryWeighter,
    disturbance_factor: float = 1.0,
    pollutant: str = 'PM2.5',
) -> dict:
    """
    Produce the final source-influence report for a target/time.

    Returns a dict suitable for display or serialization containing:
    - Top 5 source grid cells with transport influence fraction
    - India/Foreign/Ocean fractions
    - Source category breakdown (if emissions available)
    - Disturbance factor
    - Mode (TRANSPORT_ONLY or EMISSION_WEIGHTED)

    IMPORTANT: Do NOT call this output 'pollution contribution'.
    Call it 'transport-weighted source influence index'.
    """
    if influence_df.empty:
        return {'target': target_id, 'timestamp': str(timestamp), 'error': 'No influence data'}

    weighted = weighter.apply_emission_weighting(influence_df, pollutant)
    weighted = weighted.sort_values('source_influence_index', ascending=False).reset_index(drop=True)

    top5 = weighted.head(5)[['source_grid_id', 'transport_weight', 'source_influence_index']].to_dict('records')

    # Collect domain fractions (these are on all rows identically)
    domain_keys = [c for c in influence_df.columns if c.startswith('frac_')]
    domain_fracs = {}
    if not influence_df.empty:
        for k in domain_keys:
            domain_fracs[k] = float(influence_df[k].iloc[0])

    # Category aggregation (sum across all source grids, weighted by transport)
    category_totals = {}
    if weighter.mode == 'EMISSION_WEIGHTED':
        for cat in CATEGORIES:
            col = f'emission_{cat}'
            if col in weighted.columns:
                # Weighted sum: transport_weight * emission_category
                cat_weighted = (weighted['transport_weight'] * weighted[col]).sum()
                category_totals[cat] = float(cat_weighted)

    return {
        'target': target_id,
        'timestamp': str(timestamp),
        'mode': weighter.mode,
        'disturbance_factor': disturbance_factor,
        'top5_sources': top5,
        'domain_fractions': domain_fracs,
        'category_influence': category_totals,
        'n_source_cells': len(weighted),
        'pollutant': pollutant,
    }
