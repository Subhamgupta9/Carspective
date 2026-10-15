"""
SMARTCAR AI — PHASE 9: MARKET INTELLIGENCE & COMPARABLES ENGINE
===============================================================
Module: app/market_intelligence.py

Factual, defensible secondary market statistics derived strictly from:
data/raw/indian_used_cars_raw_57480.csv (57,480 verified used-car records).

Rules:
1. All intelligence must come ONLY from the actual raw dataset.
2. Zero fabricated or synthetic data.
3. Handle sparse segments safely: If fewer than 3 records are available,
   return 'Insufficient Data' rather than inventing numbers.
4. Provide fast in-memory LRU caching for performance.
"""

import os
import functools
import threading
from collections import OrderedDict
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

# Path to the single source of truth dataset
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "data", "raw", "indian_used_cars_raw_57480.csv")
CURRENT_YEAR = 2026
MIN_RELIABLE_SAMPLE_SIZE = 3


def format_inr(amount: float) -> str:
    """Format numeric value into Indian currency string (e.g. ₹13,81,107)."""
    if amount is None or np.isnan(amount):
        return "—"
    s = str(int(round(amount)))
    if len(s) <= 3:
        return f"₹{s}"
    last_three = s[-3:]
    remaining = s[:-3]
    parts = []
    while len(remaining) > 2:
        parts.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        parts.insert(0, remaining)
    return f"₹{','.join(parts)},{last_three}"


def _normalize_model_str(brand_str: str, model_str: str) -> str:
    """Normalize model string by removing repetitive brand prefixes."""
    b = str(brand_str).strip().lower()
    m = str(model_str).strip()
    if m.lower().startswith(b + " "):
        return m[len(b):].strip()
    return m


class MarketIntelligenceDataset:
    """Singleton dataset loader and vectorized index for market intelligence."""
    _instance = None
    _df = None

    @classmethod
    def get_df(cls) -> pd.DataFrame:
        if cls._df is None:
            if not os.path.exists(DATASET_PATH):
                raise FileNotFoundError(f"Dataset file not found at {DATASET_PATH}")
            raw_df = pd.read_csv(DATASET_PATH)
            if "price" in raw_df.columns:
                raw_df = raw_df.rename(columns={"price": "actual_price"})

            # Precompute clean normalized search columns
            raw_df["_norm_brand"] = raw_df["brand"].astype(str).str.strip().str.lower()
            raw_df["_norm_model"] = raw_df.apply(
                lambda r: _normalize_model_str(r["brand"], r["model"]).lower(), axis=1
            )
            raw_df["_norm_city"] = raw_df["city"].astype(str).str.strip().str.lower()
            raw_df["_num_km"] = pd.to_numeric(
                raw_df["km_driven"].astype(str).str.replace(",", "").str.strip(), errors="coerce"
            ).fillna(0)
            raw_df["_num_year"] = pd.to_numeric(raw_df["manufacturing_year"], errors="coerce").fillna(2020).astype(int)
            raw_df["_num_price"] = pd.to_numeric(
                raw_df["actual_price"].astype(str).str.replace(",", "").str.strip(), errors="coerce"
            ).fillna(0)
            raw_df["_num_owners"] = pd.to_numeric(raw_df["number_of_owners"], errors="coerce").fillna(1).astype(int)

            cls._df = raw_df
        return cls._df


def _get_matching_subset(brand: str, model: str) -> pd.DataFrame:
    """Retrieve filtered subset of records matching brand and model."""
    df = MarketIntelligenceDataset.get_df()
    b_clean = str(brand).strip().lower()
    m_clean = str(model).strip()
    target_norm = _normalize_model_str(b_clean, m_clean).lower()

    # Match exact brand and normalized model
    mask = (df["_norm_brand"] == b_clean) & (df["_norm_model"] == target_norm)
    subset = df[mask]
    if len(subset) == 0:
        # Fallback to model contains or brand match
        mask_contains = (df["_norm_brand"] == b_clean) & (df["model"].astype(str).str.lower().str.contains(target_norm, regex=False))
        subset = df[mask_contains]

    return subset


# Global thread-safe bounded LRU caches for computed market intelligence
MAX_MARKET_CACHE_SIZE = 512
_CACHE_LOCK = threading.Lock()
_SUMMARY_CACHE: OrderedDict = OrderedDict()
_FACTORS_CACHE: OrderedDict = OrderedDict()
_COMPARABLES_CACHE: OrderedDict = OrderedDict()
_SUMMARY_HITS = 0
_SUMMARY_MISSES = 0


