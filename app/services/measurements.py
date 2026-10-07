"""Measurement orchestrator: converts GeoDataFrames to MeasurementReport."""

from __future__ import annotations

import math
import time
from typing import Any

import geopandas as gpd
from pyproj import CRS
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry.base import BaseGeometry

from app.models.schemas import (
    AreaValues,
    BoundingBox,
    Centroid,
    FeatureMeasurement,
    FileMeta,
    LengthValues,
    MeasurementReport,
    PolygonExtras,
    Summary,
)
from app.services.crs import detect_crs, detect_swapped_coordinates, get_projected_crs, reproject_to_wgs84
from app.services.geodesic import (
    bounding_box_dimensions,
    compute_centroid,
    count_vertices,
    geodesic_area,
    geodesic_length,
    projected_area,
    representative_point,
)
from app.services.repair import geometry_validity, repair_geometry
from app.utils.units import convert_area, convert_length

_POLYGON_TYPES = (Polygon, MultiPolygon)
_LINE_TYPES = (LineString, MultiLineString)


def _area_values(m2: float) -> AreaValues:
    a = convert_area(m2)
    return AreaValues(**a.as_dict())


def _length_values(metres: float) -> LengthValues:
    ln = convert_length(metres)
    return LengthValues(**ln.as_dict())


def _polygon_extras(geom: Polygon | MultiPolygon) -> dict[str, Any]:
    """Compute polygon-specific extra measurements."""
    # Holes
    if isinstance(geom, Polygon):
        holes = list(geom.interiors)
        hole_area_m2 = sum(
            geodesic_area(Polygon(h)) for h in holes
        )
        num_holes = len(holes)
    else:
        num_holes = sum(len(list(p.interiors)) for p in geom.geoms)
        hole_area_m2 = sum(
            geodesic_area(Polygon(h))
            for p in geom.geoms
            for h in p.interiors
        )

    # Convex hull
    hull = geom.convex_hull
    hull_area_m2 = geodesic_area(hull)

    # Compactness (Polsby-Popper): 4π·A / P²
    area_m2 = geodesic_area(geom)
    perimeter_m = geodesic_length(geom)
    compactness = (4 * math.pi * area_m2) / (perimeter_m**2) if perimeter_m > 0 else 0.0

    # Min rotated rectangle
    mrr = geom.minimum_rotated_rectangle
    if mrr and not mrr.is_empty and isinstance(mrr, Polygon):
        coords = list(mrr.exterior.coords)
        if len(coords) >= 4:
            side1 = geodesic_length(LineString([coords[0], coords[1]]))
            side2 = geodesic_length(LineString([coords[1], coords[2]]))
            mrr_w = min(side1, side2)
            mrr_h = max(side1, side2)
        else:
            mrr_w = mrr_h = 0.0
    else:
        mrr_w = mrr_h = 0.0

    return {
        "num_holes": num_holes,
        "hole_area_m2": round(hole_area_m2, 4),
        "convex_hull_area_m2": round(hull_area_m2, 4),
        "compactness": round(min(compactness, 1.0), 6),
        "min_rotated_rect_width_m": round(mrr_w, 4),
        "min_rotated_rect_height_m": round(mrr_h, 4),
    }


def measure_feature(
    geom: BaseGeometry,
    index: int,
    feature_id: Any,
    method: str,
    properties: dict[str, Any] | None,
    do_repair: bool,
    include_properties: bool,
) -> FeatureMeasurement:
    """Measure a single geometry and return a FeatureMeasurement."""
    warnings: list[str] = []

    if geom is None or geom.is_empty:
        return FeatureMeasurement(
            index=index,
            id=feature_id,
            geometry_type="Empty",
            valid=False,
            validity_reason="Empty geometry",
            vertex_count=0,
        )

    # Validity
    valid, validity_reason = geometry_validity(geom)

    # Repair if requested
    if do_repair and not valid:
        geom, was_repaired = repair_geometry(geom)
        if was_repaired:
            valid, validity_reason = geometry_validity(geom)

    geom_type = geom.geom_type
    vertex_count = count_vertices(geom)

    # Bounding box
    bounds = geom.bounds
    bbox_dims = bounding_box_dimensions(bounds)
    bbox = BoundingBox(**bbox_dims)

    # Centroid
    centroid_dict = compute_centroid(geom)
    centroid = Centroid(**centroid_dict)

    rep_pt_dict = representative_point(geom)
    rep_pt = Centroid(**rep_pt_dict)

    # Area (polygons)
    area: AreaValues | None = None
    if isinstance(geom, _POLYGON_TYPES):
        if method == "projected":
            proj_crs = get_projected_crs(geom)
            area_m2 = projected_area(geom, proj_crs.to_epsg() or 4326)
        else:
            area_m2 = geodesic_area(geom)
        area = _area_values(area_m2)

    # Length (lines)
    length: LengthValues | None = None
    if isinstance(geom, _LINE_TYPES):
        length = _length_values(geodesic_length(geom))

    # Perimeter (polygons)
    perimeter: LengthValues | None = None
    if isinstance(geom, _POLYGON_TYPES):
        perimeter = _length_values(geodesic_length(geom))

    # Polygon extras
    from app.models.schemas import PolygonExtras
    extras = None
    if isinstance(geom, _POLYGON_TYPES):
        ex = _polygon_extras(geom)
        extras = PolygonExtras(**ex)

    return FeatureMeasurement(
        index=index,
        id=feature_id,
        geometry_type=geom_type,
        valid=valid,
        validity_reason=validity_reason,
        vertex_count=vertex_count,
        area=area,
        length=length,
        perimeter=perimeter,
        centroid=centroid,
        bbox=bbox,
        representative_point=rep_pt,
        extras=extras,
        properties=properties if include_properties else None,
    )


