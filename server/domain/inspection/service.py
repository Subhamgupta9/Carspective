"""
CARspective — Phase 7 Inspection Intelligence Domain Service
Orchestrates adaptive checklist generation, finding evaluation with strict evidence provenance,
deterministic risk synthesis across 9 dimensions, documentation verification tracking,
and purchase readiness verdicts.

Preserves core CarSpective governance:
- Intrinsic CarSpective Score remains mathematically separate from physical condition.
- Phase 3 statistical valuation remains unmutated.
- UNKNOWN items never convert to PASS.
- Seller statements remain UNVERIFIED.
- Zero LLM decision-making; 100% deterministic code.
"""

import uuid
import time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from server.domain.inspection.models import (
    InspectionRequest,
    InspectionResponse,
    ChecklistItem,
    InspectionFinding,
    InspectionRisk,
    DocumentationRequirement,
    InspectionSummary,
    PurchaseReadiness,
    ContextualDealNote,
    ContextualScoreNote,
    ImportanceLevel,
)
from server.domain.inspection.applicability import ChecklistApplicabilityEngine
from server.domain.inspection.findings import FindingsEvaluationEngine
from server.domain.inspection.risk import InspectionRiskEngine
from server.domain.inspection.readiness import PurchaseReadinessEngine
from server.domain.taxonomy.resolver import CanonicalResolver
from server.schemas.taxonomy import CanonicalResolutionRequest
from server.repositories.taxonomy_repository import TaxonomyRepository
from server.infrastructure.database import ScopedSession


