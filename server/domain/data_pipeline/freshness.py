"""
CARspective — Freshness Engine
Provides deterministic evaluation of data freshness across evidence domains and source types.
Enforces explicit freshness policies rather than arbitrary UI labels.
"""

from datetime import date, datetime, timezone
from typing import Optional, Dict, Any, List

from .models import (
    FreshnessState,
    FreshnessPolicy,
    FreshnessEvaluation,
    DomainFreshnessSummary,
)

# Canonical Freshness Policies
POLICIES: Dict[str, FreshnessPolicy] = {
    "POLICY_SAFETY_CRASH_TEST": FreshnessPolicy(
        policy_id="POLICY_SAFETY_CRASH_TEST",
        name="Global NCAP / Bharat NCAP Crash Rating Policy",
        target_domain="SAFETY",
        max_current_days=2555,     # Up to 7 years (generation lifecycle)
        review_due_days=3650,      # 7 to 10 years requires periodic protocol review
        stale_threshold_days=3650, # > 10 years or superseded protocol is stale
        description="Crash test safety ratings remain valid across the physical generation platform lifecycle."
    ),
    "POLICY_OEM_SPECIFICATIONS": FreshnessPolicy(
        policy_id="POLICY_OEM_SPECIFICATIONS",
        name="OEM Mechanical & Technical Specifications Policy",
        target_domain="SPECIFICATIONS",
        max_current_days=1825,     # 5 years
        review_due_days=2920,      # 5 to 8 years
        stale_threshold_days=2920, # > 8 years
        description="Factory mechanical specifications remain valid throughout variant production run."
    ),
    "POLICY_HISTORICAL_LISTINGS": FreshnessPolicy(
        policy_id="POLICY_HISTORICAL_LISTINGS",
        name="Historical Empirical Listing Baseline Policy",
        target_domain="MARKET_EMPIRICAL",
        max_current_days=3650,     # Empirical reference window (2018-2024)
        review_due_days=4380,
        stale_threshold_days=5475,
        description="57,480 historical seller asking-price listing observations retain their documented observation context (2018-2024) as a permanent empirical reference."
    ),
    "POLICY_MARKET_OBSERVATIONS": FreshnessPolicy(
        policy_id="POLICY_MARKET_OBSERVATIONS",
        name="Active Market Observation Policy",
        target_domain="ACTIVE_MARKET",
        max_current_days=60,       # 60 days
        review_due_days=180,      # 60-180 days
        stale_threshold_days=180, # > 180 days
        description="Active market asking prices and inventory listings reflect short-term market dynamics."
    ),
    "POLICY_CURRENT_MARKET_OBSERVATIONS": FreshnessPolicy(
        policy_id="POLICY_CURRENT_MARKET_OBSERVATIONS",
        name="Current Live Market Listing Observations Policy",
        target_domain="CURRENT_MARKET",
        max_current_days=30,       # <= 30 days: CURRENT
        review_due_days=90,        # 31 - 90 days: AGING
        stale_threshold_days=180,  # 91 - 180 days: STALE, > 180 days: EXPIRED
        description="Current market asking prices and inventory listings reflect high-velocity real-time secondary market dynamics."
    ),
    "POLICY_OWNERSHIP_AUDIT": FreshnessPolicy(
        policy_id="POLICY_OWNERSHIP_AUDIT",
        name="Reliability & Service Audit Survey Policy",
        target_domain="RELIABILITY_MAINTENANCE",
        max_current_days=1095,     # 3 years
        review_due_days=1825,      # 3 to 5 years
        stale_threshold_days=1825, # > 5 years
        description="Owner defect reports and workshop service cost audits require triennial review."
    ),
    "POLICY_REGULATORY_ARAI": FreshnessPolicy(
        policy_id="POLICY_REGULATORY_ARAI",
        name="ARAI Regulatory Homologation Policy",
        target_domain="REGULATORY",
        max_current_days=2555,     # 7 years
        review_due_days=3650,
        stale_threshold_days=3650,
        description="Official government homologation certificate figures."
    ),
}

DEFAULT_POLICY_ID = "POLICY_OEM_SPECIFICATIONS"

