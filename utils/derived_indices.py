"""
Compute derived indices from base meteorological variables.
These MUST match the formulas used in the training dataset.
"""

import numpy as np

def compute_derived_indices(t2m, wind_speed, blh, elevation_m, sp_hpa, tp_mm):
    """
    Compute all derived indices from base variables.

    IMPORTANT: These formulas are based on common definitions.
    Verify they match exactly how your training data was created.
    """
    # Avoid division by zero
    blh_safe = max(blh, 1.0)

    # Elevation to Boundary Layer Height ratio
    elevation_pblh_ratio = elevation_m / blh_safe

    # Ventilation Index (wind_speed * boundary layer height)
    ventilation_index = wind_speed * blh_safe

    # Stagnation Index - inverse of ventilation
    stagnation_index = 1.0 / (ventilation_index + 1e-6)

    # Dispersion Potential - related to ventilation
    dispersion_potential = ventilation_index / 1000.0  # scaled

    # Terrain Blocking Score - based on elevation and wind
    # Higher elevation + lower wind = more blocking
    terrain_blocking_score = (elevation_m / 1000.0) / (wind_speed + 0.5)

    return {
        'elevation_pblh_ratio': elevation_pblh_ratio,
        'ventilation_index': ventilation_index,
        'stagnation_index': stagnation_index,
        'dispersion_potential': dispersion_potential,
        'terrain_blocking_score': terrain_blocking_score
    }