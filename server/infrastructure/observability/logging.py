"""
CARspective — Structured JSON Logging & Request Tracing
Provides RFC 3339 / ISO 8601 structured JSON logging, strict request-ID validation,
sanitized exception reporting, and duplicate-handler prevention.
"""

import sys
import re
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Strict request ID policy: alphanumeric, hyphens, and underscores; max 64 chars
REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")

# Attributes to exclude from extra payload in log record dict
RESERVED_LOG_ATTRS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "module", "msecs",
    "message", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName"
}


def validate_or_generate_request_id(provided_id: Optional[str]) -> str:
    """
    Validates a caller-provided request ID against security constraints:
    - Must be a non-empty string
    - Maximum 64 characters
    - Must match regex: ^[a-zA-Z0-9_\\-]{1,64}$
    
    If invalid, malformed, empty, or None, generates a fresh cryptographically
    random UUID4 string to prevent log-injection or buffer overflow vulnerabilities.
    """
    if provided_id and isinstance(provided_id, str):
        cleaned = provided_id.strip()
        if 1 <= len(cleaned) <= 64 and REQUEST_ID_REGEX.match(cleaned):
            return cleaned

    return str(uuid.uuid4())


class StructuredJsonFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects with UTC timestamps,
    standardized log levels, logger names, and structured extra metadata.
    """

    def format(self, record: logging.LogRecord) -> str:
        try:
            # Base log fields
            log_entry: Dict[str, Any] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }

            # Include structured extra attributes if present
            for key, val in record.__dict__.items():
                if key not in RESERVED_LOG_ATTRS and not key.startswith("_"):
                    try:
                        # Test JSON serializability
                        json.dumps(val)
                        log_entry[key] = val
                    except (TypeError, OverflowError):
                        log_entry[key] = str(val)

            # Include sanitized exception metadata if present
            if record.exc_info and record.exc_info[0]:
                exc_type = record.exc_info[0].__name__
                exc_msg = str(record.exc_info[1]) if record.exc_info[1] else ""
                log_entry["error_type"] = exc_type
                # Sanitize exception message to prevent credential/path leakage
                log_entry["error_summary"] = exc_msg.splitlines()[0][:200] if exc_msg else ""

            return json.dumps(log_entry, default=str)
        except Exception:
            return json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": "Safe log formatting fallback",
            })


class SafeStreamHandler(logging.StreamHandler):
    """
    StreamHandler that gracefully suppresses I/O errors when stdout/stderr streams
    are closed during Python process exit or interpreter teardown (atexit).
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if self.stream is None or (hasattr(self.stream, "closed") and self.stream.closed):
                return
            super().emit(record)
        except (ValueError, OSError):
            # Suppress stream closed errors during process shutdown
            pass


def setup_logging(
    logger_name: str = "carspective",
    log_level: int = logging.INFO
) -> logging.Logger:
    """
    Configures structured JSON logging on the specified logger.
    Guarantees idempotency: prevents handler duplication across multiple
    create_app() invocations or test fixtures.
    """
    target_logger = logging.getLogger(logger_name)
    target_logger.setLevel(log_level)

    # Check for an existing StructuredJsonFormatter handler
    has_structured_handler = any(
        isinstance(getattr(h, "formatter", None), StructuredJsonFormatter)
        for h in target_logger.handlers
    )

    if not has_structured_handler:
        # Clear existing non-structured handlers on this specific logger to avoid double logging
        target_logger.handlers.clear()

        handler = SafeStreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        target_logger.addHandler(handler)

    # Prevent propagation to root logger if root would duplicate output
    target_logger.propagate = False

    return target_logger


def get_logger(name: str = "carspective") -> logging.Logger:
    """
    Retrieves or establishes a logger with structured logging configuration.
    """
    if name.startswith("carspective"):
        # Ensure parent carspective logger is configured
        setup_logging("carspective")
    return logging.getLogger(name)
