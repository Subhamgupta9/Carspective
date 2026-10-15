"""
CARspective — Phase 3: Production Artifact Creation & Integrity Manifest
Packages the winning LightGBM model, computes SHA-256 checksums, and creates trusted manifest.
"""

import os
import json
import hashlib
import shutil
import joblib
import pandas as pd
from datetime import datetime, timezone

DATASET_PATH = os.path.join("data", "raw", "indian_used_cars_raw_57480.csv")
SOURCE_CANDIDATE = os.path.join("models", "candidates", "LightGBM_Tuned_log1p.joblib")
PROD_MODEL_PATH = os.path.join("models", "carspective_valuation_lgbm_v1.joblib")
MANIFEST_PATH = os.path.join("models", "carspective_valuation_lgbm_v1_manifest.json")
BENCHMARKS_PATH = os.path.join("data", "ml_benchmarks", "step7_candidate_benchmarks.json")
CALIBRATION_PATH = os.path.join("data", "ml_benchmarks", "step10_range_calibration_report.json")

def compute_sha256(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    print("Packaging production model artifact...")
    if not os.path.exists(SOURCE_CANDIDATE):
        raise FileNotFoundError(f"Source candidate {SOURCE_CANDIDATE} not found!")
        
    shutil.copyfile(SOURCE_CANDIDATE, PROD_MODEL_PATH)
    artifact_size = os.path.getsize(PROD_MODEL_PATH)
    artifact_sha256 = compute_sha256(PROD_MODEL_PATH)
    dataset_sha256 = compute_sha256(DATASET_PATH)
    
    with open(BENCHMARKS_PATH, "r") as f:
        benchmarks = json.load(f)
    winner_bench = next(b for b in benchmarks if b["name"] == "LightGBM Tuned (Log1p Target)")
    
    with open(CALIBRATION_PATH, "r") as f:
        calib = json.load(f)
        
    manifest = {
        "model_id": "carspective-valuation-lgbm-v1",
        "model_version": "carspective-val-v1.0.0",
        "algorithm": "LightGBM Tuned Regressor",
        "target_variable": "price",
        "target_transformation": "log1p(price) with expm1 inverse transformation",
        "target_semantic_concept": "Statistical Model Estimate of the Historical Market Asking-Price Baseline (NOT verified transaction price)",
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "name": "indian_used_cars_raw_57480.csv",
            "total_records": 57480,
            "sha256_fingerprint": dataset_sha256,
            "split_strategy": "Random 80/20 train/test split (seed=42) verified by decile cross-validation"
        },
        "artifact": {
            "file_name": "carspective_valuation_lgbm_v1.joblib",
            "size_bytes": artifact_size,
            "size_mb": round(artifact_size / (1024 * 1024), 2),
            "sha256": artifact_sha256
        },
        "feature_schema": {
            "numeric_features": [
                "manufacturing_year",
                "km_driven",
                "number_of_owners",
                "vehicle_age",
                "log_km_driven"
            ],
            "categorical_features": [
                "model",
                "fuel_type",
                "transmission_type",
                "brand",
                "city",
                "bodytype"
            ]
        },
        "evaluation_metrics": {
            "r2": winner_bench["r2"],
            "mae_inr": winner_bench["mae"],
            "medae_inr": winner_bench["medae"],
            "rmse_inr": winner_bench["rmse"],
            "smape_percent": winner_bench["smape"],
            "within_10_percent": winner_bench["within_10_pct"],
            "within_20_percent": winner_bench["within_20_pct"],
            "inference_latency_ms": winner_bench["latency_ms_per_sample"]
        },
        "conformal_range_calibration": {
            "nominal_80_percent_interval": {
                "multiplier": calib["nominal_80_percent_interval"]["multiplier_q80"],
                "empirical_coverage_percent": calib["nominal_80_percent_interval"]["empirical_coverage_percent"],
                "formula": "predicted_value * (1.0 +/- 0.217834)"
            },
            "nominal_90_percent_interval": {
                "multiplier": calib["nominal_90_percent_interval"]["multiplier_q90"],
                "empirical_coverage_percent": calib["nominal_90_percent_interval"]["empirical_coverage_percent"],
                "formula": "predicted_value * (1.0 +/- 0.314480)"
            }
        },
        "environment": {
            "python_version": "3.11.8",
            "lightgbm_version": "4.7.0",
            "scikit_learn_version": "1.9.1",
            "joblib_version": "1.6.0"
        }
    }
    
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Artifact created: {PROD_MODEL_PATH} ({manifest['artifact']['size_mb']} MB)")
    print(f"SHA-256: {artifact_sha256}")
    print(f"Manifest created: {MANIFEST_PATH}")

if __name__ == "__main__":
    main()
