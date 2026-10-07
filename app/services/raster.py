"""GeoTIFF raster measurements using rasterio."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.services.geodesic import bounding_box_dimensions, geodesic_area

log = get_logger(__name__)


@dataclass
class RasterMeasurement:
    """Measurements derived from a GeoTIFF raster file."""

    width_px: int
    height_px: int
    band_count: int
    crs: str | None
    crs_assumed: bool
    bounds_minx: float
    bounds_miny: float
    bounds_maxx: float
    bounds_maxy: float
    bbox_width_m: float
    bbox_height_m: float
    bbox_area_m2: float
    pixel_width_m: float
    pixel_height_m: float
    pixel_area_m2: float
    warnings: list[str]


def measure_raster(path: str) -> RasterMeasurement:
    """Open a GeoTIFF and return bounding-box and pixel measurements.

    Args:
        path: Absolute path to the GeoTIFF file.

    Returns:
        RasterMeasurement with geodesic bbox and pixel dimensions.
    """
    import rasterio  # Lazy import to avoid loading at startup
    from shapely.geometry import box

    warnings: list[str] = []

    with rasterio.open(path) as ds:
        width_px = ds.width
        height_px = ds.height
        band_count = ds.count
        src_crs = ds.crs

        if src_crs is None:
            crs_str = None
            crs_assumed = True
            warnings.append("GeoTIFF has no CRS — assuming EPSG:4326")
        else:
            crs_str = src_crs.to_string()
            crs_assumed = False

        # Get bounds and reproject to WGS84 if needed
        bounds = ds.bounds
        if src_crs and not src_crs.is_geographic:
            import pyproj

            transformer = pyproj.Transformer.from_crs(
                src_crs.to_epsg() or src_crs.to_wkt(),
                4326,
                always_xy=True,
            )
            minx, miny = transformer.transform(bounds.left, bounds.bottom)
            maxx, maxy = transformer.transform(bounds.right, bounds.top)
        else:
            minx, miny = bounds.left, bounds.bottom
            maxx, maxy = bounds.right, bounds.top

    bbox_dims = bounding_box_dimensions((minx, miny, maxx, maxy))
    bbox_poly = box(minx, miny, maxx, maxy)
    bbox_area_m2 = geodesic_area(bbox_poly)

    pixel_width_m = bbox_dims["width_m"] / width_px if width_px else 0.0
    pixel_height_m = bbox_dims["height_m"] / height_px if height_px else 0.0
    pixel_area_m2 = pixel_width_m * pixel_height_m

    return RasterMeasurement(
        width_px=width_px,
        height_px=height_px,
        band_count=band_count,
        crs=crs_str,
        crs_assumed=crs_assumed,
        bounds_minx=round(minx, 8),
        bounds_miny=round(miny, 8),
        bounds_maxx=round(maxx, 8),
        bounds_maxy=round(maxy, 8),
        bbox_width_m=round(bbox_dims["width_m"], 4),
        bbox_height_m=round(bbox_dims["height_m"], 4),
        bbox_area_m2=round(bbox_area_m2, 4),
        pixel_width_m=round(pixel_width_m, 6),
        pixel_height_m=round(pixel_height_m, 6),
        pixel_area_m2=round(pixel_area_m2, 6),
        warnings=warnings,
    )
