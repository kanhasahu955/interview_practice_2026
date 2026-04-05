#!/usr/bin/env bash
# Start Docker Postgres, then run the API with reload wired to that DB (same as: make db-dev).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v make >/dev/null 2>&1; then
  echo "make not found." >&2
  exit 1
fi

make db-dev
