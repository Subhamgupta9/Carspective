"""
CARspective — Recommendation Domain Service
Orchestrates personalized decision support:
Combines:
1. Vehicle Intrinsic Quality (CARspective Score)
2. Deal Financial Merit (Phase 4 Deal Analyzer)
3. User Stated Priorities (USER_STATED)
4. Identified Risk Signals
5. Evidence Completeness
6. Market Alternatives

Produces the locked four-tier recommendation verdict:
- STRONG CONSIDERATION
- CONSIDER
- PROCEED WITH CAUTION
- NOT RECOMMENDED
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from server.domain.recommendation.models import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationVerdict,
    UserFitScore,
    MarketAlternative,
    RecommendationExplanation,
    UserProfile,
    ListingContext
)
from server.domain.scoring.models import ScoreRequest, ScoreResponse
from server.domain.scoring.service import ScoringService
from server.domain.deal_analyzer.models import DealAnalysisRequest, DealAnalysisResponse
from server.domain.deal_analyzer.service import DealAnalyzerService
from server.infrastructure.database import ScopedSession

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

class RecommendationService:
    def __init__(
        self,
        scoring_service: Optional[ScoringService] = None,
        deal_service: Optional[DealAnalyzerService] = None,
        session: Optional[Session] = None
    ):
        self._session = session
        self.scoring_service = scoring_service or ScoringService(session=session)
        self.deal_service = deal_service or DealAnalyzerService()

    @property
    def session(self) -> Session:
        if self._session is not None:
            return self._session
        return ScopedSession()

    @session.setter
    def session(self, value: Optional[Session]) -> None:
        self._session = value
        if hasattr(self, "scoring_service"):
            self.scoring_service.session = value

    def evaluate_recommendation(self, req: RecommendationRequest) -> RecommendationResponse:
        """Evaluates personalized vehicle recommendation."""
        # 1. Evaluate Intrinsic Vehicle Quality (CARspective Score)
        # Note: asking price is strictly omitted from scoring request
        score_req = ScoreRequest(
            brand=req.brand,
            model=req.model,
            manufacturing_year=req.manufacturing_year,
            fuel_type=req.fuel_type,
            transmission_type=req.transmission_type,
            variant=req.variant
        )
        score_res: ScoreResponse = self.scoring_service.calculate_score(score_req)

        # 2. Evaluate Deal Quality (if asking price provided)
        deal_res: Optional[DealAnalysisResponse] = None
        deal_quality_str = None
        risk_signals = []
        asking_price = None

        if req.listing and req.listing.asking_price and req.listing.asking_price > 0:
            asking_price = req.listing.asking_price
            deal_req = DealAnalysisRequest(
                brand=req.brand,
                model=req.model,
                manufacturing_year=req.manufacturing_year or 2019,
                km_driven=req.listing.km_driven or 45000.0,
                asking_price=req.listing.asking_price,
                fuel_type=req.fuel_type or "Petrol",
                transmission_type=req.transmission_type or "Manual",
                city=req.city or "Delhi",
                variant=req.variant,
                condition_notes=req.listing.condition_notes,
                service_history_status=req.listing.service_history_status,
                accident_history_status=req.listing.accident_history_status,
                insurance_status=req.listing.insurance_status,
                tyre_condition=req.listing.tyre_condition
            )
            deal_res = self.deal_service.analyze_deal(deal_req)
            deal_quality_str = deal_res.deal_quality.value
            risk_signals = deal_res.risk_signals

        user_profile = req.user_profile or UserProfile()

        # 3. Calculate User Fit
        user_fit = self._evaluate_user_fit(
            req=req,
            score_res=score_res,
            deal_res=deal_res,
            user_profile=user_profile
        )

        # 4. Synthesize Recommendation Verdict
        verdict = self._synthesize_verdict(
            score_res=score_res,
            deal_res=deal_res,
            user_fit=user_fit,
            user_profile=user_profile,
            risk_signals=risk_signals
        )

        # 5. Market Alternatives Search
        alternatives = self._find_alternatives(
            target_brand=req.brand,
            target_model=req.model,
            target_year=req.manufacturing_year or 2019,
            user_profile=user_profile,
            score_res=score_res
        )

        # 6. Deterministic Explanation
        explanation = self._generate_explanation(
            verdict=verdict,
            req=req,
            score_res=score_res,
            deal_res=deal_res,
            user_fit=user_fit,
            user_profile=user_profile,
            risk_signals=risk_signals
        )

        # 7. Risk Summary
        risk_summary = {
            "total_risk_signals": len(risk_signals),
            "critical_risks": sum(1 for r in risk_signals if r.severity.value == "CRITICAL"),
            "high_risks": sum(1 for r in risk_signals if r.severity.value == "HIGH"),
            "medium_risks": sum(1 for r in risk_signals if r.severity.value == "MEDIUM"),
            "low_risks": sum(1 for r in risk_signals if r.severity.value == "LOW")
        }

        limitations = [
            "Recommendation represents personalized decision support grounded in empirical data, not a purchase guarantee.",
            "User profile inputs are USER_STATED preferences and do not represent verified constraints.",
            "Deal quality reflects secondary market asking patterns, not final negotiated transaction prices.",
            "Always perform independent mechanical, electrical, and legal title verification before purchase."
        ]

        return RecommendationResponse(
            canonical_vehicle_id=score_res.canonical_vehicle_id,
            vehicle_summary=score_res.vehicle_summary,
            verdict=verdict,
            verdict_label=verdict.value,
            carspective_score=score_res.overall_score,
            carspective_score_quality=score_res.evidence_quality.value,
            deal_quality=deal_quality_str,
            user_fit=user_fit,
            risk_summary=risk_summary,
            explanation=explanation,
            alternatives=alternatives,
            limitations=limitations
        )

    def _evaluate_user_fit(
        self,
        req: RecommendationRequest,
        score_res: ScoreResponse,
        deal_res: Optional[DealAnalysisResponse],
        user_profile: UserProfile
    ) -> UserFitScore:
        """Evaluates alignment between vehicle attributes and user-stated requirements."""
        model_lower = req.model.lower()
        brand_lower = req.brand.lower()

        # A. Budget Fit
        effective_price = None
        if deal_res and deal_res.asking_price:
            effective_price = deal_res.asking_price
        elif deal_res and deal_res.valuation.estimated_fair_market_value:
            effective_price = deal_res.valuation.estimated_fair_market_value

        if user_profile.budget_max and effective_price:
            if effective_price <= user_profile.budget_max:
                budget_fit = 100
            else:
                pct_over = ((effective_price - user_profile.budget_max) / user_profile.budget_max) * 100
                if pct_over <= 10.0:
                    budget_fit = 75 if user_profile.budget_flexible else 45
                elif pct_over <= 25.0:
                    budget_fit = 50 if user_profile.budget_flexible else 20
                else:
                    budget_fit = 25 if user_profile.budget_flexible else 10
        else:
            budget_fit = 100

        # B. Family Fit
        fam_size = user_profile.family_size or 4
        is_7_seater = any(mpv in model_lower for mpv in ["ertiga", "innova", "carens", "triber", "scorpio"])
        is_lifestyle_3door = ("thar" in model_lower)

        if fam_size >= 6:
            family_fit = 95 if is_7_seater else 20
        elif fam_size == 5:
            family_fit = 95 if is_7_seater else (40 if is_lifestyle_3door else 80)
        else:
            family_fit = 60 if is_lifestyle_3door else 95

        # C. Usage Fit
        usage = (user_profile.primary_usage or "CITY").upper()
        is_hatch = any(h in model_lower for h in ["swift", "baleno", "i20", "wagon r", "alto", "tiago"])
        is_suv = any(s in model_lower for s in ["creta", "nexon", "brezza", "seltos", "venue", "thar"])
        is_sedan = any(sedan in model_lower for sedan in ["city", "verna", "ciaz", "dzire", "amaze"])

        if usage == "CITY":
            usage_fit = 95 if is_hatch else (85 if is_suv else 75)
        elif usage == "HIGHWAY":
            usage_fit = 95 if (is_sedan or is_suv) else 70
        else:
            usage_fit = 85

        # D. Powertrain Fit
        monthly_km = user_profile.monthly_km or 1000.0
        fuel = (req.fuel_type or "Petrol").upper()
        pref_fuel = (user_profile.fuel_preference or "ANY").upper()
        
        powertrain_fit = 100
        if pref_fuel not in ("ANY", None) and pref_fuel != fuel:
            powertrain_fit -= 30

        if monthly_km >= 1500 and fuel == "PETROL":
            powertrain_fit -= 20
        elif monthly_km >= 1500 and fuel in ("DIESEL", "CNG"):
            powertrain_fit += 10
        powertrain_fit = max(10, min(100, powertrain_fit))

        # E. Priority Alignment
        priority_fit = 100
        dim_map = {d.dimension_name.value: d.score for d in score_res.dimensions if d.score is not None}
        
        # Safety priority
        safety_pri = (user_profile.safety_priority or "HIGH").upper()
        safety_score = dim_map.get("Structural Safety")
        if safety_pri == "CRITICAL":
            if safety_score is not None:
                priority_fit = 95 if safety_score >= 80 else (60 if safety_score >= 65 else 20)
            else:
                priority_fit = 40
        elif safety_pri == "HIGH":
            if safety_score is not None and safety_score < 50:
                priority_fit -= 25

        # Maintenance priority
        maint_pri = (user_profile.maintenance_priority or "HIGH").upper()
        maint_score = dim_map.get("Maintenance & Ownership")
        if maint_pri == "HIGH" and maint_score is not None and maint_score < 70:
            priority_fit -= 20

        priority_fit = max(15, min(100, priority_fit))

        # Overall composite fit
        overall = int(round(
            budget_fit * 0.30 +
            family_fit * 0.20 +
            usage_fit * 0.15 +
            powertrain_fit * 0.15 +
            priority_fit * 0.20
        ))

        summary_parts = []
        if budget_fit < 50:
            summary_parts.append("Significant budget stretch required.")
        if family_fit < 50:
            summary_parts.append("Seating capacity is constrained for stated family size.")
        if priority_fit < 50:
            summary_parts.append("Conflict with stated high safety or maintenance priorities.")
        if not summary_parts:
            summary_parts.append("Strong overall alignment with buyer requirements and operating parameters.")

        return UserFitScore(
            overall_fit=overall,
            budget_fit=budget_fit,
            usage_fit=usage_fit,
            family_fit=family_fit,
            powertrain_fit=powertrain_fit,
            priority_alignment=priority_fit,
            fit_summary=" ".join(summary_parts),
            evidence_state="USER_STATED"
        )

    def _synthesize_verdict(
        self,
        score_res: ScoreResponse,
        deal_res: Optional[DealAnalysisResponse],
        user_fit: UserFitScore,
        user_profile: UserProfile,
        risk_signals: List[Any]
    ) -> RecommendationVerdict:
        """Deterministic synthesis of the four-tier recommendation spectrum."""
        has_critical_risk = any(r.severity.value == "CRITICAL" for r in risk_signals)
        is_deal_anomaly = (deal_res and deal_res.deal_quality.value == "UNUSUALLY_LOW_ASKING_PRICE")
        is_deal_overpriced = (deal_res and deal_res.deal_quality.value == "OVERPRICED")
        
        # Check Fatal Mismatch -> NOT RECOMMENDED
        if user_fit.budget_fit <= 20 and not user_profile.budget_flexible:
            return RecommendationVerdict.NOT_RECOMMENDED
        if user_fit.family_fit <= 25:
            return RecommendationVerdict.NOT_RECOMMENDED
        if user_profile.safety_priority == "CRITICAL" and user_fit.priority_alignment <= 25:
            return RecommendationVerdict.NOT_RECOMMENDED

        # Check Critical Caution Triggers -> PROCEED WITH CAUTION
        if has_critical_risk or is_deal_anomaly:
            return RecommendationVerdict.PROCEED_WITH_CAUTION
        if user_fit.budget_fit <= 45: # Budget exceeded, flexible or not
            return RecommendationVerdict.PROCEED_WITH_CAUTION
        if score_res.overall_score is not None and score_res.overall_score < 65:
            # Low intrinsic score should NOT become strong consideration even with good deal
            return RecommendationVerdict.PROCEED_WITH_CAUTION
        if score_res.evidence_quality.value == "INSUFFICIENT_DATA":
            return RecommendationVerdict.PROCEED_WITH_CAUTION

        # Check Meaningful Tradeoffs -> CONSIDER
        if is_deal_overpriced:
            # Good car, but overpriced deal
            return RecommendationVerdict.CONSIDER
        if user_fit.overall_fit < 75:
            return RecommendationVerdict.CONSIDER
        if score_res.evidence_quality.value == "LIMITED":
            return RecommendationVerdict.CONSIDER

        # Strong Match -> STRONG CONSIDERATION
        if (score_res.overall_score and score_res.overall_score >= 75) and user_fit.overall_fit >= 75:
            return RecommendationVerdict.STRONG_CONSIDERATION

        return RecommendationVerdict.CONSIDER

    def _find_alternatives(
        self,
        target_brand: str,
        target_model: str,
        target_year: int,
        user_profile: UserProfile,
        score_res: ScoreResponse
    ) -> List[MarketAlternative]:
        """Identifies grounded market alternatives from verified catalog."""
        t_model = target_model.lower()
        t_brand = target_brand.lower()
        alternatives = []

        # Verified catalog database
        catalog = [
            {
                "brand": "Tata",
                "model": "Nexon",
                "year": 2020,
                "price": 850000,
                "score": 84,
                "safety_stars": 5,
                "segment": "COMPACT_SUV",
                "advantage": "Verified 5-Star Global NCAP crash safety rating and rugged rough-road clearance."
            },
            {
                "brand": "Hyundai",
                "model": "Creta",
                "year": 2019,
                "price": 950000,
                "score": 83,
                "safety_stars": 3,
                "segment": "MID_SUV",
                "advantage": "High secondary market liquidity, refined cabin packaging, and extensive service support."
            },
            {
                "brand": "Maruti",
                "model": "Swift",
                "year": 2019,
                "price": 540000,
                "score": 79,
                "safety_stars": 2,
                "segment": "HATCHBACK",
                "advantage": "Industry-leading fuel economy, lowest maintenance parts basket, and exceptional resale liquidity."
            },
            {
                "brand": "Mahindra",
                "model": "Thar",
                "year": 2021,
                "price": 1380000,
                "score": 77,
                "safety_stars": 4,
                "segment": "LIFESTYLE_SUV",
                "advantage": "Dedicated mechanical 4x4 capability with verified 4-Star Global NCAP crashworthiness."
            }
        ]

        for cand in catalog:
            if cand["model"].lower() == t_model:
                continue

            # Budget check
            if user_profile.budget_max and cand["price"] > user_profile.budget_max * 1.15:
                continue

            rationale = ""
            # Why suggest?
            if user_profile.safety_priority in ("HIGH", "CRITICAL") and cand["safety_stars"] >= 4:
                rationale = f"Recommended because it delivers a {cand['safety_stars']}-Star verified Global NCAP rating within your budget."
            elif user_profile.maintenance_priority == "HIGH" and cand["brand"] == "Maruti":
                rationale = "Recommended for lowest total cost of ownership and 4,000+ service center accessibility."
            elif "thar" in t_model and user_profile.family_size >= 4 and cand["model"] in ("Creta", "Nexon"):
                rationale = "Recommended as a more practical 5-passenger alternative with enclosed boot space for family travel."
            elif cand["price"] < (user_profile.budget_max or 1000000):
                rationale = f"Strong alternative in the {cand['segment']} category with balanced ownership credentials."

            if rationale:
                alternatives.append(MarketAlternative(
                    brand=cand["brand"],
                    model=cand["model"],
                    manufacturing_year=cand["year"],
                    typical_price_inr=cand["price"],
                    typical_price_formatted=format_inr(cand["price"]),
                    carspective_score=cand["score"],
                    rationale=rationale,
                    advantage_over_target=cand["advantage"]
                ))
            if len(alternatives) >= 2:
                break

        return alternatives

    def _generate_explanation(
        self,
        verdict: RecommendationVerdict,
        req: RecommendationRequest,
        score_res: ScoreResponse,
        deal_res: Optional[DealAnalysisResponse],
        user_fit: UserFitScore,
        user_profile: UserProfile,
        risk_signals: List[Any]
    ) -> RecommendationExplanation:
        """Builds structured deterministic plain-language decision explanation."""
        # Positive factor
        strong_dims = [d for d in score_res.dimensions if d.score is not None and d.score >= 80]
        if strong_dims:
            positive = f"Strong intrinsic merit in {strong_dims[0].dimension_name.value} ({strong_dims[0].score}/100)."
        else:
            positive = f"Balanced overall capabilities (Score: {score_res.overall_score_formatted})."

        # Tradeoff
        weak_dims = [d for d in score_res.dimensions if d.score is not None and d.score < 70]
        if weak_dims:
            tradeoff = f"{weak_dims[0].dimension_name.value} ({weak_dims[0].score}/100) represents a compromise area."
        elif any(d.score is None for d in score_res.dimensions):
            tradeoff = "Incomplete verified crash test or platform documentation."
        else:
            tradeoff = "Minor depreciation wear expected with multi-year ownership."

        # Deal consideration
        if deal_res:
            deal_note = f"Listing is classified as {deal_res.deal_quality_label} ({deal_res.price_deviation.user_facing_summary})."
        else:
            deal_note = "No seller asking price was provided for deal evaluation."

        # User fit consideration
        user_note = f"User requirement fit is {user_fit.overall_fit}/100. {user_fit.fit_summary}"

        # Evidence limitation
        evidence_note = None
        if score_res.evidence_quality.value in ("LIMITED", "INSUFFICIENT_DATA"):
            evidence_note = "Evaluation is qualified due to limited verified evidence across critical dimensions."

        # Narrative narrative
        narrative = (
            f"Verdict: {verdict.value}. {score_res.vehicle_summary} achieves a CARspective Score of "
            f"{score_res.overall_score_formatted} with a user fit score of {user_fit.overall_fit}/100. "
            f"{positive} {tradeoff} {deal_note}"
        )

        return RecommendationExplanation(
            strongest_positive_factor=positive,
            biggest_tradeoff=tradeoff,
            deal_consideration=deal_note,
            user_fit_consideration=user_note,
            evidence_limitation=evidence_note,
            detailed_rationale=narrative
        )
