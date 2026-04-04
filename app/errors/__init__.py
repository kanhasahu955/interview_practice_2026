"""Central API error handling (readable JSON + server-side logging)."""

from app.errors.handlers import register_exception_handlers

__all__ = ["register_exception_handlers"]
