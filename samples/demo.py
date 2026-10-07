"""Demo script: exercises every endpoint against a running GeoMeasure API."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000"
FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures"
HEADERS = {}  # Add {"X-API-Key": "your-key"} if auth is enabled


def pp(label: str, data: dict) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(json.dumps(data, indent=2)[:2000])


def health_check() -> None:
    r = httpx.get(f"{BASE_URL}/health")
    pp("GET /health", r.json())


def measure_geojson() -> None:
    with open(FIXTURES / "sample.geojson", "rb") as f:
        r = httpx.post(
            f"{BASE_URL}/api/v1/measure",
            files={"file": ("sample.geojson", f, "application/geo+json")},
            headers=HEADERS,
        )
    data = r.json()
    print("\n✅ GeoJSON measurement:")
    print(f"  Features: {data['file']['feature_count']}")
    if data["summary"]["total_area"]:
        print(f"  Total area: {data['summary']['total_area']['km2']:.2f} km²")


def measure_gpx() -> None:
    with open(FIXTURES / "sample.gpx", "rb") as f:
        r = httpx.post(
            f"{BASE_URL}/api/v1/measure",
            files={"file": ("sample.gpx", f)},
            headers=HEADERS,
        )
    data = r.json()
    print("\n✅ GPX measurement:")
    print(f"  Features: {data['file']['feature_count']}")
    print(f"  Geometry types: {data['summary']['geometry_types']}")


def measure_csv() -> None:
    with open(FIXTURES / "sample.csv", "rb") as f:
        r = httpx.post(
            f"{BASE_URL}/api/v1/measure",
            files={"file": ("sample.csv", f, "text/csv")},
            headers=HEADERS,
        )
    data = r.json()
    print("\n✅ CSV measurement:")
    print(f"  Points loaded: {data['file']['feature_count']}")


def measure_geometry() -> None:
    r = httpx.post(
        f"{BASE_URL}/api/v1/measure/geometry",
        json={"wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"},
        headers=HEADERS,
    )
    data = r.json()
    print("\n✅ Inline WKT polygon:")
    print(f"  Area: {data['features'][0]['area']['km2']:.2f} km²")


def distance_query() -> None:
    r = httpx.post(
        f"{BASE_URL}/api/v1/distance",
        json={"from": [77.2090, 28.6139], "to": [72.8777, 19.0760]},
        headers=HEADERS,
    )
    data = r.json()
    print("\n✅ Delhi → Mumbai distance:")
    print(f"  {data['distance_km']:.1f} km")
    print(f"  Initial bearing: {data['initial_bearing_deg']:.1f}°")


def list_formats() -> None:
    r = httpx.get(f"{BASE_URL}/api/v1/formats")
    data = r.json()
    print("\n✅ Supported formats:")
    for fmt in data["formats"]:
        print(f"  - {fmt['name']}: {', '.join(fmt['extensions'])}")


if __name__ == "__main__":
    try:
        health_check()
        measure_geojson()
        measure_gpx()
        measure_csv()
        measure_geometry()
        distance_query()
        list_formats()
        print("\n🎉 All demo calls completed successfully!")
    except httpx.ConnectError:
        print(f"❌ Could not connect to {BASE_URL}")
        print("   Make sure the server is running: docker compose up")
        sys.exit(1)
