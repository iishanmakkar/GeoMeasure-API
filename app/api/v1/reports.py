"""GET /report/{id}.csv and GET /report/{id}.geojson — export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_api_key
from app.deps import get_db
from app.models.db import HistoryEntry
from app.models.schemas import MeasurementReport
from app.services.exporter import to_csv, to_geojson

router = APIRouter(tags=["Reports"])


@router.get(
    "/report/{entry_id}.csv",
    summary="Export measurement report as CSV",
    responses={200: {"content": {"text/csv": {}}}},
)
async def export_csv(
    entry_id: str,
    _api_key: str | None = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download per-feature measurements as a CSV file."""
    entry = await db.get(HistoryEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"History entry '{entry_id}' not found")

    report = MeasurementReport.model_validate_json(entry.report_json)
    csv_content = to_csv(report)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="report_{entry_id}.csv"'
        },
    )


@router.get(
    "/report/{entry_id}.geojson",
    summary="Export measurement report as GeoJSON",
    responses={200: {"content": {"application/geo+json": {}}}},
)
async def export_geojson(
    entry_id: str,
    _api_key: str | None = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download per-feature measurements as a GeoJSON FeatureCollection."""
    import json

    entry = await db.get(HistoryEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"History entry '{entry_id}' not found")

    report = MeasurementReport.model_validate_json(entry.report_json)
    geojson_content = to_geojson(report)

    return Response(
        content=json.dumps(geojson_content, indent=2),
        media_type="application/geo+json",
        headers={
            "Content-Disposition": f'attachment; filename="report_{entry_id}.geojson"'
        },
    )
