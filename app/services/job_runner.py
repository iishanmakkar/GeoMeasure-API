"""Background job runner for async measurement processing."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.db import HistoryEntry, Job
from app.services.file_loader import load_file
from app.services.measurements import measure_geodataframe
from app.services.raster import measure_raster

log = get_logger(__name__)


async def run_measurement_job(
    job_id: str,
    file_path: str,
    filename: str,
    size_bytes: int,
    detected_format: str,
    method: str,
    source_crs: str | None,
    do_repair: bool,
    include_properties: bool,
    simplify_tolerance: float | None,
) -> None:
    """Process a geospatial file measurement as a background task.

    Updates the Job record in the database with progress and results.
    """
    import os
    from app.models.db import AsyncSessionLocal

    log.info("job_started", job_id=job_id, format=detected_format)

    async with AsyncSessionLocal() as db_session:
        # Set status to running
        job = await db_session.get(Job, job_id)
        if not job:
            log.error("job_not_found", job_id=job_id)
            return

        job.status = "running"
        job.progress = 5
        await db_session.commit()

        try:
            # Load file
            gdf, raster_meta, loader_warnings = load_file(file_path, detected_format, source_crs)
            job.progress = 40
            await db_session.commit()

            if raster_meta.get("is_raster"):
                # Raster measurement
                raster_result = measure_raster(file_path)
                # Build a minimal report for rasters
                from app.models.schemas import (
                    BoundingBox,
                    Centroid,
                    FeatureMeasurement,
                    FileMeta,
                    MeasurementReport,
                    RasterExtras,
                    Summary,
                )
                from app.services.geodesic import bounding_box_dimensions
                from app.utils.units import convert_area

                bbox_dims = bounding_box_dimensions(
                    (
                        raster_result.bounds_minx,
                        raster_result.bounds_miny,
                        raster_result.bounds_maxx,
                        raster_result.bounds_maxy,
                    )
                )
                bbox = BoundingBox(**bbox_dims)
                area_vals = convert_area(raster_result.bbox_area_m2)
                from app.models.schemas import AreaValues

                area = AreaValues(**area_vals.as_dict())

                report = MeasurementReport(
                    file=FileMeta(
                        name=filename,
                        format="geotiff",
                        size_bytes=size_bytes,
                        crs=raster_result.crs,
                        crs_assumed=raster_result.crs_assumed,
                        feature_count=1,
                        processing_ms=0,
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
                                width_px=raster_result.width_px,
                                height_px=raster_result.height_px,
                                band_count=raster_result.band_count,
                                pixel_width_m=raster_result.pixel_width_m,
                                pixel_height_m=raster_result.pixel_height_m,
                                pixel_area_m2=raster_result.pixel_area_m2,
                                crs_wkt=raster_result.crs,
                            ),
                        )
                    ],
                    warnings=raster_result.warnings + loader_warnings,
                    method=method,
                )
            else:
                # Vector measurement
                report = measure_geodataframe(
                    gdf=gdf,
                    filename=filename,
                    file_format=detected_format,
                    size_bytes=size_bytes,
                    method=method,
                    source_crs_str=source_crs,
                    do_repair=do_repair,
                    include_properties=include_properties,
                    simplify_tolerance=simplify_tolerance,
                    extra_warnings=loader_warnings,
                )

            job.progress = 90
            await db_session.commit()

            report_json = report.model_dump_json()
            job.result_json = report_json
            job.status = "done"
            job.progress = 100
            await db_session.commit()

            # Save to history
            history = HistoryEntry(
                id=job_id,
                filename=filename,
                format=detected_format,
                feature_count=report.file.feature_count,
                summary_json=json.dumps(report.summary.model_dump()),
                report_json=report_json,
            )
            db_session.add(history)
            await db_session.commit()

            log.info("job_completed", job_id=job_id)

        except Exception as exc:
            log.exception("job_failed", job_id=job_id, error=str(exc))
            job = await db_session.get(Job, job_id)
            if job:
                job.status = "failed"
                job.error = str(exc)
                await db_session.commit()
        finally:
            # Clean up temp file
            try:
                os.unlink(file_path)
            except OSError:
                pass
