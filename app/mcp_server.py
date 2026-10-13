"""GeoMeasure Model Context Protocol (MCP) Server.

Exposes high-precision WGS84 geodesic measurements and geospatial analysis tools
directly to AI agents (Claude Desktop, Cursor, Antigravity, Windsurf, LangChain).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
from mcp.server.mcpserver import MCPServer
from shapely import from_wkt, to_wkt

from app.api.v1.meta import SUPPORTED_FORMATS
from app.services.file_loader import load_file
from app.services.geodesic import geodesic_distance
from app.services.measurements import measure_geodataframe
from app.services.raster import measure_raster
from app.services.repair import geometry_validity, repair_geometry
from app.utils.validators import sniff_format

server = MCPServer(
    name="GeoMeasure",
    instructions=(
        "High-precision WGS84 geodesic measurement and geospatial geometry analysis engine. "
        "Provides ellipsoidal distances, areas, perimeters, 3D elevation tracks, and topology repair."
    ),
)


@server.tool(
    name="calculate_distance",
    description=(
        "Calculate survey-grade Great-Circle WGS84 geodesic distance and initial/final "
        "navigation azimuth bearings between two longitude/latitude coordinates."
    ),
)
def calculate_distance(
    from_lon: float,
    from_lat: float,
    to_lon: float,
    to_lat: float,
) -> dict[str, Any]:
    """Calculate geodesic distance and navigation bearings between two WGS84 points."""
    res = geodesic_distance(from_lon, from_lat, to_lon, to_lat)
    dist_m = res["distance_m"]
    return {
        "from": [from_lon, from_lat],
        "to": [to_lon, to_lat],
        "distance_m": dist_m,
        "distance_km": round(dist_m / 1000.0, 4),
        "distance_miles": round(dist_m / 1609.344, 4),
        "distance_nautical_miles": round(dist_m / 1852.0, 4),
        "initial_bearing_deg": res["initial_bearing_deg"],
        "final_bearing_deg": res["final_bearing_deg"],
    }


@server.tool(
    name="measure_wkt",
    description=(
        "Compute exact geodesic or projected measurements for a Well-Known Text (WKT) geometry "
        "(Polygon, MultiPolygon, LineString, Point). Returns area, length, perimeter, centroid, "
        "bounding box, and compactness score."
    ),
)
def measure_wkt(
    wkt: str,
    method: str = "geodesic",
    units: str = "both",
    repair_geometry_if_invalid: bool = True,
) -> dict[str, Any]:
    """Measure an inline WKT geometry string."""
    try:
        geom = from_wkt(wkt)
    except Exception as exc:
        return {"error": f"Invalid WKT geometry: {exc}"}

    gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")
    report = measure_geodataframe(
        gdf=gdf,
        filename="<inline-wkt>",
        file_format="wkt",
        size_bytes=len(wkt.encode()),
        method=method,
        do_repair=repair_geometry_if_invalid,
    )
    return report.model_dump()


@server.tool(
    name="measure_geojson",
    description=(
        "Compute geodesic measurements for a GeoJSON string or dictionary representing "
        "a Feature or FeatureCollection. Returns multi-unit areas, perimeters, centroids, and bounds."
    ),
)
def measure_geojson(
    geojson: str | dict[str, Any],
    method: str = "geodesic",
    repair_geometry_if_invalid: bool = True,
) -> dict[str, Any]:
    """Measure an inline GeoJSON geometry or feature."""
    if isinstance(geojson, str):
        try:
            data = json.loads(geojson)
        except Exception as exc:
            return {"error": f"Invalid JSON string: {exc}"}
    else:
        data = geojson

    try:
        features = data.get("features", [data]) if isinstance(data, dict) else [data]
        gdf = gpd.GeoDataFrame.from_features(features)
        gdf.set_crs("EPSG:4326", inplace=True)
    except Exception as exc:
        return {"error": f"Failed to construct GeoDataFrame from GeoJSON: {exc}"}

    report = measure_geodataframe(
        gdf=gdf,
        filename="<inline-geojson>",
        file_format="geojson",
        size_bytes=len(json.dumps(data).encode()),
        method=method,
        do_repair=repair_geometry_if_invalid,
    )
    return report.model_dump()


@server.tool(
    name="measure_file",
    description=(
        "Load and measure any local geospatial file. Supported formats: GeoJSON (.geojson), "
        "KML (.kml), KMZ (.kmz), GPX (.gpx), Shapefile (.zip), GeoPackage (.gpkg), CSV (.csv), "
        "or GeoTIFF (.tif)."
    ),
)
def measure_file(
    file_path: str,
    method: str = "geodesic",
    repair_geometry_if_invalid: bool = True,
) -> dict[str, Any]:
    """Read a local geospatial file and return a comprehensive measurement report."""
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    size_bytes = path.stat().st_size
    with open(path, "rb") as f:
        header = f.read(512)

    detected_format = sniff_format(header, path.suffix)
    if not detected_format:
        return {"error": f"Unsupported or unrecognizable geospatial file format: {path.name}"}

    try:
        if detected_format == "geotiff":
            import dataclasses

            raster = measure_raster(str(path))
            return dataclasses.asdict(raster)

        gdf, _meta, loader_warnings = load_file(str(path), detected_format)
        report = measure_geodataframe(
            gdf=gdf,
            filename=path.name,
            file_format=detected_format,
            size_bytes=size_bytes,
            method=method,
            do_repair=repair_geometry_if_invalid,
            extra_warnings=loader_warnings,
        )
        return report.model_dump()
    except Exception as exc:
        return {"error": f"Error measuring file '{path.name}': {exc}"}


@server.tool(
    name="repair_geometry",
    description=(
        "Detect validity and repair self-intersecting, broken, or non-simple geometries "
        "using Shapely 2.0 make_valid. Returns repaired WKT and diagnostic explanation."
    ),
)
def repair_geometry_tool(wkt: str) -> dict[str, Any]:
    """Repair an invalid or self-intersecting geometry."""
    try:
        geom = from_wkt(wkt)
    except Exception as exc:
        return {"error": f"Invalid WKT geometry: {exc}"}

    is_valid, reason = geometry_validity(geom)
    if is_valid:
        return {
            "valid": True,
            "was_repaired": False,
            "reason": "Geometry is already valid",
            "wkt": to_wkt(geom),
        }

    repaired, was_repaired = repair_geometry(geom)
    return {
        "valid": repaired.is_valid,
        "was_repaired": was_repaired,
        "original_issue": reason,
        "repaired_wkt": to_wkt(repaired),
    }


@server.tool(
    name="analyze_gpx_track",
    description=(
        "Extract 3D GPS track metrics from a .gpx file, including flat 2D distance, "
        "3D true slope distance, cumulative elevation gain (ascent), loss (descent), "
        "min/max elevation, and average pace."
    ),
)
def analyze_gpx_track(file_path: str) -> dict[str, Any]:
    """Analyze a GPX track file for 3D elevation and distance profile."""
    import gpxpy

    from app.services.tracks import TrackPoint, analyze_track

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        with open(path, encoding="utf-8") as f:
            gpx = gpxpy.parse(f)

        points: list[TrackPoint] = []
        for track in gpx.tracks:
            for segment in track.segments:
                for pt in segment.points:
                    points.append(
                        TrackPoint(
                            lon=pt.longitude,
                            lat=pt.latitude,
                            elevation=pt.elevation,
                            timestamp=pt.time,
                        )
                    )
        if not points:
            for route in gpx.routes:
                for rpt in route.points:
                    points.append(
                        TrackPoint(
                            lon=rpt.longitude,
                            lat=rpt.latitude,
                            elevation=rpt.elevation,
                            timestamp=None,
                        )
                    )

        metrics = analyze_track(points)
        return {
            "file": path.name,
            "point_count": metrics.point_count,
            "has_elevation": metrics.has_elevation,
            "length_2d_m": round(metrics.length_2d_m, 2),
            "length_2d_km": round(metrics.length_2d_m / 1000.0, 3),
            "length_3d_m": round(metrics.length_3d_m, 2),
            "length_3d_km": round(metrics.length_3d_m / 1000.0, 3),
            "total_ascent_m": round(metrics.total_ascent_m, 2),
            "total_descent_m": round(metrics.total_descent_m, 2),
            "min_elevation_m": metrics.min_elevation_m,
            "max_elevation_m": metrics.max_elevation_m,
            "duration_s": metrics.duration_s,
            "avg_speed_kmh": metrics.avg_speed_kmh,
        }
    except Exception as exc:
        return {"error": f"Failed to parse GPX track: {exc}"}


@server.tool(
    name="list_supported_formats",
    description="List all geospatial vector and raster file formats supported by GeoMeasure.",
)
def list_supported_formats() -> list[dict[str, Any]]:
    """Return list of supported file formats and extensions."""
    return SUPPORTED_FORMATS


def main() -> None:
    """Entrypoint to launch the MCP Server over stdio."""
    server.run()


if __name__ == "__main__":
    main()
