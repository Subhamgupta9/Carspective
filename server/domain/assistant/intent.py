"""
CARspective — Phase 8 Assistant Intent Classification Engine
Deterministic, pattern-grounded intent routing layer covering all 16 canonical automotive intents.
"""

import re
from typing import Optional, List, Dict, Any
from server.domain.assistant.models import (
    AssistantIntent,
    AssistantContext,
    VehicleContextInput,
)

# Canonical intent detection patterns (ordered by evaluation precedence)
INTENT_PATTERNS = [
    # 1. Comparison (Explicit comparisons, fuel trade-offs, and resale benchmarks)
    (
        AssistantIntent.COMPARISON,
        [
            r"\b(?:diesel.*(?:or|vs|against|over).*petrol|petrol.*(?:or|vs|against|over).*diesel)\b",
            r"\b(?:which car has lower maintenance|better resale value)\b",
            r"\b(?:compare|comparison|versus|vs\.?)\b",
            r"\b(?:diff(?:erence)? between)\b",
        ]
    ),
    # 2. Alternatives & Budget Discovery (high precedence)
    (
        AssistantIntent.ALTERNATIVES,
        [
            r"\b(?:alternatives?|other options?|similar cars?|what else)\b",
            r"\b(?:what other (?:cars|vehicles)|competitors?)\b",
            r"\b(?:better car|better options?|better alternative)\b",
            r"\b(?:can i get a better|could i get a better|is there a better)\b",
            r"\b(?:in the same budget|for the same (?:money|price|budget)|within (?:my|the|this) budget|in this budget)\b",
            r"\b(?:should i consider another|consider (?:other|another) (?:car|model|option)|look for another)\b",
            r"\b(?:is my selected car actually the best deal|best deal under|best (?:used )?(?:car|suv|sedan|hatchback) under)\b",
            r"\b(?:which (?:used )?(?:car|suv|sedan|hatchback) is best under)\b",
            r"\b(?:what (?:car|cars|suv|suvs|sedan|vehicle|vehicles) should i buy)\b",
            r"\b(?:find alternatives|alternatives available|options near)\b",
            r"\b(?:under|below|sub|less than|up to)\s*(?:inr\s*|rs\.?\s*|₹\s*)?\d+(?:\.\d+)?\s*(?:lakhs?|lac|l)\b",
            r"\b(?:budget\s*(?:of|is|around|:)?\s*(?:inr\s*|rs\.?\s*|₹\s*)?\d+(?:\.\d+)?\s*(?:lakhs?|lac|l))\b",
            r"\b(?:\d+(?:\.\d+)?\s*(?:lakhs?|lac|l)\s*budget)\b",
        ]
    ),
    # 3. Secondary Comparison patterns
    (
        AssistantIntent.COMPARISON,
        [
            r"\b(?:diff(?:erence)?)\b",
            r"\b(?:better than|which should i pick|who wins)\b",
            r"\b(?:safer than|more reliable than|cheaper to maintain than)\b",
            r"\b(?:which (?:one|car) is (?:better|cheaper|safer|faster))\b",
        ]
    ),
    # 3. Negotiation
    (
        AssistantIntent.NEGOTIATION,
        [
            r"\b(?:negotiat(?:e|ion)|counter[\s-]?offer|bargain|discount)\b",
            r"\b(?:what should i offer|how much should i pay|target price|offer price)\b",
            r"\b(?:price flexibility|room to negotiate)\b",
        ]
    ),
    # 4. Deal Analysis
    (
        AssistantIntent.DEAL_ANALYSIS,
        [
            r"\b(?:good deal|great deal|bad deal|fair deal|unfair deal)\b",
            r"\b(?:overpriced|underpriced|steal|rip[\s-]?off|worth the price)\b",
            r"\b(?:is (?:this|it) worth (?:it|the price|that much|[\d₹])|is the deal worth|asking price (?:fair|high|reasonable))\b",
            r"\b(?:deal quality|deal rating)\b",
        ]
    ),
    # 5. Valuation
    (
        AssistantIntent.VALUATION,
        [
            r"\b(?:valuation|fair market value|estimated value|expected price|fair (?:market )?price|estimated fair (?:market )?price)\b",
            r"\b(?:how much is (?:this|it) worth|what is it worth|price range|worth in the market)\b",
            r"\b(?:is it expensive|is this car expensive|market value)\b",
            r"\b(?:asking-price baseline|historical price baseline)\b",
        ]
    ),
    # 6. Inspection
    (
        AssistantIntent.INSPECTION,
        [
            r"\b(?:inspect(?:ion)?|checklist|check before (?:buying|purchasing))\b",
            r"\b(?:what should i check|what to check|test drive check)\b",
            r"\b(?:warning signs|red flags|underbody check|apron check|welding)\b",
            r"\b(?:mechanic check|pre-purchase inspection)\b",
        ]
    ),
    # 7. Score
    (
        AssistantIntent.SCORE,
        [
            r"\b(?:carspective score|vehicle score|rating score|scored? \d+)\b",
            r"\b(?:why is (?:it|this car) scored|safety score|reliability score)\b",
            r"\b(?:maintenance score|practicality score|resale score)\b",
        ]
    ),
    # 8. Recommendation
    (
        AssistantIntent.RECOMMENDATION,
        [
            r"\b(?:should i buy|is this recommended|recommend(?:ation)?|good choice)\b",
            r"\b(?:why did (?:you|carspective) recommend|suitable for me|family fit)\b",
            r"\b(?:is this the right car|buy or skip)\b",
        ]
    ),
    # 9. Risk
    (
        AssistantIntent.RISK,
        [
            r"\b(?:biggest risks?|hidden risks?|hazard|danger|pitfalls?)\b",
            r"\b(?:what could go wrong|risk factors?|major concerns?)\b",
        ]
    ),
    # 10. Ownership
    (
        AssistantIntent.OWNERSHIP,
        [
            r"\b(?:maintenance cost|service cost|annual maintenance|running cost)\b",
            r"\b(?:ownership (?:cost|experience)|spare parts?|cost to keep)\b",
            r"\b(?:service interval|routine service)\b",
        ]
    ),
    # 11. Market
    (
        AssistantIntent.MARKET,
        [
            r"\b(?:market trend|depreciation|resale trend|demand in market)\b",
            r"\b(?:market dynamics|used car market)\b",
        ]
    ),
    # 12. Evidence & Gaps
    (
        AssistantIntent.EVIDENCE,
        [
            r"\b(?:what is missing|what don't we know|unknown information)\b",
            r"\b(?:evidence quality|is (?:this|that) verified|provenance|missing data)\b",
            r"\b(?:insufficient data|data gaps?|unverified|seller claims?|seller says)\b",
            r"\b(?:authenti(?:c|city)|genuine|odometer.*(?:verified|real|authentic))\b",
        ]
    ),
    # 13. Specification
    (
        AssistantIntent.SPECIFICATION,
        [
            r"\b(?:specs?|specifications?|engine capacity|displacement|cc)\b",
            r"\b(?:boot space|dimensions?|ground clearance|fuel tank)\b",
            r"\b(?:power|bhp|torque|nm|mileage|kmpl|seating capacity)\b",
        ]
    ),
    # 14. Explanation
    (
        AssistantIntent.EXPLANATION,
        [
            r"\b(?:why\??|explain (?:that|this|why)|how come|reasoning)\b",
            r"\b(?:how did you arrive|elaborate)\b",
        ]
    ),
    # 15. Vehicle Overview
    (
        AssistantIntent.VEHICLE_OVERVIEW,
        [
            r"\b(?:tell me about|overview of|summary of|about this (?:car|vehicle))\b",
            r"\b(?:introduce|what is this (?:car|vehicle|model))\b",
        ]
    ),
]


