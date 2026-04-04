# mo-april

FastAPI learning stack. **`app/`** holds the ASGI factory (`app/main.py`) and all Python packages (`routes`, `services`, `modules`, …). Repo root keeps **`main.py`**, **`static/`**, **`templates/`**, **`topics/`**, Docker, and env files.

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

Imports assume **`PYTHONPATH`** = repo root (`make dev`).

## Run

```bash
make db && make dev
```

## Docker

```bash
docker compose up --build -d
```
