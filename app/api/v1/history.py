"""GET/DELETE /history — paginated measurement history."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_api_key
from app.deps import get_db
from app.models.db import HistoryEntry
from app.models.schemas import HistoryItem, HistoryList, MeasurementReport

router = APIRouter(tags=["History"])


@router.get(
    "/history",
    response_model=HistoryList,
    summary="List past measurements",
)
async def list_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _api_key: str | None = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> HistoryList:
    """Return a paginated list of past measurement requests."""
    count_result = await db.execute(select(func.count()).select_from(HistoryEntry))
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    rows_result = await db.execute(
        select(HistoryEntry)
        .order_by(HistoryEntry.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = rows_result.scalars().all()

    items = [
        HistoryItem(
            id=row.id,
            filename=row.filename,
            format=row.format,
            feature_count=row.feature_count,
            created_at=row.created_at.isoformat(),
            summary=json.loads(row.summary_json) if row.summary_json else {},
        )
        for row in rows
    ]

    return HistoryList(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/history/{entry_id}",
    response_model=MeasurementReport,
    summary="Get full measurement report from history",
)
async def get_history_entry(
    entry_id: str,
    _api_key: str | None = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> MeasurementReport:
    """Return the full measurement report for a past request."""
    entry = await db.get(HistoryEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"History entry '{entry_id}' not found")

    from typing import cast
    return cast(MeasurementReport, MeasurementReport.model_validate_json(entry.report_json))


@router.delete(
    "/history/{entry_id}",
    status_code=204,
    summary="Delete a history entry",
)
async def delete_history_entry(
    entry_id: str,
    _api_key: str | None = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a past measurement record."""
    entry = await db.get(HistoryEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"History entry '{entry_id}' not found")
    await db.delete(entry)
    await db.commit()
