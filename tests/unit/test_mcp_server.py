"""Unit tests for the GeoMeasure Model Context Protocol (MCP) server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from mcp.types import CallToolResult

from app.mcp_server import server
from tests.conftest import fixture_path

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _extract_tool_result(res: Any) -> Any:
    """Validate CallToolResult and extract payload dictionary."""
    assert isinstance(res, CallToolResult)
    assert not res.is_error
    if res.structured_content:
        return res.structured_content
    if res.content and len(res.content) > 0 and hasattr(res.content[0], "text"):
        return json.loads(res.content[0].text)
    return {}


@pytest.mark.asyncio
async def test_mcp_tools_registration() -> None:
    """Verify that all core geospatial tools are registered on the MCP server."""
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]

    expected = [
        "calculate_distance",
        "measure_wkt",
        "measure_geojson",
        "measure_file",
        "repair_geometry",
        "analyze_gpx_track",
        "list_supported_formats",
    ]
    for name in expected:
        assert name in tool_names, f"Tool '{name}' missing from MCP server"


@pytest.mark.asyncio
async def test_mcp_calculate_distance() -> None:
    """Test Great-Circle distance calculation via MCP tool."""
    res = await server.call_tool(
        "calculate_distance",
        {"from_lon": 77.2090, "from_lat": 28.6139, "to_lon": 72.8777, "to_lat": 19.0760},
    )
    data: dict[str, Any] = _extract_tool_result(res)
    assert 1100.0 <= data.get("distance_km", 0.0) <= 1200.0
    assert 200.0 <= data.get("initial_bearing_deg", 0.0) <= 210.0


@pytest.mark.asyncio
async def test_mcp_measure_wkt() -> None:
    """Test inline WKT polygon measurement via MCP tool."""
    wkt = "POLYGON((77.2090 28.6139, 77.2290 28.6139, 77.2290 28.6339, 77.2090 28.6339, 77.2090 28.6139))"
    res = await server.call_tool(
        "measure_wkt",
        {"wkt": wkt, "method": "geodesic"},
    )
    data: dict[str, Any] = _extract_tool_result(res)
    assert data["summary"]["total_area"]["km2"] > 0
    assert len(data["features"]) == 1
    assert data["features"][0]["geometry_type"] == "Polygon"


@pytest.mark.asyncio
async def test_mcp_measure_geojson() -> None:
    """Test inline GeoJSON measurement via MCP tool."""
    geojson_dict = {
        "type": "Feature",
        "properties": {"name": "Test Box"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        },
    }
    res = await server.call_tool(
        "measure_geojson",
        {"geojson": geojson_dict, "method": "geodesic"},
    )
    data: dict[str, Any] = _extract_tool_result(res)
    assert data["features"][0]["area"]["km2"] > 0


@pytest.mark.asyncio
async def test_mcp_measure_file() -> None:
    """Test local geospatial file measurement via MCP tool."""
    path = str(fixture_path("sample.geojson"))
    res = await server.call_tool(
        "measure_file",
        {"file_path": path, "method": "geodesic"},
    )
    data: dict[str, Any] = _extract_tool_result(res)
    assert data["file"]["format"] == "geojson"
    assert data["file"]["feature_count"] == 2


@pytest.mark.asyncio
async def test_mcp_repair_geometry() -> None:
    """Test self-intersecting bowtie polygon repair via MCP tool."""
    bowtie_wkt = "POLYGON((0 0, 2 2, 2 0, 0 2, 0 0))"
    res = await server.call_tool("repair_geometry", {"wkt": bowtie_wkt})
    data: dict[str, Any] = _extract_tool_result(res)
    assert data["valid"] is True
    assert data["was_repaired"] is True
    assert "repaired_wkt" in data


@pytest.mark.asyncio
async def test_mcp_analyze_gpx() -> None:
    """Test GPX track 3D elevation profile analysis via MCP tool."""
    path = str(fixture_path("sample.gpx"))
    res = await server.call_tool("analyze_gpx_track", {"file_path": path})
    data: dict[str, Any] = _extract_tool_result(res)
    assert data["length_2d_m"] > 0
    assert data["length_3d_m"] >= data["length_2d_m"]


@pytest.mark.asyncio
async def test_mcp_list_supported_formats() -> None:
    """Test format discovery via MCP tool."""
    res = await server.call_tool("list_supported_formats", {})
    data = _extract_tool_result(res)
    if isinstance(data, dict) and "result" in data:
        data = data["result"]

    format_names = [f["name"] for f in data]
    assert "GeoJSON" in format_names
    assert "GPX" in format_names
    assert "Shapefile" in format_names
