"""Prometheus metrics definitions for the HomeOps MCP Server.

Defines counters, histograms, and gauges that are incremented by the
request-logging middleware and can be scraped via the ``/metrics``
endpoint.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter(
    "homeops_mcp_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_DURATION = Histogram(
    "homeops_mcp_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(
        0.01, 0.025, 0.05, 0.1, 0.25,
        0.5, 1.0, 2.5, 5.0, 10.0,
    ),
)

ADAPTER_UP = Gauge(
    "homeops_mcp_adapter_up",
    "Whether an adapter is reachable (1=up, 0=down)",
    ["adapter_name"],
)
