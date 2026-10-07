"""Unit conversion utilities for area and length measurements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Conversion factors relative to square metres
AREA_FACTORS: dict[str, float] = {
    "m2": 1.0,
    "km2": 1e-6,
    "ha": 1e-4,
    "acres": 2.471_053_814_671_654e-4,
    "ft2": 10.763_910_416_709_722,
    "mi2": 3.861_021_585_424_459e-7,
}

# Conversion factors relative to metres
LENGTH_FACTORS: dict[str, float] = {
    "m": 1.0,
    "km": 1e-3,
    "ft": 3.280_839_895_013_123,
    "mi": 6.213_711_922_373_339e-4,
    "nmi": 5.399_568_034_557_236e-4,
}

AreaUnit = Literal["m2", "km2", "ha", "acres", "ft2", "mi2"]
LengthUnit = Literal["m", "km", "ft", "mi", "nmi"]


@dataclass(frozen=True)
class AreaMeasurements:
    """All area values in every supported unit."""

    m2: float
    km2: float
    ha: float
    acres: float
    ft2: float
    mi2: float

    def as_dict(self) -> dict[str, float]:
        return {
            "m2": round(self.m2, 4),
            "km2": round(self.km2, 6),
            "ha": round(self.ha, 4),
            "acres": round(self.acres, 4),
            "ft2": round(self.ft2, 2),
            "mi2": round(self.mi2, 8),
        }


@dataclass(frozen=True)
class LengthMeasurements:
    """All length values in every supported unit."""

    m: float
    km: float
    ft: float
    mi: float
    nmi: float

    def as_dict(self) -> dict[str, float]:
        return {
            "m": round(self.m, 4),
            "km": round(self.km, 6),
            "ft": round(self.ft, 2),
            "mi": round(self.mi, 6),
            "nmi": round(self.nmi, 6),
        }


def convert_area(m2: float) -> AreaMeasurements:
    """Convert an area in square metres to all supported units."""
    return AreaMeasurements(
        m2=m2,
        km2=m2 * AREA_FACTORS["km2"],
        ha=m2 * AREA_FACTORS["ha"],
        acres=m2 * AREA_FACTORS["acres"],
        ft2=m2 * AREA_FACTORS["ft2"],
        mi2=m2 * AREA_FACTORS["mi2"],
    )


def convert_length(metres: float) -> LengthMeasurements:
    """Convert a length in metres to all supported units."""
    return LengthMeasurements(
        m=metres,
        km=metres * LENGTH_FACTORS["km"],
        ft=metres * LENGTH_FACTORS["ft"],
        mi=metres * LENGTH_FACTORS["mi"],
        nmi=metres * LENGTH_FACTORS["nmi"],
    )
