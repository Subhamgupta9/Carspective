"""
CARspective — Administrative Authorization & Authentication Utilities
Provides constant-time API key verification and endpoint protection decorators.
Conforms strictly to RFC 7807 error responses and avoids credential leakage.
"""

import hmac
import functools
import logging
from typing import Optional
from flask import request, jsonify, g
from server.config import settings

logger = logging.getLogger("carspective.auth")


def verify_admin_api_key(provided_key: Optional[str]) -> bool:
    """
    Performs constant-time comparison of the provided API key against the configured ADMIN_API_KEY.
    Rejects immediately if either the configured key or provided key is empty/None.
    """
    if not provided_key or not isinstance(provided_key, str):
        return False

    expected_key = getattr(settings, "ADMIN_API_KEY", "")
    if not expected_key or not isinstance(expected_key, str):
        logger.error("ADMIN_API_KEY is not configured or empty; rejecting authorization attempt.")
        return False

    # Constant-time comparison to prevent timing side-channel attacks
    return hmac.compare_digest(provided_key.strip(), expected_key.strip())


def extract_admin_key_from_request(req) -> Optional[str]:
    """
    Extracts the admin API key from either:
    1. 'X-Admin-Api-Key' header
    2. 'Authorization: Bearer <token>' header
    """
    key = req.headers.get("X-Admin-Api-Key")
    if key and key.strip():
        return key.strip()

    auth_header = req.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        parts = auth_header.split(" ", 1)
        if len(parts) == 2 and parts[1].strip():
            return parts[1].strip()

    return None


def require_admin_auth(f):
    """
    Decorator for administrative endpoints requiring valid admin API key credentials.
    Returns standard RFC 7807 401 Unauthorized response on failure.
    Never reflects received or expected key in responses or logs.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = extract_admin_key_from_request(request)
        if not api_key or not verify_admin_api_key(api_key):
            req_id = getattr(g, "request_id", "unknown")
            logger.warning(
                f'{{"event": "admin_auth_failed", "path": "{request.path}", '
                f'"remote_addr": "{request.remote_addr}", "request_id": "{req_id}"}}'
            )
            return jsonify({
                "type": "https://carspective.internal/errors/unauthorized",
                "title": "Unauthorized",
                "status": 401,
                "detail": "Invalid, missing, or empty administrative credentials.",
                "error_code": "UNAUTHORIZED",
                "request_id": req_id
            }), 401
        return f(*args, **kwargs)

    return decorated_function
