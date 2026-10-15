"""
CARspective — Empirical Dataset & Quality Analysis Engine
Dataset: data/raw/indian_used_cars_raw_57480.csv
Semantics: 57,480 historical Indian used-car listing records (Seller Asking Price Baseline)
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path
import pandas as pd
import numpy as np

def run_analysis(csv_path: str, output_dir: str):
    csv_file = Path(csv_path)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"Loading dataset from: {csv_file}")
    df = pd.read_csv(csv_file)
    total_records = len(df)
    print(f"Total raw listing records: {total_records}")

    # Standardize column headers for analysis (inspect original columns first)
    original_columns = df.columns.tolist()
    print(f"Original columns: {original_columns}")

    # Rename mapping if needed (preserving immutability of raw CSV)
    col_map = {
        'brand': 'brand',
        'model': 'model',
        'manufacturing_year': 'year',
        'km_driven': 'km_driven',
        'fuel_type': 'fuel_type',
        'transmission_type': 'transmission',
        'price': 'price',
        'number_of_owners': 'owners',
        'bodytype': 'bodytype',
        'city': 'city'
    }
    # Check if columns match
    work_df = df.copy()

    # 1. Basic Metadata
    missing_counts = work_df.isnull().sum().to_dict()
    missing_pct = {k: round(v / total_records * 100, 3) for k, v in missing_counts.items()}
    duplicates_count = int(work_df.duplicated().sum())

    # 2. Manufacturers
    brand_counts = work_df['brand'].value_counts()
    manufacturers = {
        'total_unique': int(work_df['brand'].nunique()),
        'top_manufacturers': brand_counts.head(15).to_dict(),
        'all_manufacturers': brand_counts.to_dict()
    }

    # 3. Models Frequency & Cumulative Distribution Function (CDF)
    model_counts = work_df['model'].value_counts()
    total_unique_models = int(len(model_counts))
    
    # Calculate CDF
    cdf_records = []
    cum_sum = 0
    for rank, (model_name, count) in enumerate(model_counts.items(), 1):
        cum_sum += count
        cum_pct = (cum_sum / total_records) * 100
        brand_for_model = work_df[work_df['model'] == model_name]['brand'].iloc[0] if count > 0 else 'Unknown'
        cdf_records.append({
            'rank': rank,
            'model': model_name,
            'brand': brand_for_model,
            'listing_count': int(count),
            'listing_share_pct': round((count / total_records) * 100, 4),
            'cumulative_count': int(cum_sum),
            'cumulative_pct': round(cum_pct, 3)
        })

    cdf_df = pd.DataFrame(cdf_records)

    # 4. Checkpoints in CDF
    milestones = [50, 60, 70, 75, 80, 85, 90, 95]
    milestone_cuts = {}
    for ms in milestones:
        match = cdf_df[cdf_df['cumulative_pct'] >= ms].iloc[0]
        milestone_cuts[f"{ms}%_volume"] = {
            'model_rank': int(match['rank']),
            'model_name': match['model'],
            'brand': match['brand'],
            'cumulative_pct': float(match['cumulative_pct']),
            'cumulative_listings': int(match['cumulative_count'])
        }

    # Inspect volume thresholds (models with >= 500, >= 200, >= 100, >= 50 listings)
    volume_thresholds = {}
    for thresh in [1000, 500, 300, 200, 100, 50, 20, 10]:
        matching_count = int((model_counts >= thresh).sum())
        vol_sum = int(model_counts[model_counts >= thresh].sum())
        volume_thresholds[f"min_{thresh}_listings"] = {
            'model_count': matching_count,
            'cumulative_listings': vol_sum,
            'cumulative_pct': round((vol_sum / total_records) * 100, 2)
        }

    # 5. Categorical Distributions
    fuel_dist = work_df['fuel_type'].value_counts(dropna=False).to_dict()
    fuel_dist = {str(k): int(v) for k, v in fuel_dist.items()}

    trans_dist = work_df['transmission_type'].value_counts(dropna=False).to_dict()
    trans_dist = {str(k): int(v) for k, v in trans_dist.items()}

    body_dist = work_df['bodytype'].value_counts(dropna=False).to_dict()
    body_dist = {str(k): int(v) for k, v in body_dist.items()}

    city_counts = work_df['city'].value_counts(dropna=False)
    city_dist = {
        'total_unique_cities': int(work_df['city'].nunique()),
        'top_cities': {str(k): int(v) for k, v in city_counts.head(20).items()}
    }

    # 6. Numeric Statistics with Data Quality Inspection for string numbers
    def parse_numeric_series(series):
        # Convert strings with commas or units to numeric safely, tracking non-convertible items
        cleaned = series.astype(str).str.replace(',', '').str.replace('km', '', case=False).str.strip()
        numeric = pd.to_numeric(cleaned, errors='coerce')
        non_convertible = series[numeric.isna() & series.notna()].tolist()
        return numeric, non_convertible

    numeric_price, invalid_price = parse_numeric_series(work_df['price'])
    numeric_km, invalid_km = parse_numeric_series(work_df['km_driven'])
    numeric_year, invalid_year = parse_numeric_series(work_df['manufacturing_year'])

    price_stats = {
        'invalid_non_numeric_count': len(invalid_price),
        'invalid_samples': invalid_price[:5],
        'min': float(numeric_price.min()) if not numeric_price.isna().all() else None,
        'p01': float(numeric_price.quantile(0.01)) if not numeric_price.isna().all() else None,
        'p25': float(numeric_price.quantile(0.25)) if not numeric_price.isna().all() else None,
        'median': float(numeric_price.median()) if not numeric_price.isna().all() else None,
        'mean': round(float(numeric_price.mean()), 2) if not numeric_price.isna().all() else None,
        'p75': float(numeric_price.quantile(0.75)) if not numeric_price.isna().all() else None,
        'p99': float(numeric_price.quantile(0.99)) if not numeric_price.isna().all() else None,
        'max': float(numeric_price.max()) if not numeric_price.isna().all() else None
    }

    km_stats = {
        'invalid_non_numeric_count': len(invalid_km),
        'invalid_samples': invalid_km[:5],
        'min': float(numeric_km.min()) if not numeric_km.isna().all() else None,
        'p01': float(numeric_km.quantile(0.01)) if not numeric_km.isna().all() else None,
        'median': float(numeric_km.median()) if not numeric_km.isna().all() else None,
        'mean': round(float(numeric_km.mean()), 2) if not numeric_km.isna().all() else None,
        'p99': float(numeric_km.quantile(0.99)) if not numeric_km.isna().all() else None,
        'max': float(numeric_km.max()) if not numeric_km.isna().all() else None
    }

    year_stats = {
        'invalid_non_numeric_count': len(invalid_year),
        'invalid_samples': invalid_year[:5],
        'min': int(numeric_year.min()) if not numeric_year.isna().all() else None,
        'median': int(numeric_year.median()) if not numeric_year.isna().all() else None,
        'max': int(numeric_year.max()) if not numeric_year.isna().all() else None,
        'distribution': {int(k): int(v) for k, v in numeric_year.value_counts().sort_index().items() if pd.notna(k)}
    }

    owner_dist = {str(k): int(v) for k, v in work_df['number_of_owners'].value_counts(dropna=False).sort_index().items()}

    # 7. Data Quality & Anomaly Checks
    anomalies = {
        'duplicate_rows_count': duplicates_count,
        'missing_fields': missing_counts,
        'missing_fields_pct': missing_pct,
        'zero_or_negative_price': int((numeric_price <= 0).sum()),
        'extremely_low_price_sub_25k': int((numeric_price < 25000).sum()),
        'extremely_high_price_above_1cr': int((numeric_price > 10000000).sum()),
        'zero_or_negative_km': int((numeric_km <= 0).sum()),
        'extremely_high_km_above_500k': int((numeric_km > 500000).sum()),
        'suspicious_years_pre_1995': int((numeric_year < 1995).sum()),
        'future_years_post_2026': int((numeric_year > 2026).sum()),
        'malformed_bodytypes': [k for k in body_dist.keys() if k in ['15', 'nan', 'None'] or not isinstance(k, str)],
        'rare_models_single_listing': int((model_counts == 1).sum()),
        'models_with_under_10_listings': int((model_counts < 10).sum())
    }

    # Brand-Model consistency: Check models where brand name is repeated inside model name (e.g. "Hyundai Creta" as model)
    brand_embedded_in_model = []
    for brand in work_df['brand'].dropna().unique():
        brand_lower = brand.lower().strip()
        models_for_brand = work_df[work_df['brand'] == brand]['model'].dropna().unique()
        for m in models_for_brand:
            m_lower = m.lower().strip()
            if m_lower.startswith(brand_lower + " ") or m_lower == brand_lower:
                brand_embedded_in_model.append({'brand': brand, 'raw_model': m})

    anomalies['brand_embedded_in_model_count'] = len(brand_embedded_in_model)
    anomalies['brand_embedded_in_model_samples'] = brand_embedded_in_model[:15]

    # Save outputs
    report = {
        'dataset_semantics': '57,480 historical Indian used-car listing records (Seller Asking Price Baseline)',
        'total_records': total_records,
        'manufacturers_summary': manufacturers,
        'models_summary': {
            'total_unique_models': total_unique_models,
            'cdf_milestones': milestone_cuts,
            'volume_thresholds': volume_thresholds
        },
        'fuel_distribution': fuel_dist,
        'transmission_distribution': trans_dist,
        'body_type_distribution': body_dist,
        'city_summary': city_dist,
        'numeric_statistics': {
            'price': price_stats,
            'km_driven': km_stats,
            'year': year_stats,
            'owners': owner_dist
        },
        'data_quality_anomalies': anomalies
    }

    report_file = out_path / 'empirical_dataset_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(f"Empirical report saved to: {report_file}")

    cdf_file = out_path / 'model_listing_cdf.csv'
    cdf_df.to_csv(cdf_file, index=False)
    print(f"Model listing CDF saved to: {cdf_file}")

    return report, cdf_df

if __name__ == '__main__':
    csv_target = sys.argv[1] if len(sys.argv) > 1 else 'data/raw/indian_used_cars_raw_57480.csv'
    out_target = sys.argv[2] if len(sys.argv) > 2 else 'data/processed'
    run_analysis(csv_target, out_target)
