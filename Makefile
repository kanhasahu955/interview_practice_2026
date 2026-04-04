.DEFAULT_GOAL := help

PROJECT_ROOT := $(CURDIR)
COMPOSE      := docker compose
COMPOSE_BASE := -f docker-compose.yml
# Reusable production bundle (copy `deploy/production/` to another repo and point PROD_COMPOSE at it)
PROD_COMPOSE ?= deploy/production/compose.yml
COMPOSE_PROD := -f $(PROD_COMPOSE)
UV           := $(shell command -v uv 2>/dev/null)

DOCKER_LOCAL_ENV := $(PROJECT_ROOT)/deploy/local/docker.env

.PHONY: help setup env lock clean docs \
	docker-build docker-up docker-down docker-logs docker-ps \
	docker-local docker-local-down docker-local-logs docker-local-ps \
	db dev prod prod-down prod-logs prod-ps prod-bundle

help: ## Show available targets
	@echo "mo-april — FastAPI API"
	@echo ""
	@grep -E '^[a-zA-Z0-9_.-]+:.*?##' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  \033[1mFull ops checklist\033[0m     docs/RUNBOOK.md   (or: make docs)"
	@echo "  \033[1mOne-shot bootstrap\033[0m    make setup"
	@echo "  \033[1mLocal development\033[0m      make db && make dev"
	@echo "  \033[1mLocal Docker stack\033[0m     make docker-local   (Postgres + API + nginx :8080)"
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
	@echo "    make db && make dev   # Postgres in Docker, API locally with reload"
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

db: ## Start Postgres only (for local make dev)
	$(COMPOSE) $(COMPOSE_BASE) up -d db
	@echo "Postgres: localhost:$${POSTGRES_PUBLISH_PORT:-5432} db=$${POSTGRES_DB:-moapril} user=$${POSTGRES_USER:-learn}"

dev: ## Local API: uvicorn with reload (PYTHONPATH=project root)
	@test -n "$(UV)" || (echo "Install uv and run: make setup" && exit 1)
	cd $(PROJECT_ROOT) && PYTHONPATH=$(PROJECT_ROOT) $(UV) run uvicorn main:app --reload --host 0.0.0.0 --port 8000

clean: ## Remove __pycache__ under app/ (all packages live there)
	@find "$(PROJECT_ROOT)/app" -type d -name __pycache__ 2>/dev/null | while read x; do rm -rf "$$x"; done; true
