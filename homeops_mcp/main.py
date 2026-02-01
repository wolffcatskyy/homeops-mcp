"""Application entry-point for the HomeOps MCP Server.

Creates and configures the FastAPI application instance, sets up
structured logging, and attaches request-logging middleware.

Run with::

    uvicorn homeops_mcp.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI

from homeops_mcp import __version__
from homeops_mcp.api.routes import router
from homeops_mcp.config import settings
from homeops_mcp.logging_config import RequestLoggingMiddleware, setup_logging


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
