"""
CARspective — Phase 8 Assistant Domain Service
Orchestrates multi-turn automotive conversation, canonical context resolution,
intent routing, evidence bundle retrieval, provider generation with deterministic fallback,
claim governance, and structured observability.
"""

import re
import time
import logging
from typing import Optional, List, Dict, Any

from server.domain.discovery.query_parser import MODEL_ALIASES, MANUFACTURER_ALIASES

from server.domain.assistant.models import (
    AssistantRequest,
    AssistantResponse,
    AssistantIntent,
    AssistantContext,
    VehicleContextInput,
    ListingContextInput,
    UserProfileInput,
    EvidenceBundle,
    EvidenceItem,
    AssistantEvidenceState,
    SourceDomain,
)
from server.domain.assistant.policy import AssistantPolicyEngine, STANDARD_DISCLAIMER
from server.domain.assistant.intent import IntentClassifier
from server.domain.assistant.tools import DomainToolDispatcher
from server.domain.assistant.provider import LLMProvider, GroundedDeterministicProvider
from server.domain.assistant.session import SessionStore

logger = logging.getLogger("carspective.assistant")


class AssistantService:
    """Production CarSpective Assistant Engine providing evidence-constrained explanations."""

    def __init__(
        self,
        session_store: Optional[SessionStore] = None,
        tool_dispatcher: Optional[DomainToolDispatcher] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.session_store = session_store or SessionStore()
        self.tool_dispatcher = tool_dispatcher or DomainToolDispatcher()
        self.default_provider = GroundedDeterministicProvider()
        self.llm_provider = llm_provider or self.default_provider

    def handle_message(self, req: AssistantRequest) -> AssistantResponse:
        """
        Coordinates full assistant pipeline:
        1. Sanitizes incoming message for privacy (PII).
        2. Retrieves or establishes conversational session context.
        3. Identifies and disambiguates vehicle identity across turns.
        4. Classifies intent using precedence-ordered routing.
        5. Dispatches calls to authoritative domain engines to populate EvidenceBundle.
        6. Generates evidence-grounded answer via provider with graceful deterministic fallback.
        7. Enforces claim governance, number integrity, and mechanical boundary disclaimers.
        8. Logs structured metadata and returns strongly typed AssistantResponse.
        """
        t0 = time.perf_counter()

        # Step 1: Privacy sanitization of input message
        clean_msg = AssistantPolicyEngine.sanitize_privacy(req.message)

        # Step 2: Session establishment
        ctx = self.session_store.get_or_create(
            session_id=req.session_id,
            vehicle=req.vehicle,
            listing=req.listing,
            user_profile=req.user_profile,
            compared_vehicles=req.compared_vehicles,
        )

        # Step 3: Vehicle Context Inference / Update from message text
        self._update_vehicle_context_from_message(clean_msg, ctx)

        # Step 4: Intent Classification
        try:
            intent = self.llm_provider.classify_intent(clean_msg, ctx)
        except Exception as e:
            logger.warning(f"Provider intent classification error: {e}. Falling back to deterministic classifier.")
            intent = IntentClassifier.classify(clean_msg, ctx)

        ctx.last_intent = intent

        # Step 5: Evidence Gathering via Domain Tools
        bundle = EvidenceBundle()
        self._gather_evidence_for_intent(intent, ctx, bundle, clean_msg)

        # Step 6: Generation via Provider with Graceful Fallback
        answer = ""
        provider_name = self.llm_provider.__class__.__name__
        try:
            answer = self.llm_provider.generate(clean_msg, bundle, ctx, intent)
        except Exception as e:
            logger.warning(f"Primary provider generation failed ({e}). Falling back to GroundedDeterministicProvider.")
            provider_name = f"{provider_name} -> GroundedDeterministicProvider (fallback)"
            answer = self.default_provider.generate(clean_msg, bundle, ctx, intent)

        # Step 7: Claim Governance & Factual Grounding
        context_meta = {}
        if ctx.current_vehicle:
            context_meta["year"] = ctx.current_vehicle.manufacturing_year
            context_meta["km"] = ctx.current_vehicle.km_driven
        if ctx.listing:
            context_meta["asking_price"] = ctx.listing.asking_price

        governed_answer, evidence_citations = AssistantPolicyEngine.validate_claim_grounding(
            answer, bundle, context_meta
        )

        # Step 8: Suggested Next Actions Formulation
        next_actions = self._formulate_next_actions(intent, ctx, bundle)

        # Step 9: Ephemeral Session Record
        self.session_store.append_turn(
            session_id=ctx.session_id,
            user_message=clean_msg,
            assistant_answer=governed_answer,
            intent=intent.value,
            evidence_refs=evidence_citations,
        )

        t1 = time.perf_counter()
        latency_ms = (t1 - t0) * 1000.0

        # Structured Observability Logging (Zero PII, Zero secrets)
        logger.info(
            f"Assistant turn completed: session={ctx.session_id} | intent={intent.value} | "
            f"domains={bundle.referenced_domains} | evidence_count={len(bundle.items)} | "
            f"provider={provider_name} | latency={latency_ms:.2f}ms"
        )

        session_updates = {
            "session_id": ctx.session_id,
            "has_current_vehicle": ctx.current_vehicle is not None,
            "compared_count": len(ctx.compared_vehicles),
            "last_intent": intent.value,
        }
        if ctx.current_vehicle:
            session_updates["current_vehicle_name"] = (
                f"{ctx.current_vehicle.brand} {ctx.current_vehicle.model}"
            )

        uncertainty_statement = (
            "; ".join(bundle.uncertainty_disclosures) if bundle.uncertainty_disclosures else None
        )

        return AssistantResponse(
            session_id=ctx.session_id,
            answer=governed_answer,
            intent=intent,
            referenced_domains=bundle.referenced_domains,
            evidence_refs=evidence_citations,
            evidence_bundle=bundle.items,
            uncertainty=uncertainty_statement,
            suggested_next_actions=next_actions,
            session_context_updates=session_updates,
            disclaimer=STANDARD_DISCLAIMER,
        )

    def _update_vehicle_context_from_message(self, message: str, ctx: AssistantContext) -> None:
        """
        Detects vehicle names mentioned in query to establish or extend context.
        Uses full taxonomy MODEL_ALIASES and preserves order of appearance in natural language.
        """
        msg_lower = message.lower()

        # Find all model matches in query with their text offsets
        matches: List[Tuple[int, str, str]] = []  # (start_index, brand, model)
        seen_models = set()

        # Sort model aliases by length descending so multi-word models match first
        for m_token, (canon_model, canon_mfg) in sorted(MODEL_ALIASES.items(), key=lambda x: -len(x[0])):
            pattern = rf"\b{re.escape(m_token)}\b"
            for m in re.finditer(pattern, msg_lower):
                idx = m.start()
                # Avoid overlapping substring matches
                if canon_model.lower() not in seen_models:
                    seen_models.add(canon_model.lower())
                    brand = canon_mfg or "Unknown"
                    matches.append((idx, brand, canon_model))

        # Check manufacturer mentions if no specific model was found
        if not matches:
            for mfg_tok, canon_mfg in sorted(MANUFACTURER_ALIASES.items(), key=lambda x: -len(x[0])):
                pattern = rf"\b{re.escape(mfg_tok)}\b"
                for m in re.finditer(pattern, msg_lower):
                    # Check if followed by an unknown model word
                    words = msg_lower[m.end():].strip().split()
                    sub_model = words[0].title() if words else "Car"
                    matches.append((m.start(), canon_mfg, sub_model))
                    break
                if matches:
                    break

        if not matches:
            return

        # Sort matches by appearance in text
        matches.sort(key=lambda x: x[0])
        detected = [(b, m) for _, b, m in matches]

        # Extract 4-digit model year if present in message
        year_match = re.search(r'\b(19\d\d|20[0-2]\d|2030)\b', message)
        extracted_year = int(year_match.group(1)) if year_match else None

        # If current vehicle is empty, set first detected
        if not ctx.current_vehicle:
            brand, model = detected[0]
            ctx.current_vehicle = VehicleContextInput(brand=brand, model=model, manufacturing_year=extracted_year)
            if len(detected) > 1:
                for b, m in detected[1:]:
                    if not any(cv.brand.lower() == b.lower() and cv.model.lower() == m.lower() for cv in ctx.compared_vehicles):
                        ctx.compared_vehicles.append(VehicleContextInput(brand=b, model=m))
        else:
            # If current vehicle exists and different vehicles are mentioned, add to comparison
            for b, m in detected:
                if (
                    b.lower() != ctx.current_vehicle.brand.lower()
                    or m.lower() != ctx.current_vehicle.model.lower()
                ):
                    if not any(
                        cv.brand.lower() == b.lower() and cv.model.lower() == m.lower()
                        for cv in ctx.compared_vehicles
                    ):
                        ctx.compared_vehicles.append(VehicleContextInput(brand=b, model=m))

    def _gather_evidence_for_intent(
        self,
        intent: AssistantIntent,
        ctx: AssistantContext,
        bundle: EvidenceBundle,
        message: str = "",
    ) -> None:
        """
        Executes appropriate domain tools based on the classified intent.
        Cross-car discovery, comparisons, and market advice do not require an active vehicle.
        """
        v = ctx.current_vehicle
        listing = ctx.listing
        user_prof = ctx.user_profile

        # 1. ALTERNATIVES & BUDGET DISCOVERY
        if intent == AssistantIntent.ALTERNATIVES:
            self.tool_dispatcher.fetch_cross_car_evidence(message, v, listing, user_prof, bundle)
            if v:
                self.tool_dispatcher.fetch_valuation_evidence(v, bundle)
                self.tool_dispatcher.fetch_score_evidence(v, bundle)
            return

        # 2. COMPARISON
        elif intent == AssistantIntent.COMPARISON:
            all_vehicles = []
            if v:
                all_vehicles.append(v)
            for cv in ctx.compared_vehicles:
                if not any(
                    x.brand.lower() == cv.brand.lower() and x.model.lower() == cv.model.lower()
                    for x in all_vehicles
                ):
                    all_vehicles.append(cv)

            if len(all_vehicles) >= 2:
                self.tool_dispatcher.fetch_comparison_evidence(all_vehicles[:3], user_prof, bundle)
                for veh in all_vehicles[:3]:
                    self.tool_dispatcher.fetch_knowledge_evidence(veh, bundle)
                    self.tool_dispatcher.fetch_score_evidence(veh, bundle)
            else:
                if v:
                    self.tool_dispatcher.fetch_knowledge_evidence(v, bundle)
                    self.tool_dispatcher.fetch_score_evidence(v, bundle)
                    self.tool_dispatcher.fetch_ownership_evidence(v, bundle)
                    self.tool_dispatcher.fetch_market_evidence(v, bundle)
                else:
                    bundle.uncertainty_disclosures.append("Comparison is evaluated based on market baselines and segments.")
            return

        # 3. RECOMMENDATION
        elif intent == AssistantIntent.RECOMMENDATION:
            if v:
                self.tool_dispatcher.fetch_score_evidence(v, bundle)
                self.tool_dispatcher.fetch_recommendation_evidence(v, listing, user_prof, bundle)
            else:
                self.tool_dispatcher.fetch_cross_car_evidence(message, v, listing, user_prof, bundle)
            return

        # 4. OWNERSHIP & RUNNING COSTS
        elif intent == AssistantIntent.OWNERSHIP:
            if v:
                self.tool_dispatcher.fetch_score_evidence(v, bundle)
                self.tool_dispatcher.fetch_knowledge_evidence(v, bundle)
                self.tool_dispatcher.fetch_ownership_evidence(v, bundle)
            else:
                bundle.uncertainty_disclosures.append("Ownership costs and resale benchmarks are based on market averages.")
            return

        # 5. MARKET & RESALE TRENDS
        elif intent == AssistantIntent.MARKET:
            if v:
                self.tool_dispatcher.fetch_valuation_evidence(v, bundle)
                self.tool_dispatcher.fetch_market_evidence(v, bundle)
                self.tool_dispatcher.fetch_current_market_intelligence(v, bundle)
            else:
                bundle.uncertainty_disclosures.append("Market trends reflect overall Indian secondary market dynamics.")
            return

        # For remaining unit-specific intents, active vehicle is required
        if not v:
            bundle.uncertainty_disclosures.append("A specific vehicle identity is required for individual valuation, inspection, or specification analysis.")
            return

        # 6. VALUATION
        if intent == AssistantIntent.VALUATION:
            self.tool_dispatcher.fetch_valuation_evidence(v, bundle)

        # 7. DEAL ANALYSIS
        elif intent == AssistantIntent.DEAL_ANALYSIS:
            self.tool_dispatcher.fetch_valuation_evidence(v, bundle)
            if listing and listing.asking_price:
                self.tool_dispatcher.fetch_deal_evidence(v, listing, bundle)
            else:
                bundle.missing_evidence.append("Seller asking price")
                bundle.uncertainty_disclosures.append("Asking price required to calculate deal classification.")

        # 8. NEGOTIATION
        elif intent == AssistantIntent.NEGOTIATION:
            self.tool_dispatcher.fetch_valuation_evidence(v, bundle)
            if listing and listing.asking_price:
                self.tool_dispatcher.fetch_deal_evidence(v, listing, bundle)

        # 9. SCORE
        elif intent == AssistantIntent.SCORE:
            self.tool_dispatcher.fetch_score_evidence(v, bundle)

        # 10. INSPECTION
        elif intent == AssistantIntent.INSPECTION:
            self.tool_dispatcher.fetch_inspection_evidence(v, listing, user_prof, bundle)

        # 11. RISK
        elif intent == AssistantIntent.RISK:
            self.tool_dispatcher.fetch_inspection_evidence(v, listing, user_prof, bundle)
            self.tool_dispatcher.fetch_knowledge_evidence(v, bundle)
            if listing and listing.asking_price:
                self.tool_dispatcher.fetch_deal_evidence(v, listing, bundle)

        # 12. SPECIFICATION / VEHICLE OVERVIEW
        elif intent in (AssistantIntent.SPECIFICATION, AssistantIntent.VEHICLE_OVERVIEW):
            self.tool_dispatcher.fetch_knowledge_evidence(v, bundle)
            self.tool_dispatcher.fetch_score_evidence(v, bundle)

        # 13. EXPLANATION / EVIDENCE
        elif intent in (AssistantIntent.EXPLANATION, AssistantIntent.EVIDENCE):
            self.tool_dispatcher.fetch_score_evidence(v, bundle)
            self.tool_dispatcher.fetch_valuation_evidence(v, bundle)

    def _formulate_next_actions(
        self,
        intent: AssistantIntent,
        ctx: AssistantContext,
        bundle: EvidenceBundle,
    ) -> List[str]:
        """Provides 2-3 concrete actionable next steps for the used-car buyer."""
        if intent == AssistantIntent.VALUATION:
            return [
                "Provide seller asking price to analyze deal quality.",
                "Review the adaptive pre-purchase inspection checklist.",
                "Check vehicle registration certificate and service invoices on-site.",
            ]
        elif intent == AssistantIntent.DEAL_ANALYSIS:
            return [
                "Use the CarSpective negotiation target to counter-offer.",
                "Verify whether tyres or battery require near-term replacement.",
                "Cross-check odometer reading against authorized service records.",
            ]
        elif intent == AssistantIntent.INSPECTION:
            return [
                "Examine engine bay apron spot welds for signs of collision repair.",
                "Verify DigiLocker RC Smart Card matches seller photo ID.",
                "Test drive at 60–80 km/h to check steering pull and brake judder.",
            ]
        elif intent == AssistantIntent.COMPARISON:
            return [
                "Review detailed trade-offs between back-seat comfort and running costs.",
                "Test drive both cars on broken city pavement.",
                "Check local spare parts availability and insurance renewal rates.",
            ]
        elif intent == AssistantIntent.SCORE:
            return [
                "Review individual dimension scores (Safety, Reliability, Maintenance).",
                "Compare intrinsic score with competing segment rivals.",
                "Verify specific unit condition with the inspection checklist.",
            ]
        elif intent == AssistantIntent.ALTERNATIVES:
            return [
                "Filter by body type and price range in Explore.",
                "Compare shortlisted rivals side-by-side on safety and boot space.",
                "Check verified listing availability and seller provenance.",
            ]
        else:
            return [
                "Check fair market valuation range for this model year.",
                "Request complete authorized service history records.",
                "Conduct a physical pre-purchase inspection before deposit.",
            ]
