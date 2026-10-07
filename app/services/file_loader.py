"""File format detectors and loaders for all supported geospatial formats."""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import geopandas as gpd
import gpxpy
import pandas as pd
from shapely.geometry import LineString, Point

from app.core.logging import get_logger
from app.utils.validators import validate_archive_safety

log = get_logger(__name__)

# Column name aliases for CSV lat/lon auto-detection
_LAT_ALIASES = frozenset(["lat", "latitude", "y", "northing"])
_LON_ALIASES = frozenset(["lon", "lng", "longitude", "x", "easting"])
_WKT_ALIASES = frozenset(["wkt", "geometry", "geom", "shape", "the_geom"])


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def load_file(
    path: str,
    detected_format: str,
    source_crs: str | None = None,
) -> tuple[gpd.GeoDataFrame | None, dict[str, Any], list[str]]:
    """Load a geospatial file and return (gdf, raster_meta, warnings).

    For raster formats (GeoTIFF), gdf is None and raster_meta is populated.
    For vector formats, raster_meta is empty.
    """
    loaders = {
        "geojson": _load_geojson,
        "kml": _load_kml,
        "kmz": _load_kmz,
        "gpx": _load_gpx,
        "zip": _load_shapefile_zip,
        "gpkg": _load_geopackage,
        "csv": _load_csv,
        "geotiff": _load_geotiff_meta,
    }

    loader = loaders.get(detected_format)
    if loader is None:
        raise ValueError(f"Unsupported format: {detected_format}")

    return loader(path)


# ---------------------------------------------------------------------------
# Individual loaders
# ---------------------------------------------------------------------------


def _load_geojson(path: str) -> tuple[gpd.GeoDataFrame, dict, list[str]]:
    """Load a GeoJSON or JSON file."""
    warnings: list[str] = []
    gdf = gpd.read_file(path, engine="pyogrio")
    if gdf.crs is None:
        warnings.append("GeoJSON has no CRS — assuming EPSG:4326")
    return gdf, {}, warnings


def _load_kml(path: str) -> tuple[gpd.GeoDataFrame, dict, list[str]]:
    """Load a KML file using lxml + defusedxml for safe XML parsing."""
    import defusedxml.ElementTree as ET  # noqa: N817

    warnings: list[str] = []

    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception as exc:
        raise ValueError(f"Failed to parse KML: {exc}") from exc

    # Strip namespaces for easier XPath
    _strip_ns(root)

    features = _extract_kml_features(root, warnings)
    if not features:
        warnings.append("KML file contains no Placemark features")

    gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
    if gdf.empty or "geometry" not in gdf.columns:
        gdf = gpd.GeoDataFrame(columns=["geometry", "name", "description"], crs="EPSG:4326")
    return gdf, {}, warnings


def _strip_ns(element: Any) -> None:
    """Remove XML namespace prefixes from all elements in-place."""
    if "}" in element.tag:
        element.tag = element.tag.split("}")[1]
    for child in element:
        _strip_ns(child)


def _extract_kml_features(root: Any, warnings: list[str]) -> list[dict[str, Any]]:
    """Walk KML tree and extract Placemark geometries."""
    features: list[dict[str, Any]] = []

    for placemark in root.iter("Placemark"):
        name_el = placemark.find("name")
        desc_el = placemark.find("description")
        name = name_el.text.strip() if name_el is not None and name_el.text else ""
        description = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

        geom = _parse_kml_geometry(placemark, warnings)
        if geom is not None:
            features.append({"geometry": geom, "name": name, "description": description})

    return features


