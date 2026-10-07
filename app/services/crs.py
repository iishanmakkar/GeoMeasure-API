"""CRS detection, reprojection, and UTM zone selection."""

from __future__ import annotations

import geopandas as gpd
from pyproj import CRS, Transformer
from shapely.geometry import MultiPolygon, Polygon

from app.core.logging import get_logger

log = get_logger(__name__)

WGS84 = CRS.from_epsg(4326)


def detect_crs(gdf: gpd.GeoDataFrame) -> tuple[CRS | None, bool]:
    """Return (detected_crs, was_assumed).

    If no CRS is found, returns (WGS84, True) indicating we assumed EPSG:4326.
    """
    if gdf.crs is not None:
        return gdf.crs, False
    log.warning("no_crs_detected", action="assuming EPSG:4326")
    return WGS84, True


def reproject_to_wgs84(gdf: gpd.GeoDataFrame, src_crs: CRS | None = None) -> gpd.GeoDataFrame:
    """Reproject *gdf* to EPSG:4326.

    If *src_crs* is provided it overrides the GeoDataFrame's own CRS.
    """
    if src_crs is not None:
        gdf = gdf.set_crs(src_crs, allow_override=True)
    if gdf.crs is None:
        gdf = gdf.set_crs(WGS84)
    if gdf.crs != WGS84:
        gdf = gdf.to_crs(WGS84)
    return gdf


def auto_utm_epsg(lon: float, lat: float) -> int:
    """Return the EPSG code of the best UTM zone for the given WGS84 coordinates."""
    zone = int((lon + 180) / 6) + 1
    if lat >= 0:
        return 32600 + zone  # Northern hemisphere
    return 32700 + zone  # Southern hemisphere


def get_projected_crs(geometry: Polygon | MultiPolygon) -> CRS:
    """Select the best projected CRS for measurement (UTM or equal-area fallback)."""
    centroid = geometry.centroid
    lon, lat = centroid.x, centroid.y

    # For geometries wider than 6 degrees, use World Cylindrical Equal Area
    bounds = geometry.bounds
    width = bounds[2] - bounds[0]
    if width > 6.0:
        return CRS.from_epsg(6933)  # NSIDC EASE-Grid 2.0 (cylindrical equal-area)

    epsg = auto_utm_epsg(lon, lat)
    return CRS.from_epsg(epsg)


def detect_swapped_coordinates(gdf: gpd.GeoDataFrame) -> list[str]:
    """Return warnings if lon/lat values look swapped."""
    warnings: list[str] = []
    if gdf.crs and gdf.crs.axis_info:
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        # In EPSG:4326, x=longitude [-180,180], y=latitude [-90,90]
        if bounds[1] > 90 or bounds[3] > 90:
            warnings.append(
                "Latitude values exceed 90° — coordinates may be swapped. "
                "Use source_crs to override."
            )
        if bounds[0] > 180 or bounds[2] > 180:
            warnings.append(
                "Longitude values exceed 180° — the file may be in a projected CRS. "
                "Use source_crs to specify the correct CRS."
            )
    return warnings
