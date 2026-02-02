"""Tests for the CrowdSecAdapter (mock mode, no live CrowdSec LAPI)."""

from __future__ import annotations

import pytest

from homeops_mcp.adapters.crowdsec_adapter import CrowdSecAdapter


@pytest.mark.asyncio
async def test_get_decisions_returns_list() -> None:
    """CrowdSecAdapter.get_decisions() should return mock decisions when
    CROWDSEC_URL is not configured.
    """
    adapter = CrowdSecAdapter(base_url=None, api_key=None)
    try:
        decisions = await adapter.get_decisions()

        assert isinstance(decisions, list)
        assert len(decisions) > 0

        for decision in decisions:
            assert "id" in decision
            assert "origin" in decision
            assert "type" in decision
            assert "scope" in decision
            assert "value" in decision
            assert "duration" in decision
            assert "scenario" in decision
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_get_bouncers_returns_list() -> None:
    """CrowdSecAdapter.get_bouncers() should return mock bouncers when
    CROWDSEC_URL is not configured.
    """
    adapter = CrowdSecAdapter(base_url=None, api_key=None)
    try:
        bouncers = await adapter.get_bouncers()

        assert isinstance(bouncers, list)
        assert len(bouncers) > 0

        for bouncer in bouncers:
            assert "name" in bouncer
            assert "ip_address" in bouncer
            assert "type" in bouncer
            assert "last_pull" in bouncer
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_get_alerts_returns_list() -> None:
    """CrowdSecAdapter.get_alerts() should return mock alerts when
    CROWDSEC_URL is not configured.
    """
    adapter = CrowdSecAdapter(base_url=None, api_key=None)
    try:
        alerts = await adapter.get_alerts()

        assert isinstance(alerts, list)
        assert len(alerts) > 0

        for alert in alerts:
            assert "scenario" in alert
            assert "source_ip" in alert
            assert "timestamp" in alert
    finally:
        await adapter.close()
