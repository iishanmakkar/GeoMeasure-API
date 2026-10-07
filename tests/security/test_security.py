"""Security tests: zip bombs, XXE, path traversal, oversized files, auth."""

from __future__ import annotations

import io
import zipfile

from fastapi.testclient import TestClient


class TestZipSecurity:
    """Tests for archive safety checks."""

    def test_path_traversal_zip_rejected(self, client: TestClient) -> None:
        """Upload a ZIP containing a path traversal entry."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            info = zipfile.ZipInfo("../../etc/passwd.shp")
            zf.writestr(info, b"fake shapefile content")
        buf.seek(0)

        resp = client.post(
            "/api/v1/measure",
            files={"file": ("malicious.zip", buf, "application/zip")},
        )
        assert resp.status_code in (400, 422), f"Expected 400/422, got {resp.status_code}"

    def test_too_many_files_in_zip_rejected(self, client: TestClient) -> None:
        """Upload a ZIP with more than MAX_ARCHIVE_FILES entries."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for i in range(200):  # Well above limit of 100
                zf.writestr(f"file_{i}.txt", b"content")
        buf.seek(0)

        resp = client.post(
            "/api/v1/measure",
            files={"file": ("bomb.zip", buf, "application/zip")},
        )
        assert resp.status_code in (400, 413, 422)

    def test_unsupported_format_rejected(self, client: TestClient) -> None:
        """Upload an executable — should be rejected with 415."""
        buf = io.BytesIO(b"MZ\x90\x00" + b"\x00" * 100)  # PE header
        resp = client.post(
            "/api/v1/measure",
            files={"file": ("malware.exe", buf, "application/octet-stream")},
        )
        assert resp.status_code == 415


class TestXXEPrevention:
    """Tests for XML External Entity injection prevention."""

    def test_xxe_in_kml_rejected(self, client: TestClient) -> None:
        """Upload a KML with an XXE payload — should not trigger file read."""
        xxe_kml = b"""<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>&xxe;</name>
      <Point><coordinates>0,0,0</coordinates></Point>
    </Placemark>
  </Document>
</kml>"""
        buf = io.BytesIO(xxe_kml)
        resp = client.post(
            "/api/v1/measure",
            files={"file": ("xxe.kml", buf, "application/vnd.google-earth.kml+xml")},
        )
        # Should return 400 (defusedxml blocks it) or 200 with name as literal text
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            # Ensure passwd content is NOT in the response
            assert "/root:" not in resp.text
            assert "nobody:" not in resp.text


class TestFileSizeLimits:
    """Tests for upload size enforcement."""

    def test_oversized_sync_file_rejected(self, client: TestClient) -> None:
        """Simulate a file larger than MAX_SYNC_SIZE_MB."""
        # We override the limit in config for testing — use a small fake file
        # that exceeds the limit we report
        # Actually send the Content-Length header claim
        large_content = b'{"type": "FeatureCollection", "features": []}' + b"x" * (51 * 1024 * 1024)
        buf = io.BytesIO(large_content)
        resp = client.post(
            "/api/v1/measure",
            files={"file": ("huge.geojson", buf, "application/geo+json")},
        )
        assert resp.status_code == 413


class TestErrorFormat:
    """Tests for consistent error response format."""

    def test_404_has_error_field(self, client: TestClient) -> None:
        resp = client.get("/api/v1/jobs/nonexistent-job-id")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]

    def test_422_validation_error_format(self, client: TestClient) -> None:
        resp = client.post("/api/v1/distance", json={"from": [0], "to": [0, 0]})
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
