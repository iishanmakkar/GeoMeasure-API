"""Health and version endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["Meta"])
settings = get_settings()


@router.get(
    "/health",
    summary="Health check",
    response_description="Service health status",
    responses={200: {"content": {"application/json": {"example": {"status": "ok"}}}}},
)
async def health_check() -> dict:
    """Return the service health status and current timestamp."""
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": settings.app_env,
    }


@router.get(
    "/version",
    summary="API version",
    response_description="API version information",
)
async def get_version() -> dict:
    """Return the current API version and metadata."""
    return {
        "name": settings.app_name,
        "version": settings.api_version,
        "api_prefix": "/api/v1",
        "docs": "/docs",
    }


SUPPORTED_FORMATS: list[dict[str, Any]] = [
    {
        "name": "GeoJSON",
        "extensions": [".geojson", ".json"],
        "description": "RFC 7946 GeoJSON — points, lines, polygons, collections",
        "max_size_mb": settings.max_sync_size_mb,
    },
    {
        "name": "KML",
        "extensions": [".kml"],
        "description": "Keyhole Markup Language (Google Earth)",
        "max_size_mb": settings.max_sync_size_mb,
    },
    {
        "name": "KMZ",
        "extensions": [".kmz"],
        "description": "Compressed KML archive",
        "max_size_mb": settings.max_sync_size_mb,
    },
    {
        "name": "GPX",
        "extensions": [".gpx"],
        "description": "GPS Exchange Format — tracks, routes, waypoints with elevation",
        "max_size_mb": settings.max_sync_size_mb,
    },
    {
        "name": "Shapefile",
        "extensions": [".zip"],
        "description": "ESRI Shapefile in a ZIP archive (.shp/.shx/.dbf/.prj)",
        "max_size_mb": settings.max_sync_size_mb,
    },
    {
        "name": "GeoPackage",
        "extensions": [".gpkg"],
        "description": "OGC GeoPackage — SQLite-based geospatial container",
        "max_size_mb": settings.max_sync_size_mb,
    },
    {
        "name": "CSV",
        "extensions": [".csv"],
        "description": "CSV with lat/lon or WKT geometry column (auto-detected)",
        "max_size_mb": settings.max_sync_size_mb,
    },
    {
        "name": "GeoTIFF",
        "extensions": [".tif", ".tiff"],
        "description": "GeoTIFF raster — returns bounding box and pixel area measurements",
        "max_size_mb": settings.max_async_size_mb,
    },
]


@router.get(
    "/api/v1/formats",
    summary="Supported formats",
    response_description="List of supported input formats and their limits",
    tags=["Meta"],
)
async def get_formats() -> dict:
    """List all supported geospatial file formats and their constraints."""
    return {
        "formats": SUPPORTED_FORMATS,
        "sync_limit_mb": settings.max_sync_size_mb,
        "async_limit_mb": settings.max_async_size_mb,
        "max_features": settings.max_features,
    }


@router.get(
    "/api/v1/config",
    summary="Client configuration",
    response_description="Client-facing configuration and map keys",
    tags=["Meta"],
)
async def get_client_config() -> dict[str, Any]:
    """Return public configuration and integration keys for map rendering."""
    return {
        "carto_api_key": settings.carto_api_key,
        "api_version": settings.api_version,
        "max_sync_size_mb": settings.max_sync_size_mb,
    }
