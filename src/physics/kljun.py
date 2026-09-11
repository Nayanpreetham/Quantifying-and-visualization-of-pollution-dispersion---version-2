import numpy as np
import warnings

def kljun_ffp(zm, z0, u_mean, h, L, sigma_v, u_star, x, y):
    """
    Simplified Kljun Flux Footprint Prediction (FFP) parameterization (Kljun et al., 2015).
    Evaluates the footprint function f(x,y) for a single receptor.
    
    Parameters:
    zm: Measurement height (receptor height) [m]
    z0: Roughness length [m]
    u_mean: Mean wind speed at zm [m/s]
    h: Boundary layer height [m]
    L: Obukhov length [m]
    sigma_v: Standard deviation of lateral wind velocity [m/s]
    u_star: Friction velocity [m/s]
    x: downwind distance from receptor [m]
    y: crosswind distance from receptor [m]
    
    Returns:
    f: footprint contribution at (x,y)
    flag: validity flag (1 = valid, 0 = outside validity range)
    """
    # Validity checks according to Kljun et al. (2015)
    flag = 1
    if zm < 20 * z0: flag = 0
    if h < 10: flag = 0
    if zm > h: flag = 0
    
    # Kljun parameters
    a = 1.4524
    b = -1.9914
    c = 1.4622
    d = 0.1359
    
    # Scaled parameters
    z_star = zm / h
    
    if L > 0: # Stable
        L_star = L / h
        if L_star < 0.1: flag = 0 # Very stable
    else: # Unstable
        pass # L < 0 is fine
        
    # Simplified crosswind dispersion
    sigma_y = sigma_v * (x / u_mean)
    sigma_y = np.maximum(sigma_y, 0.001)
    
    # 1D Crosswind-integrated footprint (simplified approximation for FFP)
    # Using the Kljun scaling variables
    X = (x * u_star) / (u_mean * zm)
    
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        # Avoid division by zero
        X = np.maximum(X, 1e-6)
        
        # Main F_y integrated function
        Fy = (a / X**2) * np.exp(b / X) * np.exp(-c * X)
        
        # 2D Footprint 
        f = (Fy / (np.sqrt(2 * np.pi) * sigma_y)) * np.exp(- (y**2) / (2 * sigma_y**2))
    
    # Set upwind footprint to zero
    f = np.where(x <= 0, 0, f)
    # Filter nan/inf
    f = np.nan_to_num(f, posinf=0, neginf=0)
    
    return f, flag
