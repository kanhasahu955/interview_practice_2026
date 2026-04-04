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
| `POSTGRES_PASSWORD` | Strong password; must match `DATABASE_URL` |
| `DATABASE_URL` | Keep `...@db:5432/...` when using Compose service `db` |
| `CORS_ORIGINS` | `https://yourdomain.com,https://www.yourdomain.com` |
| `NGINX_HTTP_PORT` | `80` for production |

Optional: `APP_NAME`, `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` for a first admin user.

## 7. Start the stack (HTTP first)

From `/opt/mo-april`:

```bash
docker compose -f docker-compose.yml -f deploy/production/compose.yml up --build -d
docker compose -f docker-compose.yml -f deploy/production/compose.yml ps
```

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

## 10. Logs and backups

- Logs: `docker compose -f docker-compose.yml -f deploy/production/compose.yml logs -f api`
- Database: schedule **volume** or `pg_dump` backups (Hostinger snapshots + off-server copies).

## Files in this folder

| File | Purpose |
|------|--------|
| `env.hostinger.example` | VPS-oriented `.env` template |
| `nginx/default-https.conf.example` | TLS reverse proxy example |
| `docker-compose.override.example.yml` | Copy to repo root as `docker-compose.override.yml` for HTTPS |

## Hostinger shared hosting?

If you only have **shared hosting** (no SSH/Docker), you cannot run this stack there. Options: upgrade to **VPS**, or deploy the API elsewhere (Railway, Fly.io, etc.) and point a subdomain to it.
