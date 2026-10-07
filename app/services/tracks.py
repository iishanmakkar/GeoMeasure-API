"""GPX / KML track analysis: elevation, ascent, descent, speed."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class TrackPoint:
    """A single point in a track."""

    lon: float
    lat: float
    elevation: float | None = None
    timestamp: datetime | None = None


@dataclass
class TrackAnalysis:
    """Result of analysing a GPS/KML track."""

    has_elevation: bool
    length_2d_m: float
    length_3d_m: float
    total_ascent_m: float
    total_descent_m: float
    min_elevation_m: float | None
    max_elevation_m: float | None
    duration_s: float | None
    avg_speed_kmh: float | None
    point_count: int


def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Compute Haversine distance in metres (fast approximation for track segments)."""
    r = 6_371_000.0  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def analyze_track(points: Sequence[TrackPoint]) -> TrackAnalysis:
    """Analyse a sequence of track points.

    Returns a TrackAnalysis with 2D/3D length, ascent, descent, elevation stats,
    duration and average speed (if timestamps are present).
    """
    if len(points) < 2:
        return TrackAnalysis(
            has_elevation=False,
            length_2d_m=0.0,
            length_3d_m=0.0,
            total_ascent_m=0.0,
            total_descent_m=0.0,
            min_elevation_m=None,
            max_elevation_m=None,
            duration_s=None,
            avg_speed_kmh=None,
            point_count=len(points),
        )

    elevations = [p.elevation for p in points if p.elevation is not None]
    has_elevation = len(elevations) >= len(points) // 2

    length_2d = 0.0
    length_3d = 0.0
    ascent = 0.0
    descent = 0.0

    for i in range(len(points) - 1):
        p1, p2 = points[i], points[i + 1]
        d2 = haversine_distance(p1.lon, p1.lat, p2.lon, p2.lat)
        length_2d += d2

        if has_elevation and p1.elevation is not None and p2.elevation is not None:
            dz = p2.elevation - p1.elevation
            d3 = math.sqrt(d2**2 + dz**2)
            length_3d += d3
            if dz > 0:
                ascent += dz
            else:
                descent += abs(dz)
        else:
            length_3d += d2

    # Elevation stats
    min_elev = min(elevations) if elevations else None
    max_elev = max(elevations) if elevations else None

    # Duration and speed
    duration_s: float | None = None
    avg_speed_kmh: float | None = None
    ts_start = points[0].timestamp
    ts_end = points[-1].timestamp
    if ts_start and ts_end:
        duration_s = abs((ts_end - ts_start).total_seconds())
        if duration_s > 0:
            avg_speed_kmh = round((length_2d / 1000) / (duration_s / 3600), 2)

    return TrackAnalysis(
        has_elevation=has_elevation,
        length_2d_m=round(length_2d, 2),
        length_3d_m=round(length_3d, 2),
        total_ascent_m=round(ascent, 2),
        total_descent_m=round(descent, 2),
        min_elevation_m=round(min_elev, 2) if min_elev is not None else None,
        max_elevation_m=round(max_elev, 2) if max_elev is not None else None,
        duration_s=round(duration_s, 2) if duration_s is not None else None,
        avg_speed_kmh=avg_speed_kmh,
        point_count=len(points),
    )
