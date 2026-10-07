"""Pydantic v2 response schemas for the GeoMeasure API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Measurement value models
# ---------------------------------------------------------------------------


class AreaValues(BaseModel):
    """Area measurements in all supported units."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "m2": 1230800000.0,
                "km2": 1230.8,
                "ha": 123080.0,
                "acres": 304165.5,
                "ft2": 13249305600.0,
                "mi2": 475.2,
            }
        }
    )

    m2: float = Field(description="Square metres")
    km2: float = Field(description="Square kilometres")
    ha: float = Field(description="Hectares")
    acres: float = Field(description="Acres")
    ft2: float = Field(description="Square feet")
    mi2: float = Field(description="Square miles")


class LengthValues(BaseModel):
    """Length measurements in all supported units."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "m": 1150000.0,
                "km": 1150.0,
                "ft": 3772966.0,
                "mi": 714.6,
                "nmi": 620.7,
            }
        }
    )

    m: float = Field(description="Metres")
    km: float = Field(description="Kilometres")
    ft: float = Field(description="Feet")
    mi: float = Field(description="Miles")
    nmi: float = Field(description="Nautical miles")


class BoundingBox(BaseModel):
    """Bounding box with WGS84 coordinates and geodesic dimensions."""

    minx: float = Field(description="Minimum longitude (west)")
    miny: float = Field(description="Minimum latitude (south)")
    maxx: float = Field(description="Maximum longitude (east)")
    maxy: float = Field(description="Maximum latitude (north)")
    width_m: float = Field(description="Width of bounding box in metres")
    height_m: float = Field(description="Height of bounding box in metres")


class Centroid(BaseModel):
    """Centroid coordinates."""

    lon: float
    lat: float


class PolygonExtras(BaseModel):
    """Extra measurements specific to polygons."""

    num_holes: int = Field(description="Number of interior holes")
    hole_area_m2: float = Field(description="Total area of holes in m²")
    convex_hull_area_m2: float = Field(description="Convex hull area in m²")
    compactness: float = Field(description="Polsby-Popper compactness score [0,1]")
    min_rotated_rect_width_m: float = Field(description="Width of minimum rotated rectangle in m")
    min_rotated_rect_height_m: float = Field(
        description="Height of minimum rotated rectangle in m"
    )


class TrackExtras(BaseModel):
    """Extra measurements for GPX/KML tracks with elevation data."""

    has_elevation: bool
    length_2d_m: float = Field(description="2D (horizontal) length in metres")
    length_3d_m: float = Field(description="3D (slant) length including elevation in metres")
    total_ascent_m: float = Field(description="Total elevation gain in metres")
    total_descent_m: float = Field(description="Total elevation loss in metres")
    min_elevation_m: float | None = None
    max_elevation_m: float | None = None
    duration_s: float | None = Field(default=None, description="Track duration in seconds")
    avg_speed_kmh: float | None = Field(default=None, description="Average speed in km/h")


class RasterExtras(BaseModel):
    """Extra measurements for GeoTIFF raster files."""

    width_px: int
    height_px: int
    band_count: int
    pixel_width_m: float
    pixel_height_m: float
    pixel_area_m2: float
    crs_wkt: str | None = None


# ---------------------------------------------------------------------------
# Feature-level output
# ---------------------------------------------------------------------------


class FeatureMeasurement(BaseModel):
    """Measurements for a single geospatial feature."""

    model_config = ConfigDict(populate_by_name=True)

    index: int = Field(description="Zero-based feature index in the file")
    id: Any = Field(default=None, description="Feature ID from the source file")
    geometry_type: str
    valid: bool
    validity_reason: str
    vertex_count: int
    area: AreaValues | None = Field(default=None, description="Area (polygons only)")
    length: LengthValues | None = Field(
        default=None, description="Length (lines) or None for points"
    )
    perimeter: LengthValues | None = Field(
        default=None, description="Perimeter (polygons only)"
    )
    centroid: Centroid | None = None
    bbox: BoundingBox | None = None
    representative_point: Centroid | None = None
    extras: PolygonExtras | TrackExtras | RasterExtras | None = None
    properties: dict[str, Any] | None = Field(
        default=None, description="Original feature properties from the file"
    )


# ---------------------------------------------------------------------------
# File-level metadata
# ---------------------------------------------------------------------------


class FileMeta(BaseModel):
    """Metadata about the uploaded file."""

    name: str
    format: str
    size_bytes: int
    crs: str | None = Field(default=None, description="Detected CRS identifier")
    crs_assumed: bool = Field(
        default=False, description="True if CRS was not present in file and EPSG:4326 was assumed"
    )
    feature_count: int
    processing_ms: float


class Summary(BaseModel):
    """Aggregate measurements across all features."""

    total_area: AreaValues | None = None
    total_length: LengthValues | None = None
    bbox: BoundingBox | None = None
    centroid: Centroid | None = None
    geometry_types: dict[str, int] = Field(
        default_factory=dict, description="Count of each geometry type"
    )
    invalid_features: int = 0


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------


class MeasurementReport(BaseModel):
    """Full measurement report returned by POST /measure."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file": {
                    "name": "sample.geojson",
                    "format": "geojson",
                    "size_bytes": 2048,
                    "crs": "EPSG:4326",
                    "crs_assumed": False,
                    "feature_count": 2,
                    "processing_ms": 42.1,
                },
                "summary": {"total_area": {"km2": 1230.8}},
                "features": [],
                "warnings": [],
                "method": "geodesic",
            }
        }
    )

    file: FileMeta
    summary: Summary
    features: list[FeatureMeasurement]
    warnings: list[str] = Field(default_factory=list)
    method: str = Field(default="geodesic")


