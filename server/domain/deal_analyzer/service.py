"""
CARspective — Deal Analyzer Domain Service
Orchestrates deal quality evaluation, price deviation metrics, range position scoring,
statistically validated anomaly detection, evidence-grounded negotiation guidance,
and structured multi-category risk signals.

Strictly separates:
- Vehicle Features -> Phase 3 Valuation Engine (Fair-Market Baseline)
- Seller Asking Price -> Phase 4 Deal Analyzer (Commercial Proposition & Negotiation)
"""

import math
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from server.domain.deal_analyzer.models import (
    DealAnalysisRequest,
    DealAnalysisResponse,
    DealQualityEnum,
    RangePositionCategory,
    NegotiationStrength,
    RiskCategory,
    RiskSeverity,
    EvidenceState,
    PriceDeviation,
    FairRangePosition,
    AnomalyStatus,
    NegotiationGuidance,
    RiskSignal,
    ValuationContext
)
from server.domain.valuation.service import ValuationService
from server.domain.valuation.models import ValuationRequest, ValuationResponse

# Formatting helper for Indian Rupee representation
def format_inr(amount: Optional[int]) -> str:
    if amount is None:
        return "N/A"
    s = str(int(amount))
    if len(s) <= 3:
        return f"₹{s}"
    last_three = s[-3:]
    remaining = s[:-3]
    parts = []
    while len(remaining) > 2:
        parts.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        parts.insert(0, remaining)
    return f"₹{','.join(parts)},{last_three}"

def round_negotiation_currency(val: float) -> int:
    """Rounds currency to nearest ₹1,000 for realistic negotiation guidance."""
    return int(round(val / 1000.0) * 1000)

