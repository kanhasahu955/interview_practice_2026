# mo-april documentation

| Doc | Use when you want to… |
|-----|------------------------|
| **[RUNBOOK.md](RUNBOOK.md)** | **Start here** — copy-paste flows for local dev, Docker, production, troubleshooting, and automation. |
| **[../deploy/local/README.md](../deploy/local/README.md)** | Short reference for `make docker-local` only. |
| **[../deploy/hostinger/README.md](../deploy/hostinger/README.md)** | Deploy on a Hostinger **VPS** (Docker). |
| **[../deploy/production/env.example](../deploy/production/env.example)** | Production / `make prod` env checklist. |
| **[../.env.example](../.env.example)** | Local dev / generic Compose variable reference. |

**Automation (no thinking next time):**

- `scripts/docker-local-up.sh` — same as `make docker-local`
- `scripts/dev-stack.sh` — optional: `make db` then remind `make dev`
- CI: `.github/workflows/ci.yml` — builds the API image on push/PR

Run **`make help`** for every Makefile target.
