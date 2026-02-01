"""Adapter for interacting with the Docker daemon.

Provides an async interface to query container state and resource
usage.  The current implementation returns mock data; see the TODO
comments for guidance on wiring up the real Docker socket.
"""

from __future__ import annotations


class DockerAdapter:
    """High-level async client for Docker container operations.

    Parameters:
        socket_path: Path to the Docker daemon socket
                     (e.g. ``unix:///var/run/docker.sock``).
    """

    def __init__(self, socket_path: str) -> None:
        self.socket_path = socket_path

    async def list_containers(self) -> list[dict]:
        """Return a list of running containers.

        Each entry is a dict with ``id``, ``name``, ``status``, and
        ``image`` keys.

        Returns:
            A list of container info dictionaries.
        """
        # TODO: Replace mock data with real Docker socket implementation.
        #       Use an async HTTP client against the Docker Engine API
        #       (e.g. GET /containers/json over the unix socket).
        return [
            {
                "id": "abc123def456",
                "name": "crowdsec",
                "status": "running",
                "image": "crowdsecurity/crowdsec:latest",
            },
            {
                "id": "789ghi012jkl",
                "name": "emby",
                "status": "running",
                "image": "emby/embyserver:4.8.10",
            },
            {
                "id": "345mno678pqr",
                "name": "qbittorrent",
                "status": "running",
                "image": "linuxserver/qbittorrent:latest",
            },
        ]

    async def container_stats(self, container_id: str) -> dict:
        """Return resource usage statistics for a single container.

        Parameters:
            container_id: The short or full ID of the container.

        Returns:
            A dict with ``cpu_percent``, ``memory_usage`` (bytes), and
            ``memory_limit`` (bytes).
        """
        # TODO: Replace mock data with real Docker socket implementation.
        #       Use GET /containers/{id}/stats?stream=false and parse the
        #       response to compute CPU and memory metrics.
        return {
            "container_id": container_id,
            "cpu_percent": 2.35,
            "memory_usage": 268_435_456,   # ~256 MiB
            "memory_limit": 2_147_483_648,  # 2 GiB
        }
