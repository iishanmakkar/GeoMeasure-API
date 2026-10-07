# GeoMeasure API

A **production-quality REST API** for accurate geospatial measurements. Upload GeoJSON, KML, KMZ, GPX, Shapefile, GeoPackage, CSV, or GeoTIFF files and receive geodetically accurate area, length, distance, centroid, bounding box, and more.

[![CI](https://github.com/iishanmakkar/GeoMeasure-API/actions/workflows/ci.yml/badge.svg)](https://github.com/iishanmakkar/GeoMeasure-API/actions)

---

## Architecture

```
Client → FastAPI (RequestID · CORS · RateLimit · Auth)
           ├── POST /measure          → format_detectors → file_loader → CRS → measurements (geodesic.py)
           ├── POST /measure/async    → background job → SQLite (Jobs table)
           ├── GET  /jobs/{id}        → SQLite poll
           ├── POST /measure/geometry → inline WKT/GeoJSON
           ├── POST /distance         → pyproj.Geod.inv
           ├── GET  /history          → SQLite (History table)
           └── GET  /report/{id}.csv  → exporter.py
```

**Key libraries:** FastAPI · pyproj (Geod WGS84) · Shapely 2 · GeoPandas · pyogrio · gpxpy · rasterio · defusedxml · SQLAlchemy 2.0 async · slowapi

---

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/iishanmakkar/GeoMeasure-API.git
cd GeoMeasure-API
cp .env.example .env
docker compose up --build
# API is now at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Local (Python 3.12+)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python tests/fixtures/generate_fixtures.py   # Create binary test fixtures
uvicorn app.main:app --reload
```

---

## API Endpoints

All endpoints are under `/api/v1` prefix.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/measure` | Upload & measure file (sync, ≤50 MB) |
| `POST` | `/measure/async` | Upload & measure file (async, ≤500 MB) |
| `GET` | `/jobs/{job_id}` | Poll async job status |
| `POST` | `/measure/geometry` | Measure inline GeoJSON or WKT |
| `POST` | `/distance` | Geodesic distance + bearings |
| `GET` | `/history` | Paginated history list |
| `GET` | `/history/{id}` | Full past report |
| `DELETE` | `/history/{id}` | Delete history entry |
| `GET` | `/report/{id}.csv` | Export report as CSV |
| `GET` | `/report/{id}.geojson` | Export report as GeoJSON |
| `GET` | `/formats` | List supported formats |
| `GET` | `/health` | Health check |
| `GET` | `/version` | API version |

### Supported Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| GeoJSON | `.geojson`, `.json` | RFC 7946 |
| KML | `.kml` | defusedxml parser — XXE-safe |
| KMZ | `.kmz` | ZIP-safe extraction |
| GPX | `.gpx` | Tracks + elevation + speed |
| Shapefile | `.zip` | Must contain .shp/.shx/.dbf |
| GeoPackage | `.gpkg` | Multi-layer (first layer used) |
| CSV | `.csv` | Auto-detect lat/lon or WKT column |
| GeoTIFF | `.tif`, `.tiff` | Bounding box + pixel area |

---

## Example curl Commands

```bash
# Health check
curl http://localhost:8000/health

# Measure a GeoJSON file
curl -X POST http://localhost:8000/api/v1/measure \
  -F "file=@tests/fixtures/sample.geojson" \
  -F "method=geodesic"

# Measure a GPX track (with elevation)
curl -X POST http://localhost:8000/api/v1/measure \
  -F "file=@tests/fixtures/sample.gpx"

# Measure inline WKT polygon
curl -X POST http://localhost:8000/api/v1/measure/geometry \
  -H "Content-Type: application/json" \
  -d '{"wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"}'

# Delhi → Mumbai geodesic distance
curl -X POST http://localhost:8000/api/v1/distance \
  -H "Content-Type: application/json" \
  -d '{"from": [77.2090, 28.6139], "to": [72.8777, 19.0760]}'
# Returns: {"distance_km": 1150.4, "initial_bearing_deg": 220.7, ...}

# Async large file
curl -X POST http://localhost:8000/api/v1/measure/async \
  -F "file=@large.geojson"
# {"job_id": "abc-123", "status": "pending"}
curl http://localhost:8000/api/v1/jobs/abc-123
```

---

## Python Client Example

```python
import httpx

API = "http://localhost:8000/api/v1"
HEADERS = {"X-API-Key": "dev-key-12345"}  # from .env

# Upload and measure
with open("my_area.geojson", "rb") as f:
    r = httpx.post(f"{API}/measure", files={"file": f}, headers=HEADERS)

report = r.json()
print(f"Total area: {report['summary']['total_area']['km2']:.2f} km²")
print(f"Features: {report['file']['feature_count']}")

# Point-to-point distance
r = httpx.post(f"{API}/distance",
               json={"from": [77.209, 28.614], "to": [72.877, 19.076]},
               headers=HEADERS)
print(f"Distance: {r.json()['distance_km']:.1f} km")
```

---

## Accuracy Notes

### Geodesic vs Projected

| Method | When to use | Error |
|--------|-------------|-------|
| **Geodesic** (default) | Any geometry on WGS84 | < 0.01% (ellipsoid-exact) |
| **Projected** (UTM) | Local features < 500 km | < 0.05% within zone |
| **Projected** (Equal-area) | Continental scale | < 0.1% |

The API **always uses `pyproj.Geod(ellps="WGS84")`** by default — this is the IERS-standard WGS84 ellipsoid and is correct for any region on Earth without needing to choose a projection.

### Known Values (test assertions)

- 1°×1° box at the equator → **~12,308 km²** (exact geodesic) vs 12,392 km² naive planar
- Delhi → Mumbai → **~1,150 km** (verified against Google Maps, Vincenty)
- 1° of longitude at the equator → **111.32 km**

---

## Configuration (.env)

```env
APP_ENV=production
MAX_SYNC_SIZE_MB=50
MAX_ASYNC_SIZE_MB=500
MAX_FEATURES=10000
DATABASE_URL=sqlite+aiosqlite:///./geomeasure.db
API_KEYS=your-secret-key-here
RATE_LIMIT=100/minute
ALLOWED_ORIGINS=https://yourdomain.com
LOG_FORMAT=json
```

---

## Development

```bash
# Install dev extras
pip install -e ".[dev]"

# Generate test fixtures
python tests/fixtures/generate_fixtures.py

# Run all tests
pytest tests/ -v --cov=app --cov-report=term-missing

# Run specific phases
pytest tests/unit/test_geodesic.py        # Phase 2: engine
pytest tests/unit/test_file_loader.py     # Phase 3: loaders
pytest tests/integration/test_measure.py  # Phase 4: API
pytest tests/security/test_security.py   # Phase 7: security

# Lint
ruff check app/ tests/
ruff format app/ tests/

# Type check
mypy app/ --ignore-missing-imports
```

---

## Response Shape

```json
{
  "file": {
    "name": "sample.geojson",
    "format": "geojson",
    "size_bytes": 2048,
    "crs": "EPSG:4326",
    "crs_assumed": false,
    "feature_count": 2,
    "processing_ms": 42.1
  },
  "summary": {
    "total_area": {"m2": 1.23e10, "km2": 12308, "ha": 1230800, "acres": 3041655, "ft2": 1.32e11, "mi2": 4752},
    "total_length": null,
    "bbox": {"minx": 77.0, "miny": 28.0, "maxx": 78.0, "maxy": 29.0, "width_m": 98430, "height_m": 111195},
    "centroid": {"lon": 77.5, "lat": 28.5},
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
      "area": {"km2": 12308.0, ...},
      "perimeter": {"km": 440.2, ...},
      "centroid": {"lon": 77.5, "lat": 28.5},
      "extras": {
        "num_holes": 0,
        "compactness": 0.857,
        "convex_hull_area_m2": 1.23e10
      },
      "properties": {"name": "Test Polygon"}
    }
  ],
  "warnings": [],
  "method": "geodesic"
}
```

---

## License

MIT
