"""
CARspective — Phase 15 Natural Language Requirements Parser
Deterministic, pattern-grounded parser converting conversational buyer statements
into structured UserRequirementsProfile with strict field-level provenance.
Zero hidden profiling. Zero sensitive attribute inference.
"""

import re
import time
from typing import Tuple, List, Dict, Any, Optional
from server.domain.decision.models import (
    UserRequirementsProfile,
    PurchaseType,
    UsageProfile,
    PriorityLevel,
    ToleranceLevel,
    ProvenanceState,
    NaturalLanguageRequirementsResponse,
)


class NaturalLanguageRequirementsParser:
    """Deterministic extractor converting plain-language user requests into decision profiles."""

    @classmethod
    def parse(cls, statement: str) -> NaturalLanguageRequirementsResponse:
        t0 = time.perf_counter()
        clean_text = statement.strip()
        lower_text = clean_text.lower()

        profile = UserRequirementsProfile()
        clarifications: List[str] = []
        extracted_count = 0

        # 1. Budget Extraction
        # Patterns like: "between 8 and 12 lakh", "under 10 lakh", "below 7.5 lakhs", "max 15l", "budget 8 lakh"
        between_match = re.search(r"\b(?:between|from)\s+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:and|to|-)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b", lower_text)
        if between_match:
            min_val = float(between_match.group(1)) * 100000
            max_val = float(between_match.group(2)) * 100000
            profile.budget_min_inr = min_val
            profile.budget_max_inr = max_val
            profile.set_provenance("budget_min_inr", ProvenanceState.USER_EXPLICIT, source_phrase=between_match.group(0))
            profile.set_provenance("budget_max_inr", ProvenanceState.USER_EXPLICIT, source_phrase=between_match.group(0))
            extracted_count += 2
        else:
            under_match = re.search(r"\b(?:under|below|less than|within|upto|up to|max(?:imum)?|budget(?:\s*of)?)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b", lower_text)
            if under_match:
                max_val = float(under_match.group(1)) * 100000
                profile.budget_max_inr = max_val
                profile.set_provenance("budget_max_inr", ProvenanceState.USER_EXPLICIT, source_phrase=under_match.group(0))
                extracted_count += 1
            else:
                # Raw number check e.g. "under 1000000" or "under 800000"
                raw_budget_match = re.search(r"\b(?:under|below|max)\s*(?:₹|rs\.?|inr)?\s*(\d{5,8})\b", lower_text)
                if raw_budget_match:
                    profile.budget_max_inr = float(raw_budget_match.group(1))
                    profile.set_provenance("budget_max_inr", ProvenanceState.USER_EXPLICIT, source_phrase=raw_budget_match.group(0))
                    extracted_count += 1

        # Ambiguity check for budget
        if profile.budget_max_inr and not profile.monthly_running_budget_max_inr:
            if "total cost" in lower_text or "overall budget" in lower_text or "tco" in lower_text:
                clarifications.append("Do you mean ₹{0:,.0f} acquisition purchase price or total multi-year ownership budget?".format(profile.budget_max_inr))
        elif re.search(r"\b(?:around|about|approx|nearly)\s*(\d{1,2})\b", lower_text) and not profile.budget_max_inr:
            clarifications.append("Could you clarify whether your target acquisition budget is in Lakhs (e.g., under 10 Lakh)?")
        elif re.search(r"\b(?:cheap|affordable|budget)\b", lower_text) and not profile.budget_max_inr:
            clarifications.append("Please specify your desired acquisition budget range in Lakhs.")

        # 2. Transmission Preference
        if re.search(r"\b(?:automatic|auto|amt|cvt|dsg|dct|torque converter)\b", lower_text):
            profile.transmission_preferences = ["Automatic"]
            profile.set_provenance("transmission_preferences", ProvenanceState.USER_EXPLICIT, source_phrase="automatic")
            extracted_count += 1
        elif re.search(r"\b(?:manual|stick|hand shift|mt)\b", lower_text):
            profile.transmission_preferences = ["Manual"]
            profile.set_provenance("transmission_preferences", ProvenanceState.USER_EXPLICIT, source_phrase="manual")
            extracted_count += 1

        # 3. Fuel Preference
        fuels_found = []
        if re.search(r"\b(?:petrol|gasoline)\b", lower_text):
            fuels_found.append("Petrol")
        if re.search(r"\b(?:diesel)\b", lower_text):
            fuels_found.append("Diesel")
        if re.search(r"\b(?:cng)\b", lower_text):
            fuels_found.append("CNG")
        if re.search(r"\b(?:electric|ev)\b", lower_text):
            fuels_found.append("Electric")

        if fuels_found:
            profile.fuel_preferences = fuels_found
            profile.set_provenance("fuel_preferences", ProvenanceState.USER_EXPLICIT, source_phrase=", ".join(fuels_found))
            extracted_count += 1

        # 4. Usage Profile
        if re.search(r"\b(?:city)\b", lower_text) and re.search(r"\b(?:highway|outstation|trips)\b", lower_text):
            profile.usage_profile = UsageProfile.MIXED
            profile.set_provenance("usage_profile", ProvenanceState.USER_EXPLICIT, source_phrase="city and highway")
            extracted_count += 1
        elif re.search(r"\b(?:city)\b", lower_text):
            profile.usage_profile = UsageProfile.CITY
            profile.set_provenance("usage_profile", ProvenanceState.USER_EXPLICIT, source_phrase="city")
            extracted_count += 1
        elif re.search(r"\b(?:highway|outstation|touring|long drive)\b", lower_text):
            profile.usage_profile = UsageProfile.HIGHWAY
            profile.set_provenance("usage_profile", ProvenanceState.USER_EXPLICIT, source_phrase="highway")
            extracted_count += 1
        elif re.search(r"\b(?:commute|traffic|daily commute|office run|local driving)\b", lower_text):
            profile.usage_profile = UsageProfile.CITY
            profile.set_provenance("usage_profile", ProvenanceState.USER_INFERRED, source_phrase="commute / local traffic")
            extracted_count += 1

        # 5. Body Type
        body_types = []
        body_explicit = False
        body_inferred = False
        if re.search(r"\b(?:suv|compact suv|crossover)\b", lower_text):
            body_types.append("SUV")
            body_explicit = True
        if re.search(r"\b(?:sedan)\b", lower_text):
            body_types.append("Sedan")
            body_explicit = True
        if re.search(r"\b(?:hatchback)\b", lower_text):
            body_types.append("Hatchback")
            body_explicit = True
        elif re.search(r"\b(?:small car)\b", lower_text):
            body_types.append("Hatchback")
            body_inferred = True
        if re.search(r"\b(?:mpv|muv|van)\b", lower_text):
            body_types.append("MUV")
            body_explicit = True

        if body_types:
            profile.body_type_preferences = body_types
            prov_state = ProvenanceState.USER_EXPLICIT if body_explicit else ProvenanceState.USER_INFERRED
            profile.set_provenance("body_type_preferences", prov_state, source_phrase=", ".join(body_types))
            extracted_count += 1

        # 6. Family Size / Seating
        seat_match = re.search(r"\b(7|6|5|4)\s*(?:seater|seats|seat|occupants|family of \d)\b", lower_text)
        if seat_match:
            seats = int(seat_match.group(1))
            profile.family_size = seats
            profile.set_provenance("family_size", ProvenanceState.USER_EXPLICIT, source_phrase=seat_match.group(0))
            extracted_count += 1
        elif re.search(r"\b(?:family car|family use|for family)\b", lower_text):
            profile.family_size = 4
            profile.set_provenance("family_size", ProvenanceState.USER_INFERRED, source_phrase="family car")
            extracted_count += 1

        # 7. Priorities
        # Safety
        if re.search(r"\b(?:safe|safety|crash test|ncap|airbags|high safety)\b", lower_text):
            profile.safety_priority = PriorityLevel.CRITICAL if ("very safe" in lower_text or "top safety" in lower_text) else PriorityLevel.HIGH
            profile.set_provenance("safety_priority", ProvenanceState.USER_EXPLICIT, source_phrase="safety")
            extracted_count += 1

        # Reliability
        if re.search(r"\b(?:reliable|reliability|trouble[\s-]?free|durable|bulletproof)\b", lower_text):
            profile.reliability_priority = PriorityLevel.CRITICAL if ("most reliable" in lower_text or "bulletproof" in lower_text) else PriorityLevel.HIGH
            profile.set_provenance("reliability_priority", ProvenanceState.USER_EXPLICIT, source_phrase="reliable")
            extracted_count += 1

        # Maintenance / Running Cost
        if re.search(r"\b(?:low maintenance|cheap maintenance|cheap service|easy service|affordable parts)\b", lower_text):
            profile.maintenance_priority = PriorityLevel.HIGH
            profile.maintenance_tolerance = ToleranceLevel.LOW
            profile.set_provenance("maintenance_priority", ProvenanceState.USER_EXPLICIT, source_phrase="low maintenance")
            extracted_count += 1

        # Efficiency / Mileage
        if re.search(r"\b(?:good mileage|high mileage|fuel efficient|efficient|economy|kmpl)\b", lower_text):
            profile.efficiency_priority = PriorityLevel.HIGH
            profile.set_provenance("efficiency_priority", ProvenanceState.USER_EXPLICIT, source_phrase="good mileage")
            extracted_count += 1

        # Resale
        if re.search(r"\b(?:resale|good resale|resale value|retain value)\b", lower_text):
            profile.resale_priority = PriorityLevel.HIGH
            profile.set_provenance("resale_priority", ProvenanceState.USER_EXPLICIT, source_phrase="resale")
            extracted_count += 1

        # Performance
        if re.search(r"\b(?:performance|fast|powerful|punchy|turbo|fun to drive|speed)\b", lower_text):
            profile.performance_priority = PriorityLevel.HIGH
            profile.set_provenance("performance_priority", ProvenanceState.USER_EXPLICIT, source_phrase="performance")
            extracted_count += 1

        # 8. Ownership Duration
        year_match = re.search(r"\b(?:keep for|own for|retention of|duration)\s*(\d{1,2})\s*(?:year|years|yrs)\b", lower_text)
        if year_match:
            profile.ownership_years = int(year_match.group(1))
            profile.set_provenance("ownership_years", ProvenanceState.USER_EXPLICIT, source_phrase=year_match.group(0))
            extracted_count += 1

        # Provenance summary dictionary
        prov_summary = {
            k: f"{v.state.value} (source: '{v.source_phrase}')"
            for k, v in profile.provenance_map.items()
        }

        parser_state = "AMBIGUOUS" if clarifications else "SUCCESS"
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        return NaturalLanguageRequirementsResponse(
            parsed_profile=profile,
            extracted_fields_count=extracted_count,
            clarification_questions=clarifications,
            provenance_summary=prov_summary,
            parser_state=parser_state,
            computation_latency_ms=latency_ms,
        )
