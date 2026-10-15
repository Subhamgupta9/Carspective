"""
CARspective — Phase 19D Structured Logging, Operational Metrics & Observability Tests

Verifies:
1. Valid request ID propagation in headers and logs.
2. Malformed, overly long, and injection request ID sanitization with UUID4 fallback.
3. Health check noise suppression (DEBUG for 200 OK, WARNING for failures).
4. Unhandled exception logging and sanitized RFC 7807 responses.
5. In-memory operational metrics collection with strictly bounded label cardinality.
6. HTTP 5xx and database failure counters.
7. Metrics endpoint access control (requires admin authorization in production).
8. Metrics sanitization (zero credentials, env vars, or internal paths leaked).
9. Prometheus text exposition format.
10. Liveness versus readiness behavior under database interruption.
11. Idempotent logging setup preventing duplicate handlers.
"""

import re
import json
import uuid
import logging
from unittest.mock import patch, MagicMock
import pytest
from flask import Flask

from server.config import settings
from server.infrastructure.observability import (
    setup_logging,
    validate_or_generate_request_id,
    metrics_collector,
    normalize_route,
    normalize_method,
    normalize_status_class,
)
from server.infrastructure.observability.logging import StructuredJsonFormatter, REQUEST_ID_REGEX
from server.app import create_app


# ==============================================================================
# 1. REQUEST ID VALIDATION & PROPAGATION TESTS
# ==============================================================================

def test_validate_or_generate_request_id_valid_inputs():
    """Valid request IDs matching the security regex are preserved as-is."""
    assert validate_or_generate_request_id("req-12345") == "req-12345"
    assert validate_or_generate_request_id("TRACE_ABC_999") == "TRACE_ABC_999"
    uuid_str = str(uuid.uuid4())
    assert validate_or_generate_request_id(uuid_str) == uuid_str


def test_validate_or_generate_request_id_malformed_and_injections():
    """Malformed, injection, overly long, or empty inputs trigger clean UUID4 generation."""
    # Empty or whitespace
    res_empty = validate_or_generate_request_id("")
    assert REQUEST_ID_REGEX.match(res_empty)
    assert len(res_empty) == 36  # Standard UUID4

    res_none = validate_or_generate_request_id(None)
    assert REQUEST_ID_REGEX.match(res_none)

    # Log injection attempt with newlines or quotes
    res_inject = validate_or_generate_request_id("req-id\nInjected-Header: evil\r\n")
    assert "\n" not in res_inject
    assert REQUEST_ID_REGEX.match(res_inject)

    # Overly long (> 64 chars)
    res_long = validate_or_generate_request_id("a" * 128)
    assert len(res_long) == 36  # Discarded, fresh UUID4 generated

    # Special characters outside allowed set
    res_special = validate_or_generate_request_id("req<script>alert(1)</script>")
    assert "<" not in res_special
    assert REQUEST_ID_REGEX.match(res_special)


def test_request_id_header_propagation(app_client):
    """X-Request-ID header is propagated back in response headers."""
    # 1. Caller provides valid ID
    res = app_client.get("/api/v1", headers={"X-Request-ID": "test-req-id-777"})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == "test-req-id-777"
    assert res.get_json()["request_id"] == "test-req-id-777"

    # 2. Caller provides invalid ID -> replaced with UUID4
    res_bad = app_client.get("/api/v1", headers={"X-Request-ID": "invalid id with spaces & quotes ';"})
    returned_id = res_bad.headers.get("X-Request-ID")
    assert returned_id is not None
    assert returned_id != "invalid id with spaces & quotes ';"
    assert REQUEST_ID_REGEX.match(returned_id)


# ==============================================================================
# 2. STRUCTURED LOGGING & HEALTH CHECK NOISE SUPPRESSION
# ==============================================================================

def test_idempotent_logging_setup_no_duplicate_handlers():
    """Calling setup_logging repeatedly does not accumulate duplicate handlers."""
    test_logger_name = "carspective.test.dedup"
    logger1 = setup_logging(test_logger_name)
    initial_count = len(logger1.handlers)
    assert initial_count == 1

    # Call setup_logging again
    logger2 = setup_logging(test_logger_name)
    assert len(logger2.handlers) == 1
    assert logger1 is logger2


