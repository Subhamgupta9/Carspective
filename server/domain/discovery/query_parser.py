"""
CARspective — Phase 12: Deterministic Automotive Query Parser
Parses natural automotive discovery and vehicle search queries into strongly-typed
VehicleSearchIntent models with explicit provenance tracking.
"""

import re
import unicodedata
from typing import Optional, Tuple, Dict, Any, List
from server.domain.discovery.models import (
    VehicleSearchIntent,
    IntentField,
    IntentFieldProvenance,
)

# Canonical normalization lookups
MANUFACTURER_ALIASES: Dict[str, str] = {
    "maruti": "Maruti Suzuki",
    "maruti suzuki": "Maruti Suzuki",
    "suzuki": "Maruti Suzuki",
    "ms": "Maruti Suzuki",
    "hyundai": "Hyundai",
    "tata": "Tata",
    "tata motors": "Tata",
    "honda": "Honda",
    "mahindra": "Mahindra",
    "m&m": "Mahindra",
    "toyota": "Toyota",
    "kia": "Kia",
    "volkswagen": "Volkswagen",
    "vw": "Volkswagen",
    "skoda": "Skoda",
    "renault": "Renault",
    "ford": "Ford",
    "bmw": "BMW",
    "beemer": "BMW",
    "bimmer": "BMW",
    "mercedes": "Mercedes-Benz",
    "mercedes-benz": "Mercedes-Benz",
    "merc": "Mercedes-Benz",
    "audi": "Audi",
}

MODEL_ALIASES: Dict[str, Tuple[str, Optional[str]]] = {
    # model_token -> (canonical_model, optional_canonical_manufacturer)
    "swift": ("Swift", "Maruti Suzuki"),
    "dzire": ("Dzire", "Maruti Suzuki"),
    "swift dzire": ("Dzire", "Maruti Suzuki"),
    "wagon r": ("Wagon R", "Maruti Suzuki"),
    "wagonr": ("Wagon R", "Maruti Suzuki"),
    "baleno": ("Baleno", "Maruti Suzuki"),
    "alto": ("Alto 800", "Maruti Suzuki"),
    "alto 800": ("Alto 800", "Maruti Suzuki"),
    "alto k10": ("Alto K10", "Maruti Suzuki"),
    "ertiga": ("Ertiga", "Maruti Suzuki"),
    "celerio": ("Celerio", "Maruti Suzuki"),
    "brezza": ("Brezza", "Maruti Suzuki"),
    "vitara brezza": ("Brezza", "Maruti Suzuki"),
    "creta": ("Creta", "Hyundai"),
    "i20": ("i20", "Hyundai"),
    "elite i20": ("i20", "Hyundai"),
    "i10": ("i10", "Hyundai"),
    "grand i10": ("Grand i10", "Hyundai"),
    "grand i10 nios": ("Grand i10", "Hyundai"),
    "venue": ("Venue", "Hyundai"),
    "verna": ("Verna", "Hyundai"),
    "nexon": ("Nexon", "Tata"),
    "tiago": ("Tiago", "Tata"),
    "altroz": ("Altroz", "Tata"),
    "harrier": ("Harrier", "Tata"),
    "safari": ("Safari", "Tata"),
    "city": ("City", "Honda"),
    "amaze": ("Amaze", "Honda"),
    "civic": ("Civic", "Honda"),
    "thar": ("Thar", "Mahindra"),
    "scorpio": ("Scorpio", "Mahindra"),
    "scorpio-n": ("Scorpio", "Mahindra"),
    "xuv700": ("XUV700", "Mahindra"),
    "xuv500": ("XUV500", "Mahindra"),
    "xuv300": ("XUV300", "Mahindra"),
    "innova": ("Innova Crysta", "Toyota"),
    "innova crysta": ("Innova Crysta", "Toyota"),
    "fortuner": ("Fortuner", "Toyota"),
    "seltos": ("Seltos", "Kia"),
    "sonet": ("Sonet", "Kia"),
    "carens": ("Carens", "Kia"),
    "kwid": ("KWID", "Renault"),
    "polo": ("Polo", "Volkswagen"),
    "virtus": ("Virtus", "Volkswagen"),
    "slavia": ("Slavia", "Skoda"),
    "taigun": ("Taigun", "Volkswagen"),
    "kushaq": ("Kushaq", "Skoda"),
    "punch": ("Punch", "Tata"),
}

