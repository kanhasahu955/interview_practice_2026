.DEFAULT_GOAL := help

PROJECT_ROOT := $(CURDIR)
COMPOSE      := docker compose
COMPOSE_BASE := -f docker-compose.yml
# Reusable production bundle (copy `deploy/production/` to another repo and point PROD_COMPOSE at it)
PROD_COMPOSE ?= deploy/production/compose.yml
COMPOSE_PROD := -f $(PROD_COMPOSE)
UV           := $(shell command -v uv 2>/dev/null)

DOCKER_LOCAL_ENV := $(PROJECT_ROOT)/deploy/local/docker.env
SUPABASE_COMPOSE_ENV := $(PROJECT_ROOT)/deploy/supabase/compose.env

.PHONY: help setup env lock clean docs \
	docker-build docker-up docker-down docker-logs docker-ps \
	docker-local docker-local-down docker-local-logs docker-local-ps \
	docker-local-supabase \
	db db-dev dev prod prod-down prod-logs prod-ps prod-bundle prod-external-db

help: ## Show available targets
	@echo "mo-april — FastAPI API"
	@echo ""
	@grep -E '^[a-zA-Z0-9_.-]+:.*?##' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  \033[1mFull ops checklist\033[0m     docs/RUNBOOK.md   (or: make docs)"
	@echo "  \033[1mOne-shot bootstrap\033[0m    make setup"
	@echo "  \033[1mLocal + Docker Postgres\033[0m  make db-dev   (not make db && make dev if .env is MySQL)"
	@echo "  \033[1mLocal + your DATABASE_URL\033[0m  make dev      (uses .env only)"
	@echo "  \033[1mLocal Docker stack\033[0m     make docker-local   (Postgres + API + nginx :8080)"
	@echo "  \033[1mLocal Docker + Supabase\033[0m  make docker-local-supabase   (deploy/supabase/compose.env)"
	@echo "  \033[1mVPS + external Postgres\033[0m  make prod-external-db   (.env DATABASE_URL e.g. Supabase)"
	@echo "  \033[1mShell automation\033[0m       ./scripts/docker-local-up.sh"
	@echo "  \033[1mProduction (Docker)\033[0m    make prod   (see deploy/production/env.example)"
	@echo ""

docs: ## Open documentation index path (prints location)
	@echo "$(PROJECT_ROOT)/docs/README.md"
	@echo "$(PROJECT_ROOT)/docs/RUNBOOK.md"

setup: env ## Bootstrap: .env from example + install deps (uv sync)
	@test -n "$(UV)" || (echo "Install uv: https://docs.astral.sh/uv/" && exit 1)
	cd $(PROJECT_ROOT) && $(UV) sync
	@echo ""
	@echo "  Done. Choose one:"
	@echo "    make db-dev           # Postgres in Docker + API reload (works with MySQL in .env)"
	@echo "    make prod             # nginx + API + Postgres (uses $(PROD_COMPOSE))"
	@echo ""

env: ## Copy .env.example -> .env if missing
	@if [ ! -f $(PROJECT_ROOT)/.env ] && [ -f $(PROJECT_ROOT)/.env.example ]; then \
		cp $(PROJECT_ROOT)/.env.example $(PROJECT_ROOT)/.env; \
		echo "Created .env from .env.example"; \
	elif [ -f $(PROJECT_ROOT)/.env ]; then \
		echo ".env already exists"; \
	else \
		echo "No .env.example; create .env manually"; \
	fi

prod-bundle: ## Show reusable production config paths (copy deploy/production/ for other projects)
	@echo "Production bundle (copy as a unit or override PROD_COMPOSE=...):"
	@echo "  $(PROJECT_ROOT)/deploy/production/compose.yml"
	@echo "  $(PROJECT_ROOT)/deploy/production/nginx/default.conf"
	@echo "  $(PROJECT_ROOT)/deploy/production/env.example"

lock: ## Refresh uv.lock after editing pyproject.toml
	@test -n "$(UV)" || (echo "Install uv" && exit 1)
	cd $(PROJECT_ROOT) && $(UV) lock

docker-build: ## Build API image (base compose file)
	$(COMPOSE) $(COMPOSE_BASE) build api

docker-up: ## Start nginx + API + Postgres (compose base only, no prod overrides)
	$(COMPOSE) $(COMPOSE_BASE) up --build -d

docker-down: ## Stop base compose stack
	$(COMPOSE) $(COMPOSE_BASE) down

docker-logs: ## Follow logs (base compose)
	$(COMPOSE) $(COMPOSE_BASE) logs -f

docker-ps: ## Service status (base compose)
	$(COMPOSE) $(COMPOSE_BASE) ps

docker-local: ## Full stack locally: Postgres + API + nginx (uses deploy/local/docker.env)
	@test -f $(DOCKER_LOCAL_ENV) || (echo "Missing $(DOCKER_LOCAL_ENV)" && exit 1)
	cd $(PROJECT_ROOT) && set -a && . $(DOCKER_LOCAL_ENV) && set +a && $(COMPOSE) $(COMPOSE_BASE) up --build -d
	@echo ""
	@echo "  Local Docker: http://127.0.0.1:8080  (override NGINX_HTTP_PORT in deploy/local/docker.env)"
	@echo "  Logs: make docker-local-logs   Stop: make docker-local-down   Runbook: docs/RUNBOOK.md"
	@echo ""

docker-local-down: ## Stop local Docker stack (same compose project as docker-local)
	cd $(PROJECT_ROOT) && $(COMPOSE) $(COMPOSE_BASE) down

docker-local-logs: ## Follow logs (local Docker stack)
	cd $(PROJECT_ROOT) && $(COMPOSE) $(COMPOSE_BASE) logs -f

docker-local-ps: ## Status (local Docker stack)
	cd $(PROJECT_ROOT) && $(COMPOSE) $(COMPOSE_BASE) ps

docker-local-supabase: ## API + nginx only; DB = Supabase (create deploy/supabase/compose.env from example)
	@test -f $(SUPABASE_COMPOSE_ENV) || (echo "Missing $(SUPABASE_COMPOSE_ENV) — cp deploy/supabase/compose.env.example" >&2 && exit 1)
	cd $(PROJECT_ROOT) && set -a && . $(SUPABASE_COMPOSE_ENV) && set +a && \
	  $(COMPOSE) $(COMPOSE_BASE) up --build -d --no-deps api nginx
	@echo ""
	@echo "  Supabase-backed Docker: http://127.0.0.1:$${NGINX_HTTP_PORT:-8080}"
	@echo "  Stop: make docker-local-down   Docs: deploy/supabase/README.md"
	@echo ""

prod: ## Production: merge base + deploy/production (Gunicorn workers, prod nginx, restarts)
	$(COMPOSE) $(COMPOSE_BASE) $(COMPOSE_PROD) up --build -d
	@echo ""
	@echo "  Stack is up. HTTP (via nginx): http://localhost:$${NGINX_HTTP_PORT:-8080}"
	@echo "  Bundle: deploy/production/   Logs: make prod-logs   Stop: make prod-down"
	@echo ""

prod-down: ## Stop production compose stack (merged files)
	$(COMPOSE) $(COMPOSE_BASE) $(COMPOSE_PROD) down

prod-logs: ## Follow production stack logs
	$(COMPOSE) $(COMPOSE_BASE) $(COMPOSE_PROD) logs -f

prod-ps: ## Production stack status
	$(COMPOSE) $(COMPOSE_BASE) $(COMPOSE_PROD) ps

prod-external-db: ## Production compose without bundled Postgres; DATABASE_URL from repo .env (e.g. Supabase)
	cd $(PROJECT_ROOT) && $(COMPOSE) $(COMPOSE_BASE) $(COMPOSE_PROD) up --build -d --no-deps api nginx
	@echo ""
	@echo "  api + nginx only — ensure .env sets DATABASE_URL (e.g. Supabase). deploy/supabase/README.md"
	@echo ""

db: ## Start Postgres only (Compose). Pair with make db-dev if .env points at MySQL.
	$(COMPOSE) $(COMPOSE_BASE) up -d db
	@echo "Postgres: localhost:$${POSTGRES_PUBLISH_PORT:-5432} db=$${POSTGRES_DB:-moapril} user=$${POSTGRES_USER:-learn}"

db-dev: db ## Uvicorn reload against Docker Postgres (builds DATABASE_URL from POSTGRES_* in .env)
	@test -n "$(UV)" || (echo "Install uv and run: make setup" && exit 1)
	cd $(PROJECT_ROOT) && if [ -f ./.env ]; then set -a && . ./.env && set +a; fi && \
		export DATABASE_URL="postgresql+psycopg2://$${POSTGRES_USER:-learn}:$${POSTGRES_PASSWORD:-learn}@127.0.0.1:$${POSTGRES_PUBLISH_PORT:-5432}/$${POSTGRES_DB:-moapril}" && \
		PYTHONPATH=$(PROJECT_ROOT) $(UV) run uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev: ## Local API: uvicorn with reload (uses DATABASE_URL from .env as-is)
	@test -n "$(UV)" || (echo "Install uv and run: make setup" && exit 1)
	cd $(PROJECT_ROOT) && PYTHONPATH=$(PROJECT_ROOT) $(UV) run uvicorn main:app --reload --host 0.0.0.0 --port 8000

clean: ## Remove __pycache__ under app/ (all packages live there)
	@find "$(PROJECT_ROOT)/app" -type d -name __pycache__ 2>/dev/null | while read x; do rm -rf "$$x"; done; true
