"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Point to a test SQLite DB
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_geomeasure.db")
os.environ.setdefault("API_KEYS", "")  # Disable auth for tests

from app.main import app

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Synchronous test client."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest_asyncio.fixture
async def async_client() -> AsyncClient:
    """Async test client for async endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def fixture_path(name: str) -> Path:
    """Return the absolute path to a test fixture file."""
    return FIXTURES_DIR / name
