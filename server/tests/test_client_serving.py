"""
CARspective — Client Static Serving Integration Tests
Verifies that the Flask production application factory serves the built modern
React client application from client/dist while preserving all API endpoints.
"""

import pytest
from server.app import create_app

@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as c:
        yield c

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
