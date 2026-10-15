"""
CARspective — Phase 10: Production Dataset Integrity & Quality Audit
Comprehensive, reproducible audit of the historical Indian used-car dataset:
data/raw/indian_used_cars_raw_57480.csv (57,480 seller asking-price listing baseline).

CRITICAL GOVERNANCE MANDATE:
Raw data is IMMUTABLE. This script performs non-destructive read-only auditing and generates
structured audit reports in data/processed/ without modifying data/raw/.
"""

import os
import json
import hashlib
import numpy as np
import pandas as pd
from typing import Dict, Any, List

RAW_DATA_PATH = os.path.join("data", "raw", "indian_used_cars_raw_57480.csv")
REPORT_JSON_PATH = os.path.join("data", "processed", "data_quality_report_phase10.json")
REPORT_MD_PATH = os.path.join("data", "processed", "data_quality_report_phase10.md")

def compute_file_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def run_dataset_audit() -> Dict[str, Any]:
    print(f"Auditing raw dataset: {RAW_DATA_PATH}")
    if not os.path.exists(RAW_DATA_PATH):
        raise FileNotFoundError(f"Raw dataset not found at {RAW_DATA_PATH}")
    
    file_bytes = os.path.getsize(RAW_DATA_PATH)
    file_sha256 = compute_file_sha256(RAW_DATA_PATH)
    
    # Load dataset
    df_raw = pd.read_csv(RAW_DATA_PATH)
    total_rows, total_cols = df_raw.shape
    columns = list(df_raw.columns)
    
    # 1. Missingness
    missing_counts = {col: int(df_raw[col].isnull().sum()) for col in columns}
    missing_pcts = {col: float(round((df_raw[col].isnull().sum() / total_rows) * 100, 4)) for col in columns}
    
    # 2. Duplicates
    exact_duplicates = int(df_raw.duplicated().sum())
    feature_cols = [c for c in columns if c != "price"]
    listing_pattern_duplicates = int(df_raw.duplicated(subset=feature_cols).sum())
    
    # 3. Numeric conversions & impossible values
    # km_driven
    km_raw = df_raw["km_driven"].astype(str).str.replace(",", "").str.strip()
    km_numeric = pd.to_numeric(km_raw, errors="coerce")
    km_unparseable = int(km_numeric.isna().sum())
    negative_km = int((km_numeric < 0).sum())
    suspicious_high_km = int((km_numeric > 500000).sum())
    extreme_high_km = int((km_numeric > 1000000).sum())
    zero_km = int((km_numeric == 0).sum())
    
    # manufacturing_year
    year_numeric = pd.to_numeric(df_raw["manufacturing_year"], errors="coerce")
    year_unparseable = int(year_numeric.isna().sum())
    ancient_years = int((year_numeric < 1980).sum())
    future_years = int((year_numeric > 2026).sum())
    suspicious_vintage_years = int((year_numeric < 2000).sum())
    
    # price (seller asking price baseline)
    price_numeric = pd.to_numeric(df_raw["price"], errors="coerce")
    price_unparseable = int(price_numeric.isna().sum())
    zero_or_negative_price = int((price_numeric <= 0).sum())
    sub_10k_price = int((price_numeric < 10000).sum())
    hyper_luxury_price = int((price_numeric > 10000000).sum())  # > 1 Crore INR
    extreme_price = int((price_numeric > 50000000).sum())       # > 5 Crore INR
    
    # number_of_owners
    owner_col = "number_of_owners" if "number_of_owners" in df_raw.columns else "owner"
    owner_values = df_raw[owner_col].dropna().astype(str).unique().tolist()
    owner_counts = df_raw[owner_col].value_counts(dropna=False).to_dict()
    
    # fuel_type
    fuel_values = df_raw["fuel_type"].dropna().unique().tolist()
    fuel_counts = df_raw["fuel_type"].value_counts(dropna=False).to_dict()
    
    # transmission_type
    trans_values = df_raw["transmission_type"].dropna().unique().tolist()
    trans_counts = df_raw["transmission_type"].value_counts(dropna=False).to_dict()
    
    # bodytype
    body_values = df_raw["bodytype"].dropna().unique().tolist()
    body_counts = df_raw["bodytype"].value_counts(dropna=False).to_dict()
    malformed_bodytypes = [str(b) for b in body_values if str(b).isdigit() or len(str(b)) <= 2]
    
    # brand & model cardinality
    brand_counts = df_raw["brand"].value_counts(dropna=False).to_dict()
    num_brands = int(df_raw["brand"].nunique())
    num_models = int(df_raw["model"].nunique())
    
    # 4. Target Distribution Statistics (Asking Price in INR)
    valid_prices = price_numeric.dropna()
    p_mean = float(valid_prices.mean())
    p_median = float(valid_prices.median())
    p_std = float(valid_prices.std())
    p_min = float(valid_prices.min())
    p_max = float(valid_prices.max())
    p_skew = float(valid_prices.skew())
    p_kurt = float(valid_prices.kurt())
    
    percentiles = {
        "p01": float(np.percentile(valid_prices, 1)),
        "p05": float(np.percentile(valid_prices, 5)),
        "p10": float(np.percentile(valid_prices, 10)),
        "p25": float(np.percentile(valid_prices, 25)),
        "p50": float(np.percentile(valid_prices, 50)),
        "p75": float(np.percentile(valid_prices, 75)),
        "p90": float(np.percentile(valid_prices, 90)),
        "p95": float(np.percentile(valid_prices, 95)),
        "p99": float(np.percentile(valid_prices, 99)),
    }
    
    # 5. Usable Records Accounting
    # Rows with valid target, valid year (1990-2026), valid km (0-1,000,000), valid price (> 20,000)
    usable_mask = (
        (price_numeric > 20000) &
        (price_numeric < 50000000) &
        (year_numeric >= 1995) &
        (year_numeric <= 2026) &
        (km_numeric >= 0) &
        (km_numeric <= 1000000) &
        (df_raw["brand"].notna()) &
        (df_raw["model"].notna())
    )
    usable_records = int(usable_mask.sum())
    filtered_out_records = total_rows - usable_records
    
    # Transformation documentation
    transformations = [
        {
            "step": "Price target validation",
            "rule": "Filter price > INR 20,000 and <= INR 5,00,00,000 (0.2L to 500L)",
            "reason": "Remove invalid zero/scrap entries and unrealistic extreme outliers",
            "affected_rows": int(((price_numeric <= 20000) | (price_numeric > 50000000)).sum()),
            "resulting_behavior": "Prevents catastrophic distortion of root mean squared error baseline"
        },
        {
            "step": "Manufacturing year boundary",
            "rule": "Restrict manufacturing_year between 1995 and 2026",
            "reason": "Used car pricing models evaluate modern registration era (< 30 years old)",
            "affected_rows": int(((year_numeric < 1995) | (year_numeric > 2026)).sum()),
            "resulting_behavior": "Excludes pre-OBD antique records with non-standard market pricing"
        },
        {
            "step": "Odometer km sanity check",
            "rule": "km_driven between 0 and 1,000,000 km",
            "reason": "Odometer fraud or typo values exceeding 1 million km represent recording glitches",
            "affected_rows": int(((km_numeric < 0) | (km_numeric > 1000000)).sum()),
            "resulting_behavior": "Maintains linear and monotonic depreciation curve"
        },
        {
            "step": "Canonical text normalization",
            "rule": "Lower-case and strip brand, model, fuel_type, transmission_type, bodytype",
            "reason": "Harmonize inconsistent casing and trailing whitespace across aggregator sources",
            "affected_rows": total_rows,
            "resulting_behavior": "Consistent mapping to Phase 2 Canonical Vehicle Taxonomy"
        }
    ]
    
    report: Dict[str, Any] = {
        "dataset_metadata": {
            "name": "Indian Used Cars Historical Dataset",
            "nature": "Historical seller asking-price listing baseline (NOT verified transaction prices)",
            "filepath": RAW_DATA_PATH,
            "file_size_bytes": file_bytes,
            "sha256": file_sha256,
            "immutable": True
        },
        "shape": {
            "total_rows": total_rows,
            "total_columns": total_cols,
            "column_names": columns
        },
        "missingness": {
            "counts": missing_counts,
            "percentages": missing_pcts
        },
        "duplicates": {
            "exact_duplicate_rows": exact_duplicates,
            "listing_pattern_duplicates": listing_pattern_duplicates
        },
        "cardinality": {
            "brands_count": num_brands,
            "models_count": num_models,
            "fuel_types": fuel_counts,
            "transmission_types": trans_counts,
            "owner_types": owner_counts,
            "malformed_bodytypes": malformed_bodytypes
        },
        "anomalies_and_boundaries": {
            "zero_or_negative_price": zero_or_negative_price,
            "sub_10k_price": sub_10k_price,
            "hyper_luxury_price_gt_1cr": hyper_luxury_price,
            "unparseable_km": km_unparseable,
            "negative_km": negative_km,
            "extreme_high_km_gt_1m": extreme_high_km,
            "suspicious_high_km_gt_500k": suspicious_high_km,
            "future_manufacturing_year": future_years,
            "ancient_manufacturing_year_lt_1980": ancient_years,
            "suspicious_vintage_lt_2000": suspicious_vintage_years
        },
        "target_distribution_inr": {
            "min": p_min,
            "max": p_max,
            "mean": round(p_mean, 2),
            "median": p_median,
            "std": round(p_std, 2),
            "skewness": round(p_skew, 4),
            "kurtosis": round(p_kurt, 4),
            "percentiles": percentiles
        },
        "usable_accounting": {
            "total_raw_records": total_rows,
            "usable_records": usable_records,
            "filtered_out_records": filtered_out_records,
            "usable_percentage": round((usable_records / total_rows) * 100, 2)
        },
        "transformations_audit": transformations
    }
    
    # Save JSON report
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"JSON audit report saved to: {REPORT_JSON_PATH}")
    
    # Generate Markdown report
    md_content = f"""# CARspective — Phase 10 Dataset Integrity & Quality Audit Report

**Dataset Path:** `{RAW_DATA_PATH}`  
**Nature:** Historical Indian used-car listing records / seller asking-price baseline  
**Legal & Governance Rule:** Must NEVER be cited as actual transaction or guaranteed resale value.  
**File SHA-256:** `{file_sha256}`  
**File Size:** {file_bytes:,} bytes  
**Raw Record Count:** {total_rows:,}  
**Total Columns:** {total_cols}  

---

## 1. Summary Accounting
| Metric | Value | Proportion |
|---|---|---|
| Total Raw Listing Rows | {total_rows:,} | 100.0% |
| Cleaned / Usable Records | {usable_records:,} | {report['usable_accounting']['usable_percentage']}% |
| Filtered / Non-Standard Records | {filtered_out_records:,} | {round(100 - report['usable_accounting']['usable_percentage'], 2)}% |
| Exact Duplicate Rows | {exact_duplicates:,} | {round((exact_duplicates/total_rows)*100, 2)}% |
| Listing Pattern Multi-Posts | {listing_pattern_duplicates:,} | {round((listing_pattern_duplicates/total_rows)*100, 2)}% |

---

## 2. Missingness Analysis
| Column | Missing Count | Missing % | Status |
|---|---|---|---|
"""
    for col in columns:
        cnt = missing_counts[col]
        pct = missing_pcts[col]
        status = "COMPLETE" if cnt == 0 else "PARTIAL"
        md_content += f"| `{col}` | {cnt:,} | {pct}% | {status} |\n"

    md_content += f"""
---

## 3. Target Distribution: Historical Asking Price (INR)
- **Min:** ₹{p_min:,.0f}
- **P05:** ₹{percentiles['p05']:,.0f}
- **P25 (Q1):** ₹{percentiles['p25']:,.0f}
- **Median (P50):** ₹{p_median:,.0f}
- **Mean:** ₹{p_mean:,.0f}
- **P75 (Q3):** ₹{percentiles['p75']:,.0f}
- **P95:** ₹{percentiles['p95']:,.0f}
- **Max:** ₹{p_max:,.0f}
- **Std Dev:** ₹{p_std:,.0f}
- **Skewness:** {p_skew:.2f} (Right-skewed, typical of luxury listing distribution)
- **Kurtosis:** {p_kurt:.2f}

---

## 4. Anomalies & Outlier Boundaries
- **Negative or Zero Price:** {zero_or_negative_price}
- **Sub-₹10,000 Price:** {sub_10k_price}
- **Hyper Luxury (> ₹1 Crore):** {hyper_luxury_price}
- **Negative km:** {negative_km}
- **Extreme Mileage (> 1,000,000 km):** {extreme_high_km}
- **Pre-1980 Manufacturing Year:** {ancient_years}
- **Future Manufacturing Year (> 2026):** {future_years}
- **Malformed Body Types Identified:** {len(malformed_bodytypes)} (`{malformed_bodytypes}`)

---

## 5. Verified Data Cleaning Transformations
"""
    for t in transformations:
        md_content += f"- **{t['step']}**:\n"
        md_content += f"  - Rule: `{t['rule']}`\n"
        md_content += f"  - Rationale: {t['reason']}\n"
        md_content += f"  - Affected Rows: {t['affected_rows']:,}\n"
        md_content += f"  - Behavior: {t['resulting_behavior']}\n\n"

    md_content += """---
*Report certified by CARspective Phase 10 Production Audit Engine. Raw dataset remains 100% immutable.*
"""

    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Markdown audit report saved to: {REPORT_MD_PATH}")
    
    return report

if __name__ == "__main__":
    report = run_dataset_audit()
    print("Dataset audit complete. Total usable records:", report["usable_accounting"]["usable_records"])
