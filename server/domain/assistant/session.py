"""
CARspective — Phase 8 Ephemeral Assistant Session Management
Provides lightweight, thread-safe, in-memory session state management with TTL expiration
and strict PII privacy sanitization. No mandatory user accounts or persistent database needed.
"""

import time
import uuid
import threading
from typing import Optional, Dict, Any, List

from server.domain.assistant.models import (
    AssistantContext,
    VehicleContextInput,
    ListingContextInput,
    UserProfileInput,
    ConversationTurn,
)
from server.domain.assistant.policy import AssistantPolicyEngine

# Default session time-to-live: 2 hours (7200 seconds)
DEFAULT_SESSION_TTL_SECONDS = 7200
MAX_CONVERSATION_TURNS = 20


class SessionStore:
    """Thread-safe ephemeral session store for multi-turn assistant conversations."""

    def __init__(self, ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self._sessions: Dict[str, AssistantContext] = {}
        self._lock = threading.Lock()

    def get_or_create(
        self,
        session_id: Optional[str] = None,
        vehicle: Optional[VehicleContextInput] = None,
        listing: Optional[ListingContextInput] = None,
        user_profile: Optional[UserProfileInput] = None,
        compared_vehicles: Optional[List[VehicleContextInput]] = None,
    ) -> AssistantContext:
        """Retrieves existing session or initializes a new one with optional context."""
        now = time.time()
        with self._lock:
            # Clean expired sessions occasionally
            self._purge_expired(now)

            if session_id and session_id in self._sessions:
                ctx = self._sessions[session_id]
                ctx.last_accessed_at = now
                # Update context if new values provided in request
                if vehicle:
                    ctx.current_vehicle = vehicle
                if listing:
                    ctx.listing = listing
                if user_profile:
                    ctx.user_profile = user_profile
                if compared_vehicles:
                    for cv in compared_vehicles:
                        if not any(
                            existing.brand.lower() == cv.brand.lower() and existing.model.lower() == cv.model.lower()
                            for existing in ctx.compared_vehicles
                        ):
                            ctx.compared_vehicles.append(cv)
                return ctx

            # Initialize new session
            new_id = session_id or f"asst-{uuid.uuid4().hex[:12]}"
            ctx = AssistantContext(
                session_id=new_id,
                current_vehicle=vehicle,
                compared_vehicles=compared_vehicles or [],
                listing=listing,
                user_profile=user_profile,
                conversation_history=[],
                created_at=now,
                last_accessed_at=now,
            )
            self._sessions[new_id] = ctx
            return ctx

    def append_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_answer: str,
        intent: Optional[str] = None,
        evidence_refs: Optional[List[str]] = None,
    ) -> None:
        """Appends user and assistant turns with PII redaction."""
        with self._lock:
            if session_id not in self._sessions:
                return

            ctx = self._sessions[session_id]
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            # Redact sensitive data from user message before storing
            sanitized_user = AssistantPolicyEngine.sanitize_privacy(user_message)
            sanitized_assistant = AssistantPolicyEngine.sanitize_privacy(assistant_answer)

            # User turn
            ctx.conversation_history.append(
                ConversationTurn(
                    role="user",
                    content=sanitized_user,
                    timestamp=now_iso,
                    intent=intent,
                )
            )
            # Assistant turn
            ctx.conversation_history.append(
                ConversationTurn(
                    role="assistant",
                    content=sanitized_assistant,
                    timestamp=now_iso,
                    intent=intent,
                    evidence_refs=evidence_refs or [],
                )
            )

            # Bound history size
            if len(ctx.conversation_history) > MAX_CONVERSATION_TURNS:
                ctx.conversation_history = ctx.conversation_history[-MAX_CONVERSATION_TURNS:]

            ctx.last_accessed_at = time.time()

    def _purge_expired(self, current_time: float) -> None:
        """Removes sessions exceeding TTL."""
        expired = [
            sid for sid, ctx in self._sessions.items()
            if (current_time - ctx.last_accessed_at) > self.ttl_seconds
        ]
        for sid in expired:
            del self._sessions[sid]

    def clear(self) -> None:
        """Clears all sessions (useful for tests)."""
        with self._lock:
            self._sessions.clear()