class IntentClassifier:
    """Classifies user queries into strongly typed AssistantIntent enum values."""

    @staticmethod
    def classify(
        message: str,
        context: Optional[AssistantContext] = None,
        extracted_vehicle: Optional[VehicleContextInput] = None,
    ) -> AssistantIntent:
        """
        Classifies incoming query using pattern precedence and conversational context.
        """
        clean_msg = message.strip().lower()

        # Contextual check: If query mentions a second car while a vehicle is already active,
        # it's a comparison query (e.g. "What about the Verna?" or "How about City?")
        if context and context.current_vehicle:
            # If the user is asking for budget discovery or alternatives (e.g. "under 8 lakh", "alternatives"),
            # do not hijack to COMPARISON!
            is_budget_or_alt = bool(re.search(r'\b(?:under|below|sub|<|less than|up to|budget|alternatives?)\b', clean_msg))
            if not is_budget_or_alt:
                comp_keywords = ["what about", "how about", "vs", "versus", "compare with", "instead of"]
                if any(k in clean_msg for k in comp_keywords):
                    return AssistantIntent.COMPARISON

        # Contextual check: "Is it expensive?" with asking price present -> DEAL_ANALYSIS
        if "expensive" in clean_msg or "cheap" in clean_msg:
            if context and context.listing and context.listing.asking_price:
                return AssistantIntent.DEAL_ANALYSIS
            return AssistantIntent.VALUATION

        # Rule evaluation through ordered patterns
        for intent, patterns in INTENT_PATTERNS:
            for pat in patterns:
                if re.search(pat, clean_msg, re.IGNORECASE):
                    return intent

        # Contextual fallback: If message mentions a vehicle model name directly
        known_models = ["city", "verna", "creta", "swift", "baleno", "nexon", "innova", "harrier", "seltos", "brezza"]
        if any(m in clean_msg for m in known_models):
            if any(term in clean_msg for term in ["worth", "price", "cost"]):
                return AssistantIntent.VALUATION
            return AssistantIntent.VEHICLE_OVERVIEW

        return AssistantIntent.UNKNOWN
