"""
CARspective — Taxonomy & Evidence REST API Tests
Asserts endpoint responses, schema validations, error formats, and resolution routes.
"""

def test_health_endpoints(app_client):
    """Liveness and readiness health checks must return 200 UP and READY."""
    res_live = app_client.get("/health/liveness")
    assert res_live.status_code == 200
    assert res_live.json["status"] == "UP"

    res_ready = app_client.get("/health/readiness")
    assert res_ready.status_code == 200
    assert res_ready.json["status"] == "READY"

def test_list_manufacturers_api(app_client):
    """GET /api/v1/vehicles/manufacturers returns list of active manufacturers."""
    res = app_client.get("/api/v1/vehicles/manufacturers")
    assert res.status_code == 200
    data = res.json
    assert isinstance(data, list)
    assert len(data) >= 7
    slugs = [m["slug"] for m in data]
    assert "maruti-suzuki" in slugs
    assert "hyundai" in slugs

def test_get_manufacturer_detail_api(app_client):
    """GET /api/v1/vehicles/<make_slug> returns manufacturer details with models and aliases."""
    res = app_client.get("/api/v1/vehicles/hyundai")
    assert res.status_code == 200
    data = res.json
    assert data["name"] == "Hyundai"
    assert "Creta" in [m["name"] for m in data["models"]]

def test_get_manufacturer_not_found(app_client):
    """GET /api/v1/vehicles/<unknown_make> returns structured RFC 7807 404 error."""
    res = app_client.get("/api/v1/vehicles/unknown-brand-xyz")
    assert res.status_code == 404
    assert res.json["title"] == "Manufacturer Not Found"

def test_list_models_for_manufacturer(app_client):
    """GET /api/v1/vehicles/<make>/models returns models."""
    res = app_client.get("/api/v1/vehicles/maruti-suzuki/models")
    assert res.status_code == 200
    models = res.json
    assert any(m["name"] == "Swift" for m in models)
    assert any(m["name"] == "Baleno" for m in models)

def test_resolve_vehicle_post_successful_exact_match(app_client):
    """POST /api/v1/vehicles/resolve returns exact match for verified parameters."""
    payload = {
        "brand": "Hyundai",
        "model": "Creta",
        "year": 2022,
        "variant": "SX (O)",
        "fuel_type": "Diesel",
        "transmission_type": "Automatic"
    }
    res = app_client.post("/api/v1/vehicles/resolve", json=payload)
    assert res.status_code == 200
    data = res.json
    assert data["status"] == "EXACT_MATCH"
    assert data["canonical_vehicle_id"] == "hyundai::creta::gen-2-2020::2022::sx-opt::1-5-crdi-6at"
    assert data["confidence_score"] == 1.0

def test_resolve_vehicle_get_query_params(app_client):
    """GET /api/v1/vehicles/resolve works with query parameters."""
    res = app_client.get("/api/v1/vehicles/resolve?brand=Maruti&model=Swift&year=2021")
    assert res.status_code == 200
    data = res.json
    assert data["status"] in ["EXACT_MATCH", "PARTIAL_MATCH"]
    assert "swift" in data["canonical_vehicle_id"]

def test_resolve_vehicle_ambiguous_when_no_year(app_client):
    """POST /api/v1/vehicles/resolve returns AMBIGUOUS_MATCH when year is omitted for multi-generation car."""
    res = app_client.post("/api/v1/vehicles/resolve", json={"brand": "Honda", "model": "City"})
    assert res.status_code == 200
    data = res.json
    assert data["status"] == "AMBIGUOUS_MATCH"
    assert len(data["ambiguous_candidates"]) >= 2

def test_resolve_vehicle_unresolved_for_unknown(app_client):
    """POST /api/v1/vehicles/resolve returns UNRESOLVED for unknown vehicle."""
    res = app_client.post("/api/v1/vehicles/resolve", json={"brand": "Pagani", "model": "Zonda"})
    assert res.status_code == 200
    data = res.json
    assert data["status"] == "UNRESOLVED"
    assert data["canonical_vehicle_id"] is None

def test_provenance_api_endpoint(app_client):
    """GET /api/v1/vehicles/provenance/<canonical_id> returns verified knowledge claims."""
    res = app_client.get("/api/v1/vehicles/provenance/tata::nexon::gen-1-2017")
    assert res.status_code == 200
    data = res.json
    assert data["total_claims"] >= 1
    assert any(c["attribute_category"] == "SAFETY" for c in data["claims"])
