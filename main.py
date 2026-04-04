"""
Root bootstrap: run the ASGI app built in `app.main`.

    uvicorn main:app --reload

PYTHONPATH must be this directory (see Makefile).
"""

import uvicorn

from app.main import create_app
from app.config import get_settings

app = create_app()


def run() -> None:
    """Run with `python main.py` (no reload). For reload: `make dev` or `uvicorn main:app --reload`."""
    s = get_settings()
    uvicorn.run(app, host=s.uvicorn_host, port=s.uvicorn_port, reload=False)


if __name__ == "__main__":
    run()
