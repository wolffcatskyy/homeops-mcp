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
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel
from starlette.responses import Response as StarletteResponse

from homeops_mcp import __version__
from homeops_mcp.adapters.crowdsec_adapter import CrowdSecAdapter
from homeops_mcp.adapters.docker_adapter import DockerAdapter
from homeops_mcp.adapters.emby_adapter import EmbyAdapter
from homeops_mcp.adapters.network_adapter import NetworkAdapter
from homeops_mcp.auth import require_admin_key
from homeops_mcp.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Adapter singletons (created once at import time)
# ---------------------------------------------------------------------------
_crowdsec = CrowdSecAdapter(
    base_url=settings.CROWDSEC_URL,
    api_key=settings.CROWDSEC_API_KEY,
)
_docker = DockerAdapter(socket_path=settings.DOCKER_SOCKET)
_emby = EmbyAdapter(base_url=settings.EMBY_URL, api_key=settings.EMBY_API_KEY)
_network = NetworkAdapter(mock_mode=False)


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
# Prometheus metrics
# ---------------------------------------------------------------------------

@router.get("/metrics", tags=["monitoring"])
async def prometheus_metrics() -> StarletteResponse:
    """Prometheus metrics endpoint.

    Unauthenticated so that Prometheus can scrape without an API key.

    Returns:
        Metrics in Prometheus text exposition format.
    """
    return StarletteResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


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

    Probes Docker, Emby, CrowdSec, and any future adapters.  Returns
    per-service status with latency and an overall health summary.

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

    # --- CrowdSec check ---
    if settings.CROWDSEC_URL:
        checks["crowdsec"] = await _check_adapter(
            name="crowdsec",
            probe=_crowdsec.get_decisions,
            timeout=timeout_seconds,
        )
    else:
        checks["crowdsec"] = {"status": "unconfigured"}

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
# CrowdSec
# ---------------------------------------------------------------------------

@router.get("/v1/crowdsec/decisions", tags=["crowdsec"])
async def crowdsec_decisions(
    _key: str = Depends(require_admin_key),
) -> list[dict]:
    """List active CrowdSec ban/captcha decisions.

    Requires a valid admin API key.

    Returns:
        A list of decision dicts with id, type, scope, value, and scenario.
    """
    return await _crowdsec.get_decisions()


@router.get("/v1/crowdsec/bouncers", tags=["crowdsec"])
async def crowdsec_bouncers(
    _key: str = Depends(require_admin_key),
) -> list[dict]:
    """List registered CrowdSec bouncers and their last heartbeat.

    Requires a valid admin API key.

    Returns:
        A list of bouncer dicts with name, ip_address, type, and last_pull.
    """
    return await _crowdsec.get_bouncers()


@router.get("/v1/crowdsec/alerts", tags=["crowdsec"])
async def crowdsec_alerts(
    since_hours: int = Query(24, ge=1, description="Hours to look back"),
    _key: str = Depends(require_admin_key),
) -> list[dict]:
    """List recent CrowdSec alerts.

    Parameters:
        since_hours: Number of hours to look back (default 24).

    Returns:
        A list of alert dicts with scenario, source_ip, and timestamp.
    """
    return await _crowdsec.get_alerts(since_hours=since_hours)


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

@router.get("/v1/network/ping", tags=["network"])
async def network_ping(
    host: str = Query(..., description="Host to ping"),
    count: int = Query(4, ge=1, le=20, description="Number of packets"),
    _key: str = Depends(require_admin_key),
) -> dict:
    """Ping a host and return latency statistics.

    Parameters:
        host: Hostname or IP address to ping.
        count: Number of packets to send (1--20).

    Returns:
        A dict with latency stats and packet loss information.
    """
    return await _network.ping(host, count)


@router.get("/v1/network/dns", tags=["network"])
async def network_dns(
    hostname: str = Query(..., description="Hostname to resolve"),
    record_type: str = Query("A", description="DNS record type"),
    _key: str = Depends(require_admin_key),
) -> dict:
    """Resolve a hostname to IP addresses.

    Parameters:
        hostname: The hostname to look up.
        record_type: DNS record type (e.g. A, AAAA).

    Returns:
        A dict with hostname, record_type, and resolved addresses.
    """
    return await _network.dns_lookup(hostname, record_type)


@router.get("/v1/network/traceroute", tags=["network"])
async def network_traceroute(
    host: str = Query(..., description="Host to trace"),
    max_hops: int = Query(
        20, ge=1, le=64, description="Maximum number of hops"
    ),
    _key: str = Depends(require_admin_key),
) -> dict:
    """Trace the network route to a host.

    Parameters:
        host: Hostname or IP address to trace.
        max_hops: Maximum number of hops (1--64).

    Returns:
        A dict with hop-by-hop routing information.
    """
    return await _network.traceroute(host, max_hops)


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
