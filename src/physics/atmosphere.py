import math

def pressure_to_altitude_isa(pressure_hpa):
    """
    Converts atmospheric pressure (hPa) to altitude (meters) above mean sea level (ASL)
    using the International Standard Atmosphere (ISA) barometric formula for the troposphere.
    
    P = P0 * (1 - L*h / T0) ** (g * M / (R * L))
    where:
    P0 = 1013.25 hPa
    T0 = 288.15 K
    L = 0.0065 K/m (temperature lapse rate)
    g = 9.80665 m/s^2
    M = 0.0289644 kg/mol (molar mass of Earth's air)
    R = 8.3144598 J/(mol*K)
    
    h = (T0 / L) * (1 - (pressure_hpa / P0) ** (R * L / (g * M)))
    """
    P0 = 1013.25
    if pressure_hpa <= 0:
        return float('nan')
    
    # 288.15 / 0.0065 = 44330.769
    # (R * L) / (g * M) = 0.190263
    
    altitude_m = 44330.77 * (1 - (pressure_hpa / P0) ** 0.190263)
    return altitude_m

def altitude_to_pressure_isa(altitude_m):
    """
    Converts altitude (meters ASL) to pressure (hPa) using ISA.
    """
    P0 = 1013.25
    pressure_hpa = P0 * (1 - (altitude_m / 44330.77)) ** (1 / 0.190263)
    return pressure_hpa
