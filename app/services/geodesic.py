"""Core geodesic measurement engine using pyproj.Geod (WGS84 ellipsoid)."""

from __future__ import annotations

import math

import numpy as np
from pyproj import CRS, Geod, Transformer
from shapely.geometry import (
    GeometryCollection,
    LinearRing,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry.base import BaseGeometry

from app.core.logging import get_logger

log = get_logger(__name__)

# WGS84 ellipsoid — used for all geodesic calculations
_GEOD = Geod(ellps="WGS84")


# ---------------------------------------------------------------------------
# Area
# ---------------------------------------------------------------------------


def geodesic_area(geometry: BaseGeometry) -> float:
    """Return the geodesic area in square metres using pyproj.Geod.

    Handles Polygon, MultiPolygon, and GeometryCollections recursively.
    Returns 0 for non-area geometries.
    """
    if geometry is None or geometry.is_empty:
        return 0.0

    if isinstance(geometry, Polygon):
        return _polygon_geodesic_area(geometry)

    if isinstance(geometry, MultiPolygon):
        return sum(_polygon_geodesic_area(p) for p in geometry.geoms)

    if isinstance(geometry, GeometryCollection):
        return sum(geodesic_area(g) for g in geometry.geoms)

    return 0.0


def _polygon_geodesic_area(polygon: Polygon) -> float:
    """Compute geodesic area of a single Polygon (exterior minus holes)."""
    if polygon.is_empty:
        return 0.0

    # Exterior shell
    coords = polygon.exterior.coords
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    area, _ = _GEOD.polygon_area_perimeter(lons, lats)
    total = abs(area)

    # Subtract holes
    for interior in polygon.interiors:
        icoords = interior.coords
        hlons = [c[0] for c in icoords]
        hlats = [c[1] for c in icoords]
        hole_area, _ = _GEOD.polygon_area_perimeter(hlons, hlats)
        total -= abs(hole_area)

    return max(total, 0.0)


def projected_area(polygon: Polygon, epsg: int) -> float:
    """Return area in m² using a local projected CRS (e.g., UTM)."""
    src_crs = CRS.from_epsg(4326)
    dst_crs = CRS.from_epsg(epsg)
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)

    def _project_ring(ring: LinearRing) -> list[tuple[float, float]]:
        coords = ring.coords
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        px, py = transformer.transform(xs, ys)
        return list(zip(px, py))

    proj_exterior = _project_ring(polygon.exterior)
    proj_interiors = [_project_ring(i) for i in polygon.interiors]
    proj_poly = Polygon(proj_exterior, proj_interiors)
    return abs(proj_poly.area)


# ---------------------------------------------------------------------------
# Length / Perimeter
# ---------------------------------------------------------------------------


def geodesic_length(geometry: BaseGeometry) -> float:
    """Return the geodesic length of a line or polygon perimeter in metres."""
    if geometry is None or geometry.is_empty:
        return 0.0

    if isinstance(geometry, (LineString, LinearRing)):
        return _line_geodesic_length(geometry)

    if isinstance(geometry, Polygon):
        return _line_geodesic_length(geometry.exterior)

    if isinstance(geometry, (MultiLineString, MultiPolygon)):
        return sum(geodesic_length(g) for g in geometry.geoms)

    if isinstance(geometry, GeometryCollection):
        return sum(geodesic_length(g) for g in geometry.geoms)

    return 0.0


def _line_geodesic_length(line: LineString | LinearRing) -> float:
    """Compute geodesic length for a single line or ring."""
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0
    total = 0.0
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i][:2]
        lon2, lat2 = coords[i + 1][:2]
        _, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
        total += dist
    return total


# ---------------------------------------------------------------------------
# Distance & Bearing
# ---------------------------------------------------------------------------


def geodesic_distance(
    lon1: float, lat1: float, lon2: float, lat2: float
) -> dict[str, float]:
    """Return geodesic distance and bearings between two WGS84 points.

    Returns a dict with distance_m, initial_bearing_deg, final_bearing_deg.
    """
    az12, az21, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
    return {
        "distance_m": round(dist, 4),
        "initial_bearing_deg": round(az12 % 360, 4),
        "final_bearing_deg": round(az21 % 360, 4),
    }


def point_to_line_distance(point: Point, line: LineString) -> float:
    """Approximate geodesic distance from a point to a LineString in metres.

    Uses projected nearest point on line, then geodesic distance.
    """
    nearest = line.interpolate(line.project(point))
    result = geodesic_distance(point.x, point.y, nearest.x, nearest.y)
    return result["distance_m"]


# ---------------------------------------------------------------------------
# Bounding Box Dimensions
# ---------------------------------------------------------------------------


def bounding_box_dimensions(bounds: tuple[float, float, float, float]) -> dict[str, float]:
    """Return width and height of a WGS84 bounding box in metres."""
    minx, miny, maxx, maxy = bounds
    # Width: along bottom edge
    _, _, width_m = _GEOD.inv(minx, miny, maxx, miny)
    # Height: along left edge
    _, _, height_m = _GEOD.inv(minx, miny, minx, maxy)
    return {
        "minx": minx,
        "miny": miny,
        "maxx": maxx,
        "maxy": maxy,
        "width_m": round(abs(width_m), 4),
        "height_m": round(abs(height_m), 4),
    }


# ---------------------------------------------------------------------------
# Centroid
# ---------------------------------------------------------------------------


def compute_centroid(geometry: BaseGeometry) -> dict[str, float]:
    """Return the centroid coordinates [lon, lat].

    For polygons uses the Shapely centroid (sufficient for small polygons on WGS84).
    """
    c = geometry.centroid
    return {"lon": round(c.x, 8), "lat": round(c.y, 8)}


def representative_point(geometry: BaseGeometry) -> dict[str, float]:
    """Return a point guaranteed to lie inside the geometry."""
    rp = geometry.representative_point()
    return {"lon": round(rp.x, 8), "lat": round(rp.y, 8)}


# ---------------------------------------------------------------------------
# Vertex Count
# ---------------------------------------------------------------------------


def count_vertices(geometry: BaseGeometry) -> int:
    """Count total coordinate vertices across all rings of a geometry."""
    if geometry is None or geometry.is_empty:
        return 0
    if hasattr(geometry, "exterior"):
        # Polygon
        n = len(geometry.exterior.coords)
        for interior in geometry.interiors:
            n += len(interior.coords)
        return n
    if hasattr(geometry, "geoms"):
        return sum(count_vertices(g) for g in geometry.geoms)
    if hasattr(geometry, "coords"):
        return len(list(geometry.coords))
    return 0
