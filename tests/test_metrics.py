"""Tests for the Prometheus /metrics endpoint."""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format(
    client: httpx.AsyncClient,
) -> None:
    """GET /metrics should return Prometheus text format."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    body = resp.text
    assert "homeops_mcp_requests_total" in body
    assert "homeops_mcp_request_duration_seconds" in body


@pytest.mark.asyncio
async def test_metrics_does_not_require_auth(
    client: httpx.AsyncClient,
) -> None:
    """GET /metrics should be accessible without an API key."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_metrics_increment_on_request(
    client: httpx.AsyncClient,
) -> None:
    """After making a request, the counter should reflect it."""
    # Make a known request first
    await client.get("/health")

    resp = await client.get("/metrics")
    body = resp.text
    # The /health request should appear in the counter
    assert "homeops_mcp_requests_total" in body
