"""POST /measure and POST /measure/geometry endpoints."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import verify_api_key
from app.deps import get_db
from app.models.db import Job
from app.models.schemas import GeometryRequest, JobResponse, MeasurementReport
from app.services.file_loader import load_file
from app.services.job_runner import run_measurement_job
from app.services.measurements import measure_geodataframe
from app.services.raster import measure_raster
from app.utils.validators import sniff_format

router = APIRouter(tags=["Measurements"])
settings = get_settings()


def _save_upload(upload: UploadFile) -> tuple[str, int, bytes]:
    """Save UploadFile to a secure temp file. Returns (path, size, header)."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(upload.filename or "")[-1])
    try:
        content = upload.file.read()
        tmp.write(content)
        tmp.flush()
        return tmp.name, len(content), content[:512]
    finally:
        tmp.close()


def _detect_and_validate_format(header: bytes, filename: str, size_bytes: int, max_bytes: int) -> str:
    """Detect format from header bytes, enforce size limit, return format string."""
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {size_bytes / 1e6:.1f} MB exceeds limit of {max_bytes / 1e6:.0f} MB",
        )

    detected = sniff_format(header, filename or "")
    if detected is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Unsupported or unrecognised file format. "
                "Accepted: GeoJSON, KML, KMZ, GPX, Shapefile (.zip), GeoPackage, CSV, GeoTIFF"
            ),
        )
    return detected


