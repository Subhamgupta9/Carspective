"""
CARspective — Phase 4 Empirical Deal Analyzer & Anomaly Threshold Study
Investigates:
1. Empirical ratio of asking_price / estimated_fair_value (y / y_hat)
2. Relative residual distribution (y - y_hat) / y_hat
3. Log-price residual distribution ln(y) - ln(y_hat)
4. Robust Z-score (median and MAD)
5. Comparison of candidate anomaly detection methods for UNUSUALLY LOW ASKING PRICE
6. Segment-wise breakdown (Budget, Mass-Market, Mid-Premium, Luxury)
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from scipy import stats

CURRENT_YEAR = 2026
MODEL_PATH = os.path.join("models", "carspective_valuation_lgbm_v1.joblib")
DATA_PATH = os.path.join("data", "raw", "indian_used_cars_raw_57480.csv")

def main():
    print("Loading dataset and model...")
    df = pd.read_csv(DATA_PATH)
    pipeline = joblib.load(MODEL_PATH)
    
    # Feature preparation
    df['km_driven'] = df['km_driven'].astype(str).str.replace(',', '').str.strip()
    df['km_driven'] = pd.to_numeric(df['km_driven'], errors='coerce').fillna(60000.0)
    df['fuel_type'] = df['fuel_type'].fillna('Petrol')
    df.loc[df['bodytype'] == '15', 'bodytype'] = 'Hatchback'
    df['manufacturing_year'] = pd.to_numeric(df['manufacturing_year'], errors='coerce').fillna(2018).astype(int)
    df['vehicle_age'] = np.maximum(0, CURRENT_YEAR - df['manufacturing_year'])
    df['log_km_driven'] = np.log1p(df['km_driven'])
    df['price'] = pd.to_numeric(df['price'], errors='coerce').astype(float)
    
    # Stratified/seeded split to match Phase 3 test set
    from sklearn.model_selection import train_test_split
    train_df, test_df = train_test_split(df, test_size=0.20, random_state=42)
    
    # Inference on test set
    features = [
        "manufacturing_year", "km_driven", "number_of_owners", "vehicle_age", "log_km_driven",
        "model", "fuel_type", "transmission_type", "brand", "city", "bodytype"
    ]
    
    print(f"Generating predictions on test set ({len(test_df)} samples)...")
    y_test_actual = test_df['price'].values
    log_preds = pipeline.predict(test_df[features])
    y_test_pred = np.maximum(15000.0, np.expm1(log_preds))
    
    # Analysis metrics
    # 1. Price ratio: actual asking price / estimated fair value
    ratio = y_test_actual / y_test_pred
    
    # 2. Relative deviation: (actual - pred) / pred
    rel_dev = (y_test_actual - y_test_pred) / y_test_pred
    
    # 3. Log residual: ln(actual) - ln(pred)
    log_res = np.log(y_test_actual) - np.log(y_test_pred)
    
    # 4. Robust z-score of log residual
    med_log = np.median(log_res)
    mad_log = stats.median_abs_deviation(log_res, scale='normal')
    robust_z_log = (log_res - med_log) / (mad_log if mad_log > 0 else 1.0)
    
    # 5. Robust z-score of ratio
    med_ratio = np.median(ratio)
    mad_ratio = stats.median_abs_deviation(ratio, scale='normal')
    robust_z_ratio = (ratio - med_ratio) / (mad_ratio if mad_ratio > 0 else 1.0)
    
    # Percentiles of ratio
    percentiles = [0.1, 0.5, 1.0, 2.0, 2.5, 5.0, 10.0, 20.0, 50.0, 80.0, 90.0, 95.0, 97.5, 99.0, 99.5, 99.9]
    ratio_percentiles = {f"p{p}": float(np.percentile(ratio, p)) for p in percentiles}
    rel_dev_percentiles = {f"p{p}": float(np.percentile(rel_dev, p)) for p in percentiles}
    
    print("\n--- RATIO PERCENTILES (Actual Asking / Model Fair Value) ---")
    for k, v in ratio_percentiles.items():
        print(f"  {k}: {v:.4f} (Dev: {(v-1)*100:+.2f}%)")
        
    # Phase 3 calibrated conformal range:
    # lower_bound = pred * (1 - 0.217834) = pred * 0.782166 (ratio = 0.7822)
    # upper_bound = pred * (1 + 0.217834) = pred * 1.217834 (ratio = 1.2178)
    in_range = (ratio >= 0.782166) & (ratio <= 1.217834)
    below_range = (ratio < 0.782166)
    above_range = (ratio > 1.217834)
    
    print("\n--- FAIR MARKET RANGE COVERAGE (80% Conformal) ---")
    print(f"  Inside Range (0.7822 <= ratio <= 1.2178): {np.mean(in_range)*100:.2f}% ({np.sum(in_range)} cars)")
    print(f"  Below Range (ratio < 0.7822): {np.mean(below_range)*100:.2f}% ({np.sum(below_range)} cars)")
    print(f"  Above Range (ratio > 1.2178): {np.mean(above_range)*100:.2f}% ({np.sum(above_range)} cars)")
    
    # Now let's examine candidates for UNUSUALLY LOW ASKING PRICE within the below-range population:
    # Candidate A: Conformal extreme lower quantile (e.g. 99% coverage lower bound or 99.5%)
    # Let's check 99% conformal bound:
    q_99 = float(np.percentile(np.abs(rel_dev), 99.0))
    # Or purely directional lower tail percentiles:
    p1_ratio = float(np.percentile(ratio, 1.0)) # 1st percentile of ratio
    p05_ratio = float(np.percentile(ratio, 0.5)) # 0.5th percentile
    p25_ratio = float(np.percentile(ratio, 2.5)) # 2.5th percentile
    
    # Candidate B: Robust Z-Score threshold (e.g., robust_z < -2.5 or -3.0)
    # Candidate C: Log-price residual threshold: log_res < -0.45 or -0.50
    # Candidate D: Direct empirical ratio threshold: e.g. ratio < 0.65 (-35% from fair value)
    
    methods_evaluation = {}
    
    # Method 1: Directional Tail Percentile (1st percentile: ~1% of dataset)
    mask_p1 = ratio < p1_ratio
    methods_evaluation["Directional_1st_Percentile"] = {
        "threshold_ratio": p1_ratio,
        "implied_discount_percent": float((1 - p1_ratio) * 100),
        "flagged_count": int(np.sum(mask_p1)),
        "flagged_percent": float(np.mean(mask_p1) * 100)
    }
    
    # Method 2: Robust Z-score < -2.5 on log residuals
    mask_rz25 = robust_z_log < -2.5
    methods_evaluation["Robust_Z_Score_Log_2.5"] = {
        "cutoff_z": -2.5,
        "flagged_count": int(np.sum(mask_rz25)),
        "flagged_percent": float(np.mean(mask_rz25) * 100),
        "max_ratio_flagged": float(np.max(ratio[mask_rz25])) if np.sum(mask_rz25) > 0 else 0.0
    }
    
    # Method 3: Robust Z-score < -3.0 on log residuals
    mask_rz30 = robust_z_log < -3.0
    methods_evaluation["Robust_Z_Score_Log_3.0"] = {
        "cutoff_z": -3.0,
        "flagged_count": int(np.sum(mask_rz30)),
        "flagged_percent": float(np.mean(mask_rz30) * 100),
        "max_ratio_flagged": float(np.max(ratio[mask_rz30])) if np.sum(mask_rz30) > 0 else 0.0
    }
    
    # Method 4: Calibrated Conformal 99% Lower Bound
    # r = |y - y_hat| / y_hat; 99th percentile residual is q_99
    # lower 99% bound = 1 - q_99
    conformal_lower_99_ratio = 1.0 - q_99
    mask_conf99 = ratio < conformal_lower_99_ratio
    methods_evaluation["Conformal_99pct_Lower_Bound"] = {
        "q_99_residual": q_99,
        "implied_ratio_threshold": conformal_lower_99_ratio,
        "implied_discount_percent": float(q_99 * 100),
        "flagged_count": int(np.sum(mask_conf99)),
        "flagged_percent": float(np.mean(mask_conf99) * 100)
    }
    
    # Method 5: Dual Condition: Below Conformal 80% Range AND (ratio < 0.65 OR robust_z < -2.5)
    # Let's inspect ratio < 0.65 (35% below fair value)
    mask_ratio_65 = ratio < 0.65
    methods_evaluation["Relative_Ratio_Below_0.65"] = {
        "threshold_ratio": 0.65,
        "implied_discount_percent": 35.0,
        "flagged_count": int(np.sum(mask_ratio_65)),
        "flagged_percent": float(np.mean(mask_ratio_65) * 100)
    }

    # Method 6: Ratio < 0.60 (40% below fair value)
    mask_ratio_60 = ratio < 0.60
    methods_evaluation["Relative_Ratio_Below_0.60"] = {
        "threshold_ratio": 0.60,
        "implied_discount_percent": 40.0,
        "flagged_count": int(np.sum(mask_ratio_60)),
        "flagged_percent": float(np.mean(mask_ratio_60) * 100)
    }
    
    print("\n--- ANOMALY DETECTION CANDIDATE METHODS ---")
    print(json.dumps(methods_evaluation, indent=2))
    
    # Segment-wise analysis of ratio
    segments = [
        ("Budget (< 3L)", test_df['price'] < 300000),
        ("Mass-Market (3L-8L)", (test_df['price'] >= 300000) & (test_df['price'] < 800000)),
        ("Mid-Premium (8L-15L)", (test_df['price'] >= 800000) & (test_df['price'] < 1500000)),
        ("Luxury (> 15L)", test_df['price'] >= 1500000)
    ]
    
    segment_results = {}
    for seg_name, mask in segments:
        sub_ratio = ratio[mask]
        segment_results[seg_name] = {
            "count": int(np.sum(mask)),
            "median_ratio": float(np.median(sub_ratio)),
            "p1_ratio": float(np.percentile(sub_ratio, 1.0)),
            "p5_ratio": float(np.percentile(sub_ratio, 5.0)),
            "p10_ratio": float(np.percentile(sub_ratio, 10.0)),
            "p90_ratio": float(np.percentile(sub_ratio, 90.0)),
            "in_80_range_pct": float(np.mean((sub_ratio >= 0.782166) & (sub_ratio <= 1.217834)) * 100),
            "below_0.65_pct": float(np.mean(sub_ratio < 0.65) * 100),
            "below_0.60_pct": float(np.mean(sub_ratio < 0.60) * 100)
        }
        
    print("\n--- SEGMENT-WISE ANALYSIS ---")
    print(json.dumps(segment_results, indent=2))
    
    # Save complete study report to data/ml_benchmarks
    os.makedirs(os.path.join("data", "ml_benchmarks"), exist_ok=True)
    report_path = os.path.join("data", "ml_benchmarks", "phase4_empirical_threshold_study.json")
    with open(report_path, "w") as f:
        json.dump({
            "test_sample_size": len(test_df),
            "conformal_80_bounds": {"lower_ratio": 0.782166, "upper_ratio": 1.217834},
            "ratio_percentiles": ratio_percentiles,
            "rel_dev_percentiles": rel_dev_percentiles,
            "methods_evaluation": methods_evaluation,
            "segment_results": segment_results,
            "log_residual_stats": {
                "median": med_log,
                "mad_normal_scale": mad_log
            }
        }, f, indent=2)
    print(f"\nSaved empirical report to {report_path}")

if __name__ == "__main__":
    main()
