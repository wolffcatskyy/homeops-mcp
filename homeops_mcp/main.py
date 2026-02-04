"""Application entry-point for the HomeOps MCP Server.

Creates and configures the FastAPI application instance, sets up
structured logging, attaches request-logging middleware, and mounts
the MCP SSE server alongside the FastAPI routes.

Run modes::

    # HTTP + SSE (FastAPI + MCP SSE transport)
    uvicorn homeops_mcp.main:app --host 0.0.0.0 --port 8000

    # STDIO (for Claude Code / local MCP clients)
    python -m homeops_mcp.main --stdio
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI

from homeops_mcp import __version__
from homeops_mcp.api.routes import router
from homeops_mcp.config import settings
from homeops_mcp.logging_config import RequestLoggingMiddleware, setup_logging
from homeops_mcp.mcp_server import mcp


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler -- runs once on startup and shutdown.

    On startup the structured logging subsystem is initialised at the
    configured log level.
    """
    setup_logging(log_level=settings.LOG_LEVEL)
    logger = structlog.get_logger("homeops_mcp.startup")
    await logger.ainfo(
        "server_starting",
        version=__version__,
        log_level=settings.LOG_LEVEL,
    )
    yield
    await logger.ainfo("server_shutting_down")


app = FastAPI(
    title="HomeOps MCP Server",
    description=(
        "Unified API for home infrastructure management. "
        "Provides Docker container visibility, Emby media-server "
        "integration, and a safe action-execution framework."
    ),
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.include_router(router)

# ---------------------------------------------------------------------------
# Mount MCP SSE transport alongside FastAPI
# ---------------------------------------------------------------------------
# The MCP SSE app handles /sse and /messages paths for remote MCP clients.
# API key auth for SSE is handled via the X-API-Key header check in the
# SSE handler middleware below.

_sse_app = mcp.sse_app()
app.mount("/mcp", _sse_app)


# ---------------------------------------------------------------------------
# STDIO entry-point
# ---------------------------------------------------------------------------


def _run_stdio() -> None:
    """Run the MCP server over STDIO transport (unauthenticated).

    Used by Claude Code and other local MCP clients.
    """
    mcp.run(transport="stdio")


if __name__ == "__main__":
    if "--stdio" in sys.argv:
        _run_stdio()
    else:
        import uvicorn

        uvicorn.run(
            "homeops_mcp.main:app",
            host="0.0.0.0",
            port=8000,
            log_level="info",
        )
