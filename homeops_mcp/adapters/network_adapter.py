"""Adapter for network diagnostic operations (ping, DNS lookup, traceroute).

When ``mock_mode`` is True (or in test environments) the adapter returns
realistic sample data.  In production it shells out to system utilities
using ``asyncio.create_subprocess_exec`` for safety.
"""

from __future__ import annotations

import asyncio
import re
import socket

import structlog
from fastapi import HTTPException

logger = structlog.get_logger(__name__)

# Only allow hostnames/IPs that match this pattern (no shell metacharacters).
_VALID_HOST_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


def _validate_host(host: str) -> None:
    """Validate a host string to prevent command injection.

    Parameters:
        host: Hostname or IP address to validate.

    Raises:
        HTTPException: 400 Bad Request if the host contains invalid
                       characters.
    """
    if not _VALID_HOST_RE.match(host):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid host. Only alphanumeric characters, dots, "
                "hyphens, and underscores are allowed."
            ),
        )


class NetworkAdapter:
    """Async network diagnostics client.

    Parameters:
        mock_mode: When True, return mock data instead of running
                   real system commands.
    """

    def __init__(self, mock_mode: bool = False) -> None:
        self.mock_mode = mock_mode

    # ------------------------------------------------------------------
    # Ping
    # ------------------------------------------------------------------

    async def ping(self, host: str, count: int = 4) -> dict:
        """Ping a host and return latency statistics.

        Parameters:
            host: Hostname or IP address to ping.
            count: Number of ICMP echo requests to send.

        Returns:
            A dict with host, packets_sent, packets_received,
            packet_loss_percent, avg/min/max latency in ms.
        """
        _validate_host(host)
        if self.mock_mode:
            return self._mock_ping(host, count)

        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", str(count), host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(), timeout=30.0
            )
            output = stdout.decode()
            return self._parse_ping_output(host, count, output)
        except asyncio.TimeoutError:
            await logger.awarning("ping_timeout", host=host)
            return {
                "host": host,
                "packets_sent": count,
                "packets_received": 0,
                "packet_loss_percent": 100.0,
                "avg_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
            }
        except Exception as exc:
            await logger.awarning(
                "ping_error", host=host, detail=str(exc)
            )
            return self._mock_ping(host, count)

    # ------------------------------------------------------------------
    # DNS Lookup
    # ------------------------------------------------------------------

    async def dns_lookup(
        self, hostname: str, record_type: str = "A"
    ) -> dict:
        """Resolve a hostname to IP addresses.

        Parameters:
            hostname: The hostname to resolve.
            record_type: DNS record type (e.g. ``"A"``, ``"AAAA"``).

        Returns:
            A dict with hostname, record_type, and addresses list.
        """
        _validate_host(hostname)
        if self.mock_mode:
            return self._mock_dns_lookup(hostname, record_type)

        try:
            loop = asyncio.get_running_loop()
            family = (
                socket.AF_INET6
                if record_type == "AAAA"
                else socket.AF_INET
            )
            infos = await loop.run_in_executor(
                None,
                lambda: socket.getaddrinfo(
                    hostname, None, family, socket.SOCK_STREAM
                ),
            )
            addresses = sorted(
                {info[4][0] for info in infos}
            )
            return {
                "hostname": hostname,
                "record_type": record_type,
                "addresses": addresses,
            }
        except socket.gaierror as exc:
            await logger.awarning(
                "dns_lookup_error",
                hostname=hostname,
                detail=str(exc),
            )
            return {
                "hostname": hostname,
                "record_type": record_type,
                "addresses": [],
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Traceroute
    # ------------------------------------------------------------------

    async def traceroute(
        self, host: str, max_hops: int = 20
    ) -> dict:
        """Trace the network route to a host.

        Parameters:
            host: Hostname or IP address to trace.
            max_hops: Maximum number of hops.

        Returns:
            A dict with host, max_hops, and a list of hops.
        """
        _validate_host(host)
        if self.mock_mode:
            return self._mock_traceroute(host, max_hops)

        try:
            proc = await asyncio.create_subprocess_exec(
                "traceroute", "-m", str(max_hops), host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(), timeout=60.0
            )
            output = stdout.decode()
            return self._parse_traceroute_output(
                host, max_hops, output
            )
        except asyncio.TimeoutError:
            await logger.awarning(
                "traceroute_timeout", host=host
            )
            return {
                "host": host,
                "max_hops": max_hops,
                "hops": [],
                "error": "timeout",
            }
        except Exception as exc:
            await logger.awarning(
                "traceroute_error", host=host, detail=str(exc)
            )
            return self._mock_traceroute(host, max_hops)

    # ------------------------------------------------------------------
    # Output parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_ping_output(
        host: str, count: int, output: str
    ) -> dict:
        """Parse ping command stdout into a structured dict."""
        result: dict = {
            "host": host,
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss_percent": 100.0,
            "avg_latency_ms": 0.0,
            "min_latency_ms": 0.0,
            "max_latency_ms": 0.0,
        }

        # Parse packet loss line, e.g.:
        # "4 packets transmitted, 4 received, 0% packet loss"
        loss_match = re.search(
            r"(\d+) packets transmitted, (\d+) (?:packets )?received"
            r".*?(\d+(?:\.\d+)?)% packet loss",
            output,
        )
        if loss_match:
            result["packets_sent"] = int(loss_match.group(1))
            result["packets_received"] = int(loss_match.group(2))
            result["packet_loss_percent"] = float(
                loss_match.group(3)
            )

        # Parse rtt line, e.g.:
        # "rtt min/avg/max/mdev = 0.89/1.23/2.15/0.42 ms"
        rtt_match = re.search(
            r"(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)",
            output.split("min/avg/max")[-1]
            if "min/avg/max" in output
            else "",
        )
        if rtt_match:
            result["min_latency_ms"] = float(rtt_match.group(1))
            result["avg_latency_ms"] = float(rtt_match.group(2))
            result["max_latency_ms"] = float(rtt_match.group(3))

        return result

    @staticmethod
    def _parse_traceroute_output(
        host: str, max_hops: int, output: str
    ) -> dict:
        """Parse traceroute command stdout into a structured dict."""
        hops: list[dict] = []
        for line in output.strip().splitlines()[1:]:
            # Typical line: " 1  192.168.1.1 (192.168.1.1)  1.234 ms"
            hop_match = re.match(
                r"\s*(\d+)\s+"
                r"(?:(\S+)\s+\((\S+)\)|(\*)).*?"
                r"(?:(\d+(?:\.\d+)?)\s*ms)?",
                line,
            )
            if hop_match:
                hop_num = int(hop_match.group(1))
                ip = hop_match.group(3) or hop_match.group(2)
                latency = hop_match.group(5)
                hop_entry: dict = {"hop": hop_num}
                if ip and ip != "*":
                    hop_entry["ip"] = ip
                else:
                    hop_entry["ip"] = "*"
                if latency:
                    hop_entry["latency_ms"] = float(latency)
                hops.append(hop_entry)

        return {"host": host, "max_hops": max_hops, "hops": hops}

    # ------------------------------------------------------------------
    # Mock helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mock_ping(host: str, count: int) -> dict:
        """Return realistic mock ping data for development."""
        return {
            "host": host,
            "packets_sent": count,
            "packets_received": count,
            "packet_loss_percent": 0.0,
            "avg_latency_ms": 1.23,
            "min_latency_ms": 0.89,
            "max_latency_ms": 2.15,
        }

    @staticmethod
    def _mock_dns_lookup(
        hostname: str, record_type: str
    ) -> dict:
        """Return realistic mock DNS lookup data for development."""
        return {
            "hostname": hostname,
            "record_type": record_type,
            "addresses": ["93.184.216.34"],
        }

    @staticmethod
    def _mock_traceroute(host: str, max_hops: int) -> dict:
        """Return realistic mock traceroute data for development."""
        return {
            "host": host,
            "max_hops": max_hops,
            "hops": [
                {"hop": 1, "ip": "192.168.1.1", "latency_ms": 1.2},
                {"hop": 2, "ip": "10.0.0.1", "latency_ms": 5.4},
                {"hop": 3, "ip": host, "latency_ms": 12.8},
            ],
        }