FUEL_ALIASES: Dict[str, str] = {
    "petrol": "Petrol",
    "diesel": "Diesel",
    "cng": "CNG",
    "electric": "Electric",
    "ev": "Electric",
    "hybrid": "Hybrid",
}

TRANSMISSION_ALIASES: Dict[str, str] = {
    "manual": "Manual",
    "mt": "Manual",
    "automatic": "Automatic",
    "at": "Automatic",
    "auto": "Automatic",
    "amt": "AMT",
    "cvt": "CVT",
    "dsg": "Automatic",
    "dct": "Automatic",
}

BODY_TYPE_ALIASES: Dict[str, str] = {
    "suv": "SUV",
    "compact suv": "SUV",
    "csuv": "SUV",
    "sedan": "Sedan",
    "compact sedan": "Sedan",
    "hatchback": "Hatchback",
    "hatch": "Hatchback",
    "mpv": "MPV",
    "muv": "MPV",
}

VARIANT_TOKENS: List[str] = [
    # Multi-token variants first
    "zxi plus", "zxi+", "zdi plus", "zdi+", "vxi amt", "zxi amt",
    "sx(o)", "sx plus", "sx+", "zx cvt", "vx cvt", "xz+", "xz plus",
    "ax7 l", "ax7", "ax5", "lx hard top", "lx soft top", "htx+", "gtx+",
    # Single token variants
    "vxi", "zxi", "lxi", "vdi", "zdi", "ldi",
    "sx", "ex", "s+", "s", "e",
    "zx", "vx", "v", "sv",
    "xz", "xt", "xm", "xe",
    "lx", "ax",
    "htx", "gtx", "hte", "htk",
]

USE_CASE_KEYWORDS: Dict[str, str] = {
    "family": "family_utility",
    "reliable": "high_reliability",
    "reliability": "high_reliability",
    "highway": "highway_cruiser",
    "resale": "high_resale_value",
    "budget": "budget_conscious",
    "cheap": "budget_conscious",
    "affordable": "budget_conscious",
    "mileage": "fuel_efficient",
    "efficient": "fuel_efficient",
    "off-road": "offroad_capable",
    "4x4": "offroad_capable",
    "city driving": "city_commute",
    "city commute": "city_commute",
}

def damerau_levenshtein(s1: str, s2: str) -> int:
    """Calculates edit distance between two strings."""
    len1, len2 = len(s1), len(s2)
    H = [[0] * (len2 + 2) for _ in range(len1 + 2)]
    INF = len1 + len2
    H[0][0] = INF
    for i in range(0, len1 + 1):
        H[i + 1][0] = INF
        H[i + 1][1] = i
    for j in range(0, len2 + 1):
        H[0][j + 1] = INF
        H[1][j + 1] = j

    DA = {}
    for i in range(1, len1 + 1):
        db = 0
        for j in range(1, len2 + 1):
            i1 = DA.get(s2[j - 1], 0)
            j1 = db
            cost = 1 if s1[i - 1] != s2[j - 1] else 0
            if cost == 0:
                db = j

            H[i + 1][j + 1] = min(
                H[i][j] + cost,                  # substitution
                H[i + 1][j] + 1,                 # insertion
                H[i][j + 1] + 1,                 # deletion
                H[i1][j1] + (i - i1 - 1) + 1 + (j - j1 - 1)  # transposition
            )
        DA[s1[i - 1]] = i
    return H[len1 + 1][len2 + 1]

