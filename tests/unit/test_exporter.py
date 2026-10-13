"""Unit tests for exporter module (CSV & GeoJSON serialisation)."""

from __future__ import annotations

import csv
import io

from app.models.schemas import (
    AreaValues,
    BoundingBox,
    Centroid,
    FeatureMeasurement,
    FileMeta,
    MeasurementReport,
    PolygonExtras,
    Summary,
)
from app.services.exporter import to_csv, to_geojson


def _mock_report() -> MeasurementReport:
    """Construct a sample MeasurementReport for testing."""
    file_meta = FileMeta(
        name="test.geojson",
        format="geojson",
        size_bytes=1024,
        crs="EPSG:4326",
        crs_assumed=False,
        feature_count=1,
        processing_ms=12.5,
    )
    feat = FeatureMeasurement(
        index=0,
        id="feat-1",
        geometry_type="Polygon",
        valid=True,
        validity_reason="Valid Geometry",
        vertex_count=5,
        area=AreaValues(m2=1000000.0, km2=1.0, ha=100.0, acres=247.1, ft2=10763910.0, mi2=0.386),
        perimeter=None,
        length=None,
        centroid=Centroid(lon=77.5, lat=28.5),
        bbox=BoundingBox(
            minx=77.0, miny=28.0, maxx=78.0, maxy=29.0, width_m=98000.0, height_m=111000.0
        ),
        extras=PolygonExtras(
            num_holes=0,
            hole_area_m2=0.0,
            convex_hull_area_m2=1000000.0,
            compactness=0.88,
            min_rotated_rect_width_m=1000.0,
            min_rotated_rect_height_m=1000.0,
        ),
        properties={"zone": "Downtown", "population": 50000},
    )
    summary = Summary(
        total_area=feat.area,
        total_length=None,
        bbox=feat.bbox,
        centroid=feat.centroid,
        geometry_types={"Polygon": 1},
        invalid_features=0,
    )
    return MeasurementReport(
        file=file_meta,
        summary=summary,
        features=[feat],
        warnings=[],
        method="geodesic",
    )


class TestExporter:
    """Tests for report exporters."""

    def test_to_csv_output(self) -> None:
        report = _mock_report()
        csv_str = to_csv(report)
        assert len(csv_str) > 0

        # Validate CSV can be parsed
        reader = csv.DictReader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 1
        row = rows[0]
        assert row["geometry_type"] == "Polygon"
        assert float(row["area_km2"]) == 1.0
        assert float(row["centroid_lon"]) == 77.5
        assert float(row["centroid_lat"]) == 28.5
        assert row["prop_zone"] == "Downtown"

    def test_to_csv_empty_features(self) -> None:
        report = _mock_report()
        report.features = []
        csv_str = to_csv(report)
        assert csv_str == ""

    def test_to_geojson_output(self) -> None:
        report = _mock_report()
        geojson_data = to_geojson(report)

        assert geojson_data["type"] == "FeatureCollection"
        assert len(geojson_data["features"]) == 1

        f = geojson_data["features"][0]
        assert f["type"] == "Feature"
        assert f["id"] == "feat-1"
        assert f["geometry"]["type"] == "Point"
        assert f["geometry"]["coordinates"] == [77.5, 28.5]
        assert f["properties"]["area_km2"] == 1.0
        assert f["properties"]["prop_zone"] == "Downtown"
        assert geojson_data["metadata"]["method"] == "geodesic"
