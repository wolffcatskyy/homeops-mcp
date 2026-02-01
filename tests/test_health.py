"""Tests for the /health endpoint."""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client: httpx.AsyncClient) -> None:
    """GET /health should return 200 with status 'ok'."""
    response = await client.get("/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
