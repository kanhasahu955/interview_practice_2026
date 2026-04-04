#!/usr/bin/env bash
# Bring up Postgres + API + nginx (local full stack). Same as: make docker-local
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/deploy/local/docker.env"
cd "$ROOT"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found; install Docker Desktop or Docker Engine." >&2
  exit 1
fi

set -a
# shellcheck source=deploy/local/docker.env
source "$ENV_FILE"
set +a

docker compose -f docker-compose.yml up --build -d

echo ""
echo "  Local Docker: http://127.0.0.1:${NGINX_HTTP_PORT:-8080}"
echo "  Logs: make docker-local-logs   Stop: ./scripts/docker-local-down.sh"
echo "  Docs: docs/RUNBOOK.md"
echo ""
