"""Unit tests for track analysis."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.services.tracks import TrackPoint, analyze_track


class TestTrackAnalysis:
    """Tests for GPX/KML track analysis."""

    def _make_points(
        self,
        n: int,
        with_elevation: bool = True,
        with_timestamps: bool = True,
    ) -> list[TrackPoint]:
        """Generate n evenly-spaced track points moving east from Delhi."""
        points = []
        base_lon = 77.0
        base_time = datetime(2024, 1, 1, 6, 0, 0, tzinfo=UTC)
        for i in range(n):
            elev = 200 + i * 10 if with_elevation else None
            ts = base_time + timedelta(hours=i) if with_timestamps else None
            points.append(
                TrackPoint(lon=base_lon + i * 0.1, lat=28.0, elevation=elev, timestamp=ts)
            )
        return points

    def test_basic_2d_length(self) -> None:
        points = self._make_points(5, with_elevation=False, with_timestamps=False)
        result = analyze_track(points)
        assert result.length_2d_m > 0
        assert result.length_3d_m > 0

    def test_3d_length_greater_than_2d_with_elevation(self) -> None:
        points = self._make_points(5, with_elevation=True, with_timestamps=False)
        result = analyze_track(points)
        assert result.has_elevation
        assert result.length_3d_m >= result.length_2d_m

    def test_ascent_and_descent(self) -> None:
        # Points going up then down
        pts = [
            TrackPoint(0.0, 0.0, 0.0),
            TrackPoint(0.1, 0.0, 100.0),
            TrackPoint(0.2, 0.0, 200.0),
            TrackPoint(0.3, 0.0, 100.0),
            TrackPoint(0.4, 0.0, 50.0),
        ]
        result = analyze_track(pts)
        assert result.total_ascent_m == pytest.approx(200.0, abs=1.0)
        assert result.total_descent_m == pytest.approx(150.0, abs=1.0)

    def test_elevation_min_max(self) -> None:
        pts = [
            TrackPoint(0.0, 0.0, 100.0),
            TrackPoint(0.1, 0.0, 500.0),
            TrackPoint(0.2, 0.0, 300.0),
        ]
        result = analyze_track(pts)
        assert result.min_elevation_m == pytest.approx(100.0, abs=0.1)
        assert result.max_elevation_m == pytest.approx(500.0, abs=0.1)

    def test_duration_and_speed(self) -> None:
        points = self._make_points(3, with_elevation=False, with_timestamps=True)
        result = analyze_track(points)
        assert result.duration_s is not None
        assert result.duration_s == pytest.approx(7200.0, abs=1.0)  # 2 hours
        assert result.avg_speed_kmh is not None
        assert result.avg_speed_kmh > 0

    def test_single_point_returns_zero(self) -> None:
        pts = [TrackPoint(77.0, 28.0, 100.0)]
        result = analyze_track(pts)
        assert result.length_2d_m == 0.0
        assert result.point_count == 1
