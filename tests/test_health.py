"""Tests for the /health and /v1/status endpoints."""

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


@pytest.mark.asyncio
async def test_service_status_returns_aggregated_health(
    client: httpx.AsyncClient,
) -> None:
    """GET /v1/status should return overall status and per-service checks."""
    resp = await client.get(
        "/v1/status",
        headers={"X-API-Key": "test-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "overall" in data
    assert data["overall"] in ("healthy", "degraded", "unhealthy")
    assert "services" in data
    assert "docker" in data["services"]
    assert "emby" in data["services"]
    assert "timestamp" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_service_status_requires_auth(
    client: httpx.AsyncClient,
) -> None:
    """GET /v1/status should return 403 without an API key."""
    resp = await client.get("/v1/status")
    assert resp.status_code == 403
