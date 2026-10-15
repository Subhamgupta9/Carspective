"""
CARspective — Phase 19B Security-First Configuration Hardening and Administrative Authorization Tests

Comprehensive test suite verifying:
1. Mandatory administrative authorization on /api/v1/data/admin/* (401 on missing/invalid, 200/201 on valid)
2. Constant-time API key verification semantics (timing-attack resistant, whitespace tolerant)
3. Public data routes remain accessible without credentials
4. Market administrative ingestion route security
5. Production fail-fast configuration validation (ConfigurationError on insecure/empty keys, wildcards)
6. Host header spoofing / DNS rebinding defense (400 on untrusted host in production)
7. Sanitized readiness diagnostic responses (UNAVAILABLE on failure, zero tracebacks or paths leaked)
8. ProxyFix reverse proxy header integration
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask

from server.config import settings
from server.config.settings import Settings, ConfigurationError
from server.utils.auth import (
    verify_admin_api_key,
    extract_admin_key_from_request,
    require_admin_auth,
)
from server.app import create_app


# ==============================================================================
# 1. CONSTANT-TIME AUTHENTICATION & EXTRACTION UTILITIES
# ==============================================================================

def test_verify_admin_api_key_validity():
    """Constant-time verification correctly validates expected key and rejects invalid inputs."""
    valid_key = settings.ADMIN_API_KEY
    assert verify_admin_api_key(valid_key) is True
    assert verify_admin_api_key(f"  {valid_key}  ") is True
    assert verify_admin_api_key("invalid-token-here") is False
    assert verify_admin_api_key("") is False
    assert verify_admin_api_key(None) is False
    assert verify_admin_api_key(12345) is False


def test_extract_admin_key_header_support():
    """Extracts admin key from both X-Admin-Api-Key and Authorization Bearer headers."""
    req_mock = MagicMock()

    # 1. X-Admin-Api-Key header
    req_mock.headers = {"X-Admin-Api-Key": "my-admin-key-123"}
    assert extract_admin_key_from_request(req_mock) == "my-admin-key-123"

    # 2. Authorization: Bearer header
    req_mock.headers = {"Authorization": "Bearer my-bearer-token-456"}
    assert extract_admin_key_from_request(req_mock) == "my-bearer-token-456"

    # 3. Missing headers
    req_mock.headers = {}
    assert extract_admin_key_from_request(req_mock) is None


# ==============================================================================
# 2. MANDATORY ADMINISTRATIVE AUTHORIZATION ON DATA PIPELINE ROUTES
# ==============================================================================

def test_data_admin_batches_requires_auth(app_client):
    """GET /api/v1/data/admin/batches returns 401 without credentials or with invalid key."""
    # Missing credentials
    res_unauth = app_client.get("/api/v1/data/admin/batches")
    assert res_unauth.status_code == 401
    err = res_unauth.get_json()
    assert err["status"] == 401
    assert err["error_code"] == "UNAUTHORIZED"
    assert "Invalid, missing, or empty" in err["detail"]

    # Invalid credentials
    res_invalid = app_client.get(
        "/api/v1/data/admin/batches",
        headers={"X-Admin-Api-Key": "bad-key-123"}
    )
    assert res_invalid.status_code == 401

    # Valid X-Admin-Api-Key
    res_valid_header = app_client.get(
        "/api/v1/data/admin/batches",
        headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY}
    )
    assert res_valid_header.status_code == 200
    assert isinstance(res_valid_header.get_json(), list)

    # Valid Authorization: Bearer
    res_valid_bearer = app_client.get(
        "/api/v1/data/admin/batches",
        headers={"Authorization": f"Bearer {settings.ADMIN_API_KEY}"}
    )
    assert res_valid_bearer.status_code == 200


def test_data_admin_batch_detail_requires_auth(app_client):
    """GET /api/v1/data/admin/batches/<id> returns 401 without credentials."""
    res_unauth = app_client.get("/api/v1/data/admin/batches/batch-test-999")
    assert res_unauth.status_code == 401

    # With valid key, non-existent batch returns 404
    res_valid = app_client.get(
        "/api/v1/data/admin/batches/batch-test-nonexistent",
        headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY}
    )
    assert res_valid.status_code == 404


def test_data_admin_stage_batch_requires_auth(app_client):
    """POST /api/v1/data/admin/ingest/stage returns 401 and causes zero data mutation without valid credentials."""
    # Count batches before
    batches_res_before = app_client.get(
        "/api/v1/data/admin/batches",
        headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY}
    )
    count_before = len(batches_res_before.get_json())

    payload = {
        "source_id": "src-empirical-listings-57480",
        "records": [{"make": "Hyundai", "model": "Creta", "year": 2020, "price": 1100000}]
    }

    # 1. Missing credentials -> 401
    res_unauth = app_client.post("/api/v1/data/admin/ingest/stage", json=payload)
    assert res_unauth.status_code == 401

    # 2. Invalid credentials -> 401
    res_invalid = app_client.post(
        "/api/v1/data/admin/ingest/stage",
        headers={"X-Admin-Api-Key": "completely-invalid-key"},
        json=payload
    )
    assert res_invalid.status_code == 401

    # Verify zero data mutation occurred
    batches_res_after = app_client.get(
        "/api/v1/data/admin/batches",
        headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY}
    )
    assert len(batches_res_after.get_json()) == count_before

    # 3. With valid key, staging succeeds (201) and increments batch count
    res_valid = app_client.post(
        "/api/v1/data/admin/ingest/stage",
        headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY},
        json=payload
    )
    assert res_valid.status_code == 201
    assert "batch_id" in res_valid.get_json()

    batches_res_final = app_client.get(
        "/api/v1/data/admin/batches",
        headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY}
    )
    assert len(batches_res_final.get_json()) == count_before + 1


def test_data_admin_commit_and_rollback_require_auth(app_client):
    """Commit and rollback routes strictly return 401 without credentials and prevent state transitions."""
    # 1. Stage a batch with valid key first
    stage_payload = {
        "source_id": "src-empirical-listings-57480",
        "records": [{"make": "Tata", "model": "Harrier", "year": 2022, "price": 1600000}]
    }
    stage_res = app_client.post(
        "/api/v1/data/admin/ingest/stage",
        headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY},
        json=stage_payload
    )
    assert stage_res.status_code == 201
    batch_id = stage_res.get_json()["batch_id"]

    # 2. Attempt commit with missing credentials -> 401
    res_commit_unauth = app_client.post(f"/api/v1/data/admin/ingest/commit/{batch_id}")
    assert res_commit_unauth.status_code == 401

    # 3. Attempt commit with invalid credentials -> 401
    res_commit_invalid = app_client.post(
        f"/api/v1/data/admin/ingest/commit/{batch_id}",
        headers={"X-Admin-Api-Key": "invalid-token"}
    )
    assert res_commit_invalid.status_code == 401

    # Verify batch is still STAGED (not COMMITTED)
    batch_check = app_client.get(
        f"/api/v1/data/admin/batches/{batch_id}",
        headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY}
    )
    assert batch_check.status_code == 200
    assert batch_check.get_json()["commit_status"] == "STAGED"

    # 4. Attempt rollback with missing credentials -> 401
    res_rollback_unauth = app_client.post(f"/api/v1/data/admin/ingest/rollback/{batch_id}")
    assert res_rollback_unauth.status_code == 401

    # 5. Attempt rollback with invalid credentials -> 401
    res_rollback_invalid = app_client.post(
        f"/api/v1/data/admin/ingest/rollback/{batch_id}",
        headers={"X-Admin-Api-Key": "invalid-token"}
    )
    assert res_rollback_invalid.status_code == 401

    # Verify batch is STILL STAGED
    batch_check2 = app_client.get(
        f"/api/v1/data/admin/batches/{batch_id}",
        headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY}
    )
    assert batch_check2.get_json()["commit_status"] == "STAGED"

    # 6. Valid rollback succeeds (200)
    res_rollback_valid = app_client.post(
        f"/api/v1/data/admin/ingest/rollback/{batch_id}",
        headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY}
    )
    assert res_rollback_valid.status_code == 200
    assert res_rollback_valid.get_json()["commit_status"] == "ROLLED_BACK"


def test_public_data_routes_remain_accessible_without_auth(app_client):
    """Public data pipeline routes remain completely accessible without any credentials."""
    # 1. Sources registry
    res_sources = app_client.get("/api/v1/data/sources")
    assert res_sources.status_code == 200
    assert len(res_sources.get_json()) > 0

    # 2. Quality scores
    res_quality = app_client.get("/api/v1/data/quality")
    assert res_quality.status_code == 200

    # 3. Freshness metrics
    res_freshness = app_client.get("/api/v1/data/freshness")
    assert res_freshness.status_code == 200


def test_market_admin_ingest_auth_flow(app_client):
    """POST /api/v1/market/admin/ingest adheres to the updated auth verification and rejects unauthenticated mutations."""
    # 1. Unauthenticated -> 401
    res_unauth = app_client.post("/api/v1/market/admin/ingest", json={})
    assert res_unauth.status_code == 401

    # 2. Invalid credentials -> 401
    res_invalid = app_client.post(
        "/api/v1/market/admin/ingest",
        headers={"X-Admin-Api-Key": "bad-key-xyz"},
        json={}
    )
    assert res_invalid.status_code == 401

    # 3. Authenticated -> 201
    res_auth = app_client.post(
        "/api/v1/market/admin/ingest",
        headers={"Authorization": f"Bearer {settings.ADMIN_API_KEY}"},
        json={}
    )
    assert res_auth.status_code == 201


# ==============================================================================
# 3. PRODUCTION CONFIGURATION HARDENING & FAIL-FAST VALIDATION
# ==============================================================================

def test_production_config_validation_rules():
    """validate_production_config strictly enforces all required security invariants."""
    cfg = Settings()

    # In development mode, validation does not fail on default keys
    cfg.IS_PRODUCTION = False
    cfg.validate_production_config()  # Should not raise

    # In production mode:
    cfg.IS_PRODUCTION = True

    # 1. Insecure / empty SECRET_KEY
    cfg.SECRET_KEY = "PRODUCTION_SECRET_KEY_NOT_SET"
    with pytest.raises(ConfigurationError, match="SECRET_KEY is missing"):
        cfg.validate_production_config()

    cfg.SECRET_KEY = "short-key"
    with pytest.raises(ConfigurationError, match="SECRET_KEY is missing"):
        cfg.validate_production_config()

    # Set valid SECRET_KEY
    cfg.SECRET_KEY = "0123456789abcdef0123456789abcdef"

    # 2. Insecure / empty ADMIN_API_KEY
    cfg.ADMIN_API_KEY = "carspective-admin-phase17-key"
    with pytest.raises(ConfigurationError, match="ADMIN_API_KEY is missing"):
        cfg.validate_production_config()

    cfg.ADMIN_API_KEY = "too-short"
    with pytest.raises(ConfigurationError, match="ADMIN_API_KEY is missing"):
        cfg.validate_production_config()

    # Set valid ADMIN_API_KEY
    cfg.ADMIN_API_KEY = "admin-secret-key-32-chars-length!"

    # 3. Empty ALLOWED_HOSTS
    cfg.ALLOWED_HOSTS = []
    with pytest.raises(ConfigurationError, match="ALLOWED_HOSTS must be non-empty"):
        cfg.validate_production_config()

    cfg.ALLOWED_HOSTS = ["carspective.internal", "localhost"]

    # 4. Wildcard in CORS ALLOWED_ORIGINS
    cfg.ALLOWED_ORIGINS = ["*"]
    with pytest.raises(ConfigurationError, match="Wildcard '\*' is strictly forbidden"):
        cfg.validate_production_config()

    cfg.ALLOWED_ORIGINS = ["https://app.carspective.internal"]

    # 5. Negative TRUSTED_PROXIES
    cfg.TRUSTED_PROXIES = -1
    with pytest.raises(ConfigurationError, match="TRUSTED_PROXIES must be a non-negative"):
        cfg.validate_production_config()

    cfg.TRUSTED_PROXIES = 1

    # With all production requirements satisfied, validation succeeds
    cfg.validate_production_config()


def test_app_factory_fail_fast_on_invalid_production_config():
    """create_app fails fast when validate_config=True and production invariants are violated."""
    with patch.object(settings, "IS_PRODUCTION", True), \
         patch.object(settings, "SECRET_KEY", "carspective-dev-secret-key-phase2"):
        with pytest.raises(ConfigurationError):
            create_app(validate_config=True)


# ==============================================================================
# 4. SANITIZED READINESS DIAGNOSTIC PROBE
# ==============================================================================

def test_readiness_probe_sanitizes_database_failure(app_client):
    """When database connectivity fails, /ready reports UNAVAILABLE without leaking paths."""
    from server.infrastructure import database

    with patch.object(database.engine, "connect", side_effect=RuntimeError("sqlite3.OperationalError: unable to open database file at /secret/path/carspective.db")):
        res = app_client.get("/ready")
        assert res.status_code == 503
        data = res.get_json()
        assert data["status"] == "NOT_READY"
        assert data["checks"]["database"] == "UNAVAILABLE"
        # Must NOT leak filesystem path or raw exception
        assert "/secret/path" not in str(data)
        assert "OperationalError" not in str(data)


def test_readiness_probe_sanitizes_taxonomy_failure(app_client):
    """When taxonomy query fails, /health/readiness reports UNAVAILABLE without leaking tracebacks."""
    with patch("server.models.taxonomy.Manufacturer") as mock_mfg:
        mock_mfg.query.side_effect = RuntimeError("Internal Database Corrupt: Table 'manufacturers' missing at /db/var")
        with patch("server.infrastructure.database.ScopedSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.query.side_effect = RuntimeError("Fatal syntax error in SQL dialect parser")
            mock_session_cls.return_value = mock_session

            res = app_client.get("/health/readiness")
            assert res.status_code == 503
            data = res.get_json()
            assert data["status"] == "NOT_READY"
            assert data["checks"]["taxonomy"] == "UNAVAILABLE"
            assert "Fatal syntax error" not in str(data)
            assert "manufacturers missing" not in str(data)


# ==============================================================================
# 5. HOST HEADER VALIDATION IN PRODUCTION
# ==============================================================================

def test_host_header_validation_in_production():
    """In production mode, untrusted Host headers are blocked with 400."""
    with patch.object(settings, "IS_PRODUCTION", True), \
         patch.object(settings, "ALLOWED_HOSTS", ["api.carspective.internal", "localhost"]):
        
        prod_app = create_app({"TESTING": False}, validate_config=False)
        client = prod_app.test_client()

        # 1. Untrusted host -> 400
        res_blocked = client.get("/health/liveness", headers={"Host": "attacker-spoofed-host.com"})
        assert res_blocked.status_code == 400

        # 2. Allowed host -> 200
        res_allowed = client.get("/health/liveness", headers={"Host": "api.carspective.internal"})
        assert res_allowed.status_code == 200


# ==============================================================================
# 6. PROXYFIX REVERSE PROXY SUPPORT
# ==============================================================================

def test_proxyfix_initialization():
    """ProxyFix middleware is applied when TRUSTED_PROXIES > 0."""
    with patch.object(settings, "TRUSTED_PROXIES", 2):
        app = create_app({"TESTING": True}, validate_config=False)
        # Verify app.wsgi_app is wrapped by ProxyFix
        assert app.wsgi_app.__class__.__name__ == "ProxyFix"


def test_forwarded_headers_trust_boundaries():
    """Forwarded headers are strictly ignored when TRUSTED_PROXIES=0 and respected when TRUSTED_PROXIES=1."""
    # Case A: TRUSTED_PROXIES = 0 (Direct exposure / untrusted proxy)
    with patch.object(settings, "TRUSTED_PROXIES", 0):
        app_direct = create_app({"TESTING": False}, validate_config=False)
        client_direct = app_direct.test_client()

        @app_direct.route("/test-echo-remote")
        def echo_remote():
            from flask import request, jsonify
            return jsonify({
                "remote_addr": request.remote_addr,
                "host": request.host
            })

        # Attacker injects fake X-Forwarded-For and X-Forwarded-Host
        res_direct = client_direct.get(
            "/test-echo-remote",
            headers={
                "Host": "localhost",
                "X-Forwarded-For": "198.51.100.1, 203.0.113.195",
                "X-Forwarded-Host": "spoofed-attacker-domain.com"
            }
        )
        data_direct = res_direct.get_json()
        # When TRUSTED_PROXIES=0, request.host is NOT replaced by X-Forwarded-Host
        assert data_direct["host"] == "localhost"

    # Case B: TRUSTED_PROXIES = 1 (Behind 1 trusted reverse proxy)
    with patch.object(settings, "TRUSTED_PROXIES", 1):
        app_proxied = create_app({"TESTING": False}, validate_config=False)
        client_proxied = app_proxied.test_client()

        @app_proxied.route("/test-echo-proxied")
        def echo_proxied():
            from flask import request, jsonify
            return jsonify({
                "remote_addr": request.remote_addr,
                "host": request.host
            })

        # Single trusted proxy appends client IP in X-Forwarded-For and sets X-Forwarded-Host
        res_proxied = client_proxied.get(
            "/test-echo-proxied",
            headers={
                "Host": "internal-backend-cluster",
                "X-Forwarded-Host": "api.carspective.internal",
                "X-Forwarded-For": "203.0.113.195"
            }
        )
        data_proxied = res_proxied.get_json()
        # ProxyFix unpacks the trusted hop
        assert data_proxied["host"] == "api.carspective.internal"
        assert data_proxied["remote_addr"] == "203.0.113.195"

