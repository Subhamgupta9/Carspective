"""
CARspective — Phase 17 Market Deduplication Engine
Detects exact and probable duplicate vehicle observations using non-sensitive signals.
Enforces zero silent merging: duplicate records remain auditable but flagged for analytical exclusion.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict, Any
from .current_models import DuplicateClassification


class MarketDeduplicationEngine:
    """
    Deterministic deduplication evaluator for incoming vehicle market observations.
    Never silently merges uncertain records.
    """

    EXACT_TIME_WINDOW_DAYS = 7
    PROBABLE_TIME_WINDOW_DAYS = 14
    PROBABLE_PRICE_TOLERANCE_RATIO = 0.015 # 1.5%
    PROBABLE_MILEAGE_TOLERANCE_KM = 500.0

    @classmethod
    def evaluate_duplicate(
        cls,
        candidate: Dict[str, Any],
        existing_observations: List[Dict[str, Any]],
    ) -> Tuple[DuplicateClassification, Optional[str]]:
        """
        Evaluates a candidate record against a pool of existing observations.
        Returns (classification, duplicate_of_id).
        """
        cand_source = candidate.get("source_id", "")
        cand_ref = candidate.get("source_record_reference", "")
        cand_vehicle_id = candidate.get("canonical_vehicle_id", "")
        cand_price = float(candidate.get("asking_price", 0.0))
        cand_year = int(candidate.get("model_year", 0))
        cand_mileage = float(candidate.get("mileage", 0.0))
        cand_city = (candidate.get("location_city") or "").strip().lower()
        cand_trans = (candidate.get("transmission") or "").strip().lower()
        cand_fuel = (candidate.get("fuel_type") or "").strip().lower()
        
        cand_obs_time = candidate.get("observed_at")
        if isinstance(cand_obs_time, str):
            try:
                cand_obs_time = datetime.fromisoformat(cand_obs_time.replace("Z", "+00:00"))
            except Exception:
                cand_obs_time = datetime.now(timezone.utc)
        elif not isinstance(cand_obs_time, datetime):
            cand_obs_time = datetime.now(timezone.utc)

        # 1. Exact Source Listing Duplicate check
        for obs in existing_observations:
            obs_id = obs.get("observation_id") or obs.get("id")
            if (
                obs.get("source_id") == cand_source
                and obs.get("source_record_reference") == cand_ref
            ):
                return DuplicateClassification.EXACT_DUPLICATE, obs_id

        # 2. Exact Vehicle Metric Duplicate check
        for obs in existing_observations:
            obs_id = obs.get("observation_id") or obs.get("id")
            if obs.get("canonical_vehicle_id") != cand_vehicle_id:
                continue

            obs_price = float(obs.get("asking_price", 0.0))
            obs_year = int(obs.get("model_year", 0))
            obs_mileage = float(obs.get("mileage", 0.0))
            obs_city = (obs.get("location_city") or "").strip().lower()

            obs_time = obs.get("observed_at")
            if isinstance(obs_time, str):
                try:
                    obs_time = datetime.fromisoformat(obs_time.replace("Z", "+00:00"))
                except Exception:
                    obs_time = cand_obs_time
            elif not isinstance(obs_time, datetime):
                obs_time = cand_obs_time

            # Normalize timezone between cand_obs_time and obs_time
            if isinstance(obs_time, datetime) and isinstance(cand_obs_time, datetime):
                if obs_time.tzinfo is None and cand_obs_time.tzinfo is not None:
                    obs_time = obs_time.replace(tzinfo=cand_obs_time.tzinfo)
                elif obs_time.tzinfo is not None and cand_obs_time.tzinfo is None:
                    obs_time = obs_time.replace(tzinfo=None)

            # Same vehicle, year, exact price, exact mileage, same city within 7 days
            if (
                obs_year == cand_year
                and abs(obs_price - cand_price) < 1.0
                and abs(obs_mileage - cand_mileage) < 1.0
                and obs_city == cand_city
            ):
                time_delta = abs((cand_obs_time - obs_time).total_seconds()) / 86400.0
                if time_delta <= cls.EXACT_TIME_WINDOW_DAYS:
                    return DuplicateClassification.EXACT_DUPLICATE, obs_id

        # 3. Probable Cross-Source Duplicate check
        for obs in existing_observations:
            obs_id = obs.get("observation_id") or obs.get("id")
            if obs.get("canonical_vehicle_id") != cand_vehicle_id:
                continue

            obs_price = float(obs.get("asking_price", 0.0))
            obs_year = int(obs.get("model_year", 0))
            obs_mileage = float(obs.get("mileage", 0.0))
            obs_trans = (obs.get("transmission") or "").strip().lower()
            obs_fuel = (obs.get("fuel_type") or "").strip().lower()

            obs_time = obs.get("observed_at")
            if isinstance(obs_time, str):
                try:
                    obs_time = datetime.fromisoformat(obs_time.replace("Z", "+00:00"))
                except Exception:
                    obs_time = cand_obs_time
            elif not isinstance(obs_time, datetime):
                obs_time = cand_obs_time

            # Normalize timezone between cand_obs_time and obs_time
            if isinstance(obs_time, datetime) and isinstance(cand_obs_time, datetime):
                if obs_time.tzinfo is None and cand_obs_time.tzinfo is not None:
                    obs_time = obs_time.replace(tzinfo=cand_obs_time.tzinfo)
                elif obs_time.tzinfo is not None and cand_obs_time.tzinfo is None:
                    obs_time = obs_time.replace(tzinfo=None)

            if (
                obs_year == cand_year
                and obs_trans == cand_trans
                and obs_fuel == cand_fuel
            ):
                price_diff_ratio = abs(obs_price - cand_price) / max(cand_price, 1.0)
                mileage_diff_km = abs(obs_mileage - cand_mileage)
                time_delta = abs((cand_obs_time - obs_time).total_seconds()) / 86400.0

                if (
                    price_diff_ratio <= cls.PROBABLE_PRICE_TOLERANCE_RATIO
                    and mileage_diff_km <= cls.PROBABLE_MILEAGE_TOLERANCE_KM
                    and time_delta <= cls.PROBABLE_TIME_WINDOW_DAYS
                ):
                    return DuplicateClassification.PROBABLE_DUPLICATE, obs_id

        return DuplicateClassification.DISTINCT, None
