# Supabase PostgreSQL

Use your **Supabase** project as the database for **local Docker** (API + nginx only) or a **VPS** (no bundled Postgres container).

From the dashboard you should see:

| Field | Example (this project) |
|-------|-------------------------|
| Host | `db.tutkjihhixijaqzhfyxk.supabase.co` |
| Port | `5432` |
| Database | `postgres` |
| User | `postgres` |
| Password | **Database password** (Settings → Database — not the `anon` service role key) |

## Connection URL (app / Docker)

The app reads **`DATABASE_URL`** in **sync** form (`postgresql+psycopg2://…`); it switches to **asyncpg** at runtime.

```bash
postgresql+psycopg2://postgres:YOUR_DATABASE_PASSWORD@db.tutkjihhixijaqzhfyxk.supabase.co:5432/postgres
```

If the password has special characters, **URL-encode** it (e.g. `@` → `%40`).

TLS: hosts under **`*.supabase.co`** get **`ssl=True`** for asyncpg automatically unless you already set `ssl=` / `sslmode=` in the URL.

## Local Docker (API + nginx → Supabase)

Does **not** start the Compose **`db`** service.

```bash
cp deploy/supabase/compose.env.example deploy/supabase/compose.env
nano deploy/supabase/compose.env   # real password + JWT_SECRET_KEY
make docker-local-supabase
```

Open **http://127.0.0.1:8080**. Tables are created on first API startup (`create_all`).

## VPS (Hostinger, etc.)

1. In the server’s repo-root **`.env`**, set **`DATABASE_URL`** to the same Supabase URL (and **`JWT_SECRET_KEY`**, **`CORS_ORIGINS`**, etc.).
2. Start **only** **`api`** and **`nginx`** (no local Postgres):

```bash
make prod-external-db
```

Same idea as:

```bash
docker compose -f docker-compose.yml -f deploy/production/compose.yml up --build -d --no-deps api nginx
```

See also **[deploy/hostinger/README.md](../hostinger/README.md)** (Supabase section).

## Pooler (optional)

For very high connection counts, Supabase offers a **pooler** (often port **6543**) and a different username format. For typical Gunicorn worker counts, **direct** `db.<ref>.supabase.co:5432` is usually enough. Check current limits in the Supabase dashboard.
