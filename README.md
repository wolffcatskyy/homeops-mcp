# HomeOps MCP Server

![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![CI](https://img.shields.io/github/actions/workflow/status/wolffcatskyy/homeops-mcp/ci.yml?branch=main&label=CI)

A Model Context Protocol (MCP) server for home infrastructure management. Provides a unified API for Docker, Emby, and future Servarr/UniFi/CrowdSec integrations.

**Built by [wolffcatskyy](https://github.com/wolffcatskyy) and [Claude](https://claude.ai).**

---

## Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| **Phase 0** | Skeleton -- project structure, CI, Docker build, health endpoint | Done |
| **Phase 1** | Docker + Emby adapters, API-key auth middleware, full CI pipeline | Planned |
| **Phase 2** | Servarr (Sonarr/Radarr/Prowlarr), WordPress, Synology, UniFi, CrowdSec adapters | Planned |
| **Phase 3** | UI dashboard, audit logs, secrets management (Vault/SOPS), production hardening | Planned |

---

## Quick Start

### Option A -- Docker Compose (recommended)

```bash
cp .env.example .env
# Edit .env with your real values
docker compose up -d
```

The server will be available at `http://localhost:8000`.

### Option B -- Run locally

```bash
# Requires Python 3.11+ and Poetry
poetry install
bash scripts/run_local.sh
```

---

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and edit as needed.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MCP_ADMIN_KEY` | Yes | `changeme-to-a-strong-random-key` | API key for admin endpoints |
| `LOG_LEVEL` | No | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `EMBY_URL` | No | *(mock data)* | Emby server URL, e.g. `http://192.168.1.100:8096` |
| `EMBY_API_KEY` | No | *(mock data)* | Emby API key for authentication |
| `DOCKER_SOCKET` | No | `unix:///var/run/docker.sock` | Path to Docker socket |

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | No | Health check -- returns `{"status": "ok"}` |
| `GET` | `/v1/docker/containers` | API Key | List Docker containers |
| `GET` | `/v1/docker/containers/{id}/stats` | API Key | Container resource stats |
| `GET` | `/v1/emby/sessions` | API Key | List active Emby sessions |
| `GET` | `/v1/emby/search?q=term` | API Key | Search Emby library |
| `POST` | `/v1/actions/execute` | API Key | Log action (non-destructive) |

All authenticated endpoints require the `X-API-Key` header set to the value of `MCP_ADMIN_KEY`.

---

## Security

- **Never commit real API keys or secrets.** The `.env` file is git-ignored.
- Only placeholder values appear in `.env.example`.
- The Docker socket is mounted read-only in `docker-compose.yml`.
- The container runs as a non-root user (`appuser`).
- All adapter API keys are loaded from environment variables at startup and are never logged.

---

## Architecture

HomeOps MCP uses an **adapter pattern** to integrate with external services:

```
Client Request
      |
      v
  FastAPI Router
      |
      v
  Auth Middleware  (validates X-API-Key)
      |
      v
  Adapter Layer
      |
      +---> DockerAdapter    --> Docker Engine API (socket)
      +---> EmbyAdapter      --> Emby REST API
      +---> ServarrAdapter   --> Sonarr / Radarr / Prowlarr APIs  (Phase 2)
      +---> UniFiAdapter     --> UniFi Controller API              (Phase 2)
      +---> CrowdSecAdapter  --> CrowdSec LAPI                    (Phase 2)
```

Each adapter:

1. Lives in `homeops_mcp/adapters/<name>_adapter.py`
2. Implements a common interface (`BaseAdapter`)
3. Returns mock/demo data when the upstream service is not configured
4. Has its own unit tests in `tests/`

---

## Development

```bash
# Install all dependencies (including dev)
poetry install

# Run linter
poetry run ruff check .

# Run tests
poetry run pytest -v

# Build Docker image
docker build -t homeops-mcp .
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT -- see [LICENSE](LICENSE).
