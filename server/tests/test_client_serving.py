"""
CARspective — Client Static Serving Integration Tests
Verifies that the Flask production application factory serves the built modern
React client application from client/dist while preserving all API endpoints.
"""

import shutil
from pathlib import Path
import pytest
from server.app import create_app

@pytest.fixture
def client():
    client_dist = Path(__file__).resolve().parent.parent.parent / "client" / "dist"
    index_file = client_dist / "index.html"
    created_dist = False
    created_index = False
    if not client_dist.exists():
        client_dist.mkdir(parents=True, exist_ok=True)
        created_dist = True
    if not index_file.exists():
        index_file.write_text("<!DOCTYPE html><html><body><div id=\"root\"></div>CARspective</body></html>", encoding="utf-8")
        created_index = True

    app = create_app({"TESTING": True})
    with app.test_client() as c:
        yield c

    if created_index and index_file.exists():
        index_file.unlink(missing_ok=True)
    if created_dist and client_dist.exists():
        shutil.rmtree(client_dist, ignore_errors=True)

def test_client_index_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"CARspective" in res.data
    assert b"<div id=\"root\"></div>" in res.data

def test_client_deep_route_serves_spa_html(client):
    res = client.get("/vehicle/honda-city-2021")
    assert res.status_code == 200
    assert b"<div id=\"root\"></div>" in res.data

def test_api_endpoints_not_shadowed(client):
    res = client.get("/api/v1")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["status"] == "OPERATIONAL"
    assert "endpoints" in json_data

def test_health_endpoints_not_shadowed(client):
    res = client.get("/health/liveness")
    assert res.status_code == 200
    assert res.get_json()["status"] == "UP"

def test_unknown_api_route_returns_404_not_html(client):
    res = client.get("/api/v1/nonexistent-route")
    assert res.status_code == 404
