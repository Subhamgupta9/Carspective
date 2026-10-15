"""
CARspective — Inspection Findings Evaluation & Provenance Engine
Evaluates user, inspector, and seller observations against canonical checklist items.
Enforces strict provenance rules:
- Seller statements -> UNVERIFIED
- Buyer physical observations -> USER_STATED
- Official documents / service logs -> VERIFIED
- Uninspected items -> UNKNOWN (never converted to PASS)
"""

import uuid
from typing import List, Dict, Optional, Tuple
from server.domain.inspection.models import (
    ChecklistItem,
    FindingInput,
    InspectionFinding,
    FindingStatus,
    FindingSource,
    EvidenceState,
    RiskSeverity,
)


class FindingsEvaluationEngine:
    """Evaluates inspection inputs and generates strongly-typed findings with evidence provenance."""

    @staticmethod
    def evaluate_findings(
        checklist: List[ChecklistItem],
        finding_inputs: List[FindingInput],
    ) -> List[InspectionFinding]:
        """
        Synthesizes provided observations against active checklist items.
        Enforces evidence governance:
        - UNKNOWN is never treated as PASS.
        - Seller claims remain UNVERIFIED.
        """
        checklist_map: Dict[str, ChecklistItem] = {item.item_id: item for item in checklist}
        evaluated_findings: List[InspectionFinding] = []

        for f_in in finding_inputs:
            item = checklist_map.get(f_in.item_id)
            if not item:
                continue

            finding_id = f"fnd-{uuid.uuid4().hex[:10]}"

            # Determine Evidence State and Source
            if f_in.seller_claim or f_in.source == FindingSource.SELLER:
                source = FindingSource.SELLER
                evidence_state = EvidenceState.UNVERIFIED
            elif f_in.source == FindingSource.DOCUMENTED_EVIDENCE:
                source = FindingSource.DOCUMENTED_EVIDENCE
                evidence_state = EvidenceState.VERIFIED
            elif f_in.source == FindingSource.THIRD_PARTY_REPORT:
                source = FindingSource.THIRD_PARTY_REPORT
                evidence_state = EvidenceState.SUPPORTED
            else:
                source = FindingSource.BUYER_OBSERVATION
                evidence_state = EvidenceState.USER_STATED

            # Assign Severity based on status and item importance
            severity = RiskSeverity.LOW
            professional_inspection = False

            if f_in.status == FindingStatus.FAIL:
                severity = item.severity_if_failed
                professional_inspection = item.professional_inspection_required
            elif f_in.status == FindingStatus.ATTENTION:
                severity = RiskSeverity.MEDIUM if item.severity_if_failed == RiskSeverity.CRITICAL else RiskSeverity.LOW
                if item.professional_inspection_required and item.importance in ("CRITICAL", "HIGH"):
                    professional_inspection = True
            elif f_in.status == FindingStatus.UNKNOWN:
                severity = RiskSeverity.MEDIUM if item.importance == "CRITICAL" else RiskSeverity.LOW
                evidence_state = EvidenceState.INSUFFICIENT_DATA

            # Interpretation & Risk Effect narrative
            obs_text = f_in.observation or ("Condition verified as satisfactory" if f_in.status == FindingStatus.PASS else "No specific observation narrative provided")

            if f_in.status == FindingStatus.PASS:
                interpretation = f"Meets expected criteria: {item.expected_observation}"
                risk_effect = "No adverse risk identified from this verification."
                action = "Maintain documentation proof."
            elif f_in.status == FindingStatus.ATTENTION:
                interpretation = f"Minor anomaly or wear observed. Deviates slightly from expected: {item.expected_observation}."
                risk_effect = f"Potential maintenance expenditure or cosmetic negotiation leverage ({severity.value} severity)."
                action = item.verification_action
            elif f_in.status == FindingStatus.FAIL:
                interpretation = f"Critical discrepancy or defect confirmed. Triggers warning signs: {', '.join(item.warning_signs[:2]) if item.warning_signs else 'Defect confirmed'}."
                risk_effect = f"Material purchase risk detected ({severity.value} severity). Compromises vehicle reliability, safety, or legal title."
                action = f"{item.verification_action} Immediate resolution required before proceeding."
                if item.professional_inspection_required:
                    professional_inspection = True
            elif f_in.status == FindingStatus.UNKNOWN:
                interpretation = f"Item has not been verified. Condition remains unknown. (Rule: UNKNOWN != PASS)."
                risk_effect = f"Uncertainty gap on {item.title}. Cannot rule out latent defects."
                action = item.verification_action
            else:  # NOT_APPLICABLE
                interpretation = "Item is not applicable to this vehicle configuration."
                risk_effect = "No effect on purchase assessment."
                action = "None required."

            evaluated_findings.append(InspectionFinding(
                finding_id=finding_id,
                item_id=item.item_id,
                category=item.category,
                title=item.title,
                status=f_in.status,
                severity=severity,
                source=source,
                evidence_state=evidence_state,
                observation=obs_text,
                interpretation=interpretation,
                verification_action=action,
                risk_effect=risk_effect,
                professional_inspection_required=professional_inspection,
            ))

        return evaluated_findings