class InspectionService:
    """Production Inspection Intelligence Engine orchestrating verification workflows."""

    def __init__(
        self,
        taxonomy_resolver: Optional[CanonicalResolver] = None,
        session: Optional[Session] = None,
    ):
        self._session = session
        if taxonomy_resolver is None:
            repo = TaxonomyRepository(session=session)
            self.taxonomy_resolver = CanonicalResolver(repo)
        else:
            self.taxonomy_resolver = taxonomy_resolver

    @property
    def session(self) -> Session:
        if self._session is not None:
            return self._session
        return ScopedSession()

    @session.setter
    def session(self, value: Optional[Session]) -> None:
        self._session = value
        if hasattr(self.taxonomy_resolver, "repo") and hasattr(self.taxonomy_resolver.repo, "session"):
            self.taxonomy_resolver.repo.session = value

    def evaluate_inspection(self, req: InspectionRequest) -> InspectionResponse:
        """
        Executes complete inspection intelligence pipeline:
        1. Resolves canonical taxonomy identity.
        2. Generates vehicle-aware adaptive checklist.
        3. Compiles required documentation checklist.
        4. Evaluates observations into provenance-tagged findings.
        5. Computes multi-dimensional inspection risks and escalation triggers.
        6. Derives deterministic purchase readiness and summary metrics.
        7. Produces contextual deal and score notes preserving mathematical isolation.
        """
        t_start = time.perf_counter()
        session_id = f"insp-{uuid.uuid4().hex[:12]}"

        # Step 1: Canonical taxonomy resolution
        tax_req = CanonicalResolutionRequest(
            brand=req.vehicle.brand,
            model=req.vehicle.model,
            year=req.vehicle.manufacturing_year,
            variant=req.vehicle.variant,
            fuel_type=req.vehicle.fuel_type,
            transmission_type=req.vehicle.transmission_type,
        )
        tax_res = self.taxonomy_resolver.resolve(tax_req)

        canonical_id = tax_res.canonical_vehicle_id
        if tax_res.hierarchy:
            mfg_val = tax_res.hierarchy.get("manufacturer")
            if isinstance(mfg_val, dict):
                brand_clean = (mfg_val.get("name") or req.vehicle.brand).strip().title()
            elif isinstance(mfg_val, str):
                brand_clean = mfg_val.strip().title()
            else:
                brand_clean = str(req.vehicle.brand).strip().title()

            model_val = tax_res.hierarchy.get("model")
            if isinstance(model_val, dict):
                model_clean = (model_val.get("name") or req.vehicle.model).strip().title()
            elif isinstance(model_val, str):
                model_clean = model_val.strip().title()
            else:
                model_clean = str(req.vehicle.model).strip().title()
        else:
            brand_clean = str(req.vehicle.brand).strip().title()
            model_clean = str(req.vehicle.model).strip().title()

        vehicle_summary = f"{req.vehicle.manufacturing_year or ''} {brand_clean} {model_clean}".strip()
        if req.vehicle.variant:
            vehicle_summary += f" {req.vehicle.variant}"

        # Step 2: Adaptive Checklist Generation
        checklist = ChecklistApplicabilityEngine.generate_adaptive_checklist(
            vehicle=req.vehicle,
            user_profile=req.user_profile,
        )

        # Step 3: Documentation Requirements
        doc_requirements = self._build_documentation_requirements(req.documentation_records or {})

        # Step 4: Findings Evaluation
        findings = FindingsEvaluationEngine.evaluate_findings(
            checklist=checklist,
            finding_inputs=req.findings or [],
        )

        # Step 5: Risk Engine & Professional Escalation Triggers
        risks, pro_required, pro_reasons = InspectionRiskEngine.evaluate_risks(
            vehicle=req.vehicle,
            findings=findings,
            checklist=checklist,
        )

        # Step 6: Purchase Readiness & Summary
        readiness, summary = PurchaseReadinessEngine.evaluate_readiness_and_summary(
            checklist=checklist,
            findings=findings,
            risks=risks,
            doc_requirements=doc_requirements,
            professional_required=pro_required,
            pro_reasons=pro_reasons,
        )

        # Step 7: Contextual Deal Note (Valuation Isolation)
        deal_note = None
        if req.listing and req.listing.asking_price and req.listing.asking_price > 0:
            deal_note = self._build_contextual_deal_note(
                asking_price=int(req.listing.asking_price),
                readiness=readiness,
                risks=risks,
            )

        # Step 8: Contextual Score Note (Score Isolation)
        score_note = ContextualScoreNote(
            carspective_score=None,  # Intrinsic score is evaluated by Phase 5, not recalculated here
            purchase_readiness=readiness,
        )

        # Step 9: Limitations and Disclaimers
        limitations = [
            "CarSpective inspection intelligence is decision support and verification guidance, not a substitute for professional mechanical inspection.",
            "Condition assessments are derived from user-reported observations and documentary evidence supplied.",
            "Items not inspected remain strictly UNKNOWN and are never assumed to be satisfactory.",
            "Intrinsic CarSpective Score evaluates platform-level quality and is not mutated by individual vehicle wear.",
            "Underlying statistical fair market valuation remains mathematically independent from physical inspection findings.",
            "Always commission an independent hoist and electronic diagnostic scan before executing binding financial transfers."
        ]

        elapsed_ms = (time.perf_counter() - t_start) * 1000

        return InspectionResponse(
            session_id=session_id,
            vehicle_summary=vehicle_summary,
            canonical_vehicle_id=canonical_id,
            checklist=checklist,
            findings=findings,
            risks=risks,
            documentation_requirements=doc_requirements,
            summary=summary,
            purchase_readiness=readiness,
            deal_context=deal_note,
            score_context=score_note,
            limitations=limitations,
            computation_latency_ms=round(elapsed_ms, 2),
        )

    # ────────────────────────────────────────────────────────────────
    # Documentation Requirements Builder
    # ────────────────────────────────────────────────────────────────

    def _build_documentation_requirements(
        self, doc_records: Dict[str, str]
    ) -> List[DocumentationRequirement]:
        docs = [
            DocumentationRequirement(
                document_name="Original Registration Certificate (RC)",
                purpose="Confirms legal ownership, state jurisdiction, and vehicle chassis/engine numbers.",
                importance=ImportanceLevel.CRITICAL,
                status=doc_records.get("rc", "PENDING_VERIFICATION"),
                verification_checks=[
                    "Check chassis number on RC against firewall metal stamping",
                    "Verify owner sequence number on VAHAN portal",
                    "Ensure smart card has no physical tampering or micro-chip damage"
                ],
                consequence_if_missing="Vehicle cannot be legally transferred or registered in buyer's name."
            ),
            DocumentationRequirement(
                document_name="Bank Loan Clearance / Form 35 + NOC",
                purpose="Proves the vehicle has zero outstanding bank finance liens or hypothecation encumbrances.",
                importance=ImportanceLevel.CRITICAL,
                status=doc_records.get("noc", "PENDING_VERIFICATION"),
                verification_checks=[
                    "Check Bank NOC date (must be within 90 days of RTO submission)",
                    "Ensure Form 35 is signed by authorized bank signatory with bank stamp",
                    "Verify loan account number matches lender records"
                ],
                consequence_if_missing="Lending bank retains legal repossession lien; RTO rejects ownership transfer."
            ),
            DocumentationRequirement(
                document_name="Insurance Policy & Claim History (NCB)",
                purpose="Validates third-party liability compliance and reveals unstated accident repairs via No Claim Bonus.",
                importance=ImportanceLevel.HIGH,
                status=doc_records.get("insurance", "PENDING_VERIFICATION"),
                verification_checks=[
                    "Verify policy expiry date on insurer customer portal",
                    "Inspect NCB percentage for correlation with claim-free history",
                    "Ensure engine and chassis numbers on policy match RC"
                ],
                consequence_if_missing="Buyer assumes immediate liability for transit accidents and pre-existing damage."
            ),
            DocumentationRequirement(
                document_name="Authorized Service Records & Invoices",
                purpose="Provides verifiable proof of regular preventive maintenance and authentic mileage continuity.",
                importance=ImportanceLevel.HIGH,
                status=doc_records.get("service_history", "PENDING_VERIFICATION"),
                verification_checks=[
                    "Verify chronological mileage stamps match odometer progression",
                    "Check for major timing belt, gearbox oil, and brake fluid replacements",
                    "Cross-check dealer invoice numbers with authorized OEM network"
                ],
                consequence_if_missing="High uncertainty regarding deferred maintenance, engine sludge, and odometer fraud."
            ),
            DocumentationRequirement(
                document_name="Pollution Under Control (PUC) Certificate",
                purpose="Verifies emission compliance and provides recent third-party date/odometer benchmark.",
                importance=ImportanceLevel.LOW,
                status=doc_records.get("puc", "PENDING_VERIFICATION"),
                verification_checks=[
                    "Scan QR code on PUC to confirm authentic Parivahan server entry",
                    "Verify emission levels are within permissible limits"
                ],
                consequence_if_missing="Statutory fine under Motor Vehicles Act; inability to complete RTO ownership transfer."
            ),
        ]
        return docs

    # ────────────────────────────────────────────────────────────────
    # Contextual Deal Note Builder
    # ────────────────────────────────────────────────────────────────

    def _build_contextual_deal_note(
        self, asking_price: int, readiness: PurchaseReadiness, risks: List[InspectionRisk]
    ) -> ContextualDealNote:
        if readiness == PurchaseReadiness.HIGH_RISK_DO_NOT_PROCEED_YET:
            interpretation = (
                f"Asking price of ₹{asking_price:,} appears irrelevant: critical defects or title risks "
                "were identified during inspection. Commercial purchase is not recommended regardless of price."
            )
        elif readiness == PurchaseReadiness.PROFESSIONAL_INSPECTION_RECOMMENDED:
            interpretation = (
                f"Asking price of ₹{asking_price:,} must not be finalized until recommended professional "
                "hoist inspection quantifies repair costs for identified mechanical or structural anomalies."
            )
        elif readiness == PurchaseReadiness.VERIFY_BEFORE_NEGOTIATING:
            interpretation = (
                f"Asking price of ₹{asking_price:,} can be negotiated once pending documentation records "
                "are produced. Use observed attention items as concrete negotiation discount leverage."
            )
        elif readiness == PurchaseReadiness.INSUFFICIENT_EVIDENCE:
            interpretation = (
                f"Asking price of ₹{asking_price:,} cannot be evaluated against condition: over 60% of physical "
                "inspection items remain unknown. Do not commit funds without completing physical verification."
            )
        else:
            interpretation = (
                f"Vehicle physical and documentary condition is largely verified. Asking price of ₹{asking_price:,} "
                "can be evaluated directly against statistical fair market valuation baselines."
            )

        return ContextualDealNote(
            asking_price=asking_price,
            deal_interpretation=interpretation,
        )
