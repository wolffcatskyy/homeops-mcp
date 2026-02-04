"""Adapter for the CrowdSec Local API (LAPI).

When ``base_url`` and ``api_key`` are provided the adapter makes real HTTP
calls to the CrowdSec LAPI.  If the connection details are absent it falls
back to realistic mock data so that development and testing can proceed
without a live CrowdSec instance.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import structlog

logger = structlog.get_logger(__name__)


class CrowdSecAdapter:
    """Async client for the CrowdSec Local API.

    Parameters:
        base_url: Root URL of the CrowdSec LAPI
                  (e.g. ``http://localhost:8080``).  Pass ``None``
                  to use mock data.
        api_key: CrowdSec bouncer API key for authentication.
    """

    def __init__(
        self, base_url: str | None, api_key: str | None
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=10.0)

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------

    async def get_decisions(self) -> list[dict]:
        """Retrieve active ban/captcha decisions from CrowdSec.

        Returns:
            A list of decision dicts with ``id``, ``origin``, ``type``,
            ``scope``, ``value``, ``duration``, and ``scenario`` keys.
        """
        if self.base_url and self.api_key:
            try:
                url = f"{self.base_url}/v1/decisions"
                resp = await self._client.get(
                    url,
                    headers={"X-Api-Key": self.api_key},
                )
                resp.raise_for_status()
                data = resp.json()
                return data if data else []
            except httpx.HTTPStatusError as exc:
                await logger.awarning(
                    "crowdsec_decisions_http_error",
                    status_code=exc.response.status_code,
                    detail=str(exc),
                )
            except httpx.RequestError as exc:
                await logger.awarning(
                    "crowdsec_decisions_request_error",
                    detail=str(exc),
                )

        return self._mock_decisions()

    # ------------------------------------------------------------------
    # Bouncers
    # ------------------------------------------------------------------

    async def get_bouncers(self) -> list[dict]:
        """Retrieve the list of registered bouncers.

        Returns:
            A list of bouncer dicts with ``name``, ``ip_address``,
            ``type``, and ``last_pull`` keys.
        """
        if self.base_url and self.api_key:
            try:
                url = f"{self.base_url}/v1/bouncers"
                resp = await self._client.get(
                    url,
                    headers={"X-Api-Key": self.api_key},
                )
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]
            except httpx.HTTPStatusError as exc:
                await logger.awarning(
                    "crowdsec_bouncers_http_error",
                    status_code=exc.response.status_code,
                    detail=str(exc),
                )
            except httpx.RequestError as exc:
                await logger.awarning(
                    "crowdsec_bouncers_request_error",
                    detail=str(exc),
                )

        return self._mock_bouncers()

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    async def get_alerts(self, since_hours: int = 24) -> list[dict]:
        """Retrieve recent alerts from CrowdSec.

        Parameters:
            since_hours: Number of hours to look back for alerts.

        Returns:
            A list of alert dicts with ``scenario``, ``source_ip``,
            and ``timestamp`` keys.
        """
        if self.base_url and self.api_key:
            try:
                since = datetime.now(timezone.utc) - timedelta(
                    hours=since_hours
                )
                url = f"{self.base_url}/v1/alerts"
                resp = await self._client.get(
                    url,
                    headers={"X-Api-Key": self.api_key},
                    params={"since": since.isoformat()},
                )
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]
            except httpx.HTTPStatusError as exc:
                await logger.awarning(
                    "crowdsec_alerts_http_error",
                    status_code=exc.response.status_code,
                    detail=str(exc),
                )
            except httpx.RequestError as exc:
                await logger.awarning(
                    "crowdsec_alerts_request_error",
                    detail=str(exc),
                )

        return self._mock_alerts()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client and release resources."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Mock helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mock_decisions() -> list[dict]:
        """Return realistic mock decision data for development."""
        return [
            {
                "id": 1,
                "origin": "crowdsec",
                "type": "ban",
                "scope": "Ip",
                "value": "203.0.113.42",
                "duration": "3h59m",
                "scenario": "crowdsecurity/ssh-bf",
            },
            {
                "id": 2,
                "origin": "crowdsec",
                "type": "ban",
                "scope": "Ip",
                "value": "198.51.100.17",
                "duration": "1h12m",
                "scenario": "crowdsecurity/http-probing",
            },
        ]

    @staticmethod
    def _mock_bouncers() -> list[dict]:
        """Return realistic mock bouncer data for development."""
        return [
            {
                "name": "cs-firewall-bouncer",
                "ip_address": "127.0.0.1",
                "type": "firewall",
                "last_pull": "2025-12-01T10:30:00Z",
            },
            {
                "name": "cs-nginx-bouncer",
                "ip_address": "127.0.0.1",
                "type": "nginx",
                "last_pull": "2025-12-01T10:28:00Z",
            },
        ]

    @staticmethod
    def _mock_alerts() -> list[dict]:
        """Return realistic mock alert data for development."""
        return [
            {
                "scenario": "crowdsecurity/ssh-bf",
                "source_ip": "203.0.113.42",
                "timestamp": "2025-12-01T09:15:00Z",
            },
            {
                "scenario": "crowdsecurity/http-probing",
                "source_ip": "198.51.100.17",
                "timestamp": "2025-12-01T08:42:00Z",
            },
            {
                "scenario": "crowdsecurity/http-bad-user-agent",
                "source_ip": "192.0.2.88",
                "timestamp": "2025-12-01T07:30:00Z",
            },
        ]
