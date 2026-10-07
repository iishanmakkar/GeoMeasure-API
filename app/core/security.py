"""API key authentication and dependency."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.config import get_settings


async def verify_api_key(x_api_key: str | None = Header(default=None)) -> str | None:
    """Verify the X-API-Key header.

    Returns the key if valid, or None if no keys are configured (open dev mode).
    Raises 401 if keys are configured but the provided key is invalid.
    """
    settings = get_settings()
    valid_keys = settings.api_keys_set

    # If no keys configured, auth is disabled
    if not valid_keys:
        return None

    if x_api_key is None or x_api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Provide a valid X-API-Key header.",
        )
    return x_api_key
