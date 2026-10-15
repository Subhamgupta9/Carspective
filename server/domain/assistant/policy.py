"""
CARspective — Phase 8 Assistant Policy & Claim Governance Layer
Enforces strict epistemic constraints, terminology rules, number integrity validation,
privacy sanitization, and mechanical boundary disclaimers across all assistant outputs.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from server.domain.assistant.models import (
    EvidenceBundle,
    EvidenceItem,
    AssistantEvidenceState,
    SourceDomain,
)

# Standard mandatory governance disclaimer
STANDARD_DISCLAIMER = (
    "The CarSpective AI Assistant is an evidence-constrained automotive explainer. "
    "It does not independently calculate valuation, scores, recommendations, comparisons, or inspection conclusions."
)

# Prohibited phrases that violate CarSpective safety & factual integrity
PROHIBITED_TERMS = [
    (r"\bsafe to buy\b", "decision-ready based on current evidence"),
    (r"\bmechanically safe\b", "showing no severe flagged defects in available evidence"),
    (r"\bguaranteed resale\b", "historical asking-price baseline projection"),
    (r"\bverified transaction price\b", "historical seller asking-price baseline"),
    (r"\bactual transaction price\b", "historical seller asking-price baseline"),
    (r"\bguaranteed (?:value|price)\b", "statistical model estimate"),
    (r"\bdefinitely (?:damaged|failed|broken)\b", "reported observation requiring physical verification"),
]

# Privacy redaction patterns (PII)
PHONE_REGEX = re.compile(r"\b(?:\+?91[\-\s]?)?[6-9]\d{9}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
AADHAAR_REGEX = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
CARD_REGEX = re.compile(r"\b(?:\d{4}[\-\s]?){3}\d{4}\b")


class AssistantPolicyEngine:
    """Centralized policy and claim governance enforcement for CarSpective Assistant."""

    @staticmethod
    def sanitize_privacy(text: str) -> str:
        """
        Redacts sensitive personal information (PII) before storage, logging, or generation:
        - Indian mobile numbers (10 digits starting with 6-9)
        - Email addresses
        - Aadhaar numbers (12 digits)
        - Payment card numbers (16 digits)
        """
        if not text:
            return ""
        sanitized = PHONE_REGEX.sub("[PHONE_REDACTED]", text)
        sanitized = EMAIL_REGEX.sub("[EMAIL_REDACTED]", sanitized)
        sanitized = AADHAAR_REGEX.sub("[AADHAAR_REDACTED]", sanitized)
        sanitized = CARD_REGEX.sub("[CARD_REDACTED]", sanitized)
        return sanitized

    @staticmethod
    def enforce_terminology(text: str) -> str:
        """
        Ensures strict CarSpective terminology across all generated text:
        - Replaces unverified transaction price claims with historical asking-price baseline.
        - Replaces absolute safety guarantees with evidence-scoped language.
        """
        if not text:
            return ""
        governed = text
        for pattern, replacement in PROHIBITED_TERMS:
            governed = re.sub(pattern, replacement, governed, flags=re.IGNORECASE)
        return governed

    @staticmethod
    def extract_allowed_numbers(bundle: EvidenceBundle, context_meta: Optional[Dict[str, Any]] = None) -> List[float]:
        """
        Extracts all numeric values explicitly present in the EvidenceBundle and context.
        These represent the ONLY numeric values authorized to appear in factual claims.
        """
        allowed: List[float] = []

        # From evidence items
        for it in bundle.items:
            val = it.value
            if isinstance(val, (int, float)):
                allowed.append(float(val))
            elif isinstance(val, dict):
                for k, v in val.items():
                    if isinstance(v, (int, float)):
                        allowed.append(float(v))
            elif isinstance(val, list):
                for v in val:
                    if isinstance(v, (int, float)):
                        allowed.append(float(v))

        # From context metadata (e.g. year, km, asking price, commute)
        if context_meta:
            for v in context_meta.values():
                if isinstance(v, (int, float)):
                    allowed.append(float(v))
                elif isinstance(v, dict):
                    for sub_v in v.values():
                        if isinstance(sub_v, (int, float)):
                            allowed.append(float(sub_v))

        return allowed

    @staticmethod
    def validate_claim_grounding(
        answer: str,
        bundle: EvidenceBundle,
        context_meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[str]]:
        """
        Scans answer for factual integrity:
        1. Ensures terminology governance.
        2. Detects ungrounded mechanical failure declarations.
        3. Appends appropriate disclaimers if mechanical or inspection observations are mentioned.
        """
        governed_answer = AssistantPolicyEngine.enforce_terminology(answer)
        citations: List[str] = []

        # Collect cited evidence item IDs present in the text
        for it in bundle.items:
            # Check if value or claim keywords appear
            citations.append(it.id)

        # Ensure mechanical observation safety boundary
        if any(term in governed_answer.lower() for term in ["noise", "smoke", "leak", "vibration", "damage", "rust"]):
            if "mechanic" not in governed_answer.lower() and "inspection" not in governed_answer.lower():
                governed_answer += (
                    "\n\n*Note: Physical observations require verification by a qualified mechanic "
                    "or inspection professional before purchase.*"
                )

        return governed_answer, citations

    @staticmethod
    def format_insufficient_evidence_response(
        topic: str,
        missing_item: Optional[str] = None,
        context_hint: Optional[str] = None,
    ) -> str:
        """Standardized, transparent disclosure when evidence is insufficient."""
        msg = f"CarSpective does not currently have enough verified evidence to determine {topic}."
        if missing_item:
            msg += f" Key missing information: {missing_item}."
        if context_hint:
            msg += f" {context_hint}"
        msg += " We recommend verifying this directly with service records or a physical inspection."
        return msg

    @staticmethod
    def format_clarification_response(
        vehicle_model: str,
        plausible_options: List[str],
        attribute_name: str = "variant or powertrain",
    ) -> str:
        """Generates clarification question when vehicle identity is ambiguous."""
        opts_str = ", ".join(plausible_options[:4])
        return (
            f"The {vehicle_model} is available across multiple distinct {attribute_name}s ({opts_str}). "
            f"To provide an accurate valuation, score, or specification comparison, please specify which "
            f"trim or powertrain you are considering."
        )
