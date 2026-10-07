"""Unit tests for geometry repair."""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from app.services.repair import geometry_validity, repair_geometry


class TestRepair:
    """Tests for geometry validity checking and repair."""

    def test_valid_polygon_not_repaired(self) -> None:
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        repaired, was_repaired = repair_geometry(poly)
        assert not was_repaired
        assert repaired.equals(poly)

    def test_self_intersecting_polygon_repaired(self) -> None:
        # Bowtie / self-intersecting polygon
        bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
        valid, reason = geometry_validity(bowtie)
        assert not valid

        repaired, was_repaired = repair_geometry(bowtie)
        assert was_repaired
        assert repaired.is_valid

    def test_validity_reason_for_valid_geometry(self) -> None:
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        valid, reason = geometry_validity(poly)
        assert valid
        assert "Valid" in reason

    def test_none_geometry_returns_unchanged(self) -> None:
        repaired, was_repaired = repair_geometry(None)
        assert repaired is None
        assert not was_repaired
