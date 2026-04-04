# Scripts

Executable helpers (run from **repository root**).

| Script | Equivalent |
|--------|------------|
| `docker-local-up.sh` | `make docker-local` |
| `docker-local-down.sh` | `make docker-local-down` |
| `dev-stack.sh` | `make db` + instructions for `make dev` |

First time:

```bash
chmod +x scripts/*.sh
```

Requires **Docker** and **docker compose** for the docker-* scripts; **uv** + **make** for `dev-stack.sh` (it calls `make db`).

More context: **[docs/RUNBOOK.md](../docs/RUNBOOK.md)**.
