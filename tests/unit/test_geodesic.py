"""Unit tests for the geodesic measurement engine.

Validates known-value calculations against real-world values.
"""

from __future__ import annotations

import math

import pytest
from shapely.geometry import LineString, Point, Polygon

from app.services.geodesic import (
    bounding_box_dimensions,
    compute_centroid,
    count_vertices,
    geodesic_area,
    geodesic_distance,
    geodesic_length,
    representative_point,
)
from app.services.crs import auto_utm_epsg


class TestGeodesicArea:
    """Test geodesic area calculations."""

    def test_1_degree_box_at_equator(self) -> None:
        """A 1°×1° box at the equator should be approximately 12,308 km².

        Reference: WGS84 ellipsoid at the equator, 1° ≈ 111.32 km,
        so 1°×1° ≈ 111.32² ≈ 12,392 km². Geodesic value ≈ 12,308 km²
        due to convergence of meridians.
        """
        # Equatorial 1x1 degree box
        box = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        area_m2 = geodesic_area(box)
        area_km2 = area_m2 / 1e6
        # Allow ±1% tolerance
        assert 12_000 <= area_km2 <= 12_600, f"Expected ~12,308 km², got {area_km2:.1f} km²"

    def test_polygon_with_hole(self) -> None:
        """Area with hole should be less than without."""
        outer = Polygon([(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)])
        hole = Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)])
        poly_with_hole = Polygon(outer.exterior, [hole.exterior])
        area_full = geodesic_area(outer)
        area_with_hole = geodesic_area(poly_with_hole)
        assert area_with_hole < area_full
        # Hole should be roughly 1/4 of outer
        assert abs(area_full - area_with_hole) / area_full == pytest.approx(0.25, abs=0.05)

    def test_empty_geometry_returns_zero(self) -> None:
        empty = Polygon()
        assert geodesic_area(empty) == 0.0

    def test_point_returns_zero(self) -> None:
        pt = Point(10, 10)
        assert geodesic_area(pt) == 0.0


class TestGeodesicDistance:
    """Test geodesic distance and bearing calculations."""

    def test_delhi_to_mumbai(self) -> None:
        """Delhi to Mumbai should be approximately 1,150 km.

        Delhi: 28.6139°N, 77.2090°E
        Mumbai: 19.0760°N, 72.8777°E
        Reference geodesic distance: ~1,148–1,155 km
        """
        result = geodesic_distance(77.2090, 28.6139, 72.8777, 19.0760)
        dist_km = result["distance_m"] / 1000
        assert 1100 <= dist_km <= 1200, f"Expected ~1150 km, got {dist_km:.1f} km"

    def test_same_point_is_zero(self) -> None:
        result = geodesic_distance(77.0, 28.0, 77.0, 28.0)
        assert result["distance_m"] == pytest.approx(0.0, abs=1.0)

    def test_bearing_north(self) -> None:
        """Moving directly north should give bearing close to 0°."""
        result = geodesic_distance(0.0, 0.0, 0.0, 10.0)
        bearing = result["initial_bearing_deg"]
        assert bearing == pytest.approx(0.0, abs=1.0) or bearing == pytest.approx(360.0, abs=1.0)

    def test_bearing_east(self) -> None:
        """Moving due east at equator should give bearing close to 90°."""
        result = geodesic_distance(0.0, 0.0, 10.0, 0.0)
        assert result["initial_bearing_deg"] == pytest.approx(90.0, abs=1.0)


class TestGeodesicLength:
    """Test geodesic length calculations."""

    def test_equatorial_line_1_degree(self) -> None:
        """1° of longitude at equator ≈ 111.32 km."""
        line = LineString([(0, 0), (1, 0)])
        length_m = geodesic_length(line)
        length_km = length_m / 1000
        assert 110 <= length_km <= 113, f"Expected ~111 km, got {length_km:.2f} km"

    def test_meridian_1_degree(self) -> None:
        """1° of latitude along a meridian ≈ 110–111 km."""
        line = LineString([(0, 0), (0, 1)])
        length_m = geodesic_length(line)
        length_km = length_m / 1000
        assert 110 <= length_km <= 112

    def test_empty_line_is_zero(self) -> None:
        empty = LineString()
        assert geodesic_length(empty) == 0.0


class TestBoundingBox:
    """Test bounding box dimension calculations."""

    def test_bbox_dimensions(self) -> None:
        """Bounding box of a 1°×1° box at equator should be ~111 km wide and tall."""
        dims = bounding_box_dimensions((0.0, 0.0, 1.0, 1.0))
        assert 110_000 <= dims["width_m"] <= 113_000
        assert 110_000 <= dims["height_m"] <= 113_000


class TestUTMZone:
    """Test UTM zone selection."""

    def test_new_delhi_zone(self) -> None:
        # Delhi is in zone 43N → EPSG 32643
        epsg = auto_utm_epsg(77.2, 28.6)
        assert epsg == 32643

    def test_new_york_zone(self) -> None:
        # New York is in zone 18N → EPSG 32618
        epsg = auto_utm_epsg(-74.0, 40.7)
        assert epsg == 32618

    def test_southern_hemisphere(self) -> None:
        # Sydney is in zone 56S → EPSG 32756
        epsg = auto_utm_epsg(151.0, -33.9)
        assert epsg == 32756


class TestVertexCount:
    """Test vertex counting."""

    def test_triangle(self) -> None:
        tri = Polygon([(0, 0), (1, 0), (0.5, 1), (0, 0)])
        assert count_vertices(tri) == 4  # 4 coords (closing vertex included)

    def test_linestring(self) -> None:
        line = LineString([(0, 0), (1, 1), (2, 0)])
        assert count_vertices(line) == 3
