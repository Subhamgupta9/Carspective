"""
CARspective — Vehicle-Aware Checklist Applicability Engine
Determines which canonical inspection items are applicable based on vehicle attributes
(transmission, fuel type, age, mileage, owner count) and elevates priorities based on
user context without altering objective inspection facts.
"""

from typing import List, Optional
from datetime import datetime
from server.domain.inspection.models import (
    ChecklistItem,
    InspectionVehicleContext,
    UserInspectionProfile,
    ImportanceLevel,
    InspectionCategory,
)
from server.domain.inspection.checklist import CANONICAL_CHECKLIST_CATALOG

CURRENT_YEAR = 2026


class ChecklistApplicabilityEngine:
    """Adapts canonical checklist items to vehicle context and user priorities."""

    @staticmethod
    def generate_adaptive_checklist(
        vehicle: InspectionVehicleContext,
        user_profile: Optional[UserInspectionProfile] = None,
    ) -> List[ChecklistItem]:
        """
        Filters and tailors canonical checklist:
        1. Excludes non-applicable powertrain / transmission items.
        2. Applies age and mileage importance elevation.
        3. Flags items aligned with user-stated buyer priorities.
        """
        trans_str = (vehicle.transmission_type or "Manual").upper()
        is_manual = "MANUAL" in trans_str
        is_auto = any(a in trans_str for a in ["AUTO", "AUTOMATIC", "AMT", "CVT", "DCT", "DSG", "TORQUE"])

        fuel_str = (vehicle.fuel_type or "Petrol").upper()
        is_diesel = "DIESEL" in fuel_str
        is_cng = "CNG" in fuel_str
        is_ev = "ELECTRIC" in fuel_str or "EV" in fuel_str

        car_year = vehicle.manufacturing_year or 2019
        vehicle_age = max(0, CURRENT_YEAR - car_year)
        is_older_vehicle = vehicle_age >= 7

        km = vehicle.km_driven or 45000.0
        is_high_mileage = km >= 90000.0

        owners = vehicle.number_of_owners or 1
        is_multi_owner = owners >= 3

        up = user_profile or UserInspectionProfile()

        adapted_items: List[ChecklistItem] = []

        for item in CANONICAL_CHECKLIST_CATALOG:
            # 1. Applicability Filtering
            app = item.applicable_to.upper()
            if app == "MANUAL" and not is_manual:
                continue
            if app == "AUTOMATIC" and not is_auto:
                continue
            if app == "DIESEL" and not is_diesel:
                continue
            if app == "CNG" and not is_cng:
                continue
            if app == "EV" and not is_ev:
                continue

            # Clone item to preserve immutability of catalog
            item_copy = item.model_copy(deep=True)

            # 2. Vehicle-attribute elevation
            if is_older_vehicle:
                if item.item_id in [
                    "EXT_DENTS_SCRATCHES_CORROSION",
                    "UND_FLOOR_PAN_CORROSION_SCRAPES",
                    "UND_SUSPENSION_STRUTS_BUSHINGS",
                    "ENG_FLUID_LEAKS_INSPECTION",
                ]:
                    item_copy.importance = ImportanceLevel.HIGH
                    item_copy.notes = f"{item_copy.notes or ''} [Elevated due to vehicle age: {vehicle_age} years old]".strip()

            if is_high_mileage:
                if item.item_id in [
                    "DOC_ODOMETER_CONSISTENCY",
                    "ENG_OIL_CAP_BLOWBY",
                    "TRANS_MANUAL_CLUTCH_BITE",
                    "TRANS_AUTOMATIC_SHIFT_QUALITY",
                    "UND_SUBFRAME_STEERING_RACK",
                ]:
                    item_copy.importance = ImportanceLevel.CRITICAL
                    item_copy.notes = f"{item_copy.notes or ''} [Elevated due to high odometer reading: {km:,.0f} km]".strip()

            if is_multi_owner:
                if item.item_id in [
                    "DOC_OWNERSHIP_CHAIN",
                    "DOC_SERVICE_HISTORY_RECORDS",
                    "DOC_INSURANCE_CLAIM_HISTORY",
                ]:
                    item_copy.importance = ImportanceLevel.CRITICAL
                    item_copy.notes = f"{item_copy.notes or ''} [Elevated due to multiple prior owners: {owners}]".strip()

            # 3. User context priority boosting (does NOT change objective facts)
            user_boost = False
            if up.safety_priority in ("HIGH", "CRITICAL") or up.family_orientation:
                if item.category in (InspectionCategory.SAFETY, InspectionCategory.UNDERBODY_AND_STRUCTURE) or item.item_id in [
                    "INT_FLOOD_DAMAGE_WATERLINES",
                    "DRV_BRAKING_STABILITY_JUDDER",
                    "DRV_STEERING_CENTERING_PULL",
                    "EXT_TYRE_TREAD_UNEVEN_WEAR",
                ]:
                    user_boost = True

            if (up.daily_commute_km or 0) >= 40.0:
                if item.item_id in [
                    "ENG_COLD_START_CRANKING",
                    "ENG_IDLE_STABILITY_VIBRATION",
                    "INT_HVAC_AIR_CONDITIONING",
                    "DRV_ENGINE_THERMAL_GAUGE",
                    "EXT_TYRE_TREAD_UNEVEN_WEAR",
                ]:
                    user_boost = True

            if up.budget_sensitivity == "HIGH":
                if item.severity_if_failed == ImportanceLevel.CRITICAL or item.item_id in [
                    "TRANS_AUTOMATIC_SHIFT_QUALITY",
                    "ENG_EXHAUST_SMOKE_COLOR",
                    "INT_FLOOD_DAMAGE_WATERLINES",
                    "UND_CHASSIS_RAIL_CRUMPLE_ZONES",
                ]:
                    user_boost = True

            item_copy.user_priority_elevated = user_boost
            adapted_items.append(item_copy)

        return adapted_items