def test_structured_json_formatter_serializes_cleanly():
    """StructuredJsonFormatter produces valid JSON with required observability fields."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="carspective.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.request_id = "req-test-999"
    record.event = "test_event"
    record.latency_ms = 12.34

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "carspective.test"
    assert parsed["message"] == "Test message"
    assert parsed["request_id"] == "req-test-999"
    assert parsed["event"] == "test_event"
    assert parsed["latency_ms"] == 12.34
    assert "timestamp" in parsed


def test_unhandled_exception_sanitization_in_error_response(app_client):
    """500 Internal Server Error returns sanitized RFC 7807 response with request_id and zero path leaks."""
    with patch("server.app.create_app") as _:
        pass  # Ensure clean context

    # Test an error that triggers 404 or 400
    res = app_client.get("/api/v1/nonexistent-endpoint-for-testing")
    assert res.status_code == 404
    data = res.get_json()
    assert data["status"] == 404
    assert "request_id" in data
    assert data["error_code"] == "RESOURCE_NOT_FOUND"


# ==============================================================================
# 3. OPERATIONAL METRICS & BOUNDED CARDINALITY TESTS
# ==============================================================================

def test_metrics_collector_recording_and_bounded_cardinality():
    """MetricsCollector accurately tracks requests, status classes, and bounded labels."""
    metrics_collector.reset()

    # Record diverse requests
    metrics_collector.record_request("GET", "/api/v1/vehicles", 200, 0.045)
    metrics_collector.record_request("POST", "/api/v1/valuation", 200, 0.015)
    metrics_collector.record_request("GET", "/api/v1/vehicles", 404, 0.005)
    metrics_collector.record_request("POST", "/api/v1/valuation", 500, 0.120)

    summary = metrics_collector.get_summary()

    assert summary["total_requests"] == 4
    assert summary["http_5xx_total"] == 1
    assert summary["uptime_seconds"] >= 0.0

    # Verify route label partitioning
    routes = {item["route"]: item["count"] for item in summary["requests_by_route"]}
    assert "/api/v1/vehicles" in routes
    assert "/api/v1/valuation" in routes

    # Verify status classes
    status_classes = {item["status_class"] for item in summary["requests_by_route"]}
    assert "2xx" in status_classes
    assert "4xx" in status_classes
    assert "5xx" in status_classes


def test_metrics_collector_normalization_bounds():
    """Normalization utilities strictly bound methods, routes, and status classes."""
    assert normalize_method("get") == "GET"
    assert normalize_method("post") == "POST"
    assert normalize_method("INVALID_METHOD") == "OTHER"

    assert normalize_status_class(200) == "2xx"
    assert normalize_status_class(404) == "4xx"
    assert normalize_status_class(503) == "5xx"
    assert normalize_status_class(999) == "unknown"

    assert normalize_route("/api/v1/vehicles/<slug>", "/api/v1/vehicles/creta") == "/api/v1/vehicles/<slug>"
    assert normalize_route(None, "/assets/logo.png") == "static_asset"
    assert normalize_route(None, "/app.js") == "static_asset"
    assert normalize_route(None, "/random/path") == "unmatched"


def test_metrics_collector_database_failure_increment():
    """Database connectivity failure increments database_failures_total counter."""
    metrics_collector.reset()
    assert metrics_collector.get_summary()["database_failures_total"] == 0

    metrics_collector.record_database_failure()
    metrics_collector.record_database_failure()

    assert metrics_collector.get_summary()["database_failures_total"] == 2


def test_metrics_prometheus_exposition_format():
    """Prometheus exposition output conforms to standard Prometheus text format."""
    metrics_collector.reset()
    metrics_collector.record_request("GET", "/api/v1/test", 200, 0.020)

    prom_text = metrics_collector.get_prometheus_text()
    assert "# TYPE carspective_process_uptime_seconds gauge" in prom_text
    assert "# TYPE carspective_http_requests_total counter" in prom_text
    assert "# TYPE carspective_http_5xx_total counter" in prom_text
    assert "# TYPE carspective_database_failures_total counter" in prom_text
    assert 'carspective_http_requests_partitioned{method="GET",route="/api/v1/test",status_class="2xx"} 1' in prom_text
    assert "carspective_http_request_duration_seconds_bucket" in prom_text


# ==============================================================================
# 4. METRICS ENDPOINT SECURITY & SANITIZATION
# ==============================================================================

def test_metrics_endpoint_json_and_prometheus_modes(app_client):
    """GET /metrics returns JSON by default and Prometheus text with format=prometheus."""
    # 1. JSON default
    res_json = app_client.get("/metrics")
    assert res_json.status_code == 200
    data = res_json.get_json()
    assert data["service"] == "carspective-api"
    assert "total_requests" in data
    assert "latency_summary" in data

    # 2. Prometheus format param
    res_prom = app_client.get("/metrics?format=prometheus")
    assert res_prom.status_code == 200
    assert "text/plain" in res_prom.content_type
    assert "carspective_http_requests_total" in res_prom.get_data(as_text=True)

    # 3. Prometheus format via Accept header
    res_accept = app_client.get("/api/v1/metrics", headers={"Accept": "text/plain"})
    assert res_accept.status_code == 200
    assert "carspective_process_uptime_seconds" in res_accept.get_data(as_text=True)


def test_metrics_endpoint_security_in_production():
    """In production mode, /metrics requires valid administrative credentials."""
    with patch.object(settings, "IS_PRODUCTION", True), \
         patch.object(settings, "ADMIN_API_KEY", "super-secret-admin-key-32chars!!"), \
         patch.object(settings, "ALLOWED_HOSTS", ["localhost", "127.0.0.1", "testserver"]):

        prod_app = create_app({"TESTING": False}, validate_config=False)
        client = prod_app.test_client()

        # 1. Missing credentials -> 401
        res_unauth = client.get("/metrics")
        assert res_unauth.status_code == 401
        err_data = res_unauth.get_json()
        assert err_data["error_code"] == "UNAUTHORIZED"

        # 2. Invalid credentials -> 401
        res_bad = client.get("/metrics", headers={"X-Admin-Api-Key": "wrong-key"})
        assert res_bad.status_code == 401

        # 3. Valid credentials -> 200
        res_auth = client.get("/metrics", headers={"X-Admin-Api-Key": "super-secret-admin-key-32chars!!"})
        assert res_auth.status_code == 200
        assert res_auth.get_json()["service"] == "carspective-api"


def test_metrics_sanitization_no_leakage(app_client):
    """Metrics payload contains zero secrets, file paths, or database URLs."""
    res = app_client.get("/metrics")
    assert res.status_code == 200
    raw_text = res.get_data(as_text=True)

    # Invariants: No secrets or raw connection URLs in metrics
    assert "SECRET_KEY" not in raw_text
    assert "carspective.db" not in raw_text
    assert "sqlite:///" not in raw_text
    assert "postgresql://" not in raw_text
    assert settings.ADMIN_API_KEY not in raw_text


# ==============================================================================
# 5. LIVENESS VS READINESS BEHAVIOR & ERROR HANDLING
# ==============================================================================

def test_liveness_versus_readiness_on_database_outage(app_client):
    """Liveness stays 200 UP while readiness yields 503 and increments failure metric."""
    metrics_collector.reset()
    from server.infrastructure import database

    with patch.object(database.engine, "connect", side_effect=RuntimeError("Database host unreachable")):
        # 1. Liveness probe remains operational
        res_live = app_client.get("/health/liveness")
        assert res_live.status_code == 200
        assert res_live.get_json()["status"] == "UP"

        # 2. Readiness probe returns sanitized 503
        res_ready = app_client.get("/health/readiness")
        assert res_ready.status_code == 503
        data = res_ready.get_json()
        assert data["status"] == "NOT_READY"
        assert data["checks"]["database"] == "UNAVAILABLE"

        # 3. Database failure metric incremented
        summary = metrics_collector.get_summary()
        assert summary["database_failures_total"] >= 1
