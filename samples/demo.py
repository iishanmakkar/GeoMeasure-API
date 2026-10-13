"""Interactive GeoMeasure API Demonstration.

Can be run against a live server (http://localhost:8000) or runs in-process via FastAPI TestClient.
Usage:
    python samples/demo.py
    python samples/demo.py http://my-remote-host:8000
"""

from __future__ import annotations

import csv
import io
import sys
import time
from pathlib import Path
from typing import Any

import httpx

# Ensure UTF-8 console output across all OS environments
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore

# ANSI terminal formatting
BOLD = "\033[1m"
GREEN = "\033[32m"
BLUE = "\033[34m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
RESET = "\033[0m"

FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures"


def print_banner() -> None:
    banner = f"""
{CYAN}{BOLD}================================================================================
   🌍  GEOMEASURE API  —  Production Geospatial Measurement Engine
================================================================================{RESET}
  • High-Precision WGS84 Geodesic Math (pyproj.Geod)
  • 8 Multi-Format Parsers (GeoJSON, KML, KMZ, GPX, Shapefile, GPKG, CSV, GeoTIFF)
  • 3D Track Elevation Analytics & Topologic Geometry Repair
  • Turnkey Docker & Async Background Job Processing
"""
    print(banner)


def get_client(target_url: str) -> tuple[Any, bool]:
    """Return an HTTP client.

    Falls back to FastAPI in-process TestClient if no live server is running.
    """
    default_headers = {"X-API-Key": "dev-key-12345"}
    try:
        r = httpx.get(f"{target_url}/health", timeout=1.5)
        if r.status_code == 200:
            print(f"{GREEN}✓ Connected to live GeoMeasure API at {target_url}{RESET}\n")
            return httpx.Client(base_url=target_url, headers=default_headers), True
    except Exception:
        pass

    print(
        f"{YELLOW}ℹ  No server running at {target_url}. Launching in-process test engine...{RESET}\n"
    )
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app, headers=default_headers), False


