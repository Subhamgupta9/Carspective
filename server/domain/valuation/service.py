"""
CARspective — Valuation Domain Service
Production valuation engine orchestrating SHA-256 secure model deserialization,
canonical taxonomy identity resolution, conformal expected fair market range,
multi-factor evidence confidence scoring, and strict target-asking price isolation.
"""

import os
import json
import hashlib
import threading
from collections import OrderedDict
import joblib
import numpy as np
import pandas as pd
import scipy.sparse as sp
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone

from server.domain.valuation.models import ValuationRequest, ValuationResponse, FairMarketRange
from server.domain.taxonomy.resolver import CanonicalResolver
from server.schemas.taxonomy import CanonicalResolutionRequest, CanonicalResolutionResult
from server.repositories.taxonomy_repository import TaxonomyRepository
from server.infrastructure.database import ScopedSession

CURRENT_YEAR = 2026
DEFAULT_MODEL_PATH = os.path.join("models", "carspective_valuation_lgbm_v1.joblib")
DEFAULT_MANIFEST_PATH = os.path.join("models", "carspective_valuation_lgbm_v1_manifest.json")

class CategoricalPreprocessingCache:
    """
    Thread-safe, bounded LRU cache for immutable categorical feature transformations.
    Caches the 1-row CSR sparse matrix resulting from OneHotEncoder for identical
    (model, fuel_type, transmission_type, brand, city, bodytype) configurations.
    """
    def __init__(self, maxsize: int = 2048):
        self.maxsize = maxsize
        self._cache: OrderedDict[Tuple[str, ...], Any] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: Tuple[str, ...]) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def put(self, key: Tuple[str, ...], value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.maxsize:
                    self._cache.popitem(last=False)
                self._cache[key] = value

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "hits": self._hits,
                "misses": self._misses
            }

class ModelSecurityIntegrityError(Exception):
    """Raised when model artifact fails cryptographic SHA-256 integrity verification."""
    pass

