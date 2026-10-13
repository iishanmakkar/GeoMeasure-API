"""Unit tests for CRS detection, reprojection, and auto-UTM selection."""

from __future__ import annotations

import geopandas as gpd
from pyproj import CRS
from shapely.geometry import Point, Polygon

from app.services.crs import (
    auto_utm_epsg,
    detect_crs,
    detect_swapped_coordinates,
    get_projected_crs,
    reproject_to_wgs84,
)


class TestCRSHandling:
    """Tests for CRS module."""

    def test_detect_crs_present(self) -> None:
        gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0)]}, crs="EPSG:4326")
        crs, assumed = detect_crs(gdf)
        assert crs is not None
        assert crs.to_epsg() == 4326
        assert not assumed

    def test_detect_crs_missing_assumed_wgs84(self) -> None:
        gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0)]}, crs=None)
        crs, assumed = detect_crs(gdf)
        assert crs is not None
        assert crs.to_epsg() == 4326
        assert assumed

    def test_reproject_to_wgs84_from_projected(self) -> None:
        # Create a point in Web Mercator (EPSG:3857) at 0, 0
        gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0)]}, crs="EPSG:3857")
        wgs_gdf = reproject_to_wgs84(gdf)
        assert wgs_gdf.crs.to_epsg() == 4326
        assert wgs_gdf.geometry.iloc[0].x == 0.0
        assert wgs_gdf.geometry.iloc[0].y == 0.0

    def test_reproject_with_source_crs_override(self) -> None:
        # Override an unprojected dataframe
        gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0)]}, crs=None)
        src = CRS.from_epsg(3857)
        wgs_gdf = reproject_to_wgs84(gdf, src_crs=src)
        assert wgs_gdf.crs.to_epsg() == 4326

    def test_auto_utm_epsg_northern(self) -> None:
        # London: ~0° Lon, 51.5° Lat -> UTM Zone 30/31 N
        epsg = auto_utm_epsg(0.0, 51.5)
        assert epsg == 32631

    def test_auto_utm_epsg_southern(self) -> None:
        # Sydney: ~151° Lon, -33.8° Lat -> UTM Zone 56 S
        epsg = auto_utm_epsg(151.2, -33.8)
        assert epsg == 32756

    def test_get_projected_crs_wide_extent(self) -> None:
        # Polygon spanning 10 degrees longitude -> should trigger EASE-Grid 2.0 (EPSG:6933)
        poly = Polygon([(0, 0), (10, 0), (10, 5), (0, 5), (0, 0)])
        crs = get_projected_crs(poly)
        assert crs.to_epsg() == 6933

    def test_get_projected_crs_narrow_extent(self) -> None:
        # Small polygon -> UTM zone
        poly = Polygon([(77.0, 28.0), (77.1, 28.0), (77.1, 28.1), (77.0, 28.1), (77.0, 28.0)])
        crs = get_projected_crs(poly)
        assert crs.to_epsg() == auto_utm_epsg(77.05, 28.05)

    def test_detect_swapped_coordinates_lat_over_90(self) -> None:
        # Latitude exceeds 90° (e.g. lat=120, lon=20)
        gdf = gpd.GeoDataFrame({"geometry": [Point(20, 120)]}, crs="EPSG:4326")
        warnings = detect_swapped_coordinates(gdf)
        assert any("Latitude values exceed 90°" in w for w in warnings)

    def test_detect_swapped_coordinates_lon_over_180(self) -> None:
        # Longitude exceeds 180°
        gdf = gpd.GeoDataFrame({"geometry": [Point(250, 45)]}, crs="EPSG:4326")
        warnings = detect_swapped_coordinates(gdf)
        assert any("Longitude values exceed 180°" in w for w in warnings)

    def test_detect_swapped_coordinates_clean(self) -> None:
        gdf = gpd.GeoDataFrame({"geometry": [Point(77.2, 28.6)]}, crs="EPSG:4326")
        warnings = detect_swapped_coordinates(gdf)
        assert len(warnings) == 0
