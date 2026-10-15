"""
CARspective — Assistant Intelligence REST API Routes
Exposes POST /api/v1/assistant for evidence-grounded automotive explanations,
multi-turn conversational continuity, and domain-routed question answering.
"""

import json
import logging
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from server.domain.assistant.models import AssistantRequest
from server.domain.assistant.service import AssistantService

logger = logging.getLogger("carspective.assistant_api")

assistant_bp = Blueprint("assistant", __name__, url_prefix="/api/v1/assistant")

# Singleton assistant service instance (lazy loaded)
_ASSISTANT_SERVICE = None


def get_assistant_service() -> AssistantService:
    global _ASSISTANT_SERVICE
    if _ASSISTANT_SERVICE is None:
        _ASSISTANT_SERVICE = AssistantService()
    return _ASSISTANT_SERVICE


@assistant_bp.route("", methods=["POST"], strict_slashes=False)
def handle_assistant_query():
    """
    POST /api/v1/assistant
    Processes user automotive inquiries, routes to authoritative domain engines,
    gathers structured evidence, and returns an evidence-constrained explanation.
    """
    if not request.is_json:
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Content-Type",
            "status": 415,
            "detail": "Request Content-Type must be 'application/json'."
        }), 415

    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify({
            "type": "about:blank",
            "title": "Malformed Request",
            "status": 400,
            "detail": "Request body must be a valid JSON object."
        }), 400

    try:
        asst_req = AssistantRequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request payload failed validation schema.",
            "errors": json.loads(e.json())
        }), 422

    try:
        service = get_assistant_service()
        response_data = service.handle_message(asst_req)
        return jsonify(response_data.model_dump()), 200
    except Exception as e:
        logger.error(f"Unexpected assistant error: {e}", exc_info=True)
        return jsonify({
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An internal error occurred while processing assistant intelligence."
        }), 500