def _parse_kml_geometry(placemark: Any, warnings: list[str]) -> Any | None:
    """Parse geometry from a KML Placemark element."""
    from shapely.geometry import Polygon

    # Point
    pt_el = placemark.find(".//Point/coordinates")
    if pt_el is not None and pt_el.text:
        coords = _parse_kml_coords(pt_el.text)
        if coords:
            c = coords[0]
            return Point(c[0], c[1]) if len(c) == 2 else Point(c[0], c[1], c[2])

    # LineString
    ls_el = placemark.find(".//LineString/coordinates")
    if ls_el is not None and ls_el.text:
        coords = _parse_kml_coords(ls_el.text)
        if len(coords) >= 2:
            return LineString(coords)

    # Polygon
    outer_el = placemark.find(".//Polygon/outerBoundaryIs/LinearRing/coordinates")
    if outer_el is not None and outer_el.text:
        outer = _parse_kml_coords(outer_el.text)
        holes = []
        for inner_el in placemark.findall(".//Polygon/innerBoundaryIs/LinearRing/coordinates"):
            if inner_el.text:
                holes.append(_parse_kml_coords(inner_el.text))
        if len(outer) >= 3:
            return Polygon(outer, holes)

    # MultiGeometry
    mg_el = placemark.find("MultiGeometry")
    if mg_el is not None:
        geoms = []
        for child in mg_el:
            type(
                "_",
                (),
                {"findall": mg_el.findall, "find": mg_el.find, "__iter__": lambda s: iter(mg_el)},
            )()
            g = _parse_kml_geometry(child, warnings)
            if g:
                geoms.append(g)
        if geoms:
            from shapely.ops import unary_union

            return unary_union(geoms)

    warnings.append("Placemark has no recognised geometry element")
    return None


def _parse_kml_coords(text: str) -> list[tuple[float, ...]]:
    """Parse KML coordinate string into a list of (lon, lat) or (lon, lat, alt) tuples."""
    result: list[tuple[float, ...]] = []
    for token in text.strip().split():
        parts = token.split(",")
        if len(parts) >= 2:
            try:
                lon, lat = float(parts[0]), float(parts[1])
                alt = float(parts[2]) if len(parts) > 2 else 0.0
                result.append((lon, lat, alt))
            except ValueError:
                pass
    return result


