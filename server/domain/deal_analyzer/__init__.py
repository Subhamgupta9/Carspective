"""
CARspective — Deal Analyzer Domain Package
"""

from .models import (
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
from .service import DealAnalyzerService

__all__ = [
    "DealAnalysisRequest",
    "DealAnalysisResponse",
    "DealQualityEnum",
    "RangePositionCategory",
    "NegotiationStrength",
    "RiskCategory",
    "RiskSeverity",
    "EvidenceState",
    "PriceDeviation",
    "FairRangePosition",
    "AnomalyStatus",
    "NegotiationGuidance",
    "RiskSignal",
    "ValuationContext",
    "DealAnalyzerService"
]
