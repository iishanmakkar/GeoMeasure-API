## Examples: curl commands for every supported format

# ─── Health & Version ────────────────────────────────────────────────────────
curl http://localhost:8000/health
curl http://localhost:8000/version
curl http://localhost:8000/api/v1/formats

# ─── GeoJSON ─────────────────────────────────────────────────────────────────
curl -X POST http://localhost:8000/api/v1/measure \
  -F "file=@tests/fixtures/sample.geojson" \
  -F "method=geodesic" \
  -F "units=metric"

# ─── KML ──────────────────────────────────────────────────────────────────────
curl -X POST http://localhost:8000/api/v1/measure \
  -F "file=@tests/fixtures/sample.kml"

# ─── KMZ ──────────────────────────────────────────────────────────────────────
curl -X POST http://localhost:8000/api/v1/measure \
  -F "file=@tests/fixtures/sample.kmz"

# ─── GPX ──────────────────────────────────────────────────────────────────────
curl -X POST http://localhost:8000/api/v1/measure \
  -F "file=@tests/fixtures/sample.gpx"

# ─── Shapefile (ZIP) ──────────────────────────────────────────────────────────
curl -X POST http://localhost:8000/api/v1/measure \
  -F "file=@tests/fixtures/sample_shp.zip"

# ─── GeoPackage ───────────────────────────────────────────────────────────────
curl -X POST http://localhost:8000/api/v1/measure \
  -F "file=@tests/fixtures/sample.gpkg"

# ─── CSV ──────────────────────────────────────────────────────────────────────
curl -X POST http://localhost:8000/api/v1/measure \
  -F "file=@tests/fixtures/sample.csv"

# ─── GeoTIFF ──────────────────────────────────────────────────────────────────
curl -X POST http://localhost:8000/api/v1/measure \
  -F "file=@tests/fixtures/sample.tif"

# ─── Async large file ─────────────────────────────────────────────────────────
curl -X POST http://localhost:8000/api/v1/measure/async \
  -F "file=@large_dataset.geojson"
# returns {"job_id": "abc-123", "status": "pending"}

curl http://localhost:8000/api/v1/jobs/abc-123

# ─── Inline geometry (WKT) ───────────────────────────────────────────────────
curl -X POST http://localhost:8000/api/v1/measure/geometry \
  -H "Content-Type: application/json" \
  -d '{"wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))", "method": "geodesic"}'

# ─── Distance (Delhi → Mumbai) ───────────────────────────────────────────────
curl -X POST http://localhost:8000/api/v1/distance \
  -H "Content-Type: application/json" \
  -d '{"from": [77.2090, 28.6139], "to": [72.8777, 19.0760]}'

# ─── History ──────────────────────────────────────────────────────────────────
curl http://localhost:8000/api/v1/history?page=1&page_size=10
curl http://localhost:8000/api/v1/history/{id}
curl -X DELETE http://localhost:8000/api/v1/history/{id}

# ─── Export reports ───────────────────────────────────────────────────────────
curl http://localhost:8000/api/v1/report/{id}.csv -o report.csv
curl http://localhost:8000/api/v1/report/{id}.geojson -o report.geojson

# ─── With API key auth ────────────────────────────────────────────────────────
curl -X POST http://localhost:8000/api/v1/measure \
  -H "X-API-Key: dev-key-12345" \
  -F "file=@tests/fixtures/sample.geojson"
