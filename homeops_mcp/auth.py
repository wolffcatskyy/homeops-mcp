"""Authentication dependencies for the FastAPI application.

Provides an API-key based authentication scheme that validates incoming
requests against the configured MCP_ADMIN_KEY.  The key must be sent in
the ``X-API-Key`` HTTP header.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from homeops_mcp.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_admin_key(
    api_key: str | None = Security(_api_key_header),
) -> str:
    """Validate the X-API-Key header against the configured admin key.

    Parameters:
        api_key: The value extracted from the ``X-API-Key`` header.

    Returns:
        The validated API key string.

    Raises:
        HTTPException: 403 Forbidden if the key is missing or does not match.
    """
    if api_key is None or api_key != settings.MCP_ADMIN_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key.",
        )
    return api_key
