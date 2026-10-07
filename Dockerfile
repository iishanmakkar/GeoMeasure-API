FROM python:3.12-slim

# Install system GDAL/GEOS/PROJ dependencies for geopandas, rasterio, pyproj
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    gdal-bin \
    libgeos-dev \
    libproj-dev \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy pyproject.toml first for layer caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

# Copy application code
COPY app/ ./app/
COPY tests/ ./tests/
COPY samples/ ./samples/

# Create temp dir for uploads
RUN mkdir -p /tmp/geomeasure && chmod 777 /tmp/geomeasure

# Non-root user for security
RUN useradd -m -u 1000 geomeasure && chown -R geomeasure:geomeasure /app
USER geomeasure

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
