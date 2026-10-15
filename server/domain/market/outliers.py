"""
CARspective — Phase 17 Market Outlier Governance Engine
Identifies data entry errors, scrap listings, extreme distortions, and unrealistic prices.
Maintains raw observation lineage: records are NEVER deleted, but flagged with analytical ineligibility.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone


class MarketOutlierEngine:
    """
    Deterministic outlier evaluator for current market observations.
    Preserves raw data integrity for audits while ensuring analytical robustness.
    """

    MIN_REALISTIC_PRICE_INR = 25_000.0        # Less than ₹25k is scrap/down-payment artifact
    MAX_REALISTIC_PRICE_INR = 100_000_000.0   # ₹10 Crore absolute ceiling
    MIN_MANUFACTURING_YEAR = 1995
    MAX_ALLOWABLE_MILEAGE_KM = 600_000.0

    @classmethod
    def evaluate_outlier(
        cls,
        record: Dict[str, Any],
        model_typical_price: float = 0.0,
    ) -> Tuple[bool, List[str], bool]:
        """
        Evaluates a market observation record.
        Returns:
            (is_outlier, outlier_reasons, analytical_eligibility)
        """
        reasons: List[str] = []
        current_year = datetime.now(timezone.utc).year

        price = float(record.get("asking_price", 0.0))
        year = int(record.get("model_year", 0))
        mileage = float(record.get("mileage", 0.0))

        # 1. Absolute Price Sanity Checks
        if price < cls.MIN_REALISTIC_PRICE_INR:
            reasons.append(
                f"Asking price ₹{price:,.0f} is below the minimum realistic threshold (₹{cls.MIN_REALISTIC_PRICE_INR:,.0f}). Possible token booking fee or scrap listing."
            )
        elif price > cls.MAX_REALISTIC_PRICE_INR:
            reasons.append(
                f"Asking price ₹{price:,.0f} exceeds maximum realistic ceiling (₹{cls.MAX_REALISTIC_PRICE_INR:,.0f}). Extreme pricing anomaly."
            )

        # 2. Year Sanity Checks
        if year < cls.MIN_MANUFACTURING_YEAR:
            reasons.append(
                f"Manufacturing year {year} precedes modern secondary market baseline ({cls.MIN_MANUFACTURING_YEAR}). Vintage or erroneous entry."
            )
        elif year > current_year + 1:
            reasons.append(
                f"Manufacturing year {year} is in the implausible future (current year: {current_year})."
            )

        # 3. Mileage Sanity Checks
        car_age = max(0, current_year - year)
        if car_age >= 2 and mileage < 100.0:
            reasons.append(
                f"Vehicle is {car_age} years old but odometer reads {mileage:.0f} km. Probable odometer reset or placeholder entry."
            )
        elif mileage > cls.MAX_ALLOWABLE_MILEAGE_KM:
            reasons.append(
                f"Mileage {mileage:,.0f} km exceeds realistic passenger vehicle operational threshold ({cls.MAX_ALLOWABLE_MILEAGE_KM:,.0f} km)."
            )

        # 4. Model Relative Price Dispersion Check
        if model_typical_price > 0:
            min_ratio = 0.20
            max_ratio = 4.00
            if price < model_typical_price * min_ratio:
                reasons.append(
                    f"Asking price ₹{price:,.0f} is suspiciously low (< {min_ratio*100:.0f}% of typical {record.get('canonical_vehicle_id')} baseline ₹{model_typical_price:,.0f}). Probable total loss salvage or fake listing."
                )
            elif price > model_typical_price * max_ratio:
                reasons.append(
                    f"Asking price ₹{price:,.0f} is suspiciously high (> {max_ratio*100:.0f}% of typical {record.get('canonical_vehicle_id')} baseline ₹{model_typical_price:,.0f}). Extreme speculative listing."
                )

        is_outlier = len(reasons) > 0
        analytical_eligibility = not is_outlier

        return is_outlier, reasons, analytical_eligibility
