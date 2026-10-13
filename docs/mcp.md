# 🤖 Model Context Protocol (MCP) Server Integration

GeoMeasure API ships with an enterprise-grade **MCP Server** built on the official Model Context Protocol standard (`mcp>=1.0.0`).

This enables any AI coding assistant or autonomous LLM agent (**Claude Desktop, Cursor, Antigravity, Windsurf, LangChain**) to directly execute survey-accurate geospatial calculations, repair broken geometries, and analyze complex vector/raster datasets.

---

## ⚡ Quickstart: Launching the MCP Server

You can launch the GeoMeasure MCP server directly over standard input/output (`stdio`):

```bash
# Using installed console script
geomeasure-mcp

# Or directly with Python
python -m app.mcp_server
```

---

## 🛠️ Client Configuration Guides

### 1. Claude Desktop (`claude_desktop_config.json`)

On **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
On **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
On **Linux**: `~/.config/Claude/claude_desktop_config.json`

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

> **Tip (Virtualenv)**: Point `"command"` to your virtual environment Python binary (e.g., `"/path/to/GeoMeasure-API/.venv/bin/python"` or `"/path/to/.venv/Scripts/python.exe"`).

---

### 2. Cursor IDE (`.cursor/mcp.json`)

Create or edit `.cursor/mcp.json` in your project root or user config:

```json
{
  "mcpServers": {
    "geomeasure": {
      "command": "python",
      "args": ["-m", "app.mcp_server"]
    }
  }
}
```

---

### 3. Google Antigravity / Windsurf

Add to your MCP settings or workspace configuration:

```json
{
  "mcpServers": {
    "geomeasure": {
      "command": "python",
      "args": ["-m", "app.mcp_server"]
    }
  }
}
```

---

## 🧰 Available MCP Tools Reference

| Tool Name | Description | Key Arguments |
|---|---|---|
| `calculate_distance` | Survey-grade Great-Circle WGS84 geodesic distance and initial/final navigation azimuth bearings. | `from_lon`, `from_lat`, `to_lon`, `to_lat` |
| `measure_wkt` | Measure any Well-Known Text (WKT) geometry (Polygon, MultiPolygon, LineString, Point) with multi-unit areas and perimeters. | `wkt`, `method` ("geodesic"/"projected"), `repair_geometry_if_invalid` |
| `measure_geojson` | Measure an inline GeoJSON geometry, Feature, or FeatureCollection JSON string. | `geojson`, `method`, `repair_geometry_if_invalid` |
| `measure_file` | Read and measure any local geospatial file: `.geojson`, `.kml`, `.kmz`, `.gpx`, `.zip` (Shapefile), `.gpkg`, `.csv`, `.tif`. | `file_path`, `method`, `repair_geometry_if_invalid` |
| `repair_geometry` | Detect validity issues (e.g. self-intersections) and repair invalid geometries via Shapely 2.0 `make_valid`. | `wkt` |
| `analyze_gpx_track` | Extract 3D GPS track metrics: 2D flat distance, 3D slant distance, elevation gain (ascent), loss (descent), min/max altitude, speed. | `file_path` |
| `list_supported_formats` | List all 8 supported vector and raster formats and their constraints. | *(None)* |

---

## 💬 Example LLM Prompts

Once configured in Claude Desktop or Cursor, you can ask natural language geospatial questions:

- *"What is the exact geodesic distance and initial bearing from Tokyo Narita Airport to London Heathrow Airport?"*
- *"Measure the area and perimeter of this WKT polygon: `POLYGON((77.20 28.61, 77.25 28.61, 77.25 28.65, 77.20 28.65, 77.20 28.61))` in hectares and acres."*
- *"I have a workout file at `samples/data/sample.gpx`. Analyze my elevation gain, descent, and 3D distance."*
- *"This parcel polygon has self-intersecting boundaries: `POLYGON((0 0, 2 2, 2 0, 0 2, 0 0))`. Repair it and return the valid WKT."*
- *"Inspect and measure the features in my local shapefile: `samples/data/sample_shp.zip`."*