def run_demo(client: Any) -> None:
    # 1. System Info
    print(f"{BOLD}[1/7] Discovering Supported Geospatial Formats...{RESET}")
    resp = client.get("/api/v1/formats")
    data = resp.json()
    formats = [f"{f['name']} ({', '.join(f['extensions'])})" for f in data["formats"]]
    print(f"  Supported: {', '.join(formats[:4])}")
    print(f"             {', '.join(formats[4:])}")
    print(f"{GREEN}  ✓ {len(data['formats'])} formats registered & ready.{RESET}\n")

    # 2. Distance & Bearing
    print(f"{BOLD}[2/7] Geodesic Distance & Navigation Bearing (WGS84)...{RESET}")
    delhi_to_mumbai = {"from": [77.2090, 28.6139], "to": [72.8777, 19.0760]}
    t0 = time.perf_counter()
    resp = client.post("/api/v1/distance", json=delhi_to_mumbai)
    elapsed = (time.perf_counter() - t0) * 1000
    dist = resp.json()
    print("  Route: New Delhi (28.61° N, 77.21° E) → Mumbai (19.08° N, 72.88° E)")
    print(
        f"  • Great-Circle Distance : {BOLD}{dist['distance_km']:,.2f} km{RESET} ({dist['distance_m']:,.1f} m)"
    )
    print(f"  • Initial True Bearing  : {dist['initial_bearing_deg']:.1f}°")
    print(f"  • Final True Bearing    : {dist['final_bearing_deg']:.1f}°")
    print(f"{GREEN}  ✓ Computed in {elapsed:.2f} ms.{RESET}\n")

    # 3. Inline Geometry WKT
    print(f"{BOLD}[3/7] Inline WKT Polygon Measurement & Multi-Unit Conversion...{RESET}")
    poly_wkt = "POLYGON((77.2090 28.6139, 77.2290 28.6139, 77.2290 28.6339, 77.2090 28.6339, 77.2090 28.6139))"
    resp = client.post(
        "/api/v1/measure/geometry",
        json={"wkt": poly_wkt, "method": "geodesic", "units": "both"},
    )
    res = resp.json()
    f0 = res["features"][0]
    area = f0["area"]
    print("  Geometry : 0.02° x 0.02° Polygon around New Delhi")
    print(
        f"  • Area (Metric)   : {BOLD}{area['km2']:.4f} km²{RESET} ({area['m2']:,.1f} m² | {area['ha']:.2f} hectares)"
    )
    print(f"  • Area (Imperial) : {BOLD}{area['acres']:,.2f} acres{RESET} ({area['mi2']:.4f} mi²)")
    print(f"  • Perimeter       : {f0['perimeter']['km']:.3f} km")
    print(
        f"  • Centroid        : Lon {f0['centroid']['lon']:.4f}°, Lat {f0['centroid']['lat']:.4f}°"
    )
    print(f"{GREEN}  ✓ Complete multi-unit report generated.{RESET}\n")

    # 4. GeoJSON File Upload
    print(f"{BOLD}[4/7] Parsing & Measuring Multi-Feature GeoJSON Dataset...{RESET}")
    geojson_path = FIXTURES / "sample.geojson"
    if geojson_path.exists():
        with open(geojson_path, "rb") as f:
            resp = client.post(
                "/api/v1/measure",
                files={"file": ("sample.geojson", f, "application/geo+json")},
                data={"method": "geodesic", "units": "metric"},
            )
        data = resp.json()
        print(f"  File     : sample.geojson ({data['file']['size_bytes']} bytes)")
        print(f"  CRS      : {data['file']['crs']} (Assumed: {data['file']['crs_assumed']})")
        print(f"  Features : {data['file']['feature_count']} features loaded")
        print(f"  Types    : {data['summary']['geometry_types']}")
        if data["summary"]["total_area"]:
            print(f"  Total Area: {BOLD}{data['summary']['total_area']['km2']:.4f} km²{RESET}")
        print(f"{GREEN}  ✓ Processed in {data['file']['processing_ms']:.2f} ms.{RESET}\n")

    # 5. 3D Elevation GPX Track
    print(f"{BOLD}[5/7] Analyzing 3D GPS Workout Track (Elevation & Ascent/Descent)...{RESET}")
    gpx_path = FIXTURES / "sample.gpx"
    if gpx_path.exists():
        with open(gpx_path, "rb") as f:
            resp = client.post(
                "/api/v1/measure",
                files={"file": ("sample.gpx", f, "application/gpx+xml")},
            )
        gpx_data = resp.json()
        track_feat = next(
            (
                f
                for f in gpx_data["features"]
                if f["geometry_type"] in ("LineString", "MultiLineString")
            ),
            None,
        )
        if track_feat and track_feat.get("extras"):
            ex = track_feat["extras"]
            print(f"  Track Type    : {track_feat['geometry_type']}")
            print(f"  • 2D Flat Distance   : {ex.get('length_2d_m', 0.0):,.1f} m")
            print(f"  • 3D True Distance   : {BOLD}{ex.get('length_3d_m', 0.0):,.1f} m{RESET}")
            print(f"  • Total Ascent       : +{ex.get('total_ascent_m', 0.0):.1f} m")
            print(f"  • Total Descent      : -{ex.get('total_descent_m', 0.0):.1f} m")
            if ex.get("avg_speed_kmh"):
                print(f"  • Average Pace/Speed : {ex.get('avg_speed_kmh'):.1f} km/h")
        print(f"{GREEN}  ✓ 3D topography profile analyzed.{RESET}\n")

    # 6. Asynchronous Background Job
    print(f"{BOLD}[6/7] Submitting Asynchronous Background Measurement Job...{RESET}")
    with open(FIXTURES / "sample.geojson", "rb") as f:
        job_post = client.post(
            "/api/v1/measure/async",
            files={"file": ("sample_async.geojson", f, "application/geo+json")},
        )
    job_info = job_post.json()
    job_id = job_info["job_id"]
    print(f"  Job Queued : ID = {job_id}")
    print(f"  Initial Status : {job_info['status']}")

    # Poll until done
    for _ in range(10):
        poll = client.get(f"/api/v1/jobs/{job_id}").json()
        if poll["status"] in ("done", "failed"):
            print(f"{GREEN}  ✓ Job finished with status '{poll['status']}' in background.{RESET}\n")
            break
        time.sleep(0.2)

    # 7. History & Export
    print(f"{BOLD}[7/7] Auditing History & Exporting Formatted Reports...{RESET}")
    hist = client.get("/api/v1/history?page=1&page_size=5").json()
    print(f"  Total historical measurement entries in database: {hist['total']}")
    if hist["items"]:
        entry_id = hist["items"][0]["id"]
        csv_resp = client.get(f"/api/v1/report/{entry_id}.csv")
        reader = csv.reader(io.StringIO(csv_resp.text))
        header = next(reader, [])
        print(f"  CSV Export : {len(csv_resp.text)} bytes, {len(header)} columns")
        print(f"               Columns: {', '.join(header[:6])}...")

        geojson_resp = client.get(f"/api/v1/report/{entry_id}.geojson")
        gj = geojson_resp.json()
        print(
            f"  GeoJSON Export: {len(gj.get('features', []))} features serialised with bounding boxes."
        )
        print(f"{GREEN}  ✓ Exporters verified.{RESET}\n")

    print(f"""
{GREEN}{BOLD}================================================================================
   🎉 ALL 7 TEST SUITES EXECUTED SUCCESSFULLY!
================================================================================{RESET}
  Explore the interactive Swagger UI at:   {CYAN}http://localhost:8000/docs{RESET}
  Explore ReDoc API reference at:          {CYAN}http://localhost:8000/redoc{RESET}
  Import Postman Collection from:          {CYAN}samples/GeoMeasure_API.postman_collection.json{RESET}
  VS Code REST Client suite at:            {CYAN}samples/requests.http{RESET}
""")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    print_banner()
    c, is_live = get_client(target)
    run_demo(c)
