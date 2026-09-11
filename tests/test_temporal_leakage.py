import pandas as pd
import sys

def test_temporal_leakage():
    try:
        contrib = pd.read_csv('data/processed/contributions/contributions_IND_047_021.csv')
    except Exception as e:
        print("Contributions not found. Run contribution.py first.")
        sys.exit(1)
        
    max_baseline = contrib['baseline_pollution_indicator'].max()
    
    # Since our mock data is from 2020-11, and we query 2020-01, 
    # strictly -1$ year or past data is NOT available. The fallback logic should return 0.
    if max_baseline > 0:
        print(f"TEMPORAL LEAKAGE DETECTED! Future data was used. Baseline is {max_baseline}")
        sys.exit(1)
        
    print("NO TEMPORAL LEAKAGE DETECTED. Baseline correctly isolated.")

if __name__ == '__main__':
    test_temporal_leakage()
