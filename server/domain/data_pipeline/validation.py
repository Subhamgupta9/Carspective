"""
CARspective — Ingestion Validation Engine & Quality Gates
Enforces deterministic validation across schema, vehicle identity, numerical sanity,
data consistency, and application security before any record is accepted.
"""

import re
from typing import Dict, Any, List, Tuple
from .models import ValidationFailure

CURRENT_YEAR = 2026
MAX_VALID_YEAR = CURRENT_YEAR + 1  # 2027
MIN_VALID_YEAR = 1980

MIN_PRICE = 20_000.0         # ₹20,000
MAX_PRICE = 100_000_000.0     # ₹10 Crore
MAX_MILEAGE = 1_000_000.0     # 1,000,000 km
MIN_DISPLACEMENT_CC = 500.0
MAX_DISPLACEMENT_CC = 8_000.0
MIN_MILEAGE_KMPL = 3.0
MAX_MILEAGE_KMPL = 45.0

ALLOWED_FUELS = {"PETROL", "DIESEL", "CNG", "LPG", "ELECTRIC", "HYBRID"}
ALLOWED_TRANSMISSIONS = {"MANUAL", "AUTOMATIC"}

# Security attack patterns
SQL_INJECTION_REGEX = re.compile(
    r"(\b(UNION\s+SELECT|DROP\s+TABLE|ALTER\s+TABLE|DELETE\s+FROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET)\b|'\s*OR\s*'?1'?\s*=\s*'?1|--|;)",
    re.IGNORECASE
)
PATH_TRAVERSAL_REGEX = re.compile(r"(\.\./|\.\.\\|/etc/passwd|/windows/system32|c:\\windows)", re.IGNORECASE)
MALICIOUS_URL_REGEX = re.compile(r"^(javascript:|data:|file:|vbscript:|http://169\.254\.169\.254)", re.IGNORECASE)

