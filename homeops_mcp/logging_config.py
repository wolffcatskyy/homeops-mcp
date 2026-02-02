"""Structured logging configuration using *structlog*.

Provides ``setup_logging`` to initialise structlog with JSON output and a
lightweight ASGI middleware class that logs every HTTP request with method,
path, status code, and duration.
"""

from __future__ import annotations

import time
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structlog with JSON rendering.

    Parameters:
        log_level: Minimum log level to emit (e.g. ``"DEBUG"``, ``"INFO"``).
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.get_level_from_name(log_level),
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that emits a structured log line for every request.

    Each log entry contains:
    - ``method``: HTTP method (GET, POST, ...)
    - ``path``: Request path
    - ``status_code``: Response status code
    - ``duration_ms``: Round-trip time in milliseconds
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process a request and log its outcome.

        Parameters:
            request: The incoming HTTP request.
            call_next: Callable to pass the request to the next middleware / route.

        Returns:
            The HTTP response produced by the application.
        """
        logger = structlog.get_logger("homeops_mcp.access")
        start = time.perf_counter()

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        await logger.ainfo(
            "request_handled",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        # Record Prometheus metrics (additive, does not replace logging).
        from homeops_mcp.metrics import REQUEST_COUNT, REQUEST_DURATION

        endpoint = request.url.path
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=str(response.status_code),
        ).inc()
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration_ms / 1000.0)

        return response