def _load_kmz(path: str) -> tuple[gpd.GeoDataFrame, dict, list[str]]:
    """Extract doc.kml from a KMZ archive and load it."""
    warnings = validate_archive_safety(path)
    tmp_dir = tempfile.mkdtemp(prefix="geomeasure_kmz_")
    try:
        with zipfile.ZipFile(path) as zf:
            kml_name = next(
                (n for n in zf.namelist() if n.lower().endswith(".kml")),
                None,
            )
            if kml_name is None:
                raise ValueError("KMZ archive contains no .kml file")
            kml_path = os.path.join(tmp_dir, "doc.kml")
            with zf.open(kml_name) as src, open(kml_path, "wb") as dst:
                dst.write(src.read())

        gdf, raster_meta, kml_warnings = _load_kml(kml_path)
        warnings.extend(kml_warnings)
        return gdf, raster_meta, warnings
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _load_gpx(path: str) -> tuple[gpd.GeoDataFrame, dict, list[str]]:
    """Load a GPX file using gpxpy."""
    warnings: list[str] = []
    features: list[dict[str, Any]] = []

    with open(path, encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    # Tracks
    for t_idx, track in enumerate(gpx.tracks):
        coords_with_elev: list[tuple[float, float, float | None]] = []
        timestamps = []
        for segment in track.segments:
            for pt in segment.points:
                coords_with_elev.append((pt.longitude, pt.latitude, pt.elevation))
                timestamps.append(pt.time)

        if len(coords_with_elev) >= 2:
            line = LineString([(c[0], c[1]) for c in coords_with_elev])
            features.append(
                {
                    "geometry": line,
                    "type": "track",
                    "name": track.name or f"Track {t_idx}",
                    "_coords_with_elev": coords_with_elev,
                    "_timestamps": timestamps,
                }
            )

    # Routes
    for r_idx, route in enumerate(gpx.routes):
        if len(route.points) >= 2:
            coords = [(pt.longitude, pt.latitude) for pt in route.points]
            features.append(
                {
                    "geometry": LineString(coords),
                    "type": "route",
                    "name": route.name or f"Route {r_idx}",
                    "_coords_with_elev": [
                        (pt.longitude, pt.latitude, pt.elevation) for pt in route.points
                    ],
                    "_timestamps": [None] * len(route.points),
                }
            )

    # Waypoints
    for wp in gpx.waypoints:
        features.append(
            {
                "geometry": Point(wp.longitude, wp.latitude),
                "type": "waypoint",
                "name": wp.name or "",
                "_coords_with_elev": [(wp.longitude, wp.latitude, wp.elevation)],
                "_timestamps": [wp.time],
            }
        )

    if not features:
        warnings.append("GPX file contains no tracks, routes, or waypoints")

    gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
    return gdf, {}, warnings


def _load_shapefile_zip(path: str) -> tuple[gpd.GeoDataFrame, dict, list[str]]:
    """Extract and load an ESRI Shapefile from a ZIP archive."""
    warnings = validate_archive_safety(path)
    tmp_dir = tempfile.mkdtemp(prefix="geomeasure_shp_")
    try:
        with zipfile.ZipFile(path) as zf:
            # Security: only extract safe extensions
            for member in zf.infolist():
                norm = os.path.normpath(member.filename)
                os.path.splitext(norm)[1].lower()
                if not norm.startswith("..") and not os.path.isabs(member.filename):
                    zf.extract(member, tmp_dir)

        # Find the .shp file
        shp_files = list(Path(tmp_dir).rglob("*.shp"))
        if not shp_files:
            raise ValueError("ZIP archive contains no .shp file")
        if len(shp_files) > 1:
            warnings.append(f"Multiple .shp files found; using {shp_files[0].name}")

        gdf = gpd.read_file(str(shp_files[0]), engine="pyogrio")
        return gdf, {}, warnings
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _load_geopackage(path: str) -> tuple[gpd.GeoDataFrame, dict, list[str]]:
    """Load the first layer from a GeoPackage."""
    import pyogrio

    warnings: list[str] = []
    layers = pyogrio.list_layers(path)
    if len(layers) == 0:
        raise ValueError("GeoPackage contains no layers")
    if len(layers) > 1:
        warnings.append(f"GeoPackage has {len(layers)} layers; loading layer '{layers[0][0]}'")

    layer_name = layers[0][0]
    gdf = gpd.read_file(path, layer=layer_name, engine="pyogrio")
    return gdf, {}, warnings


def _load_csv(path: str) -> tuple[gpd.GeoDataFrame, dict, list[str]]:
    """Load a CSV file with auto-detected lat/lon or WKT columns."""
    warnings: list[str] = []
    df = pd.read_csv(path)
    cols_lower = {c.lower(): c for c in df.columns}

    # Try WKT column first
    wkt_col = next((cols_lower[k] for k in _WKT_ALIASES if k in cols_lower), None)
    if wkt_col is None:
        # Try value-sniffing: look for a column whose first non-null value looks like WKT
        for col in df.columns:
            first_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if isinstance(first_val, str) and any(
                first_val.upper().startswith(pfx)
                for pfx in ("POINT", "LINESTRING", "POLYGON", "MULTIPOLYGON", "MULTILINESTRING")
            ):
                wkt_col = col
                break

    if wkt_col:
        gdf = gpd.GeoDataFrame(
            df.drop(columns=[wkt_col]),
            geometry=gpd.GeoSeries.from_wkt(df[wkt_col]),
            crs="EPSG:4326",
        )
        warnings.append(f"Using column '{wkt_col}' as WKT geometry")
        return gdf, {}, warnings

    # Try lat/lon columns
    lat_col = next((cols_lower[k] for k in _LAT_ALIASES if k in cols_lower), None)
    lon_col = next((cols_lower[k] for k in _LON_ALIASES if k in cols_lower), None)

    if lat_col and lon_col:
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
            crs="EPSG:4326",
        )
        warnings.append(f"Using columns '{lon_col}' (lon) and '{lat_col}' (lat) for geometry")
        return gdf, {}, warnings

    raise ValueError(
        "CSV file has no recognised geometry columns. "
        "Expected lat/lon column names (lat, latitude, lon, lng, longitude, x, y) "
        "or a WKT column (wkt, geometry, geom)."
    )


def _load_geotiff_meta(path: str) -> tuple[None, dict, list[str]]:
    """Return None GeoDataFrame + raster metadata dict for GeoTIFF files."""
    # Actual measurement happens in raster.py; here we just signal format
    return None, {"is_raster": True, "path": path}, []
