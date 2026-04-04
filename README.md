# mo-april

FastAPI learning stack. **`app/`** holds the ASGI factory (`app/main.py`) and all Python packages (`routes`, `services`, `modules`, …). Repo root keeps **`main.py`**, **`static/`**, **`templates/`**, **`topics/`**, Docker, and env files.

## Documentation (start here next time)

| Resource | Purpose |
|----------|---------|
| **[docs/RUNBOOK.md](docs/RUNBOOK.md)** | **Single checklist**: local dev, Docker, prod, env files, troubleshooting, automation. |
| **[docs/README.md](docs/README.md)** | Index of all docs and scripts. |
| **`make help`** | Every Makefile target with a one-line description. |

**Fast paths:**

```bash
make setup && make db && make dev          # API http://127.0.0.1:8000 (reload)
./scripts/docker-local-up.sh               # Full stack http://127.0.0.1:8080 (same as make docker-local)
```

- Hostinger VPS: **[deploy/hostinger/README.md](deploy/hostinger/README.md)**
- Scripts: **[scripts/README.md](scripts/README.md)**
- CI: **`.github/workflows/ci.yml`** builds the API image on push/PR

Imports assume **`PYTHONPATH`** = repo root (`make dev` handles this).

## Layout

| Path | Role |
|------|------|
| **`main.py`** | Root bootstrap: `app = create_app()` from **`app.main`**, optional `python main.py`. |
| **`app/main.py`** | `create_app()` — lifespan, logging, static mounts, middleware stack, `mount_routes`. |
| **`app/__init__.py`** | Re-exports `create_app`. |
| **`app/config/`** | Settings + logging setup. |
| **`app/db/`** | Async engine, `get_db`, `create_db_and_tables`. |
| **`app/deps/`** | Auth dependencies (`get_current_user`, OAuth2 URL, …). |
| **`app/routes/`** | HTTP routers. |
| **`app/services/`** | Business logic. |
| **`app/modules/`** | SQLModel tables per domain. |
| **`app/schema/`** | Request/response DTOs. |
| **`app/middlewares/`** | CORS, rate limit, security headers, request ID, validation stub. |
| **`app/utils/`** | e.g. thread offload for bcrypt. |
| **`app/constant/`** | Shared constants. |
| **`app/documents/`** | Bundled Markdown → **`/content`**. |
| **`static/`**, **`templates/`**, **`media/`**, **`upload/`**, **`logs/`**, **`topics/`** | As before. |
| **`docker/`** | Production **`Dockerfile`** + nginx config. |

## Run (summary)

```bash
make db && make dev
```

See **[docs/RUNBOOK.md](docs/RUNBOOK.md)** for Docker, production, and VPS.
