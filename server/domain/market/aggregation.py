"""
CARspective — Phase 17 Current Market Aggregation Engine
Computes statistical distributions, percentile intervals, regional supply,
liquidity indicators, and historical-vs-current comparative dynamics.

Performance Target: Aggregation of 10,000 observations in < 2.0 seconds.
"""

from typing import List, Dict, Any, Optional
import numpy as np

from .current_models import (
    CurrentPriceDistribution,
    CurrentMarketSupply,
    CurrentRegionalIntelligence,
    CurrentVsHistoricalComparison,
    CurrentSupplyTier,
)


class CurrentMarketAggregationEngine:
    """
    High-performance statistical aggregation engine for current market observations.
    Vectorized percentile evaluation with zero silent hallucination.
    """

    @classmethod
    def calculate_price_distribution(
        cls,
        observations: List[Dict[str, Any]],
        canonical_vehicle_id: str,
    ) -> Optional[CurrentPriceDistribution]:
        """
        Computes robust asking-price distribution over analytically eligible observations.
        """
        eligible_prices = [
            float(o.get("asking_price", 0.0))
            for o in observations
            if o.get("analytical_eligibility", True)
            and not o.get("is_outlier", False)
            and o.get("duplicate_status", "DISTINCT") == "DISTINCT"
        ]

        if len(eligible_prices) < 2:
            return None

        arr = np.array(eligible_prices, dtype=np.float64)
        min_p = float(np.min(arr))
        p10_p = float(np.percentile(arr, 10))
        p25_p = float(np.percentile(arr, 25))
        p50_p = float(np.percentile(arr, 50))
        p75_p = float(np.percentile(arr, 75))
        p90_p = float(np.percentile(arr, 90))
        max_p = float(np.max(arr))
        iqr_p = float(p75_p - p25_p)
        std_p = float(np.std(arr))
        mean_p = float(np.mean(arr))

        return CurrentPriceDistribution(
            canonical_vehicle_id=canonical_vehicle_id,
            sample_size=len(arr),
            min_price_inr=round(min_p, 2),
            p10_price_inr=round(p10_p, 2),
            p25_price_inr=round(p25_p, 2),
            median_price_inr=round(p50_p, 2),
            p75_price_inr=round(p75_p, 2),
            p90_price_inr=round(p90_p, 2),
            max_price_inr=round(max_p, 2),
            iqr_inr=round(iqr_p, 2),
            std_dev_price_inr=round(std_p, 2),
            mean_price_inr=round(mean_p, 2),
        )

    @classmethod
    def calculate_supply(
        cls,
        observations: List[Dict[str, Any]],
        canonical_vehicle_id: str,
    ) -> CurrentMarketSupply:
        """
        Computes supply metrics and inventory breakdowns across eligible records.
        """
        total_count = len(observations)
        eligible = [
            o for o in observations
            if o.get("analytical_eligibility", True)
            and not o.get("is_outlier", False)
            and o.get("duplicate_status", "DISTINCT") == "DISTINCT"
        ]
        usable_count = len(eligible)

        if usable_count >= 25:
            tier = CurrentSupplyTier.STRONG_CURRENT_SUPPLY
        elif usable_count >= 10:
            tier = CurrentSupplyTier.MODERATE_CURRENT_SUPPLY
        elif usable_count >= 1:
            tier = CurrentSupplyTier.LIMITED_CURRENT_SUPPLY
        else:
            tier = CurrentSupplyTier.INSUFFICIENT_CURRENT_DATA

        reg_counts: Dict[str, int] = {}
        seller_counts: Dict[str, int] = {}
        freshness_counts: Dict[str, int] = {}

        for o in eligible:
            r = o.get("location_region") or o.get("location_city") or "Other Regions"
            reg_counts[r] = reg_counts.get(r, 0) + 1

            s = o.get("seller_type") or "DEALER"
            seller_counts[s] = seller_counts.get(s, 0) + 1

            f = o.get("freshness_state") or "CURRENT"
            freshness_counts[f] = freshness_counts.get(f, 0) + 1

        return CurrentMarketSupply(
            canonical_vehicle_id=canonical_vehicle_id,
            total_observation_count=total_count,
            usable_observation_count=usable_count,
            supply_tier=tier,
            regional_supply=reg_counts,
            seller_distribution=seller_counts,
            freshness_distribution=freshness_counts,
            observation_period="2026-Q3 (Current Market Observations)",
            coverage_scope="Observed in available source coverage",
        )

    @classmethod
    def calculate_regional(
        cls,
        observations: List[Dict[str, Any]],
    ) -> List[CurrentRegionalIntelligence]:
        """
        Groups eligible observations by region and computes regional medians.
        """
        eligible = [
            o for o in observations
            if o.get("analytical_eligibility", True)
            and not o.get("is_outlier", False)
            and o.get("duplicate_status", "DISTINCT") == "DISTINCT"
        ]

        regions_map: Dict[str, List[Dict[str, Any]]] = {}
        for o in eligible:
            reg = o.get("location_region") or o.get("location_city")
            if reg:
                regions_map.setdefault(reg, []).append(o)

        results: List[CurrentRegionalIntelligence] = []
        for reg_name, obs_list in sorted(regions_map.items()):
            prices = [float(x.get("asking_price", 0.0)) for x in obs_list]
            kms = [float(x.get("mileage", 0.0)) for x in obs_list]

            if len(prices) >= 2:
                p_arr = np.array(prices, dtype=np.float64)
                k_arr = np.array(kms, dtype=np.float64)

                results.append(
                    CurrentRegionalIntelligence(
                        region_name=reg_name,
                        observation_count=len(obs_list),
                        median_asking_price_inr=round(float(np.percentile(p_arr, 50)), 2),
                        iqr_low_inr=round(float(np.percentile(p_arr, 25)), 2),
                        iqr_high_inr=round(float(np.percentile(p_arr, 75)), 2),
                        median_mileage_km=round(float(np.percentile(k_arr, 50)), 0),
                    )
                )
            elif len(prices) == 1:
                results.append(
                    CurrentRegionalIntelligence(
                        region_name=reg_name,
                        observation_count=1,
                        median_asking_price_inr=round(prices[0], 2),
                        iqr_low_inr=round(prices[0], 2),
                        iqr_high_inr=round(prices[0], 2),
                        median_mileage_km=round(kms[0], 0),
                    )
                )

        return results

    @classmethod
    def compare_with_historical(
        cls,
        canonical_vehicle_id: str,
        current_distribution: Optional[CurrentPriceDistribution],
        historical_sample_size: int,
        historical_median_price: float,
    ) -> Optional[CurrentVsHistoricalComparison]:
        """
        Builds transparent comparison separating historical 2018–2024 baseline from current 2026-Q3 observations.
        """
        if not current_distribution or historical_median_price <= 0:
            return None

        curr_med = current_distribution.median_price_inr
        shift_pct = round(((curr_med - historical_median_price) / historical_median_price) * 100, 2)

        if shift_pct > 5.0:
            ctx = f"Current observed asking median (₹{curr_med:,.0f}) is trending +{shift_pct:.1f}% above historical secondary market baseline (₹{historical_median_price:,.0f})."
        elif shift_pct < -5.0:
            ctx = f"Current observed asking median (₹{curr_med:,.0f}) is trending {shift_pct:.1f}% below historical secondary market baseline (₹{historical_median_price:,.0f})."
        else:
            ctx = f"Current observed asking median (₹{curr_med:,.0f}) is closely tracking historical secondary market baseline (within {abs(shift_pct):.1f}%)."

        return CurrentVsHistoricalComparison(
            canonical_vehicle_id=canonical_vehicle_id,
            historical_observation_period="2018–2024 (57,480 Historical Listings Baseline)",
            historical_sample_size=historical_sample_size,
            historical_median_asking_price_inr=historical_median_price,
            current_observation_period="2026-Q3 (Current Market Observations)",
            current_sample_size=current_distribution.sample_size,
            current_median_asking_price_inr=curr_med,
            asking_price_shift_pct=shift_pct,
            supply_context=ctx,
        )
