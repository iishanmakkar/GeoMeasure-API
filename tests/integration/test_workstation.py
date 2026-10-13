"""Integration test for the Web GIS Workstation frontend."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_serves_workstation_html(client: TestClient) -> None:
    """GET / should serve the interactive GeoMeasure workstation UI."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "GeoMeasure Workstation" in response.text
    assert "WGS84 GEODESIC" in response.text


def test_static_files_accessible(client: TestClient) -> None:
    """GET /static/index.html should be accessible directly."""
    response = client.get("/static/index.html")
    assert response.status_code == 200
    assert "GeoMeasure Workstation" in response.text


def test_client_config_endpoint(client: TestClient) -> None:
    """GET /api/v1/config should return client config with carto key support."""
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()
    assert "carto_api_key" in data
    assert "api_version" in data
