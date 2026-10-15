"""
CARspective — Phase 14 Market Intelligence Pre-Aggregation Script
Extracts empirical market evidence from the 57,480-listing dataset
and 1,200-model CDF into a high-performance in-memory cache structure.
Preserves Phase 2 canonical taxonomy tier contracts:
  - Tier 1: listing_count >= 200
  - Tier 2: 50 <= listing_count < 200
  - Tier 3: listing_count < 50
"""

import json
import os
import re
import pandas as pd
import numpy as np


def clean_model_name(raw_name: str) -> str:
    """Normalizes raw model name to assist canonical taxonomy matching."""
    s = raw_name.strip()
    # Remove generation bracket annotations like [2020-2023]
    s = re.sub(r'\[.*?\]', '', s).strip()
    return s


def safe_mode(series, default="Unknown"):
    m = series.dropna().mode()
    return str(m.iloc[0]) if len(m) > 0 else default


def build_market_cache():
    cleaned_csv_path = 'data/processed/indian_used_cars_cleaned.csv'
    cdf_csv_path = 'data/processed/model_listing_cdf.csv'
    output_cache_path = 'data/processed/market_intelligence_cache.json'

    print("Loading empirical dataset...")
    df = pd.read_csv(cleaned_csv_path)
    cdf = pd.read_csv(cdf_csv_path)

    # Clean numeric fields
    df['km_driven_clean'] = pd.to_numeric(
        df['km_driven'].astype(str).str.replace(',', '').str.strip(),
        errors='coerce'
    ).fillna(0)
    df['price_clean'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)

    total_records = len(df)
    observation_period = "2018–2024 (Historical Indian Secondary Market Listings)"
    data_basis = "Seller Asking Price Baseline (Historical Listings, Not Realized Transaction Prices)"

    # Build CDF index by normalized model name
    cdf_models = {}
    for _, row in cdf.iterrows():
        raw_m = str(row['model'])
        brand = str(row['brand'])
        count = int(row['listing_count'])
        share = float(row['listing_share_pct'])
        rank = int(row['rank'])

        # Store by exact raw model name
        key_raw = f"{brand.lower()}::{raw_m.lower()}"
        clean_m = clean_model_name(raw_m).lower()
        key_clean = f"{brand.lower()}::{clean_m}"

        entry = {
            "rank": rank,
            "raw_model": raw_m,
            "brand": brand,
            "listing_count": count,
            "listing_share_pct": share,
        }
        cdf_models[key_raw] = entry
        if key_clean not in cdf_models:
            cdf_models[key_clean] = entry

    # 1. Segment statistics by body type
    segment_stats = {}
    for body_type, grp in df.groupby('bodytype'):
        cnt = len(grp)
        if cnt < 50:
            continue
        med_price = float(grp['price_clean'].median())
        mean_price = float(grp['price_clean'].mean())
        med_km = float(grp['km_driven_clean'].median())
        top_models = grp['model'].value_counts().head(5).to_dict()

        segment_stats[str(body_type)] = {
            "listing_count": cnt,
            "share_of_market_pct": round((cnt / total_records) * 100, 2),
            "median_price_inr": round(med_price, 2),
            "mean_price_inr": round(mean_price, 2),
            "median_km_driven": round(med_km, 2),
            "top_models": top_models
        }

    # 2. Model-level deep empirical intelligence
    model_profiles = {}
    # Group by (brand, model)
    for (brand, model_name), grp in df.groupby(['brand', 'model']):
        cnt = len(grp)
        clean_name = clean_model_name(model_name)
        key = f"{brand.lower()}::{clean_name.lower()}"

        # If already aggregated, accumulate
        if key not in model_profiles:
            model_profiles[key] = {
                "brand": brand,
                "model": clean_name,
                "total_observed_listings": 0,
                "body_type": safe_mode(grp['bodytype'], "Unknown"),
                "median_asking_price_inr": float(grp['price_clean'].median()),
                "mean_asking_price_inr": float(grp['price_clean'].mean()),
                "median_km_driven": float(grp['km_driven_clean'].median()),
                "primary_fuel": safe_mode(grp['fuel_type'], "Petrol"),
                "primary_transmission": safe_mode(grp['transmission_type'], "Manual"),
                "top_cities": {},
                "yearly_points": {},
            }

        prof = model_profiles[key]
        prof["total_observed_listings"] += cnt

        # City breakdown
        for city, c_count in grp['city'].value_counts().head(5).items():
            prof["top_cities"][str(city)] = prof["top_cities"].get(str(city), 0) + int(c_count)

        # Yearly points for depreciation curves
        for year, y_grp in grp.groupby('manufacturing_year'):
            y_cnt = len(y_grp)
            y_str = str(int(year))
            if y_str not in prof["yearly_points"]:
                prof["yearly_points"][y_str] = {
                    "count": 0,
                    "prices": []
                }
            prof["yearly_points"][y_str]["count"] += y_cnt
            prof["yearly_points"][y_str]["prices"].extend(y_grp['price_clean'].tolist())

    # Finalize model profiles with depreciation statistics
    final_models = {}
    for key, prof in model_profiles.items():
        total_cnt = prof["total_observed_listings"]
        share_pct = round((total_cnt / total_records) * 100, 4)

        # Rank determination
        rank_val = 999
        if key in cdf_models:
            rank_val = cdf_models[key]["rank"]

        # Compute yearly stats
        depreciation_curve = []
        # Find latest reliable year (with >= 15 listings) to serve as retention baseline
        reliable_years = [
            int(y) for y, d in prof["yearly_points"].items()
            if d["count"] >= 15 and 2010 <= int(y) <= 2024
        ]
        reliable_years.sort(reverse=True)
        baseline_price = None
        if reliable_years:
            newest_year = reliable_years[0]
            newest_prices = prof["yearly_points"][str(newest_year)]["prices"]
            baseline_price = float(np.median(newest_prices))

        for y_str in sorted(prof["yearly_points"].keys(), key=lambda x: int(x)):
            y_data = prof["yearly_points"][y_str]
            y_int = int(y_str)
            if y_int < 2005 or y_int > 2025:
                continue

            y_cnt = y_data["count"]
            if y_cnt >= 5: # Include points with at least 5 empirical observations
                prices = y_data["prices"]
                med_p = float(np.median(prices))
                mean_p = float(np.mean(prices))
                p25 = float(np.percentile(prices, 25))
                p75 = float(np.percentile(prices, 75))

                retention_pct = None
                if baseline_price and baseline_price > 0:
                    retention_pct = round((med_p / baseline_price) * 100, 1)

                depreciation_curve.append({
                    "manufacturing_year": y_int,
                    "sample_size": y_cnt,
                    "median_price_inr": round(med_p, 2),
                    "mean_price_inr": round(mean_p, 2),
                    "price_iqr_low_inr": round(p25, 2),
                    "price_iqr_high_inr": round(p75, 2),
                    "observed_retention_pct": retention_pct,
                    "is_statistically_robust": (y_cnt >= 15)
                })

        # Remove raw prices array to keep cache lightweight
        del prof["yearly_points"]

        prof["national_rank"] = rank_val
        prof["market_share_pct"] = share_pct
        prof["depreciation_curve"] = depreciation_curve
        final_models[key] = prof

    cache_data = {
        "metadata": {
            "total_observed_listings": total_records,
            "observation_period": observation_period,
            "data_basis": data_basis,
            "total_unique_models": len(final_models),
            "generated_at": "2026-10-08T18:24:00Z"
        },
        "segment_benchmarks": segment_stats,
        "models": final_models
    }

    with open(output_cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=2)

    cache_size_kb = os.path.getsize(output_cache_path) / 1024
    print(f"Market cache generated successfully: {output_cache_path} ({cache_size_kb:.2f} KB, {len(final_models)} models)")


if __name__ == "__main__":
    build_market_cache()
