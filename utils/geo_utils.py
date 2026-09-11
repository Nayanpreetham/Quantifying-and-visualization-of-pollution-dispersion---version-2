"""
Geographic utilities for distance, bearing, and coordinate conversions.
"""

import numpy as np

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate great-circle distance between two points in kilometers.
    """
    R = 6371.0  # Earth radius in km
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)

    a = np.sin(dphi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

def bearing_to_station(lat1, lon1, lat2, lon2):
    """
    Calculate initial bearing from point 1 (target) to point 2 (station).
    Returns degrees (0-360, clockwise from North).
    """
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dlambda = np.radians(lon2 - lon1)

    x = np.sin(dlambda) * np.cos(phi2)
    y = np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlambda)

    bearing = np.degrees(np.arctan2(x, y))
    return (bearing + 360) % 360

def wind_alignment_weight(wind_dir, bearing_to_station):
    """
    Calculate wind transport alignment weight.
    wind_dir: direction wind blows FROM (meteorological convention, 0-360°)
    bearing_to_station: direction from target TO station (0-360°)

    Returns weight where:
      - Positive (~1) = upwind (station pollution blows toward target)
      - Negative (~-1) = downwind
      - Near 0 = crosswind
    """
    delta = (wind_dir - bearing_to_station + 180) % 360 - 180  # [-180, 180]
    weight = np.cos(np.radians(delta))
    return weight

def get_wind_relation(wind_dir, bearing_to_station):
    """
    Return text classification of wind relation.
    """
    delta = (wind_dir - bearing_to_station + 180) % 360 - 180
    abs_delta = abs(delta)

    if abs_delta <= 45:
        return "UPWIND"
    elif abs_delta >= 135:
        return "DOWNWIND"
    else:
        return "CROSS"

def bearing_to_compass(bearing):
    """
    Convert bearing in degrees to compass direction (e.g., '225° SW').
    """
    compass_points = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    idx = int((bearing + 22.5) // 45) % 8
    return f"{bearing:.0f}° {compass_points[idx]}"