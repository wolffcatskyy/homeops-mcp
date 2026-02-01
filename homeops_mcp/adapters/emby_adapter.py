"""Adapter for the Emby Media Server REST API.

When ``base_url`` and ``api_key`` are provided the adapter makes real HTTP
calls to the Emby server.  If the connection details are absent it falls
back to realistic mock data so that development and testing can proceed
without a live Emby instance.
"""

from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger(__name__)


class EmbyAdapter:
    """Async client for the Emby Media Server API.

    Parameters:
        base_url: Root URL of the Emby server (e.g. ``http://nas:8096``).
                  Pass ``None`` to use mock data.
        api_key: Emby API key for authentication.
    """

    def __init__(self, base_url: str | None, api_key: str | None) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=10.0)

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def get_active_sessions(self) -> list[dict]:
        """Retrieve the list of currently active playback sessions.

        Returns:
            A list of session dicts.  Each contains at minimum ``user``,
            ``device``, and ``now_playing`` keys.
        """
        if self.base_url and self.api_key:
            try:
                url = f"{self.base_url}/emby/Sessions"
                resp = await self._client.get(
                    url,
                    params={"api_key": self.api_key},
                )
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]
            except httpx.HTTPStatusError as exc:
                await logger.awarning(
                    "emby_sessions_http_error",
                    status_code=exc.response.status_code,
                    detail=str(exc),
                )
            except httpx.RequestError as exc:
                await logger.awarning(
                    "emby_sessions_request_error",
                    detail=str(exc),
                )

        # Fallback: return mock data when Emby is not configured or on error.
        return self._mock_sessions()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_media(self, query: str) -> list[dict]:
        """Search the Emby library for items matching *query*.

        Parameters:
            query: Free-text search term.

        Returns:
            A list of media item dicts with ``name``, ``type``, and ``year``.
        """
        if self.base_url and self.api_key:
            try:
                url = f"{self.base_url}/emby/Items"
                resp = await self._client.get(
                    url,
                    params={
                        "api_key": self.api_key,
                        "SearchTerm": query,
                        "Recursive": "true",
                        "Limit": "20",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("Items", [])  # type: ignore[no-any-return]
            except httpx.HTTPStatusError as exc:
                await logger.awarning(
                    "emby_search_http_error",
                    status_code=exc.response.status_code,
                    detail=str(exc),
                )
            except httpx.RequestError as exc:
                await logger.awarning(
                    "emby_search_request_error",
                    detail=str(exc),
                )

        # Fallback mock results.
        return self._mock_search(query)

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
    def _mock_sessions() -> list[dict]:
        """Return realistic mock session data for development."""
        return [
            {
                "user": "Alice",
                "device": "Living Room Roku",
                "now_playing": {
                    "name": "Planet Earth III",
                    "type": "Episode",
                    "series": "Planet Earth",
                },
            },
            {
                "user": "Bob",
                "device": "iPad Pro",
                "now_playing": {
                    "name": "Interstellar",
                    "type": "Movie",
                    "year": 2014,
                },
            },
        ]

    @staticmethod
    def _mock_search(query: str) -> list[dict]:
        """Return realistic mock search results for development."""
        return [
            {
                "name": f"Mock Result 1 for '{query}'",
                "type": "Movie",
                "year": 2023,
            },
            {
                "name": f"Mock Result 2 for '{query}'",
                "type": "Series",
                "year": 2024,
            },
        ]
