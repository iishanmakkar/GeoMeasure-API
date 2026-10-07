"""POST /distance — geodesic distance between two points."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import verify_api_key
from app.models.schemas import DistanceRequest, DistanceResponse
from app.services.geodesic import geodesic_distance
from app.utils.units import LENGTH_FACTORS

router = APIRouter(tags=["Distance"])


@router.post(
    "/distance",
    response_model=DistanceResponse,
    summary="Geodesic distance between two points",
)
async def compute_distance(
    body: DistanceRequest,
    _api_key: str | None = Depends(verify_api_key),
) -> DistanceResponse:
    """Compute the geodesic distance and bearing between two WGS84 points.

    Body fields:
    - **from**: [lon, lat] of the first point
    - **to**: [lon, lat] of the second point
    """
    lon1, lat1 = body.from_point
    lon2, lat2 = body.to_point

    result = geodesic_distance(lon1, lat1, lon2, lat2)
    dist_m = result["distance_m"]

    return DistanceResponse(
        distance_m=dist_m,
        distance_km=round(dist_m * LENGTH_FACTORS["km"], 4),
        distance_mi=round(dist_m * LENGTH_FACTORS["mi"], 6),
        distance_nmi=round(dist_m * LENGTH_FACTORS["nmi"], 6),
        initial_bearing_deg=result["initial_bearing_deg"],
        final_bearing_deg=result["final_bearing_deg"],
        from_point=body.from_point,
        to_point=body.to_point,
    )
