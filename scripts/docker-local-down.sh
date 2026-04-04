#!/usr/bin/env bash
# Stop local full stack. Same as: make docker-local-down
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found." >&2
  exit 1
fi

docker compose -f docker-compose.yml down
