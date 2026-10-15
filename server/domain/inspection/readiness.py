"""
CARspective — Purchase Readiness & Inspection Summary Engine
Synthesizes findings, risks, and documentation completeness into deterministic purchase readiness verdicts:
- READY_FOR_NEXT_STEP
- VERIFY_BEFORE_NEGOTIATING
- PROFESSIONAL_INSPECTION_RECOMMENDED
- HIGH_RISK_DO_NOT_PROCEED_YET
- INSUFFICIENT_EVIDENCE

Never outputs false certainties like 'SAFE' or 'SAFE TO BUY'.
"""

from typing import List, Tuple
from server.domain.inspection.models import (
    ChecklistItem,
    InspectionFinding,
    InspectionRisk,
    RiskCategory,
    FindingStatus,
    RiskSeverity,
    PurchaseReadiness,
    OverallInspectionStatus,
    InspectionSummary,
    DocumentationRequirement,
    ImportanceLevel,
)


class PurchaseReadinessEngine:
    """Calculates deterministic purchase readiness and summary metrics."""

    @staticmethod
    def evaluate_readiness_and_summary(
        checklist: List[ChecklistItem],
        findings: List[InspectionFinding],
        risks: List[InspectionRisk],
        doc_requirements: List[DocumentationRequirement],
        professional_required: bool,
        pro_reasons: List[str],
    ) -> Tuple[PurchaseReadiness, InspectionSummary]:
        """
        Determines overall inspection status, metrics counts, and purchase readiness verdict.
        """
        total_items = len(checklist)
        pass_count = sum(1 for f in findings if f.status == FindingStatus.PASS)
        attn_count = sum(1 for f in findings if f.status == FindingStatus.ATTENTION)
        fail_count = sum(1 for f in findings if f.status == FindingStatus.FAIL)
        unknown_count = sum(1 for f in findings if f.status == FindingStatus.UNKNOWN)
        na_count = sum(1 for f in findings if f.status == FindingStatus.NOT_APPLICABLE)

        # Uninspected items count
        inspected_item_ids = {f.item_id for f in findings}
        uninspected_count = sum(1 for item in checklist if item.item_id not in inspected_item_ids)
        total_unknown_or_missing = unknown_count + uninspected_count

        critical_risks = [r for r in risks if r.severity == RiskSeverity.CRITICAL]
        high_risks = [r for r in risks if r.severity == RiskSeverity.HIGH]

        critical_fails = sum(1 for f in findings if f.severity == RiskSeverity.CRITICAL and f.status == FindingStatus.FAIL)
        high_fails = sum(1 for f in findings if f.severity == RiskSeverity.HIGH and f.status == FindingStatus.FAIL)

        # Documentation completeness
        doc_verified_count = sum(1 for d in doc_requirements if d.status == "VERIFIED")
        doc_critical_count = sum(1 for d in doc_requirements if d.importance == ImportanceLevel.CRITICAL)
        doc_critical_verified = sum(1 for d in doc_requirements if d.importance == ImportanceLevel.CRITICAL and d.status == "VERIFIED")

        if doc_verified_count >= len(doc_requirements) and len(doc_requirements) > 0:
            doc_completeness = "COMPLETE"
        elif doc_critical_verified >= doc_critical_count and doc_critical_count > 0:
            doc_completeness = "PARTIAL"
        elif any(d.status in ("MISSING", "DISCREPANCY") for d in doc_requirements):
            doc_completeness = "INSUFFICIENT"
        else:
            doc_completeness = "UNKNOWN"

        # Evidence quality of inspection
        if pass_count + attn_count + fail_count >= total_items * 0.75 and doc_completeness == "COMPLETE":
            ev_quality = "HIGH"
        elif pass_count + attn_count + fail_count >= total_items * 0.45:
            ev_quality = "MODERATE"
        elif pass_count + attn_count + fail_count >= 5:
            ev_quality = "LIMITED"
        else:
            ev_quality = "INSUFFICIENT_DATA"

        # ── Determine Purchase Readiness ──────────────────────────
        physical_high_risks = [
            r for r in high_risks
            if r.category in (RiskCategory.STRUCTURAL_RISK, RiskCategory.POWERTRAIN_RISK, RiskCategory.SAFETY_RISK, RiskCategory.ODOMETER_RISK)
        ]

        if len(critical_risks) > 0 or critical_fails > 0:
            readiness = PurchaseReadiness.HIGH_RISK_DO_NOT_PROCEED_YET
            overall_status = OverallInspectionStatus.HIGH_RISK
            next_steps = [
                "DO NOT transfer booking advance or sign purchase agreement.",
                "Verify identified critical defect (chassis, flood, title, or odometer) with authoritative registry.",
                "Seek legal or mechanical verification if seller claims issue is resolved.",
            ]
        elif ev_quality == "INSUFFICIENT_DATA" or (pass_count + attn_count + fail_count) < 5:
            readiness = PurchaseReadiness.INSUFFICIENT_EVIDENCE
            overall_status = OverallInspectionStatus.INSUFFICIENT_EVIDENCE
            next_steps = [
                "Complete physical vehicle inspection following the adaptive checklist.",
                "Request physical Registration Certificate, service booklet, and insurance policy from seller.",
                "Execute test drive evaluating cold start, steering tracking, and braking stability.",
            ]
        elif professional_required or len(physical_high_risks) > 0 or high_fails > 0:
            readiness = PurchaseReadiness.PROFESSIONAL_INSPECTION_RECOMMENDED
            overall_status = OverallInspectionStatus.REVIEW_REQUIRED
            next_steps = [
                "Commission independent mechanical inspection on a service hoist before price commitment.",
                "Obtain electronic OBD-II diagnostic scan report for stored diagnostic fault codes.",
                "Require written estimate of repair costs from an authorized workshop.",
            ]
        elif doc_completeness in ("PARTIAL", "INSUFFICIENT", "UNKNOWN") or attn_count > 0 or len(risks) > 0:
            readiness = PurchaseReadiness.VERIFY_BEFORE_NEGOTIATING
            overall_status = OverallInspectionStatus.REVIEW_REQUIRED
            next_steps = [
                "Verify pending documentary proof (Bank NOC, service records, ownership continuity).",
                "Factor observed attention items into negotiation cost allowance.",
                "Verify chassis stamping directly against Parivahan digital register.",
            ]
        else:
            readiness = PurchaseReadiness.READY_FOR_NEXT_STEP
            overall_status = OverallInspectionStatus.CLEAR
            next_steps = [
                "Proceed to commercial deal negotiation armed with verified condition data.",
                "Ensure RTO ownership transfer forms (Forms 29 & 30) are signed with valid seller identity proof.",
                "Inspect vehicle delivery condition on handover day to ensure no parts were swapped.",
            ]

        summary = InspectionSummary(
            overall_status=overall_status,
            critical_findings_count=critical_fails,
            high_risk_findings_count=high_fails,
            attention_items_count=attn_count,
            unknown_items_count=total_unknown_or_missing,
            passed_items_count=pass_count,
            not_applicable_count=na_count,
            total_applicable_items=total_items,
            documentation_completeness=doc_completeness,
            evidence_quality=ev_quality,
            professional_inspection_required=professional_required,
            professional_inspection_reasons=pro_reasons,
            recommended_next_steps=next_steps,
        )

        return readiness, summary
