#!/usr/bin/env bash
# Start only Postgres for local API development; you run make dev separately.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v make >/dev/null 2>&1; then
  echo "make not found." >&2
  exit 1
fi

make db

echo ""
echo "  Postgres is up. Point DATABASE_URL in .env at this instance if needed."
echo "  Then run:  make dev"
echo "  Open:      http://127.0.0.1:8000"
echo "  Runbook:   docs/RUNBOOK.md"
echo ""