@router.post(
    "/measure",
    response_model=MeasurementReport,
    summary="Measure a geospatial file (synchronous)",
    response_description="Full measurement report",
)
async def measure_sync(
    request: Request,
    file: Annotated[UploadFile, File(description="Geospatial file to measure")],
    method: Annotated[str, Form()] = "geodesic",
    units: Annotated[str, Form()] = "metric",
    source_crs: Annotated[str | None, Form()] = None,
    repair_geometry: Annotated[bool, Form()] = False,
    include_properties: Annotated[bool, Form()] = True,
    simplify_tolerance: Annotated[float | None, Form()] = None,
    _api_key: str | None = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> MeasurementReport:
    """Upload a geospatial file and receive measurements synchronously.

    Files up to MAX_SYNC_SIZE_MB (default 50 MB) are processed inline.
    For larger files use POST /measure/async.
    """
    tmp_path, size_bytes, header = _save_upload(file)
    detected_format = _detect_and_validate_format(
        header, file.filename or "", size_bytes, settings.max_sync_size_bytes
    )

    try:
        t_start = time.perf_counter()

        if detected_format == "geotiff":
            from app.models.schemas import (
                AreaValues,
                BoundingBox,
                Centroid,
                FeatureMeasurement,
                FileMeta,
                MeasurementReport,
                RasterExtras,
                Summary,
            )
            from app.utils.units import convert_area

            raster = measure_raster(tmp_path)
            from app.services.geodesic import bounding_box_dimensions
            bbox_dims = bounding_box_dimensions((
                raster.bounds_minx, raster.bounds_miny,
                raster.bounds_maxx, raster.bounds_maxy,
            ))
            bbox = BoundingBox(**bbox_dims)
            area_vals = convert_area(raster.bbox_area_m2)
            area = AreaValues(**area_vals.as_dict())
            processing_ms = round((time.perf_counter() - t_start) * 1000, 2)

            return MeasurementReport(
                file=FileMeta(
                    name=file.filename or "unknown.tif",
                    format="geotiff",
                    size_bytes=size_bytes,
                    crs=raster.crs,
                    crs_assumed=raster.crs_assumed,
                    feature_count=1,
                    processing_ms=processing_ms,
                ),
                summary=Summary(
                    total_area=area,
                    bbox=bbox,
                    geometry_types={"Raster": 1},
                ),
                features=[
                    FeatureMeasurement(
                        index=0,
                        geometry_type="Raster",
                        valid=True,
                        validity_reason="Valid Geometry",
                        vertex_count=4,
                        area=area,
                        bbox=bbox,
                        extras=RasterExtras(
                            width_px=raster.width_px,
                            height_px=raster.height_px,
                            band_count=raster.band_count,
                            pixel_width_m=raster.pixel_width_m,
                            pixel_height_m=raster.pixel_height_m,
                            pixel_area_m2=raster.pixel_area_m2,
                            crs_wkt=raster.crs,
                        ),
                    )
                ],
                warnings=raster.warnings,
                method=method,
            )

        gdf, raster_meta, loader_warnings = load_file(tmp_path, detected_format, source_crs)
        if gdf is None:
            raise HTTPException(500, "File loaded as raster but raster handler not triggered")

        report = measure_geodataframe(
            gdf=gdf,
            filename=file.filename or "unknown",
            file_format=detected_format,
            size_bytes=size_bytes,
            method=method,
            source_crs_str=source_crs,
            do_repair=repair_geometry,
            include_properties=include_properties,
            simplify_tolerance=simplify_tolerance,
            extra_warnings=loader_warnings,
        )

        # Save to history
        import json
        from app.models.db import HistoryEntry
        history = HistoryEntry(
            id=str(uuid.uuid4()),
            filename=file.filename or "unknown",
            format=detected_format,
            feature_count=report.file.feature_count,
            summary_json=json.dumps(report.summary.model_dump()),
            report_json=report.model_dump_json(),
        )
        db.add(history)
        await db.commit()

        return report

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing error: {exc}") from exc
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@router.post(
    "/measure/async",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Measure a geospatial file (asynchronous)",
)
async def measure_async(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    method: Annotated[str, Form()] = "geodesic",
    units: Annotated[str, Form()] = "metric",
    source_crs: Annotated[str | None, Form()] = None,
    repair_geometry: Annotated[bool, Form()] = False,
    include_properties: Annotated[bool, Form()] = True,
    simplify_tolerance: Annotated[float | None, Form()] = None,
    _api_key: str | None = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Upload a geospatial file for async processing. Returns a job_id to poll."""
    tmp_path, size_bytes, header = _save_upload(file)
    detected_format = _detect_and_validate_format(
        header, file.filename or "", size_bytes, settings.max_async_size_bytes
    )

    job_id = str(uuid.uuid4())
    job = Job(id=job_id, filename=file.filename, status="pending")
    db.add(job)
    await db.commit()

    background_tasks.add_task(
        run_measurement_job,
        job_id=job_id,
        file_path=tmp_path,
        filename=file.filename or "unknown",
        size_bytes=size_bytes,
        detected_format=detected_format,
        method=method,
        source_crs=source_crs,
        do_repair=repair_geometry,
        include_properties=include_properties,
        simplify_tolerance=simplify_tolerance,
        db_session=db,
    )

    return JobResponse(job_id=job_id, status="pending", progress=0)


@router.post(
    "/measure/geometry",
    response_model=MeasurementReport,
    summary="Measure inline GeoJSON or WKT geometry",
)
async def measure_geometry(
    request_body: GeometryRequest,
    _api_key: str | None = Depends(verify_api_key),
) -> MeasurementReport:
    """Accept raw GeoJSON or WKT and return measurements without file upload."""
    import geopandas as gpd
    import json
    from shapely import from_wkt
    from shapely.geometry import shape

    warnings: list[str] = []

    if request_body.wkt:
        try:
            geom = from_wkt(request_body.wkt)
        except Exception as exc:
            raise HTTPException(400, f"Invalid WKT: {exc}") from exc
        gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")

    elif request_body.geojson:
        try:
            gdf = gpd.GeoDataFrame.from_features(
                request_body.geojson.get("features", [request_body.geojson])
            )
            gdf.set_crs("EPSG:4326", inplace=True)
        except Exception as exc:
            raise HTTPException(400, f"Invalid GeoJSON: {exc}") from exc
    else:
        raise HTTPException(400, "Provide either 'geojson' or 'wkt' in the request body")

    return measure_geodataframe(
        gdf=gdf,
        filename="<inline>",
        file_format="geojson",
        size_bytes=0,
        method=request_body.method,
        source_crs_str=request_body.source_crs,
        do_repair=request_body.repair_geometry,
        include_properties=request_body.include_properties,
        extra_warnings=warnings,
    )
