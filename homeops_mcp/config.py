"""Application configuration via environment variables and .env file.

Uses pydantic-settings to load configuration from environment variables
with optional fallback to a .env file. All settings can be overridden
by setting the corresponding environment variable.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the HomeOps MCP Server.

    Attributes:
        MCP_ADMIN_KEY: Shared secret used to authenticate API requests.
        EMBY_URL: Base URL of the Emby Media Server (e.g. http://nas:8096).
        EMBY_API_KEY: API key for authenticating with the Emby server.
        DOCKER_SOCKET: Path to the Docker daemon socket.
        LOG_LEVEL: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    MCP_ADMIN_KEY: str = "changeme"
    EMBY_URL: str | None = None
    EMBY_API_KEY: str | None = None
    CROWDSEC_URL: str | None = None
    CROWDSEC_API_KEY: str | None = None
    DOCKER_SOCKET: str = "unix:///var/run/docker.sock"
    LOG_LEVEL: str = "INFO"


settings = Settings()
