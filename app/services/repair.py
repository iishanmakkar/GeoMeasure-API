"""Geometry repair using shapely.validation.make_valid."""

from __future__ import annotations

from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity, make_valid

from app.core.logging import get_logger

log = get_logger(__name__)


def repair_geometry(geom: BaseGeometry) -> tuple[BaseGeometry, bool]:
    """Attempt to repair an invalid geometry.

    Returns (repaired_geometry, was_repaired).
    """
    if geom is None or geom.is_empty:
        return geom, False

    if geom.is_valid:
        return geom, False

    reason = explain_validity(geom)
    log.info("repairing_geometry", reason=reason)

    repaired = make_valid(geom)
    return repaired, True


def geometry_validity(geom: BaseGeometry) -> tuple[bool, str]:
    """Return (is_valid, validity_reason).

    If valid, validity_reason is 'Valid Geometry'.
    """
    if geom is None or geom.is_empty:
        return False, "Empty geometry"
    valid = geom.is_valid
    reason = "Valid Geometry" if valid else explain_validity(geom)
    return valid, reason
