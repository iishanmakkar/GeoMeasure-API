"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Import routers
from app.api.v1 import distance, history, jobs, measure, meta, reports
from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import RequestIDMiddleware, configure_logging
from app.core.rate_limit import limiter
from app.models.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle events."""
    configure_logging()
    await init_db()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    description=(
        "Production-quality REST API for geospatial measurements.\n\n"
        "## Features\n"
        "* **Geodesic accuracy**: Powered by `pyproj.Geod` over the WGS84 ellipsoid.\n"
        "* **Multi-format support**: GeoJSON, KML, KMZ, GPX, Shapefile, GeoPackage, CSV, and GeoTIFF.\n"
        "* **Async jobs**: Process gigabyte-scale files safely in the background.\n"
        "* **Security**: XXE protection, zip-bomb prevention, and path traversal guards built-in.\n"
    ),
    contact={
        "name": "Ishan Makkar",
        "email": "ishanmakkar651@gmail.com",
        "url": "https://github.com/iishanmakkar/GeoMeasure-API",
    },
    license_info={
        "name": "MIT License",
        "identifier": "MIT",
    },
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# State for slowapi
app.state.limiter = limiter

# Middleware (order matters — outermost first)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)

# Exception handlers
register_exception_handlers(app)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

# Routers
API_PREFIX = "/api/v1"
app.include_router(meta.router)
app.include_router(meta.router, prefix=API_PREFIX, include_in_schema=False)
app.include_router(measure.router, prefix=API_PREFIX)
app.include_router(jobs.router, prefix=API_PREFIX)
app.include_router(distance.router, prefix=API_PREFIX)
app.include_router(history.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