# ---------------------------------------------------------------------------
# Distance response
# ---------------------------------------------------------------------------


class DistanceResponse(BaseModel):
    """Result of a point-to-point geodesic distance calculation."""

    distance_m: float
    distance_km: float
    distance_mi: float
    distance_nmi: float
    initial_bearing_deg: float
    final_bearing_deg: float
    from_point: list[float] = Field(description="[lon, lat]")
    to_point: list[float] = Field(description="[lon, lat]")


# ---------------------------------------------------------------------------
# Job / async response
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    """Response for async job creation or status queries."""

    job_id: str
    status: str = Field(description="pending | running | done | failed")
    progress: int = Field(default=0, ge=0, le=100)
    result: MeasurementReport | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# History list item
# ---------------------------------------------------------------------------


class HistoryItem(BaseModel):
    """Summary item for the history list."""

    id: str
    filename: str
    format: str
    feature_count: int
    created_at: str
    summary: dict[str, Any] = Field(default_factory=dict)


class HistoryList(BaseModel):
    """Paginated list of past measurements."""

    items: list[HistoryItem]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Inline geometry request
# ---------------------------------------------------------------------------


class GeometryRequest(BaseModel):
    """Request body for POST /measure/geometry."""

    geojson: dict[str, Any] | None = Field(
        default=None, description="Raw GeoJSON object (Feature or FeatureCollection)"
    )
    wkt: str | None = Field(default=None, description="Well-Known Text geometry string")
    method: str = Field(default="geodesic", pattern="^(geodesic|projected)$")
    units: str = Field(default="metric", pattern="^(metric|imperial|both)$")
    source_crs: str | None = None
    repair_geometry: bool = False
    include_properties: bool = True


# ---------------------------------------------------------------------------
# Distance request
# ---------------------------------------------------------------------------


class DistanceRequest(BaseModel):
    """Request body for POST /distance."""

    from_point: list[float] = Field(
        alias="from",
        description="[lon, lat] in WGS84",
        min_length=2,
        max_length=2,
    )
    to_point: list[float] = Field(
        alias="to",
        description="[lon, lat] in WGS84",
        min_length=2,
        max_length=2,
    )
    model_config = ConfigDict(populate_by_name=True)
