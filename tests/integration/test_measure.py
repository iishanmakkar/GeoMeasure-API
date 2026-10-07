"""Integration tests for POST /measure endpoint — one test per format."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from tests.conftest import fixture_path

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestMeasureEndpoint:
    """Integration tests for synchronous measurement endpoint."""

    def _upload(self, client: TestClient, filename: str, **form) -> dict[str, Any]:
        path = fixture_path(filename)
        with open(path, "rb") as f:
            resp = client.post(
                "/api/v1/measure",
                files={"file": (filename, f, "application/octet-stream")},
                data=form,
            )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        from typing import Any

        return cast(dict[str, Any], resp.json())

    def test_measure_geojson(self, client: TestClient) -> None:
        report = self._upload(client, "sample.geojson")
        assert report["file"]["format"] == "geojson"
        assert report["file"]["feature_count"] == 2
        assert report["summary"]["geometry_types"].get("Polygon", 0) >= 1
        assert len(report["features"]) == 2
        # Polygon feature should have area
        poly_feat = next(f for f in report["features"] if f["geometry_type"] == "Polygon")
        assert poly_feat["area"]["km2"] > 0

    def test_measure_kml(self, client: TestClient) -> None:
        report = self._upload(client, "sample.kml")
        assert report["file"]["format"] == "kml"
        assert report["file"]["feature_count"] >= 1

    def test_measure_gpx(self, client: TestClient) -> None:
        report = self._upload(client, "sample.gpx")
        assert report["file"]["format"] == "gpx"
        assert report["file"]["feature_count"] >= 1
        # At least one LineString from a track
        geom_types = report["summary"]["geometry_types"]
        assert "LineString" in geom_types or "MultiLineString" in geom_types

    def test_measure_csv(self, client: TestClient) -> None:
        report = self._upload(client, "sample.csv")
        assert report["file"]["format"] == "csv"
        assert report["file"]["feature_count"] == 5
        assert report["summary"]["geometry_types"].get("Point", 0) == 5

    def test_measure_kmz(self, client: TestClient) -> None:
        kmz = fixture_path("sample.kmz")
        if not kmz.exists():
            pytest.skip("sample.kmz not generated")
        report = self._upload(client, "sample.kmz")
        assert report["file"]["feature_count"] >= 1

    def test_measure_shapefile(self, client: TestClient) -> None:
        shp = fixture_path("sample_shp.zip")
        if not shp.exists():
            pytest.skip("sample_shp.zip not generated")
        report = self._upload(client, "sample_shp.zip")
        assert report["file"]["feature_count"] == 2
        assert report["summary"]["geometry_types"].get("Polygon", 0) == 2

    def test_measure_geopackage(self, client: TestClient) -> None:
        gpkg = fixture_path("sample.gpkg")
        if not gpkg.exists():
            pytest.skip("sample.gpkg not generated")
        report = self._upload(client, "sample.gpkg")
        assert report["file"]["feature_count"] == 1

    def test_measure_geotiff(self, client: TestClient) -> None:
        tif = fixture_path("sample.tif")
        if not tif.exists():
            pytest.skip("sample.tif not generated")
        report = self._upload(client, "sample.tif")
        assert report["file"]["format"] == "geotiff"
        assert report["features"][0]["extras"]["width_px"] == 10


class TestMeasureGeometryEndpoint:
    """Integration tests for POST /measure/geometry."""

    def test_wkt_polygon(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/measure/geometry",
            json={"wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"},
        )
        assert resp.status_code == 200
        report = resp.json()
        assert report["features"][0]["geometry_type"] == "Polygon"
        assert report["features"][0]["area"]["km2"] > 0

    def test_wkt_linestring(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/measure/geometry",
            json={"wkt": "LINESTRING(0 0, 1 1, 2 0)"},
        )
        assert resp.status_code == 200
        report = resp.json()
        assert report["features"][0]["length"]["km"] > 0

    def test_geojson_feature(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/measure/geometry",
            json={
                "geojson": {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [77.2, 28.6]},
                    "properties": {"name": "Delhi"},
                }
            },
        )
        assert resp.status_code == 200

    def test_invalid_wkt_returns_400(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/measure/geometry",
            json={"wkt": "NOT VALID WKT"},
        )
        assert resp.status_code == 400


class TestDistanceEndpoint:
    """Tests for POST /distance."""

    def test_delhi_to_mumbai(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/distance",
            json={"from": [77.2090, 28.6139], "to": [72.8777, 19.0760]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 1100 <= data["distance_km"] <= 1200

    def test_same_point_zero_distance(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/distance",
            json={"from": [0.0, 0.0], "to": [0.0, 0.0]},
        )
        assert resp.status_code == 200
        assert resp.json()["distance_m"] == pytest.approx(0.0, abs=1.0)


class TestMetaEndpoints:
    """Tests for /health, /version, /formats."""

    def test_health(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_version(self, client: TestClient) -> None:
        resp = client.get("/version")
        assert resp.status_code == 200
        assert "version" in resp.json()

    def test_formats(self, client: TestClient) -> None:
        resp = client.get("/api/v1/formats")
        assert resp.status_code == 200
        formats = resp.json()["formats"]
        format_names = [f["name"] for f in formats]
        assert "GeoJSON" in format_names
        assert "GPX" in format_names