class IngestionValidationEngine:
    """Deterministic validation and quality gate evaluator for ingestion records."""

    @classmethod
    def validate_record(cls, record: Dict[str, Any], record_index: int = 0) -> List[ValidationFailure]:
        """
        Runs all quality gates on a single record. Returns list of failures (empty if valid).
        """
        failures: List[ValidationFailure] = []

        # 1. Security Gates
        sec_failures = cls._check_security(record, record_index)
        if sec_failures:
            # If security gate fails, fail immediately without further processing
            return sec_failures

        # 2. Schema & Required Fields Gate
        for req_field in ["make", "model", "year", "price", "mileage"]:
            val = record.get(req_field)
            if val is None or val == "":
                failures.append(ValidationFailure(
                    record_index=record_index,
                    field_name=req_field,
                    error_code="REQUIRED_FIELD_MISSING",
                    error_message=f"Mandatory field '{req_field}' is missing or empty.",
                    raw_value=str(val)
                ))

        if failures:
            return failures

        # 3. Vehicle Identity Gate
        make = str(record.get("make", "")).strip()
        model = str(record.get("model", "")).strip()
        if len(make) < 2 or not re.match(r"^[a-zA-Z0-9\s\-_]+$", make):
            failures.append(ValidationFailure(
                record_index=record_index,
                field_name="make",
                error_code="INVALID_MANUFACTURER_IDENTITY",
                error_message=f"Manufacturer name '{make}' contains invalid characters or is too short.",
                raw_value=make
            ))
        if len(model) < 1:
            failures.append(ValidationFailure(
                record_index=record_index,
                field_name="model",
                error_code="INVALID_MODEL_IDENTITY",
                error_message="Model name cannot be empty.",
                raw_value=model
            ))

        # 4. Numerical Sanity Gate
        # Year
        try:
            year_val = int(record["year"])
            if year_val < MIN_VALID_YEAR or year_val > MAX_VALID_YEAR:
                failures.append(ValidationFailure(
                    record_index=record_index,
                    field_name="year",
                    error_code="YEAR_OUT_OF_BOUNDS",
                    error_message=f"Model year {year_val} must be between {MIN_VALID_YEAR} and {MAX_VALID_YEAR}.",
                    raw_value=str(year_val)
                ))
        except (ValueError, TypeError):
            failures.append(ValidationFailure(
                record_index=record_index,
                field_name="year",
                error_code="INVALID_YEAR_FORMAT",
                error_message=f"Year '{record.get('year')}' cannot be converted to integer.",
                raw_value=str(record.get("year"))
            ))

        # Price (Seller Asking Price)
        try:
            price_val = float(record["price"])
            if price_val < MIN_PRICE or price_val > MAX_PRICE:
                failures.append(ValidationFailure(
                    record_index=record_index,
                    field_name="price",
                    error_code="PRICE_OUT_OF_BOUNDS",
                    error_message=f"Price ₹{price_val:,.2f} must be between ₹{MIN_PRICE:,.0f} and ₹{MAX_PRICE:,.0f}.",
                    raw_value=str(price_val)
                ))
        except (ValueError, TypeError):
            failures.append(ValidationFailure(
                record_index=record_index,
                field_name="price",
                error_code="INVALID_PRICE_FORMAT",
                error_message=f"Price '{record.get('price')}' cannot be converted to float.",
                raw_value=str(record.get("price"))
            ))

        # Mileage / Kilometers
        try:
            mileage_val = float(record["mileage"])
            if mileage_val < 0.0 or mileage_val > MAX_MILEAGE:
                failures.append(ValidationFailure(
                    record_index=record_index,
                    field_name="mileage",
                    error_code="MILEAGE_OUT_OF_BOUNDS",
                    error_message=f"Mileage {mileage_val:,.0f} km must be between 0 and {MAX_MILEAGE:,.0f} km.",
                    raw_value=str(mileage_val)
                ))
        except (ValueError, TypeError):
            failures.append(ValidationFailure(
                record_index=record_index,
                field_name="mileage",
                error_code="INVALID_MILEAGE_FORMAT",
                error_message=f"Mileage '{record.get('mileage')}' cannot be converted to float.",
                raw_value=str(record.get("mileage"))
            ))

        # Optional Numerical Bounds
        if "engine_cc" in record and record["engine_cc"] is not None:
            try:
                cc_val = float(record["engine_cc"])
                if cc_val < MIN_DISPLACEMENT_CC or cc_val > MAX_DISPLACEMENT_CC:
                    failures.append(ValidationFailure(
                        record_index=record_index,
                        field_name="engine_cc",
                        error_code="DISPLACEMENT_OUT_OF_BOUNDS",
                        error_message=f"Displacement {cc_val} cc must be between {MIN_DISPLACEMENT_CC} and {MAX_DISPLACEMENT_CC} cc.",
                        raw_value=str(cc_val)
                    ))
            except (ValueError, TypeError):
                failures.append(ValidationFailure(
                    record_index=record_index,
                    field_name="engine_cc",
                    error_code="INVALID_DISPLACEMENT_FORMAT",
                    error_message=f"Engine CC '{record.get('engine_cc')}' is not a valid number.",
                    raw_value=str(record.get("engine_cc"))
                ))

        if "fuel_economy_kmpl" in record and record["fuel_economy_kmpl"] is not None:
            try:
                fe_val = float(record["fuel_economy_kmpl"])
                if fe_val < MIN_MILEAGE_KMPL or fe_val > MAX_MILEAGE_KMPL:
                    failures.append(ValidationFailure(
                        record_index=record_index,
                        field_name="fuel_economy_kmpl",
                        error_code="FUEL_ECONOMY_OUT_OF_BOUNDS",
                        error_message=f"Fuel economy {fe_val} kmpl must be between {MIN_MILEAGE_KMPL} and {MAX_MILEAGE_KMPL} kmpl.",
                        raw_value=str(fe_val)
                    ))
            except (ValueError, TypeError):
                failures.append(ValidationFailure(
                    record_index=record_index,
                    field_name="fuel_economy_kmpl",
                    error_code="INVALID_FUEL_ECONOMY_FORMAT",
                    error_message=f"Fuel economy '{record.get('fuel_economy_kmpl')}' is not a valid number.",
                    raw_value=str(record.get("fuel_economy_kmpl"))
                ))

        # Enums
        fuel = str(record.get("fuel_type", "")).upper()
        if fuel and fuel not in ALLOWED_FUELS:
            failures.append(ValidationFailure(
                record_index=record_index,
                field_name="fuel_type",
                error_code="INVALID_FUEL_TYPE",
                error_message=f"Fuel type '{fuel}' is not valid. Allowed: {sorted(list(ALLOWED_FUELS))}.",
                raw_value=fuel
            ))

        transmission = str(record.get("transmission", "")).upper()
        if transmission and transmission not in ALLOWED_TRANSMISSIONS:
            failures.append(ValidationFailure(
                record_index=record_index,
                field_name="transmission",
                error_code="INVALID_TRANSMISSION",
                error_message=f"Transmission '{transmission}' is not valid. Allowed: {sorted(list(ALLOWED_TRANSMISSIONS))}.",
                raw_value=transmission
            ))

        return failures

    @classmethod
    def _check_security(cls, record: Dict[str, Any], record_index: int) -> List[ValidationFailure]:
        """Detects SQL injection, path traversal, oversized inputs, and malicious payloads."""
        sec_failures: List[ValidationFailure] = []

        for field, val in record.items():
            if isinstance(val, str):
                # Null byte injection
                if "\x00" in val:
                    sec_failures.append(ValidationFailure(
                        record_index=record_index,
                        field_name=field,
                        error_code="SECURITY_NULL_BYTE_DETECTED",
                        error_message="Null byte detected in string input.",
                        raw_value="[NULL_BYTE]"
                    ))

                # Oversized input
                if len(val) > 1000:
                    sec_failures.append(ValidationFailure(
                        record_index=record_index,
                        field_name=field,
                        error_code="SECURITY_OVERSIZED_INPUT",
                        error_message=f"Field '{field}' exceeds maximum string length of 1000 characters.",
                        raw_value=f"{val[:50]}... ({len(val)} chars)"
                    ))

                # SQL Injection check
                if SQL_INJECTION_REGEX.search(val):
                    sec_failures.append(ValidationFailure(
                        record_index=record_index,
                        field_name=field,
                        error_code="SECURITY_SQL_INJECTION_PATTERN",
                        error_message=f"Potential SQL injection pattern detected in '{field}'.",
                        raw_value=val[:50]
                    ))

                # Path Traversal check
                if PATH_TRAVERSAL_REGEX.search(val):
                    sec_failures.append(ValidationFailure(
                        record_index=record_index,
                        field_name=field,
                        error_code="SECURITY_PATH_TRAVERSAL_PATTERN",
                        error_message=f"Path traversal sequence detected in '{field}'.",
                        raw_value=val[:50]
                    ))

                # Malicious URL check
                if field.endswith("_url") or "url" in field:
                    if MALICIOUS_URL_REGEX.search(val):
                        sec_failures.append(ValidationFailure(
                            record_index=record_index,
                            field_name=field,
                            error_code="SECURITY_MALICIOUS_URL_SCHEME",
                            error_message=f"Disallowed or malicious URL scheme detected in '{field}'.",
                            raw_value=val[:50]
                        ))

        return sec_failures
