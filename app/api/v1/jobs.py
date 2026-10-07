"""GET /jobs/{job_id} — async job status and results."""

from __future__ import annotations

import contextlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_api_key
from app.deps import get_db
from app.models.db import Job
from app.models.schemas import JobResponse, MeasurementReport

router = APIRouter(tags=["Jobs"])


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get async job status",
)
async def get_job(
    job_id: str,
    _api_key: str | None = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Return the status and result of an async measurement job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    result: MeasurementReport | None = None
    if job.status == "done" and job.result_json:
        with contextlib.suppress(Exception):
            result = MeasurementReport.model_validate_json(job.result_json)

    return JobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        result=result,
        error=job.error,
    )
