"""
CARspective — Security & Path Traversal Tests
Asserts protection against path traversal, malicious input injection, and data leakage.
"""

def test_path_traversal_attempts_in_url(app_client):
    """Malicious path traversal attempts in URL parameters must be safely handled."""
    traversal_payloads = [
        "../../etc/passwd",
        "..%2F..%2Fetc%2Fpasswd",
        "....//....//windows/win.ini",
        "../../../models/smart_used_car_price_model.pkl",
        "%2e%2e%2f%2e%2e%2f"
    ]
    for payload in traversal_payloads:
        res = app_client.get(f"/api/v1/vehicles/{payload}")
        # Must return 404 Not Found, never 200 or internal file leakage
        assert res.status_code in [404, 400]
        # Ensure no internal filesystem paths are exposed in response
        response_text = res.get_data(as_text=True)
        assert "c:\\" not in response_text.lower()
        assert "/users/" not in response_text.lower()

def test_sql_injection_attempts_in_resolution(app_client):
    """SQL injection strings in resolution parameters must not compromise query integrity."""
    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE manufacturers; --",
        "\" OR \"\"=\"",
        "1 UNION SELECT null, null, null"
    ]
    for sql in sql_payloads:
        res = app_client.post("/api/v1/vehicles/resolve", json={
            "brand": sql,
            "model": "Swift"
        })
        # Should return structured 200 with UNRESOLVED status or 422
        assert res.status_code in [200, 422]
        if res.status_code == 200:
            assert res.json["status"] == "UNRESOLVED"

def test_no_filesystem_leakage_in_error_payloads(app_client):
    """Error responses must return clean RFC 7807 JSON without leaking internal server directories."""
    res = app_client.get("/api/v1/vehicles/non-existent-make-slug-testing")
    data = res.json
    assert "detail" in data
    assert "c:\\" not in data["detail"].lower()
    assert ".venv" not in data["detail"].lower()
    assert "smart-used-car-price-prediction" not in data["detail"].lower()

def test_cors_allowed_origin(app_client):
    """CORS headers must be returned for explicitly allowed origins."""
    res = app_client.get("/api/v1", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert "GET" in res.headers.get("Access-Control-Allow-Methods", "")

def test_cors_disallowed_origin(app_client):
    """CORS headers must NOT be returned for unauthorized origins."""
    res = app_client.get("/api/v1", headers={"Origin": "https://malicious-phishing-site.example"})
    assert res.headers.get("Access-Control-Allow-Origin") is None

def test_cors_options_preflight(app_client):
    """Preflight OPTIONS request should return 200 with allowed methods and headers."""
    res = app_client.options("/api/v1/valuation", headers={"Origin": "http://localhost:5173"})
    assert res.status_code == 200
    assert res.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert "POST" in res.headers.get("Access-Control-Allow-Methods", "")

