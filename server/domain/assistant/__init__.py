"""
CARspective — Phase 8 Assistant Domain Package
Exposes core models, services, policies, and provider interfaces for the Grounded Automotive AI Assistant.
"""

from .models import (
    AssistantIntent,
    AssistantEvidenceState,
    SourceDomain,
    VehicleContextInput,
    ListingContextInput,
    UserProfileInput,
    EvidenceItem,
    EvidenceBundle,
    ConversationTurn,
    AssistantContext,
    AssistantRequest,
    AssistantResponse,
)
from .policy import AssistantPolicyEngine, STANDARD_DISCLAIMER
from .intent import IntentClassifier
from .tools import DomainToolDispatcher
from .provider import LLMProvider, GroundedDeterministicProvider, MockFailingLLMProvider
from .session import SessionStore
from .service import AssistantService

__all__ = [
    "AssistantIntent",
    "AssistantEvidenceState",
    "SourceDomain",
    "VehicleContextInput",
    "ListingContextInput",
    "UserProfileInput",
    "EvidenceItem",
    "EvidenceBundle",
    "ConversationTurn",
    "AssistantContext",
    "AssistantRequest",
    "AssistantResponse",
    "AssistantPolicyEngine",
    "STANDARD_DISCLAIMER",
    "IntentClassifier",
    "DomainToolDispatcher",
    "LLMProvider",
    "GroundedDeterministicProvider",
    "MockFailingLLMProvider",
    "SessionStore",
    "AssistantService",
]
