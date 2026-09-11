"""
Periodic Disturbance Representation
====================================
Implements a sinusoidal formulation of recurring temporal disturbances
in the source/influence signal.

The model uses superimposed sine and cosine components to represent:
  - Annual cycle (seasonal variation in emissions and meteorology)
  - Diurnal cycle (day/night variation in boundary layer and traffic)
  - Known event perturbations (festivals, harvest burning)

The combined periodic disturbance factor D(t) modulates the source-influence
calculation as:

    SourceInfluence(target, source, t) = 
        TransportFootprint(target, source, t)
        * SourceStrength(source, t)
        * D(source, t)

where D(t) is bounded such that it amplifies or dampens the base influence
but does not produce physically impossible values.

Mathematical formulation:
    D(t) = 1 + sum_k [ A_k * sin(2*pi*t/P_k + phi_k) ]

where:
    A_k    = amplitude of k-th harmonic (dimensionless, 0 < A_k < 1)
    P_k    = period in hours
    phi_k  = phase offset in radians
    t      = elapsed hours from a reference time

The result is bounded to [D_min, D_max] to ensure physical plausibility.
"""

import numpy as np
import pandas as pd
from typing import Optional

# Period constants
PERIOD_ANNUAL_H = 365.25 * 24.0     # 8766 hours
PERIOD_DIURNAL_H = 24.0              # 24 hours
PERIOD_WEEKLY_H = 7.0 * 24.0         # 168 hours

# Reference epoch: 2020-01-01 00:00 UTC
REFERENCE_EPOCH = pd.Timestamp('2020-01-01T00:00:00', tz='UTC')


def compute_periodic_disturbance(
    timestamp: pd.Timestamp,
    # Annual cycle parameters
    annual_amplitude: float = 0.30,
    annual_phase_rad: float = 3.665,  # ~Dec peak (winter pollution maximum)
    # Diurnal cycle parameters
    diurnal_amplitude: float = 0.15,
    diurnal_phase_rad: float = 5.760,  # ~morning rush peak (~07:00 local)
    # Weekly cycle parameters (optional)
    weekly_amplitude: float = 0.05,
    weekly_phase_rad: float = 0.0,
    # Event perturbation (additive, from events lookup)
    event_perturbation: float = 0.0,
    # Bounds
    d_min: float = 0.5,
    d_max: float = 2.5,
) -> float:
    """
    Compute the dimensionless periodic disturbance factor D(t) for a given timestamp.

    Parameters
    ----------
    timestamp : pd.Timestamp
        The evaluation time (timezone-aware or naive UTC).
    annual_amplitude : float
        Amplitude of the annual sinusoidal cycle (default 0.30).
        Represents seasonal emission/dispersion variation (e.g., winter stagnation).
    annual_phase_rad : float
        Phase offset for the annual component in radians.
        Default ~3.665 rad places the maximum near December (Northern India winter).
    diurnal_amplitude : float
        Amplitude of the diurnal cycle (default 0.15).
        Represents boundary-layer/traffic diurnal variation.
    diurnal_phase_rad : float
        Phase offset for the diurnal component in radians.
        Default ~5.760 rad places peak near 07:00 UTC+5:30 (morning rush).
    weekly_amplitude : float
        Amplitude of the weekly cycle (default 0.05).
    weekly_phase_rad : float
        Phase offset for the weekly component.
    event_perturbation : float
        Additive perturbation from known events (e.g. +0.5 for Diwali).
        Must be supplied by the caller via the events calendar.
    d_min, d_max : float
        Bounds on the output factor.

    Returns
    -------
    float
        D(t) in [d_min, d_max].

    Notes
    -----
    The amplitudes and phases are configurable. The defaults are scientifically
    motivated estimates for Northern India but should be calibrated against
    observed AQI data before production use.

    This is documented as an initial-condition ensemble approach, NOT a
    statistically calibrated parameterization. Do NOT interpret D(t) as a
    physically derived atmospheric quantity without calibration.
    """
    if timestamp.tzinfo is None:
        ts_utc = timestamp.tz_localize('UTC')
    else:
        ts_utc = timestamp.tz_convert('UTC')

    elapsed_h = (ts_utc - REFERENCE_EPOCH).total_seconds() / 3600.0

    annual = annual_amplitude * np.sin(
        2 * np.pi * elapsed_h / PERIOD_ANNUAL_H + annual_phase_rad
    )
    diurnal = diurnal_amplitude * np.sin(
        2 * np.pi * elapsed_h / PERIOD_DIURNAL_H + diurnal_phase_rad
    )
    weekly = weekly_amplitude * np.sin(
        2 * np.pi * elapsed_h / PERIOD_WEEKLY_H + weekly_phase_rad
    )

    D = 1.0 + annual + diurnal + weekly + event_perturbation
    D = float(np.clip(D, d_min, d_max))
    return D


