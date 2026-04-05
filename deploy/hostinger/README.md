# Deploy mo-april on Hostinger

General operations (local Docker, env files, troubleshooting): **[docs/RUNBOOK.md](../../docs/RUNBOOK.md)**.

This app is **FastAPI + PostgreSQL + nginx** in Docker. It does **not** run on Hostinger **shared web hosting** (PHP-only plans). Use a **Hostinger VPS** (or Cloud VPS) with **Ubuntu** and root/SSH access.

## 1. Create the server

1. In Hostinger **hPanel**, order a **VPS** (KVM) with at least **2 GB RAM** (4 GB is more comfortable for Postgres + API + nginx).
2. Choose **Ubuntu 22.04 or 24.04**.
3. Note the **public IPv4** address and your **SSH** user (often `root`).

## 2. Point your domain

1. **DNS** → add an **A** record: `yourdomain.com` → your VPS IP.
2. Optional: `www` → same IP (or CNAME to apex).
3. Wait for DNS to propagate (often minutes, sometimes up to 24–48 hours).

## 3. Open the firewall

In **hPanel → VPS → Firewall** (or `ufw` on the server), allow:

- **22** (SSH)
- **80** (HTTP — needed for Let’s Encrypt)
- **443** (HTTPS)

Do **not** expose PostgreSQL (**5432**) to the public internet. The example env binds Postgres to **localhost only** on the host.

## 4. Install Docker on the VPS

SSH in, then:

```bash
sudo apt update && sudo apt install -y ca-certificates curl git make
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
```

Log out and back in so the `docker` group applies. Check:

```bash
docker compose version
```

## 5. Clone the project

```bash
sudo mkdir -p /opt && sudo chown "$USER":"$USER" /opt
cd /opt
git clone <your-repo-url> mo-april
cd mo-april
```

## 6. Configure environment

```bash
cp deploy/hostinger/env.hostinger.example .env
nano .env   # or vim
chmod 600 .env
```

Set at least:

| Variable | Notes |
|----------|--------|
| `JWT_SECRET_KEY` | e.g. `openssl rand -hex 32` |
| `DATABASE_URL` | **Bundled Postgres:** `...@db:5432/...` · **Supabase:** see [deploy/supabase/README.md](../supabase/README.md) |
| `POSTGRES_*` | Only when using the Compose **`db`** service (not needed for Supabase-only) |
| `CORS_ORIGINS` | `https://yourdomain.com,https://www.yourdomain.com` |
| `NGINX_HTTP_PORT` | `80` for production |

Optional: `APP_NAME`, `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` for a first admin user.

### Supabase instead of Docker Postgres

1. In **`.env`**, set **`DATABASE_URL`** to your Supabase **direct** connection (user `postgres`, host `db.<project-ref>.supabase.co`, port `5432`, database `postgres`). Use the **database password** from the Supabase dashboard, not the anon key. Details: **[deploy/supabase/README.md](../supabase/README.md)**.
2. Start **only** **`api`** and **`nginx`** (no local `db` container):

```bash
make prod-external-db
```

## 7. Start the stack (HTTP first)

From `/opt/mo-april`.

**Bundled Postgres** (`DATABASE_URL` host is `db`):

```bash
docker compose -f docker-compose.yml -f deploy/production/compose.yml up --build -d
docker compose -f docker-compose.yml -f deploy/production/compose.yml ps
```

**Supabase / external Postgres** — use **`make prod-external-db`** (see subsection above) instead of the command above.

Open `http://YOUR_VPS_IP` or `http://yourdomain.com`. You should see the HTML home page and `/docs` for the API.

The API container runs **Gunicorn + Uvicorn workers**; the database creates tables on first startup.

## 8. HTTPS (Let’s Encrypt)

1. Install Certbot on the **host** (not inside a container):

   ```bash
   sudo apt install -y certbot
   ```

2. **Stop** anything listening on port **80** temporarily (your stack’s nginx uses 80):

   ```bash
   cd /opt/mo-april
   docker compose -f docker-compose.yml -f deploy/production/compose.yml stop nginx
   ```

3. Obtain certificates (replace domains):

   ```bash
   sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
   ```

4. Copy the example TLS nginx config and edit `server_name` and certificate paths if your domain differs:

   ```bash
   cp deploy/hostinger/nginx/default-https.conf.example deploy/production/nginx/default.conf
   nano deploy/production/nginx/default.conf
   ```

5. Add a **Docker override** so nginx can read certs and listen on 443:

   ```bash
   cp deploy/hostinger/docker-compose.override.example.yml docker-compose.override.yml
   nano docker-compose.override.yml   # adjust if paths differ
   ```

6. Start everything again:

   ```bash
   docker compose -f docker-compose.yml -f deploy/production/compose.yml up -d
   ```

7. **Renewal**: Certbot installs a systemd timer. After renewal, reload nginx so it picks up new files:

   ```bash
   sudo certbot renew --dry-run
   # Example post-hook (adjust compose path):
   # sudo sh -c 'echo "0 3 * * * root certbot renew -q --deploy-hook \"docker exec mo-april-nginx-1 nginx -s reload\"" >> /etc/crontab'
   ```

   Container names may differ; use `docker ps` to find the nginx container name.

## 9. Updates after code changes

```bash
cd /opt/mo-april
git pull
docker compose -f docker-compose.yml -f deploy/production/compose.yml up --build -d
```

If you use **Supabase** (`make prod-external-db`):

```bash
make prod-external-db
```

## 9b. Nginx fails to start: “mount … default.conf … not a directory”

Compose mounts **`deploy/production/nginx/default.conf`** (a **file**) into the nginx container. This error usually means:

1. **The path is a directory** — Docker created an empty folder named `default.conf` the first time the real file was missing.
2. **The file was never deployed** — incomplete clone or wrong branch.

On the VPS, from the project root:

```bash
ls -la deploy/production/nginx/default.conf
```

- If it shows **`d`** (directory): remove it and restore the file from git:

```bash
rm -rf deploy/production/nginx/default.conf
git checkout HEAD -- deploy/production/nginx/default.conf
```

- If **missing**: `git pull` and ensure your repo contains **`deploy/production/nginx/default.conf`**, or copy it from this project.

Then run **`make prod-external-db`** (or **`make prod`**) again. **`make`** now runs a quick check before those targets.

## 10. Logs and backups

- Logs: `docker compose -f docker-compose.yml -f deploy/production/compose.yml logs -f api`
- Database: with **bundled Postgres**, schedule volume snapshots / `pg_dump`. With **Supabase**, use project backups in the Supabase dashboard (and still export off-site if you need your own copy).

## Files in this folder

| File | Purpose |
|------|--------|
| `env.hostinger.example` | VPS-oriented `.env` template (bundled Postgres or **Supabase** `DATABASE_URL`) |
| `../supabase/README.md` | Supabase connection URL and `make prod-external-db` |
| `nginx/default-https.conf.example` | TLS reverse proxy example |
| `docker-compose.override.example.yml` | Copy to repo root as `docker-compose.override.yml` for HTTPS |

## Hostinger shared hosting?

If you only have **shared hosting** (no SSH/Docker), you cannot run this stack there. Options: upgrade to **VPS**, or deploy the API elsewhere (Railway, Fly.io, etc.) and point a subdomain to it.
