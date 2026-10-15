"""
CARspective — Phase 12 Discovery & Search Domain
"""

from server.domain.discovery.models import (
    VehicleSearchIntent,
    IntentFieldProvenance,
    IntentField,
    SearchResultType,
    MatchReason,
    CandidateClarification,
    DiscoveryCandidate,
    SearchProvenance,
    DiscoveryFilterParams,
    DiscoverySearchResponse,
    AutocompleteItem,
    AutocompleteResponse,
)
from server.domain.discovery.query_parser import QueryParser
from server.domain.discovery.service import DiscoverySearchService

__all__ = [
    "VehicleSearchIntent",
    "IntentFieldProvenance",
    "IntentField",
    "SearchResultType",
    "MatchReason",
    "CandidateClarification",
    "DiscoveryCandidate",
    "SearchProvenance",
    "DiscoveryFilterParams",
    "DiscoverySearchResponse",
    "AutocompleteItem",
    "AutocompleteResponse",
    "QueryParser",
    "DiscoverySearchService",
]
