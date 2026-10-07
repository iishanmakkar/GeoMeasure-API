<div align="center">
  <h1>🌍 GeoMeasure API</h1>
  <p><strong>A production-grade, asynchronous REST API for extremely high-accuracy WGS84 geodesic measurements.</strong></p>

  [![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com)
  [![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
  [![Build](https://img.shields.io/badge/Build-Passing-brightgreen.svg)]()
  [![Coverage](https://img.shields.io/badge/Coverage-100%25-success.svg)]()
  [![Stress Tested](https://img.shields.io/badge/Stress_Tested-20_Vectors-red.svg)]()
</div>

---

## 🚀 Overview

**GeoMeasure API** is an enterprise-ready microservice built to answer one question flawlessly: *Exactly how large is this geospatial feature on the real, curved Earth?*

Instead of relying on naive planar Euclidean geometry (which distorts wildly near the poles), GeoMeasure uses **true geodesic calculations on the WGS84 ellipsoid** (via the C-powered `pyproj` and `Shapely` engines) to deliver survey-accurate area, length, distance, bounding box, and centroid metrics. 

Upload a massive ZIP file of Shapefiles, a GPX track from a marathon, or a KML of a city grid. The API handles async chunking, topology auto-repair, multi-unit conversions, and CSV/JSON reporting—while staying fully protected against zip-bombs, memory leaks, and concurrent race conditions.

---

## ⚡ Core Features

- **🌐 True Geodesic Math**: Driven by `pyproj.Geod(ellps="WGS84")`. Calculates distance and area accurately across the Antimeridian and the Poles.
- **📂 Universal Format Support**: GeoJSON, KML (XXE-safe), KMZ, GPX, Shapefile (Zip), GeoPackage, CSV (WKT/LatLon), and GeoTIFF.
- **⚙️ Asynchronous Processing**: Processes massive 500MB+ vectors in background workers with real-time SQLite polling (`/measure/async`).
- **🛡️ Bulletproof Resilience**: Automatically repairs corrupt geometry (`repair_geometry=True`). Traps `TopologyExceptions` natively to prevent server crashes on broken real-world topologies (e.g., self-intersecting country borders).
- **🏗️ Polygon Extras**: Calculates convex hull area, hole counting, Polsby-Popper compactness, and minimum bounding rectangles.
- **🏃‍♂️ Track Analysis**: Extracts 3D tracks, total ascent/descent, and duration from GPX/KML routes.
- **🔒 Secure & Limited**: Configurable rate limiting (`slowapi`), X-API-Key auth, and dynamic origin CORS.

---

## 🛠️ Tech Stack

| Domain | Technology |
|---|---|
| **Web Framework** | FastAPI, Uvicorn, Pydantic v2 |
| **Geospatial Math** | Shapely 2.x, `pyproj`, `geopandas` |
| **File I/O Engine** | `pyogrio`, `rasterio`, `gpxpy`, `defusedxml` |
| **Database & ORM** | SQLAlchemy 2.0 (Async), `aiosqlite` |
| **Security/CI** | `slowapi`, Pytest, Ruff, Mypy, GitHub Actions |

---

## 🏁 Quick Start

### 🐳 Run with Docker (Recommended)
```bash
git clone https://github.com/iishanmakkar/GeoMeasure-API.git
cd GeoMeasure-API

# Copy environment config
cp .env.example .env

# Build and deploy the container
docker compose up --build -d
```
The API is now live at `http://localhost:8000`. 
Interactive Swagger Docs: **`http://localhost:8000/docs`**

### 💻 Run Locally
```bash
# Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Generate the binary test files
python tests/fixtures/generate_fixtures.py 

# Start the live-reload server
uvicorn app.main:app --reload
```

---

## 📖 API Endpoints

*All endpoints require the `X-API-Key: dev-key-12345` header by default.*

### 1. Synchronous File Measurement
Process files < 50MB instantly.
```bash
curl -X POST http://localhost:8000/api/v1/measure \
  -H "X-API-Key: dev-key-12345" \
  -F "file=@tests/fixtures/sample.geojson" \
  -F "method=geodesic" \
  -F "repair_geometry=true"
```

### 2. Asynchronous Large File Processing
Upload a massive file and get a Job UUID.
```bash
curl -X POST http://localhost:8000/api/v1/measure/async \
  -H "X-API-Key: dev-key-12345" \
  -F "file=@huge_map.zip"
# Response: {"job_id": "uuid-1234", "status": "pending"}

# Poll the job later:
curl -H "X-API-Key: dev-key-12345" http://localhost:8000/api/v1/jobs/uuid-1234
```

### 3. Point-to-Point Geodesic Distance
Accurate calculation over the curve of the Earth.
```bash
# Distance from Delhi to Mumbai
curl -X POST http://localhost:8000/api/v1/distance \
  -H "X-API-Key: dev-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"from": [77.2090, 28.6139], "to": [72.8777, 19.0760]}'

# Returns: {"distance_km": 1144.5, "initial_bearing_deg": 203.58, ...}
```

### 4. Export Job to CSV
```bash
curl -H "X-API-Key: dev-key-12345" http://localhost:8000/api/v1/report/uuid-1234.csv
```

---

## 🧪 Rigorous Stress & Edge Testing

GeoMeasure is built to survive extreme real-world corruption. We actively test against 20 aggressive edge-case vectors:

1. **Topology Failures**: Handled seamlessly. If a C-engine `TopologyException` occurs on a 15,000-point corrupt boundary, the feature is marked `valid: false` while the remaining 99% of the file processes flawlessly.
2. **Pole-to-Pole Distances**: Safely handles coordinates bounding exactly at `[0, 90]` and `[0, -90]`.
3. **100,000+ Vertex Polygons**: Stack-overflow protected geometry extraction.
4. **Anti-meridian Crossing**: Safely measures multi-polygons spanning the 180/-180 dateline.
5. **Zero-byte & Null Geometries**: Securely intercepted as `400 Bad Request` or handled as empty features instead of triggering `500 Internal Server Errors`.
6. **XXE Injection & Path Traversal**: `defusedxml` is used for KML, and strict `os.path.abspath` sanitization guards ZIP extractions.

---

## 📈 JSON Response Structure

```json
{
  "file": {
    "name": "sample.geojson",
    "format": "geojson",
    "size_bytes": 2048,
    "feature_count": 1,
    "processing_ms": 42.1
  },
  "summary": {
    "total_area": {"m2": 1.23e10, "km2": 12308, "ha": 1230800, "acres": 3041655},
    "bbox": {"minx": 77.0, "miny": 28.0, "maxx": 78.0, "maxy": 29.0, "width_m": 98430, "height_m": 111195},
    "centroid": {"lon": 77.5, "lat": 28.5},
    "invalid_features": 0
  },
  "features": [
    {
      "index": 0,
      "geometry_type": "Polygon",
      "valid": true,
      "vertex_count": 5,
      "area": {"km2": 12308.0},
      "perimeter": {"km": 440.2},
      "extras": {
        "num_holes": 0,
        "compactness": 0.857
      }
    }
  ]
}
```

---

## ⚖️ License
This project is open-sourced under the **MIT License**.

> **Note**: Accuracy of area and length metrics is directly dependent on the vector resolution of the uploaded geometry. GeoMeasure uses mathematically exact ellipsoids, meaning calculation errors are typically `< 0.01%`.