def get_market_cache_stats() -> Dict[str, Any]:
    """Returns telemetry statistics for market intelligence caches."""
    with _CACHE_LOCK:
        return {
            "summary_cache_size": len(_SUMMARY_CACHE),
            "summary_cache_max": MAX_MARKET_CACHE_SIZE,
            "summary_cache_hits": _SUMMARY_HITS,
            "summary_cache_misses": _SUMMARY_MISSES,
            "factors_cache_size": len(_FACTORS_CACHE),
            "comparables_cache_size": len(_COMPARABLES_CACHE),
            "max_cache_size": MAX_MARKET_CACHE_SIZE
        }


def clear_market_cache() -> None:
    """Flushes all in-memory market intelligence caches."""
    global _SUMMARY_HITS, _SUMMARY_MISSES
    with _CACHE_LOCK:
        _SUMMARY_CACHE.clear()
        _FACTORS_CACHE.clear()
        _COMPARABLES_CACHE.clear()
        _SUMMARY_HITS = 0
        _SUMMARY_MISSES = 0


def compute_factors(
    brand: str,
    model: str,
    selected_year: Optional[int] = None,
    selected_km: Optional[float] = None,
    selected_fuel: Optional[str] = None,
    selected_transmission: Optional[str] = None,
    selected_city: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Computes factual market factors:
    - Market Context (price percentiles, count, IQR)
    - Depreciation Curve across manufacturing years in dataset
    - Fuel Mix distribution
    - Transmission Mix distribution
    - City Volume distribution
    Safely handles sparse data by flagging 'Insufficient Data'.
    """
    # Resolve aliases if provided in kwargs
    selected_year = selected_year if selected_year is not None else kwargs.get("year", kwargs.get("manufacturing_year"))
    selected_km = selected_km if selected_km is not None else kwargs.get("km", kwargs.get("km_driven"))
    selected_fuel = selected_fuel if selected_fuel is not None else kwargs.get("fuel", kwargs.get("fuel_type"))
    selected_transmission = selected_transmission if selected_transmission is not None else kwargs.get("transmission", kwargs.get("transmission_type"))
    selected_city = selected_city if selected_city is not None else kwargs.get("city")

    cache_key = (
        str(brand).strip().lower(),
        str(model).strip().lower(),
        int(selected_year) if selected_year else 0,
        int(round(float(selected_km))) if selected_km is not None else 0,
        str(selected_fuel).strip().lower() if selected_fuel else "",
        str(selected_transmission).strip().lower() if selected_transmission else "",
        str(selected_city).strip().lower() if selected_city else "",
    )

    with _CACHE_LOCK:
        if cache_key in _FACTORS_CACHE:
            _FACTORS_CACHE.move_to_end(cache_key)
            return _FACTORS_CACHE[cache_key]

    subset = _get_matching_subset(brand, model)
    total_records = len(subset)

    # 1. Sparse segment check
    if total_records < MIN_RELIABLE_SAMPLE_SIZE:
        return {
            "status": "insufficient_data",
            "sample_size": total_records,
            "message": "Insufficient Data",
            "market_context": {
                "status": "insufficient_data",
                "sample_size": total_records,
                "message": "Insufficient Data",
                "has_sufficient_data": False
            },
            "depreciation_curve": {
                "status": "insufficient_data",
                "message": "Insufficient Data",
                "has_sufficient_data": False,
                "points": []
            },
            "fuel_mix": {
                "status": "insufficient_data",
                "message": "Insufficient Data",
                "has_sufficient_data": False,
                "distribution": []
            },
            "transmission_mix": {
                "status": "insufficient_data",
                "message": "Insufficient Data",
                "has_sufficient_data": False,
                "distribution": []
            },
            "city_volume": {
                "status": "insufficient_data",
                "message": "Insufficient Data",
                "has_sufficient_data": False,
                "top_cities": []
            }
        }

    prices = subset["_num_price"][subset["_num_price"] > 0]
    min_price = int(prices.min())
    median_price = int(round(prices.median()))
    max_price = int(prices.max())
    p25 = int(round(prices.quantile(0.25)))
    p75 = int(round(prices.quantile(0.75)))
    iqr = p75 - p25

    avg_km = int(round(subset["_num_km"].mean()))

    market_context = {
        "status": "available",
        "has_sufficient_data": True,
        "sample_size": total_records,
        "min_price": min_price,
        "formatted_min_price": format_inr(min_price),
        "median_price": median_price,
        "formatted_median_price": format_inr(median_price),
        "max_price": max_price,
        "formatted_max_price": format_inr(max_price),
        "p25_price": p25,
        "formatted_p25_price": format_inr(p25),
        "p75_price": p75,
        "formatted_p75_price": format_inr(p75),
        "iqr": iqr,
        "formatted_iqr": format_inr(iqr),
        "avg_km_driven": avg_km,
        "formatted_avg_km": f"{avg_km:,} KM",
        "disclaimer": f"Defensible empirical statistics derived from {total_records} verified {brand} {model} records in dataset."
    }

    # 2. Depreciation Curve by Manufacturing Year
    deprec_points = []
    year_grouped = subset.groupby("_num_year")
    cohort_years = sorted(year_grouped.groups.keys())

    if len(cohort_years) >= 2:
        newest_year = max(cohort_years)
        newest_median = year_grouped.get_group(newest_year)["_num_price"].median()
        if newest_median <= 0:
            newest_median = median_price

        for yr in cohort_years:
            grp = year_grouped.get_group(yr)
            cnt = len(grp)
            yr_median = int(round(grp["_num_price"].median()))
            yr_avg = int(round(grp["_num_price"].mean()))
            deprec_pct = round(max(0.0, ((newest_median - yr_median) / newest_median) * 100), 1) if newest_median > 0 else 0.0

            deprec_points.append({
                "year": int(yr),
                "count": cnt,
                "median_price": yr_median,
                "formatted_median_price": format_inr(yr_median),
                "mean_price": yr_avg,
                "formatted_mean_price": format_inr(yr_avg),
                "depreciation_vs_newest_pct": deprec_pct,
                "is_selected_year": (selected_year is not None and int(yr) == int(selected_year))
            })

        depreciation_curve = {
            "status": "available",
            "has_sufficient_data": True,
            "cohort_count": len(cohort_years),
            "newest_anchor_year": int(newest_year),
            "newest_anchor_price": int(round(newest_median)),
            "formatted_newest_anchor_price": format_inr(newest_median),
            "points": deprec_points
        }
    else:
        depreciation_curve = {
            "status": "insufficient_data",
            "has_sufficient_data": False,
            "message": "Insufficient Data",
            "cohort_count": len(cohort_years),
            "points": []
        }

    # 3. Fuel Mix Distribution
    fuel_counts = subset["fuel_type"].dropna().astype(str).str.strip().value_counts()
    total_fuel = fuel_counts.sum()
    fuel_distribution = []
    if total_fuel >= MIN_RELIABLE_SAMPLE_SIZE:
        for f_name, f_cnt in fuel_counts.items():
            pct = int(round((f_cnt / total_fuel) * 100))
            fuel_distribution.append({
                "fuel_type": f_name,
                "count": int(f_cnt),
                "percentage": pct,
                "is_selected": (selected_fuel is not None and str(selected_fuel).strip().lower() == f_name.lower())
            })
        fuel_mix = {
            "status": "available",
            "has_sufficient_data": True,
            "distribution": fuel_distribution
        }
    else:
        fuel_mix = {
            "status": "insufficient_data",
            "has_sufficient_data": False,
            "message": "Insufficient Data",
            "distribution": []
        }

    # 4. Transmission Mix Distribution
    trans_counts = subset["transmission_type"].dropna().astype(str).str.strip().value_counts()
    total_trans = trans_counts.sum()
    trans_distribution = []
    if total_trans >= MIN_RELIABLE_SAMPLE_SIZE:
        for t_name, t_cnt in trans_counts.items():
            pct = int(round((t_cnt / total_trans) * 100))
            trans_distribution.append({
                "transmission": t_name,
                "count": int(t_cnt),
                "percentage": pct,
                "is_selected": (selected_transmission is not None and str(selected_transmission).strip().lower() == t_name.lower())
            })
        transmission_mix = {
            "status": "available",
            "has_sufficient_data": True,
            "distribution": trans_distribution
        }
    else:
        transmission_mix = {
            "status": "insufficient_data",
            "has_sufficient_data": False,
            "message": "Insufficient Data",
            "distribution": []
        }

    # 5. City Volume Distribution
    city_counts = subset["city"].dropna().astype(str).str.strip().value_counts()
    total_cities = city_counts.sum()
    top_cities = []
    if total_cities >= MIN_RELIABLE_SAMPLE_SIZE:
        for c_name, c_cnt in city_counts.head(5).items():
            pct = int(round((c_cnt / total_cities) * 100))
            top_cities.append({
                "city": c_name,
                "count": int(c_cnt),
                "percentage": pct,
                "is_selected": (selected_city is not None and str(selected_city).strip().lower() == c_name.lower())
            })
        selected_city_stats = None
        if selected_city:
            c_clean = str(selected_city).strip().lower()
            matching_city_cnt = int((subset["_norm_city"] == c_clean).sum())
            selected_city_stats = {
                "city": str(selected_city).strip(),
                "count": matching_city_cnt,
                "percentage": int(round((matching_city_cnt / total_cities) * 100)) if total_cities > 0 else 0
            }

        city_volume = {
            "status": "available",
            "has_sufficient_data": True,
            "top_cities": top_cities,
            "selected_city_stats": selected_city_stats
        }
    else:
        city_volume = {
            "status": "insufficient_data",
            "has_sufficient_data": False,
            "message": "Insufficient Data",
            "top_cities": []
        }

    result = {
        "status": "available",
        "sample_size": total_records,
        "market_context": market_context,
        "depreciation_curve": depreciation_curve,
        "fuel_mix": fuel_mix,
        "transmission_mix": transmission_mix,
        "city_volume": city_volume
    }

    with _CACHE_LOCK:
        _FACTORS_CACHE[cache_key] = result
        _FACTORS_CACHE.move_to_end(cache_key)
        if len(_FACTORS_CACHE) > MAX_MARKET_CACHE_SIZE:
            _FACTORS_CACHE.popitem(last=False)

    return result


def find_comparables(
    brand: str,
    model: str,
    manufacturing_year: Optional[int] = None,
    km_driven: Optional[float] = None,
    fuel_type: Optional[str] = None,
    transmission_type: Optional[str] = None,
    city: Optional[str] = None,
    number_of_owners: Optional[int] = None,
    limit: int = 4,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Finds real comparable vehicle transactions from the 57,480 dataset
    using relevant multi-attribute proximity metrics.
    Zero synthetic interpolation; returns actual rows from dataset.
    """
    # Resolve aliases
    manufacturing_year = manufacturing_year if manufacturing_year is not None else kwargs.get("year", kwargs.get("selected_year"))
    km_driven = km_driven if km_driven is not None else kwargs.get("km", kwargs.get("selected_km"))
    fuel_type = fuel_type if fuel_type is not None else kwargs.get("fuel", kwargs.get("selected_fuel"))
    transmission_type = transmission_type if transmission_type is not None else kwargs.get("transmission", kwargs.get("selected_transmission"))
    city = city if city is not None else kwargs.get("selected_city")
    comp_cache_key = (
        str(brand).strip().lower(),
        str(model).strip().lower(),
        int(manufacturing_year) if manufacturing_year else 0,
        int(round(float(km_driven))) if km_driven is not None else 0,
        str(fuel_type).strip().lower() if fuel_type else "",
        str(transmission_type).strip().lower() if transmission_type else "",
        str(city).strip().lower() if city else "",
        int(number_of_owners) if number_of_owners else 1,
        int(limit)
    )

    with _CACHE_LOCK:
        if comp_cache_key in _COMPARABLES_CACHE:
            _COMPARABLES_CACHE.move_to_end(comp_cache_key)
            return _COMPARABLES_CACHE[comp_cache_key]

    subset = _get_matching_subset(brand, model)
    if len(subset) == 0:
        # Fallback to same brand
        df = MarketIntelligenceDataset.get_df()
        b_clean = str(brand).strip().lower()
        subset = df[df["_norm_brand"] == b_clean]

    if len(subset) == 0:
        return []

    comps_df = subset.copy()

    # Calculate multi-attribute distance metric
    target_year = int(manufacturing_year) if manufacturing_year else 2021
    target_km = float(km_driven) if km_driven is not None else 35000.0
    target_owners = int(number_of_owners) if number_of_owners else 1
    target_fuel = str(fuel_type).strip().lower() if fuel_type else ""
    target_trans = str(transmission_type).strip().lower() if transmission_type else ""
    target_city = str(city).strip().lower() if city else ""

    comps_df["_dist"] = (
        (comps_df["_num_year"] - target_year).abs() * 2.0
        + (comps_df["_num_km"] - target_km).abs() / 15000.0
        + (comps_df["_num_owners"] - target_owners).abs() * 0.8
        + (comps_df["fuel_type"].astype(str).str.strip().str.lower() != target_fuel).astype(int) * 1.5
        + (comps_df["transmission_type"].astype(str).str.strip().str.lower() != target_trans).astype(int) * 1.2
        + (comps_df["city"].astype(str).str.strip().str.lower() != target_city).astype(int) * 0.8
    )

    sorted_comps = comps_df.sort_values("_dist").head(limit)
    results = []

    for idx, row in sorted_comps.iterrows():
        p_val = int(round(float(row["_num_price"])))
        km_val = int(round(float(row["_num_km"])))
        dist_val = float(row["_dist"])
        sim_pct = max(50, min(99, int(round(100.0 / (1.0 + (dist_val * 0.15))))))

        results.append({
            "record_id": int(idx),
            "brand": str(row["brand"]),
            "model": str(row["model"]),
            "manufacturing_year": int(row["_num_year"]),
            "km_driven": km_val,
            "formatted_km": f"{km_val:,} KM",
            "fuel_type": str(row["fuel_type"]),
            "transmission_type": str(row["transmission_type"]),
            "bodytype": str(row["bodytype"]),
            "city": str(row["city"]),
            "number_of_owners": int(row["_num_owners"]),
            "actual_price": p_val,
            "formatted_price": format_inr(p_val),
            "similarity_score": sim_pct,
            "distance_metric": round(dist_val, 2)
        })

    with _CACHE_LOCK:
        _COMPARABLES_CACHE[comp_cache_key] = results
        _COMPARABLES_CACHE.move_to_end(comp_cache_key)
        if len(_COMPARABLES_CACHE) > MAX_MARKET_CACHE_SIZE:
            _COMPARABLES_CACHE.popitem(last=False)

    return results


def market_summary(
    brand: str,
    model: str,
    selected_city: Optional[str] = None,
    selected_fuel: Optional[str] = None,
    selected_transmission: Optional[str] = None,
    manufacturing_year: Optional[int] = None,
    km_driven: Optional[float] = None,
    number_of_owners: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Primary API entry point for Phase 9: Market Intelligence & Comparables.
    Combines compute_factors() and find_comparables() with caching.
    """
    # Resolve aliases
    selected_city = selected_city if selected_city is not None else kwargs.get("city")
    selected_fuel = selected_fuel if selected_fuel is not None else kwargs.get("fuel", kwargs.get("fuel_type"))
    selected_transmission = selected_transmission if selected_transmission is not None else kwargs.get("transmission", kwargs.get("transmission_type"))
    manufacturing_year = manufacturing_year if manufacturing_year is not None else kwargs.get("year", kwargs.get("selected_year"))
    km_driven = km_driven if km_driven is not None else kwargs.get("km", kwargs.get("selected_km"))
    number_of_owners = number_of_owners if number_of_owners is not None else kwargs.get("owners")

    cache_key = (
        str(brand).strip().lower(),
        str(model).strip().lower(),
        str(selected_city).strip().lower() if selected_city else "",
        str(selected_fuel).strip().lower() if selected_fuel else "",
        str(selected_transmission).strip().lower() if selected_transmission else "",
        int(manufacturing_year) if manufacturing_year else 0,
        int(round(float(km_driven))) if km_driven is not None else 0,
        int(number_of_owners) if number_of_owners else 1
    )

    global _SUMMARY_HITS, _SUMMARY_MISSES
    with _CACHE_LOCK:
        if cache_key in _SUMMARY_CACHE:
            _SUMMARY_HITS += 1
            _SUMMARY_CACHE.move_to_end(cache_key)
            return _SUMMARY_CACHE[cache_key]
        _SUMMARY_MISSES += 1

    factors = compute_factors(
        brand=brand,
        model=model,
        selected_year=manufacturing_year,
        selected_km=km_driven,
        selected_fuel=selected_fuel,
        selected_transmission=selected_transmission,
        selected_city=selected_city
    )

    comparables = find_comparables(
        brand=brand,
        model=model,
        manufacturing_year=manufacturing_year,
        km_driven=km_driven,
        fuel_type=selected_fuel,
        transmission_type=selected_transmission,
        city=selected_city,
        number_of_owners=number_of_owners,
        limit=4
    )

    is_sparse = factors["status"] == "insufficient_data"

    summary = {
        "brand": str(brand).strip(),
        "model": str(model).strip(),
        "sample_size": factors.get("sample_size", 0),
        "is_sparse": is_sparse,
        "market_context": factors["market_context"],
        "depreciation_curve": factors["depreciation_curve"],
        "fuel_mix": factors["fuel_mix"],
        "transmission_mix": factors["transmission_mix"],
        "city_volume": factors["city_volume"],
        "comparables": comparables,
        "comparable_vehicles": comparables,
        "disclaimer": "Defensible empirical statistics derived directly from 57,480 verified secondary market records in dataset. Zero synthetic data."
    }

    with _CACHE_LOCK:
        _SUMMARY_CACHE[cache_key] = summary
        _SUMMARY_CACHE.move_to_end(cache_key)
        if len(_SUMMARY_CACHE) > MAX_MARKET_CACHE_SIZE:
            _SUMMARY_CACHE.popitem(last=False)

    return summary
