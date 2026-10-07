"""Input validators: CRS, lat/lon range, file content, archive safety."""

from __future__ import annotations

import os
import zipfile

from app.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
settings = get_settings()

# Magic bytes for format detection
_MAGIC: dict[str, bytes] = {
    "zip": b"PK\x03\x04",
    "tiff_le": b"II*\x00",
    "tiff_be": b"MM\x00*",
    "sqlite": b"SQLite format 3\x00",
}

ALLOWED_ARCHIVE_EXTENSIONS: frozenset[str] = frozenset(
    [".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx", ".kml", ".xml", ".doc"]
)


def sniff_format(header: bytes, filename: str) -> str | None:
    """Detect file format from magic bytes and filename extension.

    Returns a format string or None if unknown.
    """
    ext = os.path.splitext(filename.lower())[1]

    # GeoTIFF
    if header[:4] in (b"II*\x00", b"MM\x00*") or ext in (".tif", ".tiff"):
        return "geotiff"

    # SQLite / GeoPackage
    if header[:16] == _MAGIC["sqlite"] or ext == ".gpkg":
        return "gpkg"

    # ZIP-based: Shapefile zip or KMZ
    if header[:4] == _MAGIC["zip"]:
        if ext == ".kmz":
            return "kmz"
        return "zip"  # Could be shapefile — resolved later

    # XML-based: KML or GPX
    if header[:5] in (b"<?xml", b"<kml ", b"<gpx ") or b"<kml" in header[:512]:
        if ext == ".gpx" or b"<gpx" in header[:512]:
            return "gpx"
        if ext == ".kml" or b"<kml" in header[:512]:
            return "kml"

    # GeoJSON / JSON
    stripped = header.lstrip(b" \t\r\n\xef\xbb\xbf")
    if stripped.startswith(b"{") or ext in (".geojson", ".json"):
        return "geojson"

    # CSV
    if ext == ".csv":
        return "csv"
    try:
        header.decode("utf-8")
        return "csv"  # Optimistic text fallback
    except UnicodeDecodeError:
        pass

    return None


def validate_archive_safety(zip_path: str) -> list[str]:
    """Check a ZIP archive for zip-bomb and path-traversal entries.

    Returns a list of warning strings; raises ValueError on critical issues.
    """
    warnings: list[str] = []
    total_uncompressed = 0

    with zipfile.ZipFile(zip_path) as zf:
        members = zf.infolist()

        if len(members) > settings.max_archive_files:
            raise ValueError(
                f"Archive contains {len(members)} files, max allowed is {settings.max_archive_files}"
            )

        for member in members:
            # Path traversal check
            norm = os.path.normpath(member.filename)
            if norm.startswith("..") or os.path.isabs(member.filename):
                raise ValueError(
                    f"Archive entry '{member.filename}' contains a path traversal sequence"
                )

            total_uncompressed += member.file_size

        if total_uncompressed > settings.max_uncompressed_bytes:
            raise ValueError(
                f"Archive uncompressed size {total_uncompressed / 1e6:.1f} MB "
                f"exceeds limit of {settings.max_uncompressed_mb} MB"
            )

    return warnings


def validate_latlon_bounds(lon: float, lat: float) -> list[str]:
    """Check that lon/lat are in valid WGS84 ranges."""
    warnings: list[str] = []
    if not (-180 <= lon <= 180):
        warnings.append(f"Longitude {lon} is outside [-180, 180]")
    if not (-90 <= lat <= 90):
        warnings.append(f"Latitude {lat} is outside [-90, 90]")
    # Detect likely swapped lon/lat (lat in lon position)
    if abs(lat) > 90:
        warnings.append(
            f"Latitude value {lat} exceeds 90° — coordinates may be swapped (lon/lat ↔ lat/lon)"
        )
    return warnings
