# Operations runbook

Use this file as the **single checklist** for running mo-april locally, in Docker, or on a VPS.

---

## 1. Choose how you run

| Goal | Command | Open in browser |
|------|---------|------------------|
| **Hot reload** + **Docker Postgres** | **`make db-dev`** | http://127.0.0.1:8000 |
| **Hot reload** + **your own DB** (e.g. MySQL in `.env`) | `make dev` only | http://127.0.0.1:8000 |
| **Full stack in Docker** (matches prod shape) | `make docker-local` | http://127.0.0.1:8080 (nginx → API) |
| **Docker locally + Supabase** (no Compose `db`) | `make docker-local-supabase` | http://127.0.0.1:8080 — needs **`deploy/supabase/compose.env`** |
| **Production-style locally** | `make prod` | http://127.0.0.1:8080 (uses prod nginx + Gunicorn workers) |
| **Production + external DB** (e.g. Supabase on VPS) | `make prod-external-db` | `.env` **`DATABASE_URL`** must point at Supabase |
| **Public VPS** (e.g. Hostinger) | See [deploy/hostinger/README.md](../deploy/hostinger/README.md) | Your domain |

**API docs:** `/docs` (Swagger), `/reference` (Scalar), OpenAPI at `/openapi.json`.

---

## 2. First-time setup (machine)

Prerequisites:

- **Docker Desktop** (or Docker Engine + Compose v2) for `make db`, `make docker-local`, `make prod`
- **uv** — https://docs.astral.sh/uv/ — for `make setup` and `make dev`
- **make** (Xcode CLI tools on macOS)

From the **repo root**:

```bash
make setup    # creates .env from .env.example if missing + uv sync
```

Edit **`.env`** for your real database if you use **`make dev`** with MySQL or a remote DB (see `.env.example`).

---

## 3. Environment files (do not mix them up)

| File | Used by | Purpose |
|------|---------|---------|
| **`.env`** (repo root, gitignored) | `make dev`, `make db`, `docker compose` *without* sourcing another file | Your daily dev settings; often **MySQL** URL. |
| **`deploy/local/docker.env`** | **`make docker-local`** only (exported before Compose) | **Postgres** URL for the Compose `db` service; avoids clashing with a MySQL `.env`. |
| **`deploy/hostinger/env.hostinger.example`** | Copy to **`.env` on the VPS** | Production-style secrets, `CORS_ORIGINS`, bundled or Supabase `DATABASE_URL`. |
| **`deploy/supabase/compose.env.example`** | Copy → **`deploy/supabase/compose.env`** | Local Docker + Supabase (`make docker-local-supabase`). |
| **[deploy/supabase/README.md](../deploy/supabase/README.md)** | Supabase URL, TLS, VPS vs local | |

Compose **interpolates** variables from the process environment. `make docker-local` sources `deploy/local/docker.env` first so those values win over a conflicting `.env` for that run.

---

## 4. Makefile targets (cheat sheet)

Run **`make help`** for the live list. Common ones:

| Target | Action |
|--------|--------|
| `setup` | `env` + `uv sync` |
| `db` | Start **Postgres** container only |
| `db-dev` | **`db`** then **Uvicorn** with `DATABASE_URL` forced to that Postgres (uses **`POSTGRES_*`** from `.env`) |
| `dev` | **Uvicorn** reload; uses **`DATABASE_URL`** from `.env` as-is (MySQL or Postgres) |
| `docker-local` | Postgres + API + nginx on **`:8080`** (uses `deploy/local/docker.env`) |
| `docker-local-down` | Stop that stack |
| `docker-local-logs` | `docker compose logs -f` |
| `docker-local-ps` | Container status |
| `docker-local-supabase` | **`api` + `nginx`** only; env from **`deploy/supabase/compose.env`** |
| `prod` | Base compose + `deploy/production/compose.yml` (Gunicorn workers, prod nginx) |
| `prod-external-db` | Production compose **without** bundled Postgres; **`DATABASE_URL`** from **`.env`** (e.g. Supabase) |
| `prod-down` / `prod-logs` / `prod-ps` | Production stack |
| `docker-up` / `docker-down` | Compose **without** prod overlay; reads **`.env`** for vars |

