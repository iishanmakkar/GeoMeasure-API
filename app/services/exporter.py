"""Export measurement reports as CSV or GeoJSON."""

from __future__ import annotations

import csv
import io
from typing import Any

from app.models.schemas import FeatureMeasurement, MeasurementReport


def _flatten_feature(feat: FeatureMeasurement) -> dict[str, Any]:
    """Flatten a FeatureMeasurement into a flat dict for CSV export."""
    row: dict[str, Any] = {
        "index": feat.index,
        "id": feat.id,
        "geometry_type": feat.geometry_type,
        "valid": feat.valid,
        "validity_reason": feat.validity_reason,
        "vertex_count": feat.vertex_count,
    }
    if feat.area:
        for k, v in feat.area.model_dump().items():
            row[f"area_{k}"] = v
    if feat.length:
        for k, v in feat.length.model_dump().items():
            row[f"length_{k}"] = v
    if feat.perimeter:
        for k, v in feat.perimeter.model_dump().items():
            row[f"perimeter_{k}"] = v
    if feat.centroid:
        row["centroid_lon"] = feat.centroid.lon
        row["centroid_lat"] = feat.centroid.lat
    if feat.bbox:
        row["bbox_minx"] = feat.bbox.minx
        row["bbox_miny"] = feat.bbox.miny
        row["bbox_maxx"] = feat.bbox.maxx
        row["bbox_maxy"] = feat.bbox.maxy
        row["bbox_width_m"] = feat.bbox.width_m
        row["bbox_height_m"] = feat.bbox.height_m
    if feat.properties:
        for k, v in feat.properties.items():
            row[f"prop_{k}"] = v
    return row


def to_csv(report: MeasurementReport) -> str:
    """Serialise a MeasurementReport to a CSV string."""
    if not report.features:
        return ""

    rows = [_flatten_feature(f) for f in report.features]
    fieldnames = list(rows[0].keys())

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def to_geojson(report: MeasurementReport) -> dict[str, Any]:
    """Serialise a MeasurementReport to a GeoJSON FeatureCollection."""
    features_out = []
    for feat in report.features:
        props = _flatten_feature(feat)
        # We don't have geometry in the report, use centroid as geometry if available
        geometry = None
        if feat.centroid:
            geometry = {
                "type": "Point",
                "coordinates": [feat.centroid.lon, feat.centroid.lat],
            }
        features_out.append(
            {
                "type": "Feature",
                "id": feat.id,
                "geometry": geometry,
                "properties": props,
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features_out,
        "metadata": {
            "file": report.file.model_dump(),
            "method": report.method,
            "warnings": report.warnings,
        },
    }
