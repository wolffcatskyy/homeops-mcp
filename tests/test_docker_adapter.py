"""Tests for the DockerAdapter (mock mode)."""

from __future__ import annotations

import pytest

from homeops_mcp.adapters.docker_adapter import DockerAdapter


@pytest.mark.asyncio
async def test_list_containers_returns_list() -> None:
    """DockerAdapter.list_containers() should return a non-empty list."""
    adapter = DockerAdapter(socket_path="unix:///var/run/docker.sock")
    containers = await adapter.list_containers()

    assert isinstance(containers, list)
    assert len(containers) > 0

    # Each container should have the expected keys.
    for container in containers:
        assert "id" in container
        assert "name" in container
        assert "status" in container
        assert "image" in container


@pytest.mark.asyncio
async def test_container_stats_returns_expected_keys() -> None:
    """DockerAdapter.container_stats() should return a dict with resource metrics."""
    adapter = DockerAdapter(socket_path="unix:///var/run/docker.sock")
    stats = await adapter.container_stats("abc123")

    assert isinstance(stats, dict)
    assert "cpu_percent" in stats
    assert "memory_usage" in stats
    assert "memory_limit" in stats
    assert stats["container_id"] == "abc123"