class FreshnessEngine:
    """Deterministic data freshness evaluator."""

    @classmethod
    def get_policy(cls, policy_id: Optional[str]) -> FreshnessPolicy:
        if policy_id and policy_id in POLICIES:
            return POLICIES[policy_id]
        return POLICIES[DEFAULT_POLICY_ID]

    @classmethod
    def evaluate(
        cls,
        observed_date: Optional[Any],
        policy_id: Optional[str] = None,
        is_deprecated: bool = False,
        valid_until: Optional[Any] = None,
        observation_period: Optional[str] = None,
    ) -> FreshnessEvaluation:
        """
        Deterministically evaluates freshness based on policy rules.
        """
        policy = cls.get_policy(policy_id)

        if is_deprecated:
            return FreshnessEvaluation(
                status=FreshnessState.DEPRECATED,
                age_days=None,
                observation_period=observation_period,
                last_observed=str(observed_date) if observed_date else None,
                review_due_date=None,
                policy_id=policy.policy_id,
                notes="Source or claim has been formally marked DEPRECATED by policy."
            )

        if not observed_date:
            return FreshnessEvaluation(
                status=FreshnessState.UNKNOWN,
                age_days=None,
                observation_period=observation_period,
                last_observed=None,
                review_due_date=None,
                policy_id=policy.policy_id,
                notes="No timestamp or observation date available."
            )

        # Convert observed_date to date object
        if isinstance(observed_date, str):
            try:
                # Handle ISO datetime or date string
                dt_str = observed_date.replace("Z", "+00:00")
                if "T" in dt_str or " " in dt_str:
                    ref_date = datetime.fromisoformat(dt_str).date()
                else:
                    ref_date = date.fromisoformat(dt_str)
            except Exception:
                return FreshnessEvaluation(
                    status=FreshnessState.UNKNOWN,
                    age_days=None,
                    observation_period=observation_period,
                    last_observed=str(observed_date),
                    review_due_date=None,
                    policy_id=policy.policy_id,
                    notes=f"Malformed date string '{observed_date}'."
                )
        elif isinstance(observed_date, datetime):
            ref_date = observed_date.date()
        elif isinstance(observed_date, date):
            ref_date = observed_date
        else:
            ref_date = date.today()

        today = date.today()
        age_days = (today - ref_date).days

        # Check explicit validity boundary if provided
        if valid_until:
            if isinstance(valid_until, str):
                try:
                    vu_date = date.fromisoformat(valid_until)
                except Exception:
                    vu_date = None
            elif isinstance(valid_until, (datetime, date)):
                vu_date = valid_until.date() if isinstance(valid_until, datetime) else valid_until
            else:
                vu_date = None

            if vu_date and today > vu_date:
                return FreshnessEvaluation(
                    status=FreshnessState.STALE,
                    age_days=age_days,
                    observation_period=observation_period,
                    last_observed=ref_date.isoformat(),
                    review_due_date=vu_date.isoformat(),
                    policy_id=policy.policy_id,
                    notes=f"Validity expired on {vu_date.isoformat()}."
                )

        # Special handling for permanent historical empirical baselines
        if policy.policy_id == "POLICY_HISTORICAL_LISTINGS":
            return FreshnessEvaluation(
                status=FreshnessState.CURRENT,
                age_days=age_days,
                observation_period=observation_period or "2018-2024",
                last_observed=ref_date.isoformat(),
                review_due_date=None,
                policy_id=policy.policy_id,
                notes="Historical empirical baseline. Observation context preserved; valid reference dataset."
            )

        # Standard age-based evaluation against policy thresholds
        if age_days <= policy.max_current_days:
            status = FreshnessState.CURRENT
            notes = f"Within active currency window ({age_days} days <= {policy.max_current_days} days)."
        elif age_days <= policy.review_due_days:
            status = FreshnessState.REVIEW_DUE
            notes = f"Exceeds currency window ({age_days} days); review due before {policy.stale_threshold_days} days."
        else:
            status = FreshnessState.STALE
            notes = f"Exceeds stale threshold ({age_days} days > {policy.stale_threshold_days} days)."

        return FreshnessEvaluation(
            status=status,
            age_days=age_days,
            observation_period=observation_period,
            last_observed=ref_date.isoformat(),
            review_due_date=None,
            policy_id=policy.policy_id,
            notes=notes
        )

    @classmethod
    def summarize_domain(
        cls,
        domain_name: str,
        policy_id: str,
        items: List[Dict[str, Any]]
    ) -> DomainFreshnessSummary:
        """Computes summary stats for a domain."""
        policy = cls.get_policy(policy_id)
        current = 0
        review_due = 0
        stale = 0
        deprecated = 0
        unknown = 0

        for item in items:
            eval_res = cls.evaluate(
                observed_date=item.get("observed_date") or item.get("retrieved_at") or item.get("published_at"),
                policy_id=policy_id,
                is_deprecated=bool(item.get("is_deprecated", False)),
                valid_until=item.get("valid_until"),
                observation_period=item.get("observation_period"),
            )
            if eval_res.status == FreshnessState.CURRENT:
                current += 1
            elif eval_res.status == FreshnessState.REVIEW_DUE:
                review_due += 1
            elif eval_res.status == FreshnessState.STALE:
                stale += 1
            elif eval_res.status == FreshnessState.DEPRECATED:
                deprecated += 1
            else:
                unknown += 1

        total = len(items)
        if total == 0:
            dominant = FreshnessState.UNKNOWN
        elif current >= (total * 0.5):
            dominant = FreshnessState.CURRENT
        elif (current + review_due) >= (total * 0.5):
            dominant = FreshnessState.REVIEW_DUE
        else:
            dominant = FreshnessState.STALE

        return DomainFreshnessSummary(
            domain=domain_name,
            policy_id=policy_id,
            current_count=current,
            review_due_count=review_due,
            stale_count=stale,
            deprecated_count=deprecated,
            unknown_count=unknown,
            total_items=total,
            dominant_status=dominant,
            evaluation_notes=f"Domain '{domain_name}' evaluated under {policy.name}."
        )
