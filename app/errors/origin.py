"""Resolve file, line, and function where an exception was raised (project code preferred)."""

from __future__ import annotations

import traceback
from pathlib import Path
from types import TracebackType
from typing import Any, TypedDict

# app/errors/origin.py → parents[2] = repo root (mo-april)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ErrorOrigin(TypedDict, total=False):
    file: str
    line: int
    function: str
    code: str | None
    file_relative: str


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def _is_site_packages(filename: str) -> bool:
    return "site-packages" in _norm(filename)


def _is_app_source(filename: str) -> bool:
    n = _norm(filename)
    return "/app/" in n and not _is_site_packages(filename)


def _relative_to_project(abs_path: str) -> str:
    try:
        return str(Path(abs_path).resolve().relative_to(_PROJECT_ROOT))
    except ValueError:
        return abs_path


def _origin_from_traceback(tb: TracebackType | None) -> ErrorOrigin | None:
    if tb is None:
        return None
    frames = traceback.extract_tb(tb)
    if not frames:
        return None

    for f in reversed(frames):
        if _is_app_source(f.filename):
            return _frame_to_origin(f)

    for f in reversed(frames):
        if not _is_site_packages(f.filename):
            return _frame_to_origin(f)

    return _frame_to_origin(frames[-1])


def error_origin(exc: BaseException) -> ErrorOrigin | None:
    """
    Best-effort location: innermost `app/` frame, else first non-site-packages frame.
    Tries the exception and then `__cause__` (SQLAlchemy often chains DBAPI errors).
    """
    for candidate in (exc, exc.__cause__):
        if candidate is None:
            continue
        o = _origin_from_traceback(candidate.__traceback__)
        if o:
            return o
    return None


def _frame_to_origin(f: traceback.FrameSummary) -> ErrorOrigin:
    abs_file = f.filename
    line = f.lineno or 0
    code = (f.line or "").strip() if f.line else None
    return {
        "file": abs_file,
        "file_relative": _relative_to_project(abs_file),
        "line": line,
        "function": f.name,
        "code": code,
    }


def origin_log_suffix(origin: ErrorOrigin | None) -> str:
    """Append to log messages: ` at app/foo.py:42 in bar`."""
    if not origin:
        return ""
    rel = origin.get("file_relative") or origin.get("file", "?")
    line = origin.get("line", 0)
    fn = origin.get("function", "?")
    return f" at {rel}:{line} in {fn}()"


def origin_for_json(origin: ErrorOrigin | None) -> dict[str, Any] | None:
    """Subset for JSON `debug` / `where` payloads."""
    if not origin:
        return None
    return {
        "file": origin.get("file_relative") or origin.get("file"),
        "line": origin.get("line"),
        "function": origin.get("function"),
        **({"code": origin["code"]} if origin.get("code") else {}),
    }


def origin_log_extra(origin: ErrorOrigin | None) -> dict[str, Any]:
    """
    Pass as `logger.error(..., extra=origin_log_extra(origin))` so formatters can print
    full path + line without truncating inside a single Rich panel line.
    """
    if not origin:
        return {}
    return {
        "error_origin": {
            "file_relative": origin.get("file_relative") or "",
            "file_absolute": origin.get("file"),
            "line": int(origin.get("line") or 0),
            "function": str(origin.get("function") or "?"),
            "code": origin.get("code"),
        }
    }
