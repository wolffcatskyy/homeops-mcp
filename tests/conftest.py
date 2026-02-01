"""Shared pytest fixtures for the HomeOps MCP test suite."""

from __future__ import annotations

import os
from typing import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

# Set the admin key *before* importing the app so that the Settings
# instance picks up the test value from the environment.
os.environ["MCP_ADMIN_KEY"] = "test-key"

from homeops_mcp.main import app as _app  # noqa: E402


@pytest.fixture()
def app() -> FastAPI:
    """Return the FastAPI application instance for testing."""
    return _app


@pytest_asyncio.fixture()
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Yield an async HTTP client wired to the ASGI app.

    Uses ``httpx.ASGITransport`` so that requests are handled in-process
    without starting a real server.
    """
    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as ac:
        yield ac