def compute_event_perturbation(
    timestamp: pd.Timestamp,
    events_file: str = 'data/raw/events/india_festivals.csv',
    window_hours: int = 24,
    event_amplitude: float = 0.5,
) -> float:
    """
    Look up whether the timestamp falls within a known event window.
    Returns an additive perturbation to be passed to compute_periodic_disturbance().

    Parameters
    ----------
    timestamp : pd.Timestamp
        Evaluation timestamp.
    events_file : str
        Path to the festival/event calendar CSV.
    window_hours : int
        How many hours around the event date to consider as the event window.
    event_amplitude : float
        Additive perturbation when inside an event window (default 0.5).

    Returns
    -------
    float
        Additive event perturbation (0.0 if no event detected).
    """
    import os
    if not os.path.exists(events_file):
        return 0.0

    events = pd.read_csv(events_file)
    if 'date' not in events.columns:
        return 0.0

    events['date'] = pd.to_datetime(events['date'], errors='coerce')
    
    if timestamp.tzinfo is None:
        ts_naive = timestamp
    else:
        ts_naive = timestamp.tz_localize(None) if hasattr(timestamp, 'tz_localize') else timestamp.replace(tzinfo=None)

    window = pd.Timedelta(hours=window_hours)
    for _, row in events.iterrows():
        event_dt = row['date']
        if pd.isna(event_dt):
            continue
        if abs(ts_naive - event_dt) <= window:
            return event_amplitude

    return 0.0


def apply_periodic_disturbance_to_influence(
    influence_df: pd.DataFrame,
    timestamp: pd.Timestamp,
    events_file: str = 'data/raw/events/india_festivals.csv',
    **disturbance_kwargs,
) -> pd.DataFrame:
    """
    Apply the periodic disturbance factor D(t) to a source-influence DataFrame.

    The influence_df must contain a 'transport_weight' column. This function
    adds a 'disturbance_factor' column and a 'transport_influence_weighted'
    column that is the product:

        transport_influence_weighted = transport_weight * D(t)

    IMPORTANT: The disturbance factor is UNIFORM across all source cells
    for a given target/time — it modulates the overall signal magnitude,
    not the relative spatial distribution. If spatially varying disturbances
    are needed (e.g., regional crop burning), they must be implemented as
    source-category weights, not as D(t).

    Parameters
    ----------
    influence_df : pd.DataFrame
        Output of calculate_ensemble_influence(), must have 'transport_weight'.
    timestamp : pd.Timestamp
        Evaluation timestamp.
    events_file : str
        Path to events CSV.

    Returns
    -------
    pd.DataFrame
        influence_df with two new columns added.
    """
    if influence_df.empty or 'transport_weight' not in influence_df.columns:
        return influence_df

    event_amp = compute_event_perturbation(timestamp, events_file)
    D = compute_periodic_disturbance(timestamp, event_perturbation=event_amp, **disturbance_kwargs)

    out = influence_df.copy()
    out['disturbance_factor'] = D
    out['transport_influence_weighted'] = out['transport_weight'] * D
    return out