class ValuationService:
    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        manifest_path: str = DEFAULT_MANIFEST_PATH,
        taxonomy_resolver: Optional[CanonicalResolver] = None,
        session: Optional[Any] = None
    ):
        self.model_path = model_path
        self.manifest_path = manifest_path
        self._session = session
        if taxonomy_resolver is None:
            repo = TaxonomyRepository(session=session)
            self.taxonomy_resolver = CanonicalResolver(repo)
        else:
            self.taxonomy_resolver = taxonomy_resolver
        self.manifest: Dict[str, Any] = {}
        self.pipeline = None
        self._load_and_verify_model()

    @property
    def session(self) -> Any:
        if self._session is not None:
            return self._session
        return ScopedSession()

    @session.setter
    def session(self, value: Optional[Any]) -> None:
        self._session = value
        if hasattr(self.taxonomy_resolver, "repo") and hasattr(self.taxonomy_resolver.repo, "session"):
            self.taxonomy_resolver.repo.session = value

    def _compute_sha256(self, file_path: str) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _load_and_verify_model(self):
        """
        Cryptographic Security Gate:
        Verifies artifact SHA-256 checksum against trusted manifest before deserialization.
        Halts startup immediately if hash mismatch or missing manifest detected.
        """
        if not os.path.exists(self.manifest_path):
            raise ModelSecurityIntegrityError(f"Trusted manifest not found at {self.manifest_path}. Model loading halted.")
            
        with open(self.manifest_path, "r") as f:
            self.manifest = json.load(f)
            
        trusted_sha256 = self.manifest.get("artifact", {}).get("sha256")
        if not trusted_sha256:
            raise ModelSecurityIntegrityError("Trusted manifest missing artifact sha256 checksum.")
            
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model artifact not found at {self.model_path}.")
            
        actual_sha256 = self._compute_sha256(self.model_path)
        if actual_sha256.lower() != trusted_sha256.lower():
            raise ModelSecurityIntegrityError(
                f"SECURITY INTEGRITY FAILURE: Model file SHA-256 ({actual_sha256}) does not match "
                f"trusted manifest hash ({trusted_sha256}). Possible file corruption or tampering. Model load halted."
            )
            
        # Deserialization permitted only after hash verification
        self.pipeline = joblib.load(self.model_path)
        self.preprocessor = self.pipeline.named_steps["preprocessor"]
        self.num_trans = self.preprocessor.named_transformers_["numeric"]
        self.cat_trans = self.preprocessor.named_transformers_["categorical"]
        self.estimator = self.pipeline.named_steps["model"]
        self._cat_prep_cache = CategoricalPreprocessingCache(maxsize=2048)

    def evaluate_valuation(
        self,
        req: ValuationRequest,
        resolved_taxonomy: Optional[CanonicalResolutionResult] = None,
    ) -> ValuationResponse:
        """
        Executes valuation inference:
        1. Resolves canonical taxonomy identity (reuse pre-resolved if provided)
        2. Validates inputs and enforces target-asking price isolation
        3. Features preprocessing
        4. Model inference and inverse log1p transformation
        5. Conformal range calculation
        6. Multi-factor confidence state assignment
        """
        # Step 1: Canonical taxonomy resolution
        if resolved_taxonomy is not None:
            tax_res = resolved_taxonomy
        else:
            tax_req = CanonicalResolutionRequest(
                brand=req.brand,
                model=req.model,
                year=req.manufacturing_year,
                variant=req.variant,
                fuel_type=req.fuel_type,
                transmission_type=req.transmission_type
            )
            tax_res = self.taxonomy_resolver.resolve(tax_req)
        
        # Step 2: Check for insufficient data / completely unsupported input
        is_unresolved = (tax_res.status == "UNRESOLVED")
        extreme_mileage = (req.km_driven > 700000)
        extreme_vintage = (req.manufacturing_year < 1990)
        
        if is_unresolved and (extreme_mileage or extreme_vintage):
            return ValuationResponse(
                canonical_vehicle_id=None,
                vehicle_resolution_status=tax_res.status,
                estimated_fair_market_value=None,
                expected_fair_market_range=None,
                confidence_state="INSUFFICIENT_DATA",
                evidence_quality="INSUFFICIENT_DATA",
                market_evidence=None,
                model_metadata={
                    "model_version": self.manifest.get("model_version", "carspective-val-v1.0.0"),
                    "algorithm": self.manifest.get("algorithm", "LightGBM Tuned Regressor"),
                    "target_concept": self.manifest.get("target_semantic_concept", "")
                },
                limitations=[
                    "Insufficient verified data to provide a reliable valuation.",
                    f"Vehicle configuration '{req.brand} {req.model}' could not be matched against canonical marketplace taxonomy.",
                    "Out-of-distribution parameters prevent statistical estimation."
                ]
            )

        # Step 3: Feature engineering with immutable categorical transformation reuse
        # NOTE: asking_price is strictly ignored and isolated from predictive inputs!
        vehicle_age = max(0, CURRENT_YEAR - req.manufacturing_year)
        log_km_driven = float(np.log1p(req.km_driven))
        
        # Categorical feature resolution with immutable preprocessing result reuse
        effective_bodytype = req.bodytype
        if not effective_bodytype and tax_res and tax_res.hierarchy:
            model_info = tax_res.hierarchy.get("model")
            if isinstance(model_info, dict):
                effective_bodytype = model_info.get("body_type")
            elif isinstance(tax_res.hierarchy.get("body_type"), str):
                effective_bodytype = tax_res.hierarchy.get("body_type")
        effective_bodytype = effective_bodytype or "Hatchback"

        cat_key = (
            str(req.model).strip(),
            str(req.fuel_type or "Petrol").strip(),
            str(req.transmission_type or "Manual").strip(),
            str(req.brand).strip(),
            str(req.city or "Delhi").strip(),
            str(effective_bodytype).strip(),
        )

        cached_x_cat = self._cat_prep_cache.get(cat_key)
        if cached_x_cat is not None:
            X_cat = cached_x_cat.copy()
        else:
            df_cat = pd.DataFrame([{
                "model": cat_key[0],
                "fuel_type": cat_key[1],
                "transmission_type": cat_key[2],
                "brand": cat_key[3],
                "city": cat_key[4],
                "bodytype": cat_key[5]
            }])
            X_cat = self.cat_trans.transform(df_cat)
            self._cat_prep_cache.put(cat_key, X_cat.copy())

        # Numeric feature engineering (request-local DataFrame with exact expected columns)
        df_num = pd.DataFrame([{
            "manufacturing_year": int(req.manufacturing_year),
            "km_driven": float(req.km_driven),
            "number_of_owners": int(req.number_of_owners or 1),
            "vehicle_age": int(vehicle_age),
            "log_km_driven": log_km_driven
        }])
        X_num = self.num_trans.transform(df_num)

        # Step 4: Model inference with inverse transformation
        X_combined = sp.hstack([X_num, X_cat], format="csr")
        raw_log_pred = float(self.estimator.predict(X_combined)[0])
        pred_value = max(15000.0, float(np.expm1(raw_log_pred)))
        int_fair_value = int(round(pred_value))
        
        # Step 5: Conformal expected fair market range
        calib = self.manifest.get("conformal_range_calibration", {}).get("nominal_80_percent_interval", {})
        raw_multiplier = float(calib.get("multiplier", 0.217834))
        multiplier = round(raw_multiplier, 4)
        lower_bound = max(10000, int(round(int_fair_value * (1.0 - multiplier))))
        upper_bound = int(round(int_fair_value * (1.0 + multiplier)))
        
        fair_range = FairMarketRange(
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_interval_percent=80.0,
            multiplier=multiplier
        )
        
        # Step 6: Multi-factor confidence state & evidence quality
        limitations = [
            "Statistical Model Estimate of the Historical Market Asking-Price Baseline (NOT verified transaction price).",
            "Reflects secondary marketplace asking patterns derived from 57,480 historical listing records.",
            "Expected fair market range is empirically calibrated to 80% nominal conformal coverage.",
            "Valuation does not account for unseen cosmetic flaws, mechanical wear, accident title, or individual dealer warranties."
        ]
        
        if req.asking_price is not None:
            limitations.append(
                f"User-provided asking price (INR {int(req.asking_price):,}) was strictly isolated and not used as a predictive feature."
            )
            
        if is_unresolved:
            confidence_state = "LIMITED_CONFIDENCE"
            evidence_quality = "MODEL_ESTIMATE"
            limitations.append("Vehicle model could not be fully matched to canonical taxonomy; valuation relies on categorical fallback generalization.")
        elif extreme_mileage or vehicle_age > 15 or int_fair_value > 15000000:
            confidence_state = "LIMITED_CONFIDENCE"
            evidence_quality = "MODEL_ESTIMATE"
            limitations.append("High vehicle age, mileage, or luxury price tier represents sparse tail region in historical dataset.")
        elif tax_res.status == "EXACT_MATCH" and vehicle_age <= 10 and req.km_driven <= 150000:
            confidence_state = "HIGH_CONFIDENCE"
            evidence_quality = "SUPPORTED"
        else:
            confidence_state = "MODERATE_CONFIDENCE"
            evidence_quality = "SUPPORTED"

        market_evidence = {
            "resolution_confidence": tax_res.confidence_score,
            "matched_tier": tax_res.matched_tier,
            "vehicle_age_years": vehicle_age,
            "historical_baseline_coverage": "57,480 historical listing records (Seller Asking Price Baseline)"
        }
        
        return ValuationResponse(
            canonical_vehicle_id=tax_res.canonical_vehicle_id,
            vehicle_resolution_status=tax_res.status,
            estimated_fair_market_value=int_fair_value,
            expected_fair_market_range=fair_range,
            confidence_state=confidence_state,
            evidence_quality=evidence_quality,
            market_evidence=market_evidence,
            model_metadata={
                "model_version": self.manifest.get("model_version", "carspective-val-v1.0.0"),
                "algorithm": self.manifest.get("algorithm", "LightGBM Tuned Regressor"),
                "artifact_sha256": self.manifest.get("artifact", {}).get("sha256", ""),
                "target_concept": self.manifest.get("target_semantic_concept", "")
            },
            limitations=limitations
        )