---

## 5. One-command automation (scripts)

From repo root (bash):

```bash
chmod +x scripts/*.sh   # once per clone

./scripts/docker-local-up.sh    # same as make docker-local
./scripts/docker-local-down.sh  # same as make docker-local-down
./scripts/dev-stack.sh          # starts Postgres; prints "run make dev"
```

Use these in cron, aliases, or CI steps if you prefer shell over Make.

---

## 6. Troubleshooting

### `http://127.0.0.1:8080` → 502, 500, or blank error page

Usually **nginx is up** but the **`api`** container has **crashed**. Check:

1. `make docker-local-ps` — **`api`** should be **Up**, not **Exited**.
2. `docker compose -f docker-compose.yml logs api --tail 80` — read the traceback.

The app uses a **Postgres advisory lock** around `create_all` so multiple Gunicorn workers do not race on DDL. If you still see duplicate `CREATE TABLE` / sequence errors from an **older** image, rebuild: `make docker-local` (or `docker compose build api`) and, if the DB was left half-created, `docker compose -f docker-compose.yml down -v` then bring the stack up again (dev data loss).

### API exited: Postgres `userrole` / ENUM / duplicate type

The app uses **VARCHAR** for roles (not a native PG enum) to avoid multi-worker races. If an **old volume** still has a broken state:

```bash
make docker-local-down
docker compose -f docker-compose.yml down -v
make docker-local
```

**`-v` deletes local Postgres data** — dev only.

### Port already in use (5432 or 8080)

Edit **`deploy/local/docker.env`**: change `POSTGRES_PUBLISH_PORT` and/or `NGINX_HTTP_PORT`, then `make docker-local` again.

### `make db && make dev` fails but you use MySQL in `.env`

**`make db`** starts **Postgres** in Docker; **`make dev`** still reads **`DATABASE_URL=mysql://...`**, so the API never talks to that Postgres.

Use **`make db-dev`** instead (one command after **`make db`** is already included). Or set **`DATABASE_URL`** in **`.env`** to `postgresql+psycopg2://USER:PASS@127.0.0.1:5432/moapril` matching **`POSTGRES_*`**, then **`make db && make dev`**.

### `make dev` cannot connect to DB

- With Compose Postgres: prefer **`make db-dev`**, or align **`DATABASE_URL`** with **`POSTGRES_USER` / `POSTGRES_PASSWORD` / port **`POSTGRES_PUBLISH_PORT`**.

---

## 7. Production / VPS quick path

1. Copy **`deploy/hostinger/env.hostinger.example`** → **`.env`** on the server (or merge into your secrets).
2. Set **`JWT_SECRET_KEY`**, **`POSTGRES_PASSWORD`**, **`CORS_ORIGINS`**, **`DATABASE_URL`** (with host `db` if using Compose Postgres).
3. Run:

   ```bash
   docker compose -f docker-compose.yml -f deploy/production/compose.yml up --build -d
   ```

Full steps, TLS, and firewall: **[deploy/hostinger/README.md](../deploy/hostinger/README.md)**.

---

## 8. Continuous integration

On **GitHub**, pushing or opening a PR runs **`.github/workflows/ci.yml`**, which builds the **`api`** Docker image so breaks in `Dockerfile` / `requirements.txt` surface early.

---

## 9. Related paths in the repo

| Path | Role |
|------|------|
| `docker-compose.yml` | Services: `db`, `api`, `nginx` |
| `docker/Dockerfile` | API image |
| `docker/nginx/default.conf` | Dev-style nginx for Compose |
| `deploy/production/compose.yml` | Prod overrides (Gunicorn command, prod nginx mount) |
| `deploy/production/nginx/default.conf` | Prod nginx → `api:8000` |
