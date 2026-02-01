"""API route definitions for the HomeOps MCP Server.

All ``/v1/`` endpoints require a valid ``X-API-Key`` header.  The
``/health`` endpoint is unauthenticated so that load-balancers and
monitoring tools can probe liveness without credentials.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from homeops_mcp import __version__
from homeops_mcp.adapters.docker_adapter import DockerAdapter
from homeops_mcp.adapters.emby_adapter import EmbyAdapter
from homeops_mcp.auth import require_admin_key
from homeops_mcp.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Adapter singletons (created once at import time)
# ---------------------------------------------------------------------------
_docker = DockerAdapter(socket_path=settings.DOCKER_SOCKET)
_emby = EmbyAdapter(base_url=settings.EMBY_URL, api_key=settings.EMBY_API_KEY)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ActionRequest(BaseModel):
    """Body schema for the action-execution endpoint.

    Attributes:
        action: Identifier of the action to execute.
        params: Arbitrary key-value parameters for the action.
    """

    action: str
    params: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Unauthenticated liveness probe.

    Returns:
        A JSON object with ``status`` and ``version`` fields.
    """
    return {"status": "ok", "version": __version__}


# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

@router.get("/v1/docker/containers", tags=["docker"])
async def list_containers(
    _key: str = Depends(require_admin_key),
) -> list[dict]:
    """List all running Docker containers.

    Requires a valid admin API key.

    Returns:
        A list of container info dicts with id, name, status, and image.
    """
    return await _docker.list_containers()


@router.get("/v1/docker/containers/{container_id}/stats", tags=["docker"])
async def container_stats(
    container_id: str,
    _key: str = Depends(require_admin_key),
) -> dict:
    """Return resource-usage statistics for a single container.

    Parameters:
        container_id: Short or full container ID.

    Returns:
        A dict with cpu_percent, memory_usage, and memory_limit.
    """
    return await _docker.container_stats(container_id)


# ---------------------------------------------------------------------------
# Emby
# ---------------------------------------------------------------------------

@router.get("/v1/emby/sessions", tags=["emby"])
async def emby_sessions(
    _key: str = Depends(require_admin_key),
) -> list[dict]:
    """List active Emby playback sessions.

    Requires a valid admin API key.

    Returns:
        A list of session dicts with user, device, and now_playing info.
    """
    return await _emby.get_active_sessions()


@router.get("/v1/emby/search", tags=["emby"])
async def emby_search(
    q: str = Query(..., description="Free-text search term"),
    _key: str = Depends(require_admin_key),
) -> list[dict]:
    """Search the Emby media library.

    Parameters:
        q: Free-text search query.

    Returns:
        A list of matching media items.
    """
    return await _emby.search_media(q)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

@router.post("/v1/actions/execute", tags=["actions"])
async def execute_action(
    body: ActionRequest,
    _key: str = Depends(require_admin_key),
) -> dict[str, str]:
    """Log an action request without executing it.

    This endpoint is intentionally *non-destructive*.  It records the
    requested action for auditing but **never** performs any state-changing
    operation.  Safety first.

    Parameters:
        body: The action request containing ``action`` and ``params``.

    Returns:
        A confirmation dict indicating the action was simulated.
    """
    await logger.ainfo(
        "action_requested",
        action=body.action,
        params=body.params,
    )
    return {
        "status": "simulated",
        "action": body.action,
        "message": "Action logged but not executed. Safety first.",
    }