def measure_geodataframe(
    gdf: gpd.GeoDataFrame,
    filename: str,
    file_format: str,
    size_bytes: int,
    method: str = "geodesic",
    source_crs_str: str | None = None,
    do_repair: bool = False,
    include_properties: bool = True,
    simplify_tolerance: float | None = None,
    extra_warnings: list[str] | None = None,
) -> MeasurementReport:
    """Convert a GeoDataFrame into a full MeasurementReport.

    Args:
        gdf: Input GeoDataFrame (expected to be in EPSG:4326 already or will be reprojected).
        filename: Original uploaded filename.
        file_format: Detected format string.
        size_bytes: File size in bytes.
        method: 'geodesic' or 'projected'.
        source_crs_str: Optional override CRS string (e.g. 'EPSG:32643').
        do_repair: If True, attempt to fix invalid geometries.
        include_properties: If False, omit original attributes.
        simplify_tolerance: If set, simplify geometry by this tolerance (degrees).
        extra_warnings: Warnings from the loader to carry forward.

    Returns:
        MeasurementReport fully populated.
    """
    t_start = time.perf_counter()
    warnings: list[str] = list(extra_warnings or [])

    # CRS handling
    src_crs = None
    if source_crs_str:
        try:
            src_crs = CRS.from_user_input(source_crs_str)
        except Exception:
            warnings.append(f"Invalid source_crs '{source_crs_str}' — ignoring")

    detected_crs, crs_assumed = detect_crs(gdf)
    if crs_assumed:
        warnings.append("No CRS found in file — assuming EPSG:4326")

    gdf = reproject_to_wgs84(gdf, src_crs or detected_crs if not crs_assumed else None)
    swapped_warnings = detect_swapped_coordinates(gdf)
    warnings.extend(swapped_warnings)

    # Simplify if requested
    if simplify_tolerance is not None:
        gdf["geometry"] = gdf.geometry.simplify(simplify_tolerance)

    features: list[FeatureMeasurement] = []
    geometry_types: dict[str, int] = {}
    total_area_m2 = 0.0
    total_length_m = 0.0
    invalid_count = 0

    from app.config import get_settings
    max_features = get_settings().max_features

    if len(gdf) > max_features:
        warnings.append(
            f"File has {len(gdf)} features; only the first {max_features} were processed"
        )
        gdf = gdf.iloc[:max_features]

    for idx, row in gdf.iterrows():
        geom = row.geometry
        props = {
            k: v for k, v in row.items()
            if k != "geometry" and not (hasattr(v, "__class__") and v.__class__.__name__ == "NaT")
        }
        # Convert non-serialisable types
        cleaned_props: dict[str, Any] = {}
        for k, v in props.items():
            try:
                import json
                json.dumps(v)
                cleaned_props[k] = v
            except (TypeError, ValueError):
                cleaned_props[k] = str(v)

        fm = measure_feature(
            geom=geom,
            index=int(str(idx)) if str(idx).isdigit() else len(features),
            feature_id=row.get("id") if "id" in row.index else None,
            method=method,
            properties=cleaned_props,
            do_repair=do_repair,
            include_properties=include_properties,
        )
        features.append(fm)

        gt = fm.geometry_type
        geometry_types[gt] = geometry_types.get(gt, 0) + 1
        if not fm.valid:
            invalid_count += 1
        if fm.area:
            total_area_m2 += fm.area.m2
        if fm.length:
            total_length_m += fm.length.m

    # Summary bounding box (over whole dataset)
    total_bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    summary_bbox_dims = bounding_box_dimensions(
        (total_bounds[0], total_bounds[1], total_bounds[2], total_bounds[3])
    )
    summary_bbox = BoundingBox(**summary_bbox_dims)

    # Summary centroid
    union_geom = gdf.union_all() if hasattr(gdf, "union_all") else gdf.geometry.unary_union
    summary_centroid = Centroid(**compute_centroid(union_geom)) if union_geom and not union_geom.is_empty else None

    summary = Summary(
        total_area=_area_values(total_area_m2) if total_area_m2 > 0 else None,
        total_length=_length_values(total_length_m) if total_length_m > 0 else None,
        bbox=summary_bbox,
        centroid=summary_centroid,
        geometry_types=geometry_types,
        invalid_features=invalid_count,
    )

    processing_ms = round((time.perf_counter() - t_start) * 1000, 2)

    crs_str = gdf.crs.to_string() if gdf.crs else "EPSG:4326"

    file_meta = FileMeta(
        name=filename,
        format=file_format,
        size_bytes=size_bytes,
        crs=crs_str,
        crs_assumed=crs_assumed,
        feature_count=len(features),
        processing_ms=processing_ms,
    )

    return MeasurementReport(
        file=file_meta,
        summary=summary,
        features=features,
        warnings=warnings,
        method=method,
    )
