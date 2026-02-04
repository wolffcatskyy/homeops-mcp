"""Tests for the MCP server tool registration and execution."""

from __future__ import annotations

import json
import os

import pytest

# Ensure the admin key is set before any app import.
os.environ.setdefault("MCP_ADMIN_KEY", "test-key")

from homeops_mcp.mcp_server import mcp  # noqa: E402


def _get_text(result: object) -> str:
    """Extract the text content from a call_tool result.

    The FastMCP call_tool may return either:
    - A sequence of ContentBlock objects (each with a .text attribute)
    - A tuple of (content_list, structured_dict) when structured output is detected
    """
    # If it's a tuple, the first element is the content list
    if isinstance(result, tuple):
        content_list = result[0]
    else:
        content_list = result
    # content_list is a list of ContentBlock; get the first one's text
    first = content_list[0]
    return first.text


@pytest.mark.asyncio
async def test_mcp_server_has_tools() -> None:
    """The MCP server should have all expected tools registered."""
    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}

    expected = {
        "docker_list_containers",
        "docker_restart_container",
        "docker_get_logs",
        "docker_get_stats",
        "emby_get_sessions",
        "emby_search_library",
        "emby_scan_library",
    }
    assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"


@pytest.mark.asyncio
async def test_docker_list_containers_tool() -> None:
    """docker_list_containers tool should return valid JSON with containers."""
    result = await mcp.call_tool("docker_list_containers", {})
    text = _get_text(result)
    data = json.loads(text)
    assert isinstance(data, list)
    assert len(data) > 0
    assert "name" in data[0]
    assert "status" in data[0]


@pytest.mark.asyncio
async def test_docker_restart_container_tool() -> None:
    """docker_restart_container tool should return a restart confirmation."""
    result = await mcp.call_tool(
        "docker_restart_container",
        {"container_name": "crowdsec"},
    )
    text = _get_text(result)
    data = json.loads(text)
    assert data["container_name"] == "crowdsec"
    assert data["status"] == "restarted"


@pytest.mark.asyncio
async def test_docker_get_logs_tool() -> None:
    """docker_get_logs tool should return log lines."""
    result = await mcp.call_tool(
        "docker_get_logs",
        {"container_name": "emby", "tail": 3},
    )
    text = _get_text(result)
    data = json.loads(text)
    assert data["container_name"] == "emby"
    assert isinstance(data["logs"], list)
    assert len(data["logs"]) <= 3


@pytest.mark.asyncio
async def test_docker_get_stats_tool() -> None:
    """docker_get_stats tool should return stats for all containers."""
    result = await mcp.call_tool("docker_get_stats", {})
    text = _get_text(result)
    data = json.loads(text)
    assert isinstance(data, list)
    assert len(data) > 0
    assert "cpu_percent" in data[0]
    assert "name" in data[0]


@pytest.mark.asyncio
async def test_emby_get_sessions_tool() -> None:
    """emby_get_sessions tool should return session data."""
    result = await mcp.call_tool("emby_get_sessions", {})
    text = _get_text(result)
    data = json.loads(text)
    assert isinstance(data, list)
    assert len(data) > 0
    assert "user" in data[0]


@pytest.mark.asyncio
async def test_emby_search_library_tool() -> None:
    """emby_search_library tool should return search results."""
    result = await mcp.call_tool(
        "emby_search_library",
        {"query": "interstellar"},
    )
    text = _get_text(result)
    data = json.loads(text)
    assert isinstance(data, list)
    assert len(data) > 0
    assert "name" in data[0]


@pytest.mark.asyncio
async def test_emby_scan_library_tool() -> None:
    """emby_scan_library tool should return scan status."""
    result = await mcp.call_tool("emby_scan_library", {})
    text = _get_text(result)
    data = json.loads(text)
    assert data["status"] == "started"
