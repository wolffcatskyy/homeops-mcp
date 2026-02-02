"""Tests for the NetworkAdapter (mock mode, no real system commands)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from homeops_mcp.adapters.network_adapter import NetworkAdapter


@pytest.mark.asyncio
async def test_ping_returns_expected_keys() -> None:
    """NetworkAdapter.ping() should return a dict with latency stats."""
    adapter = NetworkAdapter(mock_mode=True)
    result = await adapter.ping("192.168.1.1")

    assert result["host"] == "192.168.1.1"
    assert "avg_latency_ms" in result
    assert "min_latency_ms" in result
    assert "max_latency_ms" in result
    assert "packet_loss_percent" in result
    assert result["packets_sent"] == 4
    assert result["packets_received"] == 4


@pytest.mark.asyncio
async def test_ping_custom_count() -> None:
    """NetworkAdapter.ping() should respect the count parameter."""
    adapter = NetworkAdapter(mock_mode=True)
    result = await adapter.ping("10.0.0.1", count=8)

    assert result["packets_sent"] == 8
    assert result["packets_received"] == 8


@pytest.mark.asyncio
async def test_dns_lookup_returns_expected_keys() -> None:
    """NetworkAdapter.dns_lookup() should return hostname and addresses."""
    adapter = NetworkAdapter(mock_mode=True)
    result = await adapter.dns_lookup("example.com")

    assert result["hostname"] == "example.com"
    assert result["record_type"] == "A"
    assert isinstance(result["addresses"], list)
    assert len(result["addresses"]) > 0


@pytest.mark.asyncio
async def test_dns_lookup_custom_record_type() -> None:
    """NetworkAdapter.dns_lookup() should pass the record_type through."""
    adapter = NetworkAdapter(mock_mode=True)
    result = await adapter.dns_lookup("example.com", record_type="AAAA")

    assert result["record_type"] == "AAAA"


@pytest.mark.asyncio
async def test_traceroute_returns_expected_keys() -> None:
    """NetworkAdapter.traceroute() should return hops list."""
    adapter = NetworkAdapter(mock_mode=True)
    result = await adapter.traceroute("1.1.1.1")

    assert result["host"] == "1.1.1.1"
    assert result["max_hops"] == 20
    assert isinstance(result["hops"], list)
    assert len(result["hops"]) > 0

    for hop in result["hops"]:
        assert "hop" in hop
        assert "ip" in hop
        assert "latency_ms" in hop


@pytest.mark.asyncio
async def test_host_validation_rejects_shell_metacharacters() -> None:
    """NetworkAdapter should reject hosts with shell metacharacters."""
    adapter = NetworkAdapter(mock_mode=True)

    with pytest.raises(HTTPException) as exc_info:
        await adapter.ping("192.168.1.1; rm -rf /")
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        await adapter.dns_lookup("example.com | cat /etc/passwd")
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        await adapter.traceroute("$(whoami)")
    assert exc_info.value.status_code == 400