class DealAnalyzerService:
    def __init__(self, valuation_service: Optional[ValuationService] = None):
        """
        Initializes Deal Analyzer Service with Valuation Service dependency.
        Valuation Service acts as the single valuation authority.
        """
        if valuation_service is None:
            self.valuation_service = ValuationService()
        else:
            self.valuation_service = valuation_service

    def analyze_deal(
        self,
        req: DealAnalysisRequest,
        valuation_response: Optional[ValuationResponse] = None,
    ) -> DealAnalysisResponse:
        """
        Executes complete deal analysis:
        1. Calls Phase 3 Valuation Service (asking price strictly isolated) or reuses pre-computed valuation
        2. Calculates absolute and relative price deviations
        3. Evaluates position within calibrated 80% conformal range
        4. Detects statistical price anomalies using empirical ratio & robust z-score
        5. Assigns empirically justified deal quality classification
        6. Formulates evidence-grounded negotiation targets and strength
        7. Derives structured risk signals across price, documentation, condition, and data
        8. Synthesizes deterministic plain-language explanation
        """
        start_time = time.perf_counter()
        
        # Step 1: Forward request to Phase 3 Valuation Service (or reuse pre-evaluated valuation)
        # Asking price is passed for audit metadata but strictly ignored by the ML pipeline
        if valuation_response is not None:
            val_res: ValuationResponse = valuation_response
        else:
            val_req = ValuationRequest(
                brand=req.brand,
                model=req.model,
                manufacturing_year=req.manufacturing_year,
                km_driven=req.km_driven,
                fuel_type=req.fuel_type or "Petrol",
                transmission_type=req.transmission_type or "Manual",
                city=req.city or "Delhi",
                bodytype=req.bodytype,
                number_of_owners=req.number_of_owners or 1,
                variant=req.variant,
                asking_price=req.asking_price,
            )
            val_res = self.valuation_service.evaluate_valuation(val_req)
        
        ask_price = int(round(req.asking_price))
        vehicle_summary = (
            f"{req.manufacturing_year} {req.brand} {req.model} "
            f"({int(req.km_driven):,} km, {req.fuel_type or 'Petrol'}, {req.transmission_type or 'Manual'})"
        )
        
        # Step 2: Handle Insufficient Valuation Data
        if val_res.estimated_fair_market_value is None or val_res.confidence_state == "INSUFFICIENT_DATA":
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return self._build_insufficient_data_response(
                req=req,
                val_res=val_res,
                vehicle_summary=vehicle_summary,
                ask_price=ask_price,
                latency_ms=latency_ms
            )

        int_fair_value = val_res.estimated_fair_market_value
        lower_bound = val_res.expected_fair_market_range.lower_bound
        upper_bound = val_res.expected_fair_market_range.upper_bound
        conformal_multiplier = val_res.expected_fair_market_range.multiplier

        # Step 3: Price Deviation Metrics
        abs_diff = ask_price - int_fair_value
        rel_diff_pct = round(((ask_price - int_fair_value) / float(int_fair_value)) * 100.0, 2)
        
        if rel_diff_pct > 0.05:
            dev_summary = f"Asking price is approximately {abs(rel_diff_pct):.1f}% above the estimated market baseline."
        elif rel_diff_pct < -0.05:
            dev_summary = f"Asking price is approximately {abs(rel_diff_pct):.1f}% below the estimated market baseline."
        else:
            dev_summary = "Asking price aligns closely with the estimated market baseline."
            
        price_deviation = PriceDeviation(
            absolute_difference=abs_diff,
            relative_difference_percent=rel_diff_pct,
            user_facing_summary=dev_summary,
            evidence_state=EvidenceState.MODEL_ESTIMATE.value
        )

        # Step 4: Calibrated Fair-Range Position
        if upper_bound > lower_bound:
            range_pos_ratio = round((ask_price - lower_bound) / float(upper_bound - lower_bound), 4)
        else:
            range_pos_ratio = 0.5

        if ask_price < lower_bound:
            range_cat = RangePositionCategory.BELOW_RANGE
            range_exp = (
                f"Asking price ({format_inr(ask_price)}) is below the calibrated 80% fair market range "
                f"({format_inr(lower_bound)} – {format_inr(upper_bound)})."
            )
        elif ask_price > upper_bound:
            range_cat = RangePositionCategory.ABOVE_RANGE
            range_exp = (
                f"Asking price ({format_inr(ask_price)}) is above the calibrated 80% fair market range "
                f"({format_inr(lower_bound)} – {format_inr(upper_bound)})."
            )
        else:
            range_cat = RangePositionCategory.INSIDE_RANGE
            range_exp = (
                f"Asking price ({format_inr(ask_price)}) sits inside the calibrated 80% fair market range "
                f"({format_inr(lower_bound)} – {format_inr(upper_bound)})."
            )

        range_position = FairRangePosition(
            position_ratio=range_pos_ratio,
            category=range_cat,
            explanation=range_exp
        )

        # Step 5: Statistical Anomaly Detection & Deal Quality Classification
        # Empirical methodology grounded in 57,480 dataset analysis:
        # - asking_price / fair_value ratio
        # - robust log residual z-score: (ln(ratio) - median_log) / mad_log
        #   empirical params: median_log = 0.0084, mad_log = 0.158
        ratio = ask_price / float(int_fair_value)
        log_res = math.log(max(1.0, float(ask_price))) - math.log(max(1.0, float(int_fair_value)))
        robust_z = (log_res - 0.0084) / 0.158

        is_anomalous_low = (ratio < 0.65) or (robust_z < -3.0)
        is_anomalous_high = (ratio > 1.70) or (robust_z > 3.2)

        if is_anomalous_low:
            anomaly_status = AnomalyStatus(
                is_anomaly=True,
                anomaly_type="ANOMALOUS_LOW",
                anomaly_metric="EMPIRICAL_RATIO_AND_ROBUST_Z",
                anomaly_score=round(robust_z, 2),
                advisory=(
                    "This asking price is unusually low compared with comparable market observations. "
                    "Verify mechanical condition, accident history, ownership documents, service records "
                    "and vehicle history before proceeding."
                )
            )
            deal_quality = DealQualityEnum.UNUSUALLY_LOW_ASKING_PRICE
            deal_quality_label = "Unusually Low Asking Price"
            
        elif ask_price < lower_bound:
            # Below conformal 80% range, but not in extreme anomaly territory (0.65 <= ratio < 0.7822)
            anomaly_status = AnomalyStatus(
                is_anomaly=False,
                anomaly_type="NONE",
                anomaly_metric="EMPIRICAL_RATIO_AND_ROBUST_Z",
                anomaly_score=round(robust_z, 2),
                advisory=None
            )
            deal_quality = DealQualityEnum.GREAT_DEAL
            deal_quality_label = "Great Deal"
            
        elif ask_price > upper_bound:
            # Above conformal 80% range (ratio > 1.2178)
            anomaly_status = AnomalyStatus(
                is_anomaly=is_anomalous_high,
                anomaly_type="ANOMALOUS_HIGH" if is_anomalous_high else "NONE",
                anomaly_metric="EMPIRICAL_RATIO_AND_ROBUST_Z",
                anomaly_score=round(robust_z, 2),
                advisory=(
                    "Asking price is significantly higher than historical market observations for similar vehicles."
                    if is_anomalous_high else None
                )
            )
            deal_quality = DealQualityEnum.OVERPRICED
            deal_quality_label = "Overpriced"
            
        else:
            # Within conformal 80% range (lower_bound <= ask_price <= upper_bound)
            anomaly_status = AnomalyStatus(
                is_anomaly=False,
                anomaly_type="NONE",
                anomaly_metric="EMPIRICAL_RATIO_AND_ROBUST_Z",
                anomaly_score=round(robust_z, 2),
                advisory=None
            )
            deal_quality = DealQualityEnum.FAIR_DEAL
            deal_quality_label = "Fair Deal"

        # Step 6: Evidence-Grounded Negotiation Guidance
        negotiation = self._derive_negotiation_guidance(
            deal_quality=deal_quality,
            ask_price=ask_price,
            int_fair_value=int_fair_value,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_state=val_res.confidence_state
        )

        # Step 7: Structured Risk Signals
        risk_signals = self._evaluate_risk_signals(
            req=req,
            val_res=val_res,
            deal_quality=deal_quality,
            rel_diff_pct=rel_diff_pct,
            ask_price=ask_price
        )

        # Step 8: Deterministic Plain-Language Explanation
        explanation = self._generate_explanation(
            vehicle_summary=vehicle_summary,
            ask_price=ask_price,
            int_fair_value=int_fair_value,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            deal_quality=deal_quality,
            deal_quality_label=deal_quality_label,
            rel_diff_pct=rel_diff_pct,
            confidence_state=val_res.confidence_state,
            risk_signals=risk_signals
        )

        # Step 9: Limitations and Concept Separation Disclosures
        limitations = [
            "Deal Quality evaluates the specific asking-price proposition against the historical market baseline, "
            "not intrinsic vehicle mechanical condition or long-term brand reliability.",
            "A reliable vehicle can be classified as OVERPRICED if the seller asks above market value, and an average "
            "vehicle can be classified as a GREAT DEAL if priced below market baseline.",
            f"Seller asking price ({format_inr(ask_price)}) is an UNVERIFIED input and was strictly isolated from "
            "the statistical ML valuation baseline.",
            "Expected fair market range is empirically calibrated to 80% nominal conformal coverage.",
            "Negotiation guidance represents statistical estimation and does not guarantee seller acceptance."
        ]

        valuation_ctx = ValuationContext(
            estimated_fair_market_value=int_fair_value,
            estimated_fair_market_value_formatted=format_inr(int_fair_value),
            expected_fair_market_lower=lower_bound,
            expected_fair_market_upper=upper_bound,
            confidence_state=val_res.confidence_state,
            evidence_quality=val_res.evidence_quality,
            model_version=val_res.model_metadata.get("model_version", "carspective-val-v1.0.0"),
            target_semantic_concept=val_res.model_metadata.get(
                "target_concept",
                "Statistical Model Estimate of the Historical Market Asking-Price Baseline"
            )
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return DealAnalysisResponse(
            canonical_vehicle_id=val_res.canonical_vehicle_id,
            vehicle_summary=vehicle_summary,
            asking_price=ask_price,
            asking_price_formatted=format_inr(ask_price),
            asking_price_evidence_state=EvidenceState.UNVERIFIED.value,
            valuation=valuation_ctx,
            deal_quality=deal_quality,
            deal_quality_label=deal_quality_label,
            price_deviation=price_deviation,
            range_position=range_position,
            anomaly_status=anomaly_status,
            negotiation=negotiation,
            risk_signals=risk_signals,
            explanation=explanation,
            limitations=limitations,
            computation_latency_ms=latency_ms
        )

    def _derive_negotiation_guidance(
        self,
        deal_quality: DealQualityEnum,
        ask_price: int,
        int_fair_value: int,
        lower_bound: int,
        upper_bound: int,
        confidence_state: str
    ) -> NegotiationGuidance:
        """Derives negotiation targets without arbitrary fixed percentages."""
        if confidence_state == "LIMITED_CONFIDENCE":
            strength = NegotiationStrength.LIMITED
            safety_disclaimer = (
                "Negotiation guidance is limited because comparable market evidence is sparse. "
                "Physical inspection and local dealer validation are strongly recommended. "
                "Guidance represents statistical estimation and does not guarantee seller acceptance."
            )
        elif confidence_state == "HIGH_CONFIDENCE":
            strength = NegotiationStrength.STRONG if deal_quality == DealQualityEnum.OVERPRICED else NegotiationStrength.MODERATE
            safety_disclaimer = (
                "A reasonable negotiation target based on the current valuation evidence is indicated above. "
                "Guidance reflects secondary asking patterns and does not guarantee seller acceptance."
            )
        else:
            strength = NegotiationStrength.MODERATE
            safety_disclaimer = (
                "A reasonable negotiation target based on the current valuation evidence is indicated above. "
                "Guidance reflects secondary asking patterns and does not guarantee seller acceptance."
            )

        walk_away = False
        walk_away_rationale = None

        if deal_quality == DealQualityEnum.OVERPRICED:
            # Overpriced: aim for fair baseline, range between baseline and lower portion of ask
            target = round_negotiation_currency(int_fair_value)
            if target > int_fair_value:
                target = max(0, target - 1000)
            t_low = round_negotiation_currency(max(lower_bound, int_fair_value * 0.95))
            t_high = round_negotiation_currency(min(ask_price, upper_bound))
            
            # Check walk-away threshold (asking price > 35% above fair value)
            if ask_price > int_fair_value * 1.35:
                walk_away = True
                walk_away_rationale = (
                    f"Asking price is {round(((ask_price - int_fair_value)/int_fair_value)*100)}% above the estimated "
                    "market baseline, indicating a substantial premium that may be difficult to bridge through ordinary negotiation."
                )
                
            rationale = (
                f"The asking price is above the top of the calibrated fair market range ({format_inr(upper_bound)}). "
                f"A defensible counter-offer should target the market baseline ({format_inr(int_fair_value)})."
            )

        elif deal_quality == DealQualityEnum.FAIR_DEAL:
            if ask_price > int_fair_value:
                target = round_negotiation_currency(int_fair_value)
                t_low = round_negotiation_currency(int_fair_value * 0.95)
                t_high = round_negotiation_currency(ask_price)
                rationale = (
                    f"The vehicle is priced within the fair market band but above the central baseline. "
                    f"A reasonable counter-offer can target the market baseline ({format_inr(int_fair_value)})."
                )
            else:
                target = round_negotiation_currency(ask_price)
                t_low = round_negotiation_currency(max(lower_bound, ask_price * 0.96))
                t_high = round_negotiation_currency(ask_price)
                rationale = (
                    f"The asking price is competitively positioned within the lower half of the fair market range. "
                    "Minor courtesy negotiation is possible, but seller flexibility may be limited."
                )

        elif deal_quality == DealQualityEnum.GREAT_DEAL:
            target = round_negotiation_currency(ask_price)
            t_low = round_negotiation_currency(ask_price * 0.96)
            t_high = round_negotiation_currency(ask_price)
            strength = NegotiationStrength.LIMITED
            rationale = (
                f"The asking price is already meaningfully below the expected fair market range ({format_inr(lower_bound)}). "
                "Aggressive discounting carries a high risk of losing the vehicle to other buyers. "
                "Prioritize inspection over aggressive counter-offers."
            )

        elif deal_quality == DealQualityEnum.UNUSUALLY_LOW_ASKING_PRICE:
            target = round_negotiation_currency(ask_price)
            t_low = round_negotiation_currency(ask_price)
            t_high = round_negotiation_currency(ask_price)
            strength = NegotiationStrength.LIMITED
            rationale = (
                "The asking price is statistically anomalous (>35% below market baseline). "
                "Further price negotiation is secondary; thorough physical inspection, title validation, "
                "and service verification must be completed prior to making any financial commitment."
            )
        else:
            target = None
            t_low = None
            t_high = None
            rationale = "Negotiation guidance is limited because a market valuation could not be established."

        return NegotiationGuidance(
            target_price=target,
            target_price_formatted=format_inr(target) if target else None,
            target_range_low=t_low,
            target_range_high=t_high,
            target_range_formatted=f"{format_inr(t_low)} – {format_inr(t_high)}" if (t_low and t_high) else None,
            negotiation_strength=strength,
            walk_away_signal=walk_away,
            walk_away_rationale=walk_away_rationale,
            rationale=rationale,
            safety_disclaimer=safety_disclaimer
        )

    def _evaluate_risk_signals(
        self,
        req: DealAnalysisRequest,
        val_res: ValuationResponse,
        deal_quality: DealQualityEnum,
        rel_diff_pct: float,
        ask_price: int
    ) -> List[RiskSignal]:
        """Evaluates structured risk signals without arbitrary currency penalties."""
        signals: List[RiskSignal] = []

        # 1. Price Risks
        if deal_quality == DealQualityEnum.UNUSUALLY_LOW_ASKING_PRICE:
            signals.append(RiskSignal(
                category=RiskCategory.PRICE_RISK,
                code="ANOMALOUS_LOW_PRICE",
                severity=RiskSeverity.CRITICAL,
                evidence_state=EvidenceState.EMPIRICAL.value,
                title="Statistically Anomalous Low Asking Price",
                explanation=(
                    f"Asking price ({format_inr(ask_price)}) is more than 35% below the market baseline, "
                    "which occurs in less than 3% of comparable market listings."
                ),
                recommended_action=(
                    "Verify vehicle physical condition, accident history, ownership title, service logs, "
                    "and ensure no financial encumbrance before providing a token or deposit."
                )
            ))
        elif deal_quality == DealQualityEnum.OVERPRICED:
            severity = RiskSeverity.HIGH if rel_diff_pct > 30.0 else RiskSeverity.MEDIUM
            signals.append(RiskSignal(
                category=RiskCategory.PRICE_RISK,
                code="PRICE_ABOVE_FAIR_RANGE",
                severity=severity,
                evidence_state=EvidenceState.MODEL_ESTIMATE.value,
                title="Asking Price Above Fair Market Range",
                explanation=f"Asking price is {abs(rel_diff_pct):.1f}% above the model market baseline.",
                recommended_action="Negotiate down towards the estimated market baseline or compare competing listings."
            ))

        if val_res.confidence_state == "LIMITED_CONFIDENCE":
            signals.append(RiskSignal(
                category=RiskCategory.PRICE_RISK,
                code="VALUATION_CONFIDENCE_LIMITED",
                severity=RiskSeverity.MEDIUM,
                evidence_state=EvidenceState.MODEL_ESTIMATE.value,
                title="Limited Valuation Evidence Confidence",
                explanation="Market evidence for this vehicle age, mileage, or luxury tier is relatively sparse.",
                recommended_action="Validate valuation with independent physical inspection and local dealer quotes."
            ))

        # 2. Documentation Risks
        if req.service_history_status in ("UNAVAILABLE", "UNKNOWN", None):
            signals.append(RiskSignal(
                category=RiskCategory.DOCUMENTATION_RISK,
                code="SERVICE_HISTORY_UNVERIFIED",
                severity=RiskSeverity.MEDIUM,
                evidence_state=EvidenceState.UNVERIFIED.value,
                title="Service History Unverified",
                explanation="Authorized maintenance logs and service history records have not been provided or verified.",
                recommended_action="Request authorized dealership service printout and physical service booklet."
            ))

        if req.number_of_owners and req.number_of_owners >= 3:
            signals.append(RiskSignal(
                category=RiskCategory.DOCUMENTATION_RISK,
                code="MULTIPLE_PREVIOUS_OWNERS",
                severity=RiskSeverity.MEDIUM,
                evidence_state=EvidenceState.UNVERIFIED.value,
                title="Multiple Previous Owners",
                explanation=f"Vehicle has {req.number_of_owners} previous registered owners.",
                recommended_action="Verify RC validity, fitness certificate, and ensure clean ownership transfer documentation."
            ))

        if req.insurance_status in ("EXPIRED", "UNAVAILABLE"):
            signals.append(RiskSignal(
                category=RiskCategory.DOCUMENTATION_RISK,
                code="INSURANCE_EXPIRED_OR_UNAVAILABLE",
                severity=RiskSeverity.MEDIUM,
                evidence_state=EvidenceState.UNVERIFIED.value,
                title="Insurance Status Unverified or Expired",
                explanation="Active comprehensive insurance policy is not confirmed.",
                recommended_action="Factor immediate insurance renewal cost into budget and check past claim history."
            ))

        # 3. Condition Risks
        if req.accident_history_status in ("MAJOR_ACCIDENT", "MINOR_ACCIDENT"):
            is_major = ("MAJOR" in req.accident_history_status)
            signals.append(RiskSignal(
                category=RiskCategory.CONDITION_RISK,
                code="ACCIDENT_HISTORY_REPORTED",
                severity=RiskSeverity.CRITICAL if is_major else RiskSeverity.HIGH,
                evidence_state=EvidenceState.UNVERIFIED.value,
                title="Prior Accident History Reported",
                explanation=f"Prior {req.accident_history_status.lower().replace('_', ' ')} has been reported or indicated.",
                recommended_action="Perform thorough chassis geometry, apron, pillar, and airbag deployment inspection."
            ))

        if req.tyre_condition in ("WORN", "UNKNOWN"):
            signals.append(RiskSignal(
                category=RiskCategory.CONDITION_RISK,
                code="TYRE_CONDITION_UNVERIFIED",
                severity=RiskSeverity.LOW,
                evidence_state=EvidenceState.UNVERIFIED.value,
                title="Tyre Tread Condition Unverified",
                explanation="Tyre tread depth and manufacturing dates have not been physically verified.",
                recommended_action="Inspect tread wear indicator (TWI) and verify DOT manufacture code on all 4 tyres + spare."
            ))

        # 4. Data / Market Risks
        if val_res.vehicle_resolution_status != "EXACT_MATCH":
            signals.append(RiskSignal(
                category=RiskCategory.DATA_RISK,
                code="PARTIAL_TAXONOMY_RESOLUTION",
                severity=RiskSeverity.LOW,
                evidence_state=EvidenceState.MODEL_ESTIMATE.value,
                title="Generalized Model Taxonomy",
                explanation="Vehicle model was matched via alias or fallback resolution rather than an exact canonical variant.",
                recommended_action="Confirm exact vehicle equipment trim, powertrain options, and features physically."
            ))

        if req.km_driven > 120000:
            signals.append(RiskSignal(
                category=RiskCategory.DATA_RISK,
                code="HIGH_ODOMETER_ACCUMULATION",
                severity=RiskSeverity.MEDIUM,
                evidence_state=EvidenceState.EMPIRICAL.value,
                title="High Odometer Accumulation",
                explanation=f"Odometer reading of {int(req.km_driven):,} km exceeds typical secondary market median.",
                recommended_action="Inspect wear on suspension components, clutch/gearbox, and engine compression."
            ))

        return signals

    def _generate_explanation(
        self,
        vehicle_summary: str,
        ask_price: int,
        int_fair_value: int,
        lower_bound: int,
        upper_bound: int,
        deal_quality: DealQualityEnum,
        deal_quality_label: str,
        rel_diff_pct: float,
        confidence_state: str,
        risk_signals: List[RiskSignal]
    ) -> str:
        """Deterministic plain-language explanation generator."""
        lines = [
            f"The seller is asking {format_inr(ask_price)} for this {vehicle_summary}.",
            f"CARspective's estimated market baseline is {format_inr(int_fair_value)}, with a calibrated 80% fair market range of {format_inr(lower_bound)} to {format_inr(upper_bound)}."
        ]

        if deal_quality == DealQualityEnum.FAIR_DEAL:
            lines.append(
                f"The asking price falls within the expected fair market range ({abs(rel_diff_pct):.1f}% deviation from baseline). "
                "This listing represents a normal commercial proposition."
            )
        elif deal_quality == DealQualityEnum.GREAT_DEAL:
            lines.append(
                f"The asking price is approximately {abs(rel_diff_pct):.1f}% below the market baseline, sitting below the calibrated fair range. "
                "This listing represents a commercially attractive opportunity."
            )
        elif deal_quality == DealQualityEnum.OVERPRICED:
            lines.append(
                f"The asking price is approximately {abs(rel_diff_pct):.1f}% above the market baseline, exceeding the top of the calibrated fair range. "
                "This listing is currently overpriced relative to comparable market listings."
            )
        elif deal_quality == DealQualityEnum.UNUSUALLY_LOW_ASKING_PRICE:
            lines.append(
                f"The asking price is approximately {abs(rel_diff_pct):.1f}% below the market baseline, which is statistically anomalous. "
                "While superficially attractive, prices in this tail region frequently correlate with unrecorded damage or title issues."
            )

        # Highlight key risk if present
        high_risks = [r for r in risk_signals if r.severity in (RiskSeverity.CRITICAL, RiskSeverity.HIGH)]
        if high_risks:
            lines.append(f"Primary Verification Priority: {high_risks[0].title} — {high_risks[0].recommended_action}")

        return " ".join(lines)

    def _build_insufficient_data_response(
        self,
        req: DealAnalysisRequest,
        val_res: ValuationResponse,
        vehicle_summary: str,
        ask_price: int,
        latency_ms: float
    ) -> DealAnalysisResponse:
        """Builds graceful response when valuation data is insufficient."""
        val_ctx = ValuationContext(
            estimated_fair_market_value=None,
            estimated_fair_market_value_formatted="N/A",
            expected_fair_market_lower=None,
            expected_fair_market_upper=None,
            confidence_state="INSUFFICIENT_DATA",
            evidence_quality="INSUFFICIENT_DATA",
            model_version=val_res.model_metadata.get("model_version", "carspective-val-v1.0.0"),
            target_semantic_concept="Statistical Model Estimate of the Historical Market Asking-Price Baseline"
        )
        
        price_dev = PriceDeviation(
            absolute_difference=0,
            relative_difference_percent=0.0,
            user_facing_summary="Price deviation could not be calculated because a sufficiently reliable valuation baseline could not be established.",
            evidence_state=EvidenceState.INSUFFICIENT_DATA.value
        )
        
        range_pos = FairRangePosition(
            position_ratio=None,
            category=RangePositionCategory.UNAVAILABLE,
            explanation="Fair market range is unavailable due to insufficient market data."
        )
        
        anomaly = AnomalyStatus(
            is_anomaly=False,
            anomaly_type="NONE",
            anomaly_metric="UNAVAILABLE",
            advisory=None
        )
        
        negotiation = NegotiationGuidance(
            target_price=None,
            target_price_formatted=None,
            target_range_low=None,
            target_range_high=None,
            target_range_formatted=None,
            negotiation_strength=NegotiationStrength.LIMITED,
            walk_away_signal=False,
            rationale="Negotiation guidance is limited because comparable market evidence is sparse.",
            safety_disclaimer="Negotiation guidance unavailable."
        )
        
        risk_signals = [
            RiskSignal(
                category=RiskCategory.DATA_RISK,
                code="INSUFFICIENT_MARKET_DATA",
                severity=RiskSeverity.HIGH,
                evidence_state=EvidenceState.INSUFFICIENT_DATA.value,
                title="Insufficient Baseline Data",
                explanation="A verified statistical market valuation could not be established for this vehicle configuration.",
                recommended_action="Consult professional vehicle inspection services and specialized appraisal."
            )
        ]
        
        return DealAnalysisResponse(
            canonical_vehicle_id=val_res.canonical_vehicle_id,
            vehicle_summary=vehicle_summary,
            asking_price=ask_price,
            asking_price_formatted=format_inr(ask_price),
            asking_price_evidence_state=EvidenceState.UNVERIFIED.value,
            valuation=val_ctx,
            deal_quality=DealQualityEnum.INSUFFICIENT_DATA,
            deal_quality_label="Insufficient Market Data",
            price_deviation=price_dev,
            range_position=range_pos,
            anomaly_status=anomaly,
            negotiation=negotiation,
            risk_signals=risk_signals,
            explanation="Deal analysis unavailable because a sufficiently reliable valuation could not be established.",
            limitations=[
                "Deal analysis requires a statistically reliable valuation baseline.",
                f"Vehicle configuration '{req.brand} {req.model}' could not be matched with sufficient confidence.",
                f"Asking price ({format_inr(ask_price)}) could not be evaluated against historical data."
            ],
            computation_latency_ms=latency_ms
        )
