"""MCP Server module using the official MCP Python SDK.

Registers tools for Docker and Emby operations using FastMCP.
Tools route to adapter stubs that return mock data for now.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from homeops_mcp.adapters.docker_adapter import DockerAdapter
from homeops_mcp.adapters.emby_adapter import EmbyAdapter
from homeops_mcp.config import settings

# ---------------------------------------------------------------------------
# Create the FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("homeops-mcp")

# ---------------------------------------------------------------------------
# Adapter singletons
# ---------------------------------------------------------------------------

_docker = DockerAdapter(socket_path=settings.DOCKER_SOCKET)
_emby = EmbyAdapter(base_url=settings.EMBY_URL, api_key=settings.EMBY_API_KEY)


# ---------------------------------------------------------------------------
# Docker tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def docker_list_containers() -> str:
    """List Docker containers with their status.

    Returns a JSON array of container objects, each containing
    id, name, status, and image fields.
    """
    containers = await _docker.list_containers()
    return json.dumps(containers, indent=2)


@mcp.tool()
async def docker_restart_container(container_name: str) -> str:
    """Restart a Docker container by name.

    Args:
        container_name: The name of the container to restart.
    """
    result = await _docker.restart_container(container_name)
    return json.dumps(result, indent=2)


@mcp.tool()
async def docker_get_logs(container_name: str, tail: int = 50) -> str:
    """Get recent logs from a Docker container.

    Args:
        container_name: The name of the container to get logs from.
        tail: Number of log lines to retrieve (default: 50).
    """
    result = await _docker.get_logs(container_name, tail=tail)
    return json.dumps(result, indent=2)


@mcp.tool()
async def docker_get_stats() -> str:
    """Get resource usage statistics for all running containers.

    Returns a JSON array of container stats including CPU and memory usage.
    """
    containers = await _docker.list_containers()
    stats = []
    for container in containers:
        stat = await _docker.container_stats(container["id"])
        stat["name"] = container["name"]
        stats.append(stat)
    return json.dumps(stats, indent=2)


# ---------------------------------------------------------------------------
# Emby tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def emby_get_sessions() -> str:
    """List active Emby playback sessions.

    Returns a JSON array of session objects with user, device,
    and now_playing information.
    """
    sessions = await _emby.get_active_sessions()
    return json.dumps(sessions, indent=2)


@mcp.tool()
async def emby_search_library(query: str) -> str:
    """Search the Emby media library.

    Args:
        query: Free-text search term to find media items.
    """
    results = await _emby.search_media(query)
    return json.dumps(results, indent=2)


@mcp.tool()
async def emby_scan_library() -> str:
    """Trigger a library scan on the Emby media server.

    Initiates a refresh of all Emby libraries.
    """
    result = await _emby.scan_library()
    return json.dumps(result, indent=2)
