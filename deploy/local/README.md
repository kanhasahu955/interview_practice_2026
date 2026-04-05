# Local Docker (full stack)

Full checklist and troubleshooting: **[docs/RUNBOOK.md](../../docs/RUNBOOK.md)**.

Runs **Postgres**, the **API** (Gunicorn + Uvicorn in the image), and **nginx** on **`http://127.0.0.1:8080`** by default.

To use **Supabase** instead of the Compose **`db`** service: **`make docker-local-supabase`** and **`deploy/supabase/compose.env`** — see **[deploy/supabase/README.md](../supabase/README.md)**.

```bash
make docker-local
```

- Uses **`deploy/local/docker.env`** so your repo-root **`.env`** (e.g. MySQL for `make dev`) does not break Compose.
- Stop: `make docker-local-down`
- Logs: `make docker-local-logs`

Change **ports** in `docker.env` if **5432** or **8080** are already in use.

If the API container **exits** after a bad Postgres state, wipe volumes and start clean (deletes local DB data):

```bash
make docker-local-down
docker compose -f docker-compose.yml down -v
make docker-local
```

Equivalent without Make:

```bash
set -a && source deploy/local/docker.env && set +a && docker compose up --build -d
```
