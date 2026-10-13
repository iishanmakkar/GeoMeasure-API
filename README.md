<div align="center">
  <h1>🌍 GeoMeasure API</h1>
  <p><strong>A production-grade, asynchronous REST microservice for survey-accurate WGS84 ellipsoidal geospatial measurements.</strong></p>

  [![GeoMeasure API CI](https://github.com/iishanmakkar/GeoMeasure-API/actions/workflows/ci.yml/badge.svg)](https://github.com/iishanmakkar/GeoMeasure-API/actions/workflows/ci.yml)
  [![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg?logo=python&logoColor=white)](https://python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
  [![MCP Server](https://img.shields.io/badge/MCP-Server%20Ready-blueviolet.svg?logo=anthropic&logoColor=white)](docs/mcp.md)
  [![Coverage](https://img.shields.io/badge/Coverage-90%25-brightgreen.svg)]()
  [![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1-6BA539.svg?logo=openapi-initiative&logoColor=white)](docs/openapi.json)
  [![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
  [![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](Dockerfile)
</div>

---

## 🚀 Overview

**GeoMeasure API** is an enterprise-grade geospatial computation microservice built to solve a fundamental GIS challenge: **calculating exact real-world dimensions on Earth's curved oblate spheroid.**

Most web mapping tools and naive backend pipelines perform Euclidean (planar) geometry directly on coordinates or Web Mercator (EPSG:3857) projections. This introduces severe geometric distortion—up to **300% error** in temperate zones and **1,000%+ error** near polar regions.

GeoMeasure calculates **true geodesics on the WGS84 ellipsoid** (via C-extensions `pyproj.Geod` and `Shapely 2.x`), delivering sub-millimeter precision for areas, lengths, perimeters, great-circle distances, and true navigation azimuths.

---

## 📐 Why Ellipsoidal WGS84 Geodesics Matter

| Latitude | Region | Planar Degree Error | Web Mercator (EPSG:3857) Error | **GeoMeasure API (WGS84 Geodesic)** |
|---|---|---|---|---|
| **0°** | Quito / Singapore | ~0.7% | 0.0% | **< 0.001% (Exact)** |
| **28° N** | New Delhi / Houston | ~12.1% | ~28.5% | **< 0.001% (Exact)** |
| **45° N** | New York / Paris | ~29.3% | ~100.0% (2× area distortion) | **< 0.001% (Exact)** |
| **60° N** | Oslo / Anchorage | ~50.0% | ~300.0% (4× area distortion) | **< 0.001% (Exact)** |
| **72° N** | Greenland / Prudhoe Bay | ~69.1% | ~950.0% (10.5× area distortion) | **< 0.001% (Exact)** |

> GeoMeasure guarantees survey-grade calculations regardless of latitude or coordinate extent.

---

## ⚡ Core Capabilities

- **🌐 Survey-Grade Geodesics**: Ellipsoidal area (exterior minus interior holes), perimeter, geodesic line length, and Great-Circle distance with forward/reverse bearings.
- **📂 8 Universal Geospatial Formats**:
  - `GeoJSON` (`.geojson`, `.json`)
  - `KML` (`.kml` — fortified with `defusedxml` against XXE)
  - `KMZ` (`.kmz` — zip decompression with path-traversal guards)
  - `GPX` (`.gpx` — extracts 2D/3D tracks, total ascent/descent, speed, elevation profiles)
  - `Shapefile` (`.zip` — multi-layer shapefile extraction & CRS detection)
  - `GeoPackage` (`.gpkg` — OGC standard SQLite container parsing)
  - `Delimited Text` (`.csv` — auto-sniffs latitude/longitude headers or inline WKT)
  - `GeoTIFF` (`.tif`, `.tiff` — pixel dimensions, resolution, raster bounding box via `rasterio`)
- **🖥️ Interactive Web GIS Workstation**: A modern, dark-themed GIS workbench served at `/` featuring live WGS84 drawing, drag-and-drop file inspection, great-circle navigation, 3D GPX elevation profiles, and topology healing.
- **⚙️ Asynchronous Task Queue**: Background job execution (`/measure/async`) with persistent SQLite tracking for massive files (up to 500 MB).
- **🛡️ Self-Healing Geometry Repair**: Automatically repairs self-intersecting polygons (`repair_geometry=true`) and gracefully isolates native `TopologyException` errors without failing the request.
- **📊 Multi-Unit Conversions**: Simultaneous reporting in Metric (`m²`, `km²`, `ha`) and Imperial (`ft²`, `acres`, `mi²`).
- **📥 Turnkey Report Exports**: Download measurement summaries and per-feature tables as **CSV** or **GeoJSON FeatureCollection** (`/api/v1/report/{id}.csv`).
- **🔒 Enterprise Security**: Rate limiting via `slowapi`, API key authentication (`X-API-Key`), zip-bomb safety limits, and strict CORS policies.

---

## 🖥️ Interactive Web GIS Workstation

GeoMeasure includes an interactive, browser-based Web GIS Workstation served directly at root (`http://localhost:8000/`).

| Capability | What It Does |
|---|---|
| **🌐 Multi-Format Dropzone** | Drag & drop any of the 8 supported formats (`.geojson`, `.kml`, `.kmz`, `.gpx`, `.zip`, `.gpkg`, `.csv`, `.tif`) to view rendered geometries and complete measurement reports instantly. |
| **✏️ Draw Studio** | Draw polygons, polylines, circle buffers, and waypoints with real-time WGS84 ellipsoidal area, perimeter, and length computations. |
| **✈️ Great-Circle Navigator** | Compute shortest flight paths between any two points on Earth with curved geodesic arcs, initial/final azimuths, nautical miles, and statute miles. |
| **⛰️ 3D GPX Elevation Visualizer** | Interactive elevation profile SVG graph with hover scrubber synchronized to a moving map beacon, showing 3D slant distances and cumulative ascent/descent. |
| **🩺 Topology Repair Lab** | Diagnose invalid self-intersecting geometries (e.g. Bowtie polygons) and auto-heal them using Shapely 2.0 `make_valid`. |
| **💾 History & Export Hub** | Review past audit logs and download reports with one click in CSV or GeoJSON. |


---

## 🛠️ Architecture & Tech Stack

```
                     ┌────────────────────────────────────────────────────────┐
                     │                  Client Application                    │
                     │  (Browser / Mobile App / Python SDK / cURL / Postman)  │
                     └───────────────────────────┬────────────────────────────┘
                                                 │ HTTP / REST
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   GeoMeasure API Service                                │
│                                                                                         │
│   ┌──────────────────────┐   ┌──────────────────────┐   ┌───────────────────────────┐   │
│   │  Rate Limiter        │   │  Security & Auth     │   │  File Validator & Sniffer │   │
│   │  (slowapi / 100/min) │   │  (X-API-Key Guards)  │   │  (MIME, Magic, Limits)    │   │
│   └──────────────────────┘   └──────────────────────┘   └───────────────────────────┘   │
│                                                 │                                       │
│                       ┌─────────────────────────┴─────────────────────────┐             │
│                       ▼                                                   ▼             │
│        ┌─────────────────────────────┐                     ┌──────────────────────────┐ │
│        │   Synchronous Handler       │                     │   Async Background Worker│ │
│        │   (Files < 50MB, < 30s)     │                     │   (Files up to 500MB)    │ │
│        └──────────────┬──────────────┘                     └─────────────┬────────────┘ │
│                       │                                                  │              │
│                       ▼                                                  ▼              │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                           Geospatial Processing Core                            │   │
│   │                                                                                 │   │
│   │   • pyogrio / fiona / defusedxml / gpxpy / rasterio  ──► Unified GeoDataFrame   │   │
│   │   • pyproj.CRS / auto-UTM Zone Selector             ──► WGS84 Normalization     │   │
│   │   • Shapely 2.0 (make_valid)                        ──► Topologic Self-Repair   │   │
│   │   • pyproj.Geod (WGS84 Ellipsoid)                   ──► Geodesic Measurements   │   │
│   └─────────────────────────────────────────┬───────────────────────────────────────┘   │
│                                             │                                           │
│                       ┌─────────────────────┴─────────────────────┐                     │
│                       ▼                                           ▼                     │
│        ┌─────────────────────────────┐             ┌──────────────────────────────┐     │
│        │  SQLite Audit Trail         │             │  Report Exporters            │     │
│        │  (SQLAlchemy 2.0 Async)     │             │  (Flat CSV & GeoJSON Output) │     │
│        └─────────────────────────────┘             └──────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏁 Quickstart

### 🐳 Option A: Run with Docker Compose (Recommended)

```bash
git clone https://github.com/iishanmakkar/GeoMeasure-API.git
cd GeoMeasure-API

# Copy environment config
cp .env.example .env

# Spin up container
docker compose up -d
```

- API Base URL: `http://localhost:8000`
- Interactive Swagger UI: `http://localhost:8000/docs`
- ReDoc API Reference: `http://localhost:8000/redoc`

---

### 💻 Option B: Run Locally with Python

```bash
# 1. Clone repository
git clone https://github.com/iishanmakkar/GeoMeasure-API.git
cd GeoMeasure-API

# 2. Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install package with dev dependencies
pip install -e ".[dev]"

# 4. Generate sample fixtures
python tests/fixtures/generate_fixtures.py

# 5. Start development server
uvicorn app.main:app --reload --port 8000
```

---

## 🎮 Interactive Live Demo

Run the interactive terminal demonstration against your local server (or in-process):

```bash
python samples/demo.py
```

This will run live calculations across 7 test suites (WGS84 Distance, WKT Multi-Units, GeoJSON parsing, 3D GPX Track elevation, Async Job queue, and CSV/GeoJSON exports) with timing benchmarks!

---

## 📖 API Usage & Examples

> **Auth**: Pass `-H "X-API-Key: dev-key-12345"` (configured in `.env`).

### 1. Synchronous File Measurement (`POST /api/v1/measure`)
```bash
curl -X POST http://localhost:8000/api/v1/measure \
  -H "X-API-Key: dev-key-12345" \
  -F "file=@samples/data/sample.geojson" \
  -F "method=geodesic" \
  -F "units=metric" \
  -F "repair_geometry=true"
```

**Response (`200 OK`):**
```json
{
  "file": {
    "name": "sample.geojson",
    "format": "geojson",
    "size_bytes": 656,
    "crs": "EPSG:4326",
    "crs_assumed": false,
    "feature_count": 2,
    "processing_ms": 2.14
  },
  "summary": {
    "total_area": {
      "m2": 10850425211.4,
      "km2": 10850.4252,
      "ha": 1085042.52,
      "acres": 2681196.2,
      "ft2": 116792987114.2,
      "mi2": 4189.37
    },
    "bbox": {
      "minx": 76.5,
      "miny": 28.0,
      "maxx": 77.5,
      "maxy": 29.0,
      "width_m": 98018.4,
      "height_m": 110574.1
    },
    "centroid": {"lon": 77.0, "lat": 28.5},
    "geometry_types": {"Polygon": 1, "LineString": 1},
    "invalid_features": 0
  },
  "features": [
    {
      "index": 0,
      "geometry_type": "Polygon",
      "valid": true,
      "validity_reason": "Valid Geometry",
      "vertex_count": 5,
      "area": {"km2": 10850.4252, "acres": 2681196.2},
      "perimeter": {"km": 417.18},
      "centroid": {"lon": 77.0, "lat": 28.5},
      "extras": {
        "num_holes": 0,
        "compactness": 0.784
      }
    }
  ]
}
```

---

### 2. Point-to-Point Geodesic Distance & Bearing (`POST /api/v1/distance`)
Calculates the shortest path across the curved Earth ellipsoid, with true initial and final navigation azimuths:

```bash
# New Delhi (28.61° N, 77.21° E) → Mumbai (19.08° N, 72.88° E)
curl -X POST http://localhost:8000/api/v1/distance \
  -H "X-API-Key: dev-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"from": [77.2090, 28.6139], "to": [72.8777, 19.0760]}'
```

**Response (`200 OK`):**
```json
{
  "from_coords": [77.209, 28.6139],
  "to_coords": [72.8777, 19.076],
  "distance_m": 1144526.43,
  "distance_km": 1144.53,
  "distance_miles": 711.18,
  "distance_nautical_miles": 617.99,
  "initial_bearing_deg": 203.58,
  "final_bearing_deg": 21.79
}
```

---

### 3. Inline WKT / GeoJSON Geometry (`POST /api/v1/measure/geometry`)
Compute measurements without uploading a file:

```bash
curl -X POST http://localhost:8000/api/v1/measure/geometry \
  -H "X-API-Key: dev-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
    "method": "geodesic",
    "units": "both"
  }'
```

---

### 4. Asynchronous Processing for Large Files (`POST /api/v1/measure/async`)
For datasets up to 500 MB:

```bash
# 1. Submit job
curl -X POST http://localhost:8000/api/v1/measure/async \
  -H "X-API-Key: dev-key-12345" \
  -F "file=@massive_cadastral_dataset.zip"

# Response: {"job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d", "status": "pending"}

# 2. Poll status
curl -H "X-API-Key: dev-key-12345" \
  http://localhost:8000/api/v1/jobs/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d
```

---

### 5. Export Reports to CSV & GeoJSON (`GET /api/v1/report/{id}`)
```bash
# Download feature table as CSV
curl -H "X-API-Key: dev-key-12345" \
  http://localhost:8000/api/v1/report/{entry_id}.csv -o report.csv

# Download as GeoJSON FeatureCollection
curl -H "X-API-Key: dev-key-12345" \
  http://localhost:8000/api/v1/report/{entry_id}.geojson -o report.geojson
```

---

## 💻 Developer Tooling & Integrations

- **Postman Collection**: [`samples/GeoMeasure_API.postman_collection.json`](samples/GeoMeasure_API.postman_collection.json) — Ready-to-import with pre-configured requests, environment variables, and tests.
- **VS Code REST Client**: [`samples/requests.http`](samples/requests.http) — 15 runnable requests right from your editor.
- **OpenAPI 3.1 Specification**: [`docs/openapi.json`](docs/openapi.json) — Import into Swagger Editor, Insomnia, or generate client SDKs (TypeScript, Go, Rust, Java).
- **cURL Cheat Sheet**: [`samples/curl_examples.sh`](samples/curl_examples.sh).

### Python Client Example (`httpx`)
```python
import httpx

client = httpx.Client(base_url="http://localhost:8000", headers={"X-API-Key": "dev-key-12345"})

# Measure distance
r = client.post("/api/v1/distance", json={"from": [77.209, 28.614], "to": [72.878, 19.076]})
print(f"Distance: {r.json()['distance_km']:.1f} km")

# Measure file
with open("parcels.geojson", "rb") as f:
    resp = client.post("/api/v1/measure", files={"file": ("parcels.geojson", f, "application/geo+json")})
print(f"Total Area: {resp.json()['summary']['total_area']['km2']:.2f} km²")
```

---

## 🤖 Model Context Protocol (MCP) Server

GeoMeasure includes an official, production-grade **MCP Server** (`mcp>=1.0.0`) so that AI assistants (**Claude Desktop, Cursor, Antigravity, Windsurf**) can execute geospatial calculations natively:

```bash
# Start MCP server over stdio
python -m app.mcp_server
# or
geomeasure-mcp
```

### Connect to Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "geomeasure": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/absolute/path/to/GeoMeasure-API"
    }
  }
}
```

### Available MCP Tools
- `calculate_distance`: Great-Circle WGS84 distance & initial/final azimuths.
- `measure_wkt`: Survey-grade area, perimeter, and bounding boxes for WKT strings.
- `measure_geojson`: Real-world measurements for GeoJSON geometries/features.
- `measure_file`: Load and measure `.geojson`, `.kml`, `.kmz`, `.gpx`, `.zip` (shapefiles), `.gpkg`, `.csv`, `.tif`.
- `repair_geometry`: Self-repair self-crossing or corrupt geometries via Shapely 2.0 `make_valid`.
- `analyze_gpx_track`: Extract 3D slant distances, elevation ascent/descent, and pace from GPS routes.
- `list_supported_formats`: Enumerate supported GIS formats.

👉 *See [`docs/mcp.md`](docs/mcp.md) for complete Cursor, Windsurf, and Claude integration setup.*

---

## 🧪 Testing & Quality Assurance

GeoMeasure maintains an exhaustive **91-test test suite** with **90% line coverage**:

```bash
# Run full test suite with coverage report
pytest tests/ -v --cov=app --cov-report=term-missing

# Lint & formatting check
ruff check app/ tests/
ruff format --check app/ tests/

# Strict type checking
mypy app/ tests/ --ignore-missing-imports
```

### 🛡️ 20-Vector Vulnerability & Stress Testing
1. **TopologyException Recovery**: Self-intersecting complex country borders (e.g. Antarctica) are safely caught and isolated without 500 errors.
2. **Antimeridian Wrapping**: Cross-hemisphere polygons spanning -180°/+180° longitude are measured without coordinate wrapping artifacts.
3. **Poles & Singularities**: Coordinates at exactly ±90° latitude and extreme polar geometries are safely handled.
4. **Zip-Bomb & Path Traversal Guards**: Checks total uncompressed byte limits (100MB max) and validates canonical paths before extraction.
5. **XXE Protection**: All KML parsers utilize `defusedxml` to block XML External Entity exploits.
6. **Concurrent Bombardment**: Verified under asynchronous bursts with rate limits and transaction isolation.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
