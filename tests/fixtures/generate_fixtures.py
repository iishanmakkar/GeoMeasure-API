"""Script to generate binary test fixtures (Shapefile ZIP, GeoPackage, KMZ, GeoTIFF)."""

from __future__ import annotations

import io
import os
import struct
import zipfile
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures"
FIXTURES.mkdir(parents=True, exist_ok=True)


def create_kmz() -> None:
    """Create a KMZ file (zipped KML)."""
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>KMZ Test Point</name>
      <Point>
        <coordinates>77.2090,28.6139,216</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>"""
    kmz_path = FIXTURES / "sample.kmz"
    with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml_content)
    print(f"Created {kmz_path}")


def create_shapefile_zip() -> None:
    """Create a minimal Shapefile ZIP using geopandas."""
    import geopandas as gpd
    import tempfile
    from shapely.geometry import Polygon

    gdf = gpd.GeoDataFrame(
        {"name": ["Test Polygon", "Test Polygon 2"]},
        geometry=[
            Polygon([(77, 28), (78, 28), (78, 29), (77, 29), (77, 28)]),
            Polygon([(72, 19), (73, 19), (73, 20), (72, 20), (72, 19)]),
        ],
        crs="EPSG:4326",
    )

    tmp_dir = tempfile.mkdtemp()
    shp_path = os.path.join(tmp_dir, "sample.shp")
    gdf.to_file(shp_path, engine="pyogrio")

    zip_path = FIXTURES / "sample_shp.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for f in os.listdir(tmp_dir):
            zf.write(os.path.join(tmp_dir, f), f)

    import shutil
    shutil.rmtree(tmp_dir)
    print(f"Created {zip_path}")


def create_geopackage() -> None:
    """Create a minimal GeoPackage file."""
    import geopandas as gpd
    from shapely.geometry import Polygon

    gdf = gpd.GeoDataFrame(
        {"name": ["India Region"]},
        geometry=[Polygon([(68, 8), (97, 8), (97, 37), (68, 37), (68, 8)])],
        crs="EPSG:4326",
    )
    gpkg_path = FIXTURES / "sample.gpkg"
    gdf.to_file(str(gpkg_path), driver="GPKG", engine="pyogrio")
    print(f"Created {gpkg_path}")


def create_geotiff() -> None:
    """Create a minimal 10x10 GeoTIFF."""
    import numpy as np

    try:
        import rasterio
        from rasterio.transform import from_bounds

        tif_path = FIXTURES / "sample.tif"
        transform = from_bounds(77.0, 28.0, 78.0, 29.0, 10, 10)
        data = np.random.randint(0, 255, (1, 10, 10), dtype=np.uint8)

        with rasterio.open(
            str(tif_path),
            "w",
            driver="GTiff",
            height=10,
            width=10,
            count=1,
            dtype="uint8",
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(data)
        print(f"Created {tif_path}")
    except ImportError:
        print("rasterio not available, skipping GeoTIFF fixture")


if __name__ == "__main__":
    create_kmz()
    create_shapefile_zip()
    create_geopackage()
    create_geotiff()
    print("All fixtures created!")
