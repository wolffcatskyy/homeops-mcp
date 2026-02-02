"""API route definitions for the HomeOps MCP Server.

All ``/v1/`` endpoints require a valid ``X-API-Key`` header.  The
``/health`` endpoint is unauthenticated so that load-balancers and
monitoring tools can probe liveness without credentials.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable

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
# Service health dashboard
# ---------------------------------------------------------------------------

async def _check_adapter(
    name: str,
    probe: Callable[..., Any],
    timeout: float,
) -> dict:
    """Probe a single adapter and return its status.

    Parameters:
        name: Human-readable service name (for logging).
        probe: An async callable that exercises the adapter.
        timeout: Maximum seconds to wait.

    Returns:
        A dict with ``status`` (``up`` or ``down``) and ``latency_ms``.
    """
    start = time.perf_counter()
    try:
        await asyncio.wait_for(probe(), timeout=timeout)
        latency_ms = round(
            (time.perf_counter() - start) * 1000, 2
        )
        return {"status": "up", "latency_ms": latency_ms}
    except asyncio.TimeoutError:
        await logger.awarning(
            "health_check_timeout", service=name
        )
        return {"status": "down", "error": "timeout"}
    except Exception as exc:
        await logger.awarning(
            "health_check_failed",
            service=name,
            error=str(exc),
        )
        latency_ms = round(
            (time.perf_counter() - start) * 1000, 2
        )
        return {
            "status": "down",
            "latency_ms": latency_ms,
            "error": str(exc),
        }


@router.get("/v1/status", tags=["health"])
async def service_status(
    _key: str = Depends(require_admin_key),
) -> dict:
    """Aggregated health check across all configured adapters.

    Probes Docker, Emby, and any future adapters.  Returns per-service
    status with latency and an overall health summary.

    Returns:
        A dict with overall status, timestamp, version, and per-service
        health information.
    """
    from datetime import datetime, timezone

    checks: dict[str, dict] = {}
    timeout_seconds = 5.0

    # --- Docker check ---
    checks["docker"] = await _check_adapter(
        name="docker",
        probe=_docker.list_containers,
        timeout=timeout_seconds,
    )

    # --- Emby check ---
    if settings.EMBY_URL:
        checks["emby"] = await _check_adapter(
            name="emby",
            probe=_emby.get_active_sessions,
            timeout=timeout_seconds,
        )
    else:
        checks["emby"] = {"status": "unconfigured"}

    # --- Determine overall status ---
    statuses = [c["status"] for c in checks.values()]
    if all(s in ("up", "unconfigured") for s in statuses):
        overall = "healthy"
    elif any(s == "up" for s in statuses):
        overall = "degraded"
    else:
        overall = "unhealthy"

    return {
        "overall": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
        "services": checks,
    }


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
