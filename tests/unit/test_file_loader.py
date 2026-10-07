"""Unit tests for file loader — verifies each format loads correctly."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest

from tests.conftest import fixture_path


class TestFileLoaderFormats:
    """Test that each supported format loads correctly."""

    def test_geojson_loads(self) -> None:
        from app.services.file_loader import _load_geojson

        path = fixture_path("sample.geojson")
        gdf, _, warnings = _load_geojson(str(path))
        assert len(gdf) == 2
        assert "Polygon" in gdf.geometry.geom_type.values or "MultiPolygon" in gdf.geometry.geom_type.values

    def test_kml_loads(self) -> None:
        from app.services.file_loader import _load_kml

        path = fixture_path("sample.kml")
        gdf, _, warnings = _load_kml(str(path))
        assert len(gdf) >= 1
        assert gdf.crs is not None

    def test_gpx_loads(self) -> None:
        from app.services.file_loader import _load_gpx

        path = fixture_path("sample.gpx")
        gdf, _, warnings = _load_gpx(str(path))
        assert len(gdf) >= 1  # At least 1 track + 1 waypoint
        # Track should be a LineString
        track_rows = gdf[gdf["type"] == "track"]
        assert len(track_rows) >= 1

    def test_csv_latlon_loads(self) -> None:
        from app.services.file_loader import _load_csv

        path = fixture_path("sample.csv")
        gdf, _, warnings = _load_csv(str(path))
        assert len(gdf) == 5
        assert all(gdf.geometry.geom_type == "Point")

    def test_kmz_loads(self) -> None:
        kmz_path = fixture_path("sample.kmz")
        if not kmz_path.exists():
            pytest.skip("sample.kmz not generated yet — run generate_fixtures.py")
        from app.services.file_loader import _load_kmz

        gdf, _, warnings = _load_kmz(str(kmz_path))
        assert len(gdf) >= 1

    def test_shapefile_zip_loads(self) -> None:
        shp_path = fixture_path("sample_shp.zip")
        if not shp_path.exists():
            pytest.skip("sample_shp.zip not generated yet — run generate_fixtures.py")
        from app.services.file_loader import _load_shapefile_zip

        gdf, _, warnings = _load_shapefile_zip(str(shp_path))
        assert len(gdf) == 2

    def test_geopackage_loads(self) -> None:
        gpkg_path = fixture_path("sample.gpkg")
        if not gpkg_path.exists():
            pytest.skip("sample.gpkg not generated yet — run generate_fixtures.py")
        from app.services.file_loader import _load_geopackage

        gdf, _, warnings = _load_geopackage(str(gpkg_path))
        assert len(gdf) == 1

    def test_geotiff_meta_loads(self) -> None:
        tif_path = fixture_path("sample.tif")
        if not tif_path.exists():
            pytest.skip("sample.tif not generated yet — run generate_fixtures.py")
        from app.services.file_loader import _load_geotiff_meta

        gdf, meta, warnings = _load_geotiff_meta(str(tif_path))
        assert gdf is None
        assert meta.get("is_raster") is True


class TestFormatDetector:
    """Test magic-byte format detection."""

    def test_detect_geojson(self) -> None:
        from app.utils.validators import sniff_format

        header = b'{"type": "FeatureCollection"...'
        assert sniff_format(header, "data.geojson") == "geojson"

    def test_detect_kml(self) -> None:
        from app.utils.validators import sniff_format

        header = b'<?xml version="1.0"?><kml xmlns=...'
        assert sniff_format(header, "data.kml") == "kml"

    def test_detect_tiff(self) -> None:
        from app.utils.validators import sniff_format

        header = b"II*\x00" + b"\x00" * 508
        assert sniff_format(header, "raster.tif") == "geotiff"

    def test_detect_csv_by_extension(self) -> None:
        from app.utils.validators import sniff_format

        header = b"lat,lon,name\n28.6,77.2,Delhi"
        assert sniff_format(header, "points.csv") == "csv"
