#!/usr/bin/env bash
cat > .env.example << 'EOF'
MCP_ADMIN_KEY=changeme-to-a-strong-random-key
LOG_LEVEL=INFO
# EMBY_URL=http://192.168.1.100:8096
# EMBY_API_KEY=your_emby_api_key
# DOCKER_SOCKET=unix:///var/run/docker.sock
EOF
echo ".env.example generated."
