"""Tests for the EmbyAdapter (mock mode, no live Emby server)."""

from __future__ import annotations

import pytest

from homeops_mcp.adapters.emby_adapter import EmbyAdapter


@pytest.mark.asyncio
async def test_get_active_sessions_returns_list() -> None:
    """EmbyAdapter.get_active_sessions() should return mock sessions when
    EMBY_URL is not configured.
    """
    adapter = EmbyAdapter(base_url=None, api_key=None)
    try:
        sessions = await adapter.get_active_sessions()

        assert isinstance(sessions, list)
        assert len(sessions) > 0

        # Each session should have basic keys.
        for session in sessions:
            assert "user" in session
            assert "device" in session
            assert "now_playing" in session
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_search_media_returns_results() -> None:
    """EmbyAdapter.search_media() should return mock results when
    EMBY_URL is not configured.
    """
    adapter = EmbyAdapter(base_url=None, api_key=None)
    try:
        results = await adapter.search_media("interstellar")

        assert isinstance(results, list)
        assert len(results) > 0

        for item in results:
            assert "name" in item
            assert "type" in item
    finally:
        await adapter.close()
