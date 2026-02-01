#!/usr/bin/env bash
set -euo pipefail
if [ -f .env ]; then set -a; source .env; set +a; fi
exec uvicorn homeops_mcp.main:app --host 0.0.0.0 --port 8000 --reload