class QueryParser:
    """Deterministic parser for Indian automotive discovery queries."""

    @staticmethod
    def sanitize_query(raw_query: str) -> str:
        """Sanitizes raw query: removes control chars, strips, normalizes whitespace."""
        if not raw_query:
            return ""
        # Truncate extremely long payloads for security
        truncated = raw_query[:256]
        # Remove null bytes and control chars
        cleaned = "".join(ch for ch in truncated if ch >= " " or ch in "\t\n")
        # Normalize unicode
        normalized = unicodedata.normalize("NFKC", cleaned)
        # Collapse whitespace
        return " ".join(normalized.split())

    @classmethod
    def parse(cls, raw_query: str) -> VehicleSearchIntent:
        cleaned = cls.sanitize_query(raw_query)
        q_lower = cleaned.lower()
        remaining_text = q_lower

        intent = VehicleSearchIntent(
            raw_query=raw_query,
            normalized_query=cleaned,
        )

        rules_applied: List[str] = []

        # 1. Parse Budget Patterns
        between_match = re.search(r'\b(?:between\s+)?(\d+(?:\.\d+)?)\s*(?:and|to|-)\s*(\d+(?:\.\d+)?)\s*(?:lakhs?|l)\b', remaining_text)
        if between_match:
            b_min = float(between_match.group(1)) * 100000.0
            b_max = float(between_match.group(2)) * 100000.0
            intent.budget_min = IntentField(
                value=b_min,
                provenance=IntentFieldProvenance.USER_EXPLICIT,
                raw_token=between_match.group(0)
            )
            intent.budget_max = IntentField(
                value=b_max,
                provenance=IntentFieldProvenance.USER_EXPLICIT,
                raw_token=between_match.group(0)
            )
            remaining_text = remaining_text.replace(between_match.group(0), " ")
            rules_applied.append("extracted_budget_range")
        else:
            under_match = re.search(r'\b(?:under|below|sub|<|less than)\s*(\d+(?:\.\d+)?)\s*(?:lakhs?|l)\b', remaining_text)
            if under_match:
                b_max = float(under_match.group(1)) * 100000.0
                intent.budget_max = IntentField(
                    value=b_max,
                    provenance=IntentFieldProvenance.USER_EXPLICIT,
                    raw_token=under_match.group(0)
                )
                remaining_text = remaining_text.replace(under_match.group(0), " ")
                rules_applied.append("extracted_budget_max")
            else:
                above_match = re.search(r'\b(?:above|over|>|more than)\s*(\d+(?:\.\d+)?)\s*(?:lakhs?|l)\b', remaining_text)
                if above_match:
                    b_min = float(above_match.group(1)) * 100000.0
                    intent.budget_min = IntentField(
                        value=b_min,
                        provenance=IntentFieldProvenance.USER_EXPLICIT,
                        raw_token=above_match.group(0)
                    )
                    remaining_text = remaining_text.replace(above_match.group(0), " ")
                    rules_applied.append("extracted_budget_min")

        # 2. Parse Seating Capacity
        seat_match = re.search(r'\b(\d)\s*(?:-| )?\s*seater\b', remaining_text)
        if seat_match:
            seats = int(seat_match.group(1))
            intent.seating_capacity = IntentField(
                value=seats,
                provenance=IntentFieldProvenance.USER_EXPLICIT,
                raw_token=seat_match.group(0)
            )
            remaining_text = remaining_text.replace(seat_match.group(0), " ")
            rules_applied.append("extracted_seating_capacity")

        # 3. Parse 4-Digit Model Year (1990 - 2030)
        year_match = re.search(r'\b(19\d\d|20[0-2]\d|2030)\b', remaining_text)
        if year_match:
            year = int(year_match.group(1))
            intent.model_year = IntentField(
                value=year,
                provenance=IntentFieldProvenance.USER_EXPLICIT,
                raw_token=year_match.group(0)
            )
            remaining_text = remaining_text.replace(year_match.group(0), " ")
            rules_applied.append("extracted_model_year")

        # 4. Parse Manufacturer (Exact & Multi-word Aliases) FIRST before model or variants
        matched_mfg: Optional[str] = None
        for mfg_term, canon_mfg in sorted(MANUFACTURER_ALIASES.items(), key=lambda x: -len(x[0])):
            pattern = rf'\b{re.escape(mfg_term)}\b'
            if re.search(pattern, remaining_text):
                matched_mfg = canon_mfg
                intent.manufacturer = IntentField(
                    value=canon_mfg,
                    provenance=IntentFieldProvenance.USER_EXPLICIT,
                    raw_token=mfg_term
                )
                remaining_text = re.sub(pattern, " ", remaining_text)
                rules_applied.append("extracted_manufacturer")
                break

        # 5. Parse Model (Exact & Multi-word Aliases) - BEFORE general use case keywords
        matched_model: Optional[str] = None
        for model_term, (canon_model, canon_mfg) in sorted(MODEL_ALIASES.items(), key=lambda x: -len(x[0])):
            pattern = rf'\b{re.escape(model_term)}\b'
            if re.search(pattern, remaining_text):
                matched_model = canon_model
                intent.model = IntentField(
                    value=canon_model,
                    provenance=IntentFieldProvenance.USER_EXPLICIT,
                    raw_token=model_term
                )
                if not matched_mfg and canon_mfg:
                    intent.manufacturer = IntentField(
                        value=canon_mfg,
                        provenance=IntentFieldProvenance.USER_INFERRED,
                        confidence=0.9,
                        raw_token=f"inferred_from_{model_term}"
                    )
                    rules_applied.append("inferred_manufacturer_from_model")
                remaining_text = re.sub(pattern, " ", remaining_text)
                rules_applied.append("extracted_model")
                break

        # 6. Parse Variant Tokens
        for v_tok in VARIANT_TOKENS:
            pattern = rf'\b{re.escape(v_tok)}\b'
            if re.search(pattern, remaining_text):
                intent.variant = IntentField(
                    value=v_tok.upper(),
                    provenance=IntentFieldProvenance.USER_EXPLICIT,
                    raw_token=v_tok
                )
                remaining_text = re.sub(pattern, " ", remaining_text)
                rules_applied.append("extracted_variant")
                break

        # 7. Parse Transmission Aliases
        for trans_term, canon_trans in TRANSMISSION_ALIASES.items():
            pattern = rf'\b{re.escape(trans_term)}\b'
            if re.search(pattern, remaining_text):
                intent.transmission = IntentField(
                    value=canon_trans,
                    provenance=IntentFieldProvenance.USER_EXPLICIT,
                    raw_token=trans_term
                )
                remaining_text = re.sub(pattern, " ", remaining_text)
                rules_applied.append("extracted_transmission")
                break

        # 8. Parse Fuel Aliases
        for fuel_term, canon_fuel in FUEL_ALIASES.items():
            pattern = rf'\b{re.escape(fuel_term)}\b'
            if re.search(pattern, remaining_text):
                intent.fuel_type = IntentField(
                    value=canon_fuel,
                    provenance=IntentFieldProvenance.USER_EXPLICIT,
                    raw_token=fuel_term
                )
                remaining_text = re.sub(pattern, " ", remaining_text)
                rules_applied.append("extracted_fuel_type")
                break

        # 9. Parse Body Type Aliases
        for body_term, canon_body in BODY_TYPE_ALIASES.items():
            pattern = rf'\b{re.escape(body_term)}\b'
            if re.search(pattern, remaining_text):
                intent.body_type = IntentField(
                    value=canon_body,
                    provenance=IntentFieldProvenance.USER_EXPLICIT,
                    raw_token=body_term
                )
                remaining_text = re.sub(pattern, " ", remaining_text)
                rules_applied.append("extracted_body_type")
                break

        # 10. Parse Use Case Keywords from remaining tokens
        for kw, canon_uc in USE_CASE_KEYWORDS.items():
            pattern = rf'\b{re.escape(kw)}\b'
            if re.search(pattern, remaining_text):
                intent.use_case = IntentField(
                    value=canon_uc,
                    provenance=IntentFieldProvenance.USER_EXPLICIT,
                    raw_token=kw
                )
                remaining_text = re.sub(pattern, " ", remaining_text)
                rules_applied.append("extracted_use_case")
                break

        # 11. Fuzzy Matching for Spelling Variations (If no model was matched)
        clean_remaining = " ".join(remaining_text.split()).strip()
        if not matched_model and clean_remaining:
            tokens = clean_remaining.split()
            best_model = None
            best_dist = 999
            best_token = None
            for token in tokens:
                if len(token) < 3:
                    continue
                for model_key, (canon_model, canon_mfg) in MODEL_ALIASES.items():
                    if " " in model_key:
                        continue
                    dist = damerau_levenshtein(token, model_key)
                    max_allow = 2 if len(model_key) >= 6 else 1
                    if dist <= max_allow and dist < best_dist:
                        best_dist = dist
                        best_model = (canon_model, canon_mfg)
                        best_token = token

            if best_model and best_dist <= 2:
                canon_model, canon_mfg = best_model
                intent.model = IntentField(
                    value=canon_model,
                    provenance=IntentFieldProvenance.USER_INFERRED,
                    confidence=max(0.6, round(1.0 - (best_dist * 0.2), 2)),
                    raw_token=best_token
                )
                if not intent.manufacturer.value and canon_mfg:
                    intent.manufacturer = IntentField(
                        value=canon_mfg,
                        provenance=IntentFieldProvenance.USER_INFERRED,
                        confidence=0.8,
                        raw_token=f"inferred_from_{canon_model}"
                    )
                rules_applied.append(f"fuzzy_matched_model_{best_token}->{canon_model}")

        return intent
