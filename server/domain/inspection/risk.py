"""
CARspective — Inspection Risk Engine & Professional Escalation Logic
Evaluates evaluated findings and context across 9 deterministic risk dimensions:
1. DOCUMENTATION_RISK
2. STRUCTURAL_RISK
3. POWERTRAIN_RISK
4. SAFETY_RISK
5. CONDITION_RISK
6. ODOMETER_RISK
7. OWNERSHIP_RISK
8. MAINTENANCE_RISK
9. DATA_QUALITY_RISK

Identifies mandatory professional mechanic escalation triggers.
"""

from typing import List, Dict, Tuple, Optional
from server.domain.inspection.models import (
    ChecklistItem,
    InspectionFinding,
    InspectionRisk,
    RiskCategory,
    RiskSeverity,
    FindingStatus,
    InspectionVehicleContext,
    EvidenceState,
)


class InspectionRiskEngine:
    """Evaluates findings and vehicle context into structured risks and professional triggers."""

    @staticmethod
    def evaluate_risks(
        vehicle: InspectionVehicleContext,
        findings: List[InspectionFinding],
        checklist: List[ChecklistItem],
    ) -> Tuple[List[InspectionRisk], bool, List[str]]:
        """
        Returns:
        1. List of identified InspectionRisk objects across the 9 dimensions
        2. Boolean: whether professional mechanic hoist inspection is required
        3. List of specific professional escalation trigger reasons
        """
        risks: List[InspectionRisk] = []
        escalation_reasons: List[str] = []

        finding_map: Dict[str, InspectionFinding] = {f.item_id: f for f in findings}

        # ── 1. DOCUMENTATION_RISK ───────────────────────────────────
        doc_fails = [f for f in findings if f.category.value == "Documentation" and f.status == FindingStatus.FAIL]
        doc_attns = [f for f in findings if f.category.value == "Documentation" and f.status == FindingStatus.ATTENTION]

        if any(f.item_id in ["DOC_RC_VERIFICATION", "DOC_VIN_CHASSIS_STAMPING", "DOC_NOC_HYPOTHECATION"] for f in doc_fails):
            risks.append(InspectionRisk(
                category=RiskCategory.DOCUMENTATION_RISK,
                severity=RiskSeverity.CRITICAL,
                evidence_state=EvidenceState.VERIFIED,
                title="Critical Legal Title or Registration Discrepancy",
                explanation="Registration Certificate details, chassis stamping, or bank loan hypothecation verification failed. Vehicle title cannot be legally conveyed.",
                verification_action="Halt transaction immediately until original RTO smart card and bank NOC are produced and verified with issuing authorities.",
            ))
            escalation_reasons.append("Chassis/VIN stamping or legal registration document discrepancy detected.")
        elif doc_fails or doc_attns:
            risks.append(InspectionRisk(
                category=RiskCategory.DOCUMENTATION_RISK,
                severity=RiskSeverity.HIGH if doc_fails else RiskSeverity.MEDIUM,
                evidence_state=EvidenceState.SUPPORTED,
                title="Incomplete or Discrepant Documentation Records",
                explanation="Service records, insurance validity, or ownership chain documents show gaps or inconsistencies.",
                verification_action="Request itemized service bills and verify insurance policy claim history directly with the carrier.",
            ))

        # Contextual documentation risk
        if vehicle.service_history_status in ("UNAVAILABLE", "UNKNOWN"):
            risks.append(InspectionRisk(
                category=RiskCategory.MAINTENANCE_RISK,
                severity=RiskSeverity.HIGH,
                evidence_state=EvidenceState.EMPIRICAL,
                title="Missing Service History & Preventive Maintenance Uncertainty",
                explanation="Absence of verified authorized workshop records increases uncertainty regarding scheduled timing belt, fluid, and consumable maintenance adherence.",
                verification_action="Demand physical workshop invoices or commission an engine compression and fluid laboratory test.",
            ))

        # ── 2. STRUCTURAL_RISK ──────────────────────────────────────
        structural_items = [
            "UND_CHASSIS_RAIL_CRUMPLE_ZONES", "UND_FACTORY_SPOT_WELDS",
            "EXT_PANEL_GAPS_ALIGNMENT", "UND_FLOOR_PAN_CORROSION_SCRAPES", "EXT_STRUCTURAL_GLASS_OEM"
        ]
        structural_fails = [f for f in findings if f.item_id in structural_items and f.status == FindingStatus.FAIL]
        structural_attns = [f for f in findings if f.item_id in structural_items and f.status == FindingStatus.ATTENTION]

        if structural_fails:
            risks.append(InspectionRisk(
                category=RiskCategory.STRUCTURAL_RISK,
                severity=RiskSeverity.CRITICAL,
                evidence_state=EvidenceState.VERIFIED,
                title="Structural Collision Repair or Chassis Deformation Detected",
                explanation="Physical evidence indicates longitudinal chassis rail distortion, non-factory weld joints, or floor pan impact. Crashworthiness is materially compromised.",
                verification_action="Mandatory professional inspection on a 4-post vehicle hoist with chassis laser alignment measurement.",
            ))
            escalation_reasons.append("Structural chassis rail kink, non-factory weld seam, or boot floor repair observed.")
        elif structural_attns:
            risks.append(InspectionRisk(
                category=RiskCategory.STRUCTURAL_RISK,
                severity=RiskSeverity.HIGH,
                evidence_state=EvidenceState.SUPPORTED,
                title="Suspected Panel Alignment or Body Shop Repair",
                explanation="Uneven panel gaps or replaced non-OEM structural glass suggest past collision repair of undetermined severity.",
                verification_action="Inspect inner apron metal and strut towers on a lift to confirm structural frame was not affected.",
            ))
            escalation_reasons.append("Suspicious panel gaps or replaced structural glass indicate past collision.")

        # ── 3. POWERTRAIN_RISK ──────────────────────────────────────
        powertrain_items = [
            "ENG_EXHAUST_SMOKE_COLOR", "ENG_OIL_CAP_BLOWBY", "ENG_WARNING_LAMPS_DIAGNOSTIC",
            "TRANS_AUTOMATIC_SHIFT_QUALITY", "TRANS_MANUAL_CLUTCH_BITE", "ENG_FLUID_LEAKS_INSPECTION"
        ]
        pow_fails = [f for f in findings if f.item_id in powertrain_items and f.status == FindingStatus.FAIL]
        pow_attns = [f for f in findings if f.item_id in powertrain_items and f.status == FindingStatus.ATTENTION]

        if pow_fails:
            risks.append(InspectionRisk(
                category=RiskCategory.POWERTRAIN_RISK,
                severity=RiskSeverity.CRITICAL,
                evidence_state=EvidenceState.VERIFIED,
                title="Major Engine or Transmission Abnormality",
                explanation="Colored exhaust smoke (blue/white), emulsified milky oil sludge, slipping transmission, or active check-engine fault detected.",
                verification_action="Professional mechanic diagnostic scan (OBD-II live data) and cylinder compression test required.",
            ))
            escalation_reasons.append("Severe powertrain defect (exhaust smoke, blow-by, milky oil, or transmission shudder/slip).")
        elif pow_attns:
            risks.append(InspectionRisk(
                category=RiskCategory.POWERTRAIN_RISK,
                severity=RiskSeverity.MEDIUM,
                evidence_state=EvidenceState.SUPPORTED,
                title="Powertrain Fluid Weeping or Wear Symptoms",
                explanation="Minor fluid seepage, idle roughness, or high clutch bite point observed. Indicates upcoming component replacement.",
                verification_action="Inspect under-engine drip pan on lift; check clutch slip on highway grade under full load.",
            ))

        # ── 4. SAFETY_RISK ──────────────────────────────────────────
        safety_items = [
            "SAF_AIRBAG_LAMP_CYCLE", "SAF_ABS_ESC_LAMP_SEQUENCE",
            "SAF_SEATBELTS_PRETENSIONERS", "SAF_BRAKE_PEDAL_FEEL", "INT_FLOOD_DAMAGE_WATERLINES"
        ]
        safety_fails = [f for f in findings if f.item_id in safety_items and f.status == FindingStatus.FAIL]
        safety_attns = [f for f in findings if f.item_id in safety_items and f.status == FindingStatus.ATTENTION]

        if safety_fails:
            risks.append(InspectionRisk(
                category=RiskCategory.SAFETY_RISK,
                severity=RiskSeverity.CRITICAL,
                evidence_state=EvidenceState.VERIFIED,
                title="Primary Safety Restraint or Braking Failure",
                explanation="Airbag warning indicator bypassed, brake pedal sinking to floor, seatbelt pretensioners inoperable, or flood damage discovered.",
                verification_action="Vehicle is unsafe for road operation until safety electronics and braking hydraulics are rebuilt by an authorized technician.",
            ))
            escalation_reasons.append("Airbag indicator tampering, sinking brake pedal, or flood submersion detected.")
        elif safety_attns:
            risks.append(InspectionRisk(
                category=RiskCategory.SAFETY_RISK,
                severity=RiskSeverity.HIGH,
                evidence_state=EvidenceState.SUPPORTED,
                title="Safety System Maintenance Watchpoint",
                explanation="Worn brake rotors/pads or sticky seatbelt retractors detected.",
                verification_action="Inspect brake pad friction lining thickness and test ABS operation on safe open road.",
            ))

        # ── 5. ODOMETER_RISK ────────────────────────────────────────
        odo_fails = [f for f in findings if f.item_id in ["DOC_ODOMETER_CONSISTENCY", "INT_ODOMETER_PEDAL_WEAR_RATIO"] and f.status == FindingStatus.FAIL]
        if odo_fails:
            risks.append(InspectionRisk(
                category=RiskCategory.ODOMETER_RISK,
                severity=RiskSeverity.CRITICAL,
                evidence_state=EvidenceState.VERIFIED,
                title="Suspected Odometer Rollback / Mileage Tampering",
                explanation="Documentary records show higher historical mileage than current display, or physical pedal/steering wear severely contradicts claimed mileage.",
                verification_action="Retrieve authorized manufacturer digital service log with timestamped odometer entries.",
            ))
            escalation_reasons.append("Odometer reading contradicts historical service records or physical wear indicators.")

        # ── 6. OWNERSHIP_RISK ───────────────────────────────────────
        if (vehicle.number_of_owners or 1) >= 3:
            risks.append(InspectionRisk(
                category=RiskCategory.OWNERSHIP_RISK,
                severity=RiskSeverity.HIGH,
                evidence_state=EvidenceState.SUPPORTED,
                title="Multiple Previous Owners (High Churn)",
                explanation=f"Vehicle has been registered to {vehicle.number_of_owners} owners, which empirically correlates with fragmented maintenance and uneven driving habits.",
                verification_action="Scrutinize chronological ownership transfer dates on VAHAN portal to identify quick flip patterns.",
            ))

        # ── 7. CONDITION_RISK ───────────────────────────────────────
        cond_fails = [f for f in findings if f.category.value in ("Exterior", "Interior") and f.status == FindingStatus.FAIL and f.item_id not in structural_items]
        if cond_fails:
            risks.append(InspectionRisk(
                category=RiskCategory.CONDITION_RISK,
                severity=RiskSeverity.MEDIUM,
                evidence_state=EvidenceState.SUPPORTED,
                title="Accumulated Cosmetic & Cabin Wear",
                explanation="Multiple exterior or cabin wear items failed inspection (tyres, HVAC, upholstery, or electrical switchgear).",
                verification_action="Tally itemized restoration costs and deduct from final negotiation offer.",
            ))

        # ── 8. DATA_QUALITY_RISK ────────────────────────────────────
        unknown_count = sum(1 for f in findings if f.status == FindingStatus.UNKNOWN)
        total_checklist = len(checklist)
        uninspected_ratio = (total_checklist - len(findings) + unknown_count) / max(1, total_checklist)

        if uninspected_ratio > 0.60:
            risks.append(InspectionRisk(
                category=RiskCategory.DATA_QUALITY_RISK,
                severity=RiskSeverity.HIGH,
                evidence_state=EvidenceState.INSUFFICIENT_DATA,
                title="High Inspection Information Uncertainty",
                explanation=f"Over {uninspected_ratio * 100:.0f}% of applicable inspection checklist items have not been verified. Physical condition is largely unevidenced.",
                verification_action="Complete comprehensive physical vehicle inspection before agreeing to non-refundable deposit.",
            ))

        # Determine overall professional escalation
        pro_required = len(escalation_reasons) > 0 or any(r.severity == RiskSeverity.CRITICAL for r in risks)

        return risks, pro_required, escalation_reasons
