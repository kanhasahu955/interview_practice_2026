"""IST timestamps; file logs stay grep-friendly. Console: bordered Rich panels, icons, full request details (compact mode)."""

from __future__ import annotations

import logging
import re
import shutil
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.traceback import install as rich_traceback_install
from sqlalchemy.engine.url import make_url

from app.config.settings import Settings, get_settings
from app.logging.stream_hub import WebSocketLogHandler

IST = ZoneInfo("Asia/Kolkata")


def _ist_datetime(record: logging.LogRecord) -> datetime:
    return datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone(IST)


def _mask_url_password(url: str) -> str:
    return re.sub(r":([^:@/?#]+)@", r":***@", url, count=1)


def database_name_from_url(url: str) -> str:
    try:
        u = make_url(url)
        return u.database or "-"
    except Exception:
        return "?"


class DetailedFileFormatter(logging.Formatter):
    """IST; compact lines for startup_summary / http_access / shutdown_line."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        dt = _ist_datetime(record)
        return dt.strftime(datefmt or "%d-%m-%Y %H:%M:%S") + " IST"

    def format(self, record: logging.LogRecord) -> str:
        ts = self.formatTime(record)

        ss = getattr(record, "startup_summary", None)
        if isinstance(ss, dict):
            db_ok = ss.get("db_connected")
            line = (
                f"{ts} | {record.levelname:8} | {record.name} | "
                f"status=running application={ss.get('application') or ss.get('service')} "
                f"listen={ss.get('listen_url')} "
                f"database={ss.get('database')} "
                f"db_connection={'connected' if db_ok else 'failed'} "
                f"db_ping_ms={float(ss.get('db_ping_ms', 0)):.2f}"
            )
            if not db_ok and ss.get("db_error"):
                line += f" err={ss.get('db_error')}"
            return line

        sd = getattr(record, "shutdown_line", None)
        if isinstance(sd, dict):
            return (
                f"{ts} | {record.levelname:8} | {record.name} | "
                f"status=stopped application={sd.get('application') or sd.get('service')}"
            )

        ct = getattr(record, "config_table", None)
        if ct:
            lines = [
                f"{ts} | {record.levelname:8} | {record.name} | config | {key} = {val}"
                for key, val in ct
            ]
            return "\n".join(lines)

        ha = getattr(record, "http_access", None)
        if isinstance(ha, dict):
            try:
                compact_http = get_settings().log_compact
            except Exception:
                compact_http = True
            app_lbl = ha.get("application") or ha.get("service", "")
            route_lbl = ha.get("route_service", "-")
            sm = str(ha.get("static_message", ha.get("status_phrase", ""))).replace("|", "/").replace("\n", " ")
            if len(sm) > 100:
                sm = sm[:97] + "…"
            rsp = ha.get("response", "-")
            phrase = ha.get("status_phrase", "")
            code = ha.get("status_code", ha.get("status", ""))
            em = str(ha.get("log_emoji_file", ""))
            tier = str(ha.get("log_severity_tier", ""))
            pri = str(ha.get("log_priority", ""))
            mood = f"{em} tier={tier} priority={pri}" if em else ""
            if compact_http:
                return (
                    f"{ts} | {record.levelname:8} | {record.name} | "
                    f"{mood + ' | ' if mood else ''}"
                    f"application={app_lbl} route_service={route_lbl} "
                    f"method={ha.get('method')} path={ha.get('path')} "
                    f"status_code={code} status_phrase={phrase} "
                    f"response={rsp} "
                    f"static_message={sm} "
                    f"time_ms={float(ha.get('ms', 0)):.2f} "
                    f"read={ha.get('bytes_out')}"
                    f"{' SLOW' if ha.get('slow') else ''}"
                )
            return (
                f"{ts} | {record.levelname:8} | {record.name} | "
                f"{mood + ' | ' if mood else ''}"
                f"HTTP method={ha.get('method')} path={ha.get('path')} "
                f"| application={app_lbl} route_service={route_lbl} "
                f"| status_code={code} status_phrase={phrase} "
                f"| response={rsp} "
                f"| static_message={sm} "
                f"| {float(ha.get('ms', 0)):.2f} ms"
                f" | client={ha.get('client')}"
                f" | req_id={ha.get('request_id')}"
                f" | content_type={ha.get('content_type', '-')}"
                f" | bytes={ha.get('bytes_out')}"
                f" | ua={ha.get('user_agent')}"
                f"{' | SLOW' if ha.get('slow') else ''}"
            )

        ev = getattr(record, "lifecycle_event", None)
        if ev:
            msg = record.getMessage()
            bits = [ts, f"| {record.levelname:8}", f"| {record.name}", "| lifecycle", f"| {ev}", "|", msg]
            if ev == "db_ok":
                bits.append(f"| ping_ms={getattr(record, 'lifecycle_db_ms', '')}")
            elif ev == "db_err":
                bits.append(f"| error={getattr(record, 'lifecycle_db_err', '')}")
            elif ev == "ready":
                bits.append(
                    f"| bind={getattr(record, 'lifecycle_host', '')}:{getattr(record, 'lifecycle_port', '')}"
                )
            elif ev == "engine_down":
                bits.append("| pool=closed")
            return " ".join(bits)

        base = super().format(record)
        eo = getattr(record, "error_origin", None)
        if isinstance(eo, dict):
            rel = (eo.get("file_relative") or "").strip() or eo.get("file_absolute") or "?"
            line_no = eo.get("line", 0)
            fn = eo.get("function", "?")
            return f"{base.rstrip()} | ORIGIN {rel}:{line_no} in {fn}()"
        return base


def _rich_get_time(record: logging.LogRecord) -> Text:
    dt = _ist_datetime(record)
    s = dt.strftime("%d-%m-%Y %H:%M:%S")
    return Text(f"{s} IST", style="dim")


class BeautifulConsoleHandler(logging.Handler):
    # (style, icon) — icon reflects severity: low / medium / high / critical
    _LEVEL_STYLES = {
        "DEBUG": ("dim", "🔹"),
        "INFO": ("cyan", "✨"),
        "WARNING": ("yellow", "🟡"),
        "ERROR": ("bold red", "🔴"),
        "CRITICAL": ("bold white on red", "🆘"),
    }

    _METHOD_ICONS = {
        "GET": "📥",
        "POST": "📤",
        "PUT": "✏️",
        "PATCH": "📋",
        "DELETE": "🗑",
        "HEAD": "👁",
        "OPTIONS": "☰",
    }

    def __init__(self, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        width = min(120, max(80, shutil.get_terminal_size((100, 20)).columns))
        self.console = Console(
            stderr=True,
            force_terminal=sys.stderr.isatty(),
            width=width,
            soft_wrap=True,
            highlight=False,
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._emit(record)
        except Exception:
            self.handleError(record)

    def _emit(self, record: logging.LogRecord) -> None:
        try:
            compact = get_settings().log_compact
        except Exception:
            compact = True

        if compact:
            self._emit_compact(record)
            return

        ev = getattr(record, "lifecycle_event", None)
        if ev:
            self._panel_lifecycle(record, ev)
            return

        ct = getattr(record, "config_table", None)
        if ct:
            self._panel_config(record, ct)
            return

        ha = getattr(record, "http_access", None)
        if isinstance(ha, dict):
            if get_settings().log_rich_http_panel:
                self._panel_http(record, ha, beautiful=False)
            else:
                self._line_http_verbose(record, ha)
            return

        self._line_default(record, framed=False)

    def _emit_compact(self, record: logging.LogRecord) -> None:
        ss = getattr(record, "startup_summary", None)
        if isinstance(ss, dict):
            self._panel_startup_summary(record, ss)
            return

        sd = getattr(record, "shutdown_line", None)
        if isinstance(sd, dict):
            self._panel_shutdown_compact(record, sd)
            return

        ct = getattr(record, "config_table", None)
        if ct:
            self._panel_config(record, ct)
            return

        ha = getattr(record, "http_access", None)
        if isinstance(ha, dict):
            self._panel_http(record, ha, beautiful=True)
            return

        self._line_default(record, framed=True)

    def _panel_startup_summary(self, record: logging.LogRecord, ss: dict[str, Any]) -> None:
        svc = str(ss.get("application") or ss.get("service", ""))
        listen = str(ss.get("listen_url", ""))
        dbn = str(ss.get("database", ""))
        ok = ss.get("db_connected")
        ping = float(ss.get("db_ping_ms", 0))
        border = "green" if ok else "red"
        box_style = box.DOUBLE if ok else box.HEAVY

        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bright_cyan", justify="right", no_wrap=True)
        grid.add_column(ratio=1)

        ok_emoji = "😊" if ok else "😰"
        grid.add_row(f"{ok_emoji} Status", Text("running" if ok else "running (DB failed)", style="bold green" if ok else "bold red"))
        grid.add_row("◆ Application", Text(svc, style="bold white"))
        grid.add_row("🔗 Listen", Text(listen, style="bold bright_blue underline"))
        grid.add_row("🗄 Database", Text(dbn, style="white"))
        conn_cell = Text("connected", style="bold green") if ok else Text("failed", style="bold red")
        grid.add_row("🔌 DB link", conn_cell)
        grid.add_row("⏱ Round-trip", Text(f"{ping:.2f} ms", style="cyan"))

        if not ok and ss.get("db_error"):
            grid.add_row("✖ Error", Text(str(ss.get("db_error")), style="red"))

        title_emoji = "🚀😊" if ok else "🚀⚠️"
        title = Text.assemble(
            (f" {title_emoji} ", "bold green"),
            ("Application ", "bold white"),
            ("online" if ok else "degraded", "bold green" if ok else "bold yellow"),
        )
        self.console.print()
        self.console.print(
            Panel(
                grid,
                title=title,
                title_align="left",
                subtitle=_rich_get_time(record),
                subtitle_align="right",
                border_style=border,
                box=box_style,
                padding=(0, 2),
                width=min(self.console.width, 88),
            )
        )
        self.console.print()

    def _panel_shutdown_compact(self, record: logging.LogRecord, sd: dict[str, Any]) -> None:
        svc = str(sd.get("application") or sd.get("service", ""))
        body = Text.assemble(
            ("🛑 ", "bold yellow"),
            ("Application ", "dim"),
            (svc, "bold cyan"),
            "\n",
            ("   Process stopped gracefully.", "dim"),
        )
        self.console.print(
            Panel.fit(
                body,
                title=Text(" SHUTDOWN ", style="bold black on yellow"),
                subtitle=_rich_get_time(record),
                subtitle_align="right",
                border_style="yellow",
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )

    def _line_http_verbose(self, record: logging.LogRecord, d: dict[str, Any]) -> None:
        ts = _rich_get_time(record)
        status = int(d.get("status", 0))
        st_style = (
            "bold green"
            if 200 <= status < 400
            else "bold yellow"
            if 400 <= status < 500
            else "bold red"
        )
        slow = d.get("slow")
        ms_style = "bold magenta" if slow else "dim green"
        rid = str(d.get("request_id", "-"))
        rid_seg: tuple[str, str] = (rid[:8] + "…", "yellow") if len(rid) > 10 else (rid, "yellow")
        code = d.get("status_code", d.get("status", ""))
        phrase = str(d.get("status_phrase", ""))
        rsp = str(d.get("response", "-"))
        sm = str(d.get("static_message", ""))[:56]
        if len(str(d.get("static_message", ""))) > 56:
            sm += "…"
        emo = str(d.get("log_emoji_tty", ""))
        tier = str(d.get("log_severity_tier", ""))
        pri = str(d.get("log_priority", ""))
        self.console.print(
            Text.assemble(
                ts,
                " ",
                (emo + " ", "") if emo else "",
                (str(d.get("method", "")), "bold white"),
                " ",
                (str(d.get("path", ""))[:56], "cyan"),
                " → ",
                (f"{code} {phrase}".strip(), st_style),
                " ",
                (rsp, "dim cyan"),
                " ",
                (f"{float(d.get('ms', 0)):.1f} ms", ms_style),
                "\n",
                ("   ", "dim"),
                (f"[{tier}/{pri}] ", "dim yellow"),
                (sm, "dim"),
                " ",
                (str(d.get("client", "-")), "dim"),
                " ",
                rid_seg,
            )
        )

    def _panel_lifecycle(self, record: logging.LogRecord, ev: str) -> None:
        ts = _rich_get_time(record)
        if ev == "start":
            title = getattr(record, "lifecycle_title", "")
            body = Text.assemble(
                ("▶ ", "bold green"),
                ("Application starting", "bold white"),
                "\n",
                ("   ", "dim"),
                (repr(title), "cyan"),
            )
            self.console.print(
                Panel.fit(body, title=Text(" RUN ", style="bold white on green"), border_style="green", padding=(0, 2))
            )
        elif ev == "db_ok":
            ms = float(getattr(record, "lifecycle_db_ms", 0))
            self.console.print(
                Panel.fit(
                    Text.assemble(("✓ ", "bold green"), ("Database reachable ", "white"), (f"({ms:.2f} ms)", "dim cyan")),
                    border_style="dim green",
                    padding=(0, 1),
                )
            )
        elif ev == "db_err":
            err = getattr(record, "lifecycle_db_err", "?")
            self.console.print(
                Panel.fit(
                    Text.assemble(("✖ ", "bold red"), ("Database check failed\n", "white"), (err, "red")),
                    border_style="red",
                    padding=(0, 1),
                )
            )
        elif ev == "ready":
            host = getattr(record, "lifecycle_host", "0.0.0.0")
            port = getattr(record, "lifecycle_port", 8000)
            url = f"http://{host}:{port}"
            self.console.print(
                Panel.fit(
                    Text.assemble(("◆ ", "bold bright_blue"), ("Serving at ", "white"), (url, "bold underline bright_cyan")),
                    title=Text(" READY ", style="bold white on bright_blue"),
                    border_style="bright_blue",
                    padding=(0, 2),
                )
            )
        elif ev == "stop":
            self.console.print(
                Panel.fit(
                    Text.assemble(("■ ", "bold yellow"), ("Shutdown initiated", "white")),
                    subtitle=ts,
                    subtitle_align="right",
                    border_style="yellow",
                    padding=(0, 1),
                )
            )
        elif ev == "engine_down":
            self.console.print(
                Text.assemble(
                    ts,
                    " ",
                    ("◇ ", "dim cyan"),
                    ("Database pool closed", "dim"),
                )
            )
        elif ev == "stopped":
            self.console.print(
                Panel.fit(
                    Text.assemble(("● ", "dim"), ("Process exit", "dim")),
                    border_style="dim",
                    padding=(0, 1),
                )
            )
        else:
            self._line_default(record, framed=False)

    def _panel_config(self, record: logging.LogRecord, rows: list[tuple[str, Any]]) -> None:
        table = Table(
            show_header=True,
            header_style="bold bright_cyan",
            border_style="cyan",
            box=box.ROUNDED,
            pad_edge=False,
            expand=True,
        )
        table.add_column("Setting", style="dim", max_width=28, no_wrap=True)
        table.add_column("Value", style="white")
        for key, val in rows:
            table.add_row(key, str(val))
        ts = _rich_get_time(record)
        subtitle = Text.assemble(ts, "  ", (record.name, "dim"))
        self.console.print()
        self.console.print(
            Panel(
                table,
                title=Text.assemble((" ⚙ ", "cyan"), ("CONFIGURATION", "bold white")),
                subtitle=subtitle,
                subtitle_align="right",
                border_style="bright_cyan",
                box=box.DOUBLE,
                padding=(1, 2),
            )
        )
        self.console.print()

    def _panel_http(self, record: logging.LogRecord, d: dict[str, Any], *, beautiful: bool) -> None:
        status = int(d.get("status", 0))
        st_style = "bold green" if 200 <= status < 400 else "bold yellow" if 400 <= status < 500 else "bold red"
        slow = d.get("slow")
        ms = float(d.get("ms", 0))
        ms_style = "bold magenta" if slow else "green"
        method = str(d.get("method", ""))
        m_icon = self._METHOD_ICONS.get(method.upper(), "🌐")
        phrase = str(d.get("status_phrase", ""))

        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bright_cyan", justify="right", no_wrap=True)
        grid.add_column(ratio=1)
        grid.add_row(
            "◆ Application",
            Text(str(d.get("application") or d.get("service", "")), style="bold cyan"),
        )
        grid.add_row("🎯 API route", Text(str(d.get("route_service", "-")), style="bold white"))
        mood = str(d.get("log_emoji_tty", ""))
        tier = str(d.get("log_severity_tier", "-"))
        pri = str(d.get("log_priority", "-"))
        outc = str(d.get("log_outcome", "-"))
        grid.add_row(
            "🎭 Outcome",
            Text.assemble(
                (mood + " ", "") if mood else "",
                (outc, "bold white"),
                ("  ·  ", "dim"),
                ("tier=", "dim"),
                (tier, "cyan"),
                ("  ", "dim"),
                ("priority=", "dim"),
                (pri, "yellow"),
            ),
        )
        grid.add_row(f"{m_icon} Method", Text(method, style="bold bright_white"))
        grid.add_row("📍 Path", Text(str(d.get("path", "")), style="white"))
        grid.add_row(
            "✳ Status",
            Text.assemble(
                (str(status), st_style),
                (" ", "dim"),
                (phrase, "white"),
            ),
        )
        grid.add_row(
            "💬 Message",
            Text(str(d.get("static_message", phrase)), style="dim white", overflow="ellipsis"),
        )
        grid.add_row(
            "📤 Response",
            Text(str(d.get("response", "-")), style="cyan"),
        )
        grid.add_row("⏱ Latency", Text(f"{ms:.2f} ms", style=ms_style))
        grid.add_row("📖 Read", Text(str(d.get("bytes_out", "-")), style="yellow"))
        grid.add_row("📋 Content-Type", Text(str(d.get("content_type", "-")), style="dim"))
        if slow:
            grid.add_row("⚡ Note", Text("Slow request (threshold exceeded)", style="bold magenta"))
        grid.add_row("🖥 Client", Text(str(d.get("client", "-")), style="cyan"))
        grid.add_row("🆔 Request-ID", Text(str(d.get("request_id", "-")), style="yellow"))
        grid.add_row("🧭 User-Agent", Text(str(d.get("user_agent", "-")), style="dim", overflow="ellipsis"))

        subtitle = _rich_get_time(record)
        if 200 <= status < 400:
            border = "bright_blue" if not slow else "magenta"
            bx = box.ROUNDED
        elif 400 <= status < 500:
            border = "yellow"
            bx = box.HEAVY
        else:
            border = "red"
            bx = box.HEAVY

        status_line = f"{status} {phrase}".strip()
        lead = str(d.get("log_emoji_tty", ""))
        title = Text.assemble(
            (lead + " ", "") if lead else "",
            (m_icon + " ", ""),
            ("HTTP ", "bold white"),
            (method, "bold bright_cyan"),
            ("  →  ", "dim"),
            (status_line, st_style),
        )
        if slow:
            title = Text.assemble(title, ("  ⚠", "magenta"))

        panel_kw: dict[str, Any] = {
            "title": title,
            "title_align": "left",
            "subtitle": subtitle,
            "subtitle_align": "right",
            "border_style": border,
            "box": bx,
            "padding": (0, 2) if beautiful else (0, 1),
        }
        if beautiful:
            panel_kw["width"] = min(self.console.width, 100)
        self.console.print(Panel(grid, **panel_kw))

    def _line_default(self, record: logging.LogRecord, *, framed: bool) -> None:
        style, icon = self._LEVEL_STYLES.get(record.levelname, ("white", "·"))
        ts = _rich_get_time(record)
        name = record.name
        name_style = "bright_magenta" if name.startswith("app.") else "dim" if name.startswith("uvicorn") else "magenta"
        msg = record.getMessage()
        line = Text.assemble(
            ts,
            " ",
            (icon + "  ", style),
            ("⟨", "dim"),
            (f"{record.levelname:7}", style),
            ("⟩ ", "dim"),
            (name + " ", name_style),
            (msg, "default"),
        )
        eo = getattr(record, "error_origin", None)
        origin_block: list[Text] = []
        if isinstance(eo, dict):
            rel = (eo.get("file_relative") or "").strip() or eo.get("file_absolute") or "?"
            origin_block.append(
                Text.assemble(
                    ("   📍 ", "dim cyan"),
                    (str(rel), "bold yellow"),
                    (":", "dim"),
                    (str(eo.get("line", 0)), "bold red"),
                    ("  ", "dim"),
                    ("in ", "dim"),
                    (f"{eo.get('function', '?')}()", "bold cyan"),
                )
            )
            code = eo.get("code")
            if code:
                origin_block.append(Text(f"   📄 {code}", style="italic dim"))

        body: Text | Group = Group(line, *origin_block) if origin_block else line

        if framed and record.name.startswith("app.") and sys.stderr.isatty():
            border = {"ERROR": "bold red", "WARNING": "bold yellow", "CRITICAL": "bold red"}.get(
                record.levelname, "cyan"
            )
            self.console.print(
                Panel.fit(
                    body,
                    border_style=border,
                    box=box.ROUNDED,
                    padding=(0, 1),
                )
            )
        else:
            self.console.print(body)


def log_configuration_status(settings: Settings) -> None:
    if not settings.log_config_banner:
        return
    if settings.log_compact:
        return
    log = logging.getLogger("app.lifecycle")
    rows = [
        ("app_name", settings.app_name),
        ("service_display_name", settings.service_display_name or "(uses app_name)"),
        ("api_v1_prefix", settings.api_v1_prefix),
        ("database (async)", _mask_url_password(settings.database_url_async)),
        ("jwt_algorithm", settings.jwt_algorithm),
        (
            "jwt_secret_key",
            f"set ({len(settings.jwt_secret_key)} chars)" if settings.jwt_secret_key else "empty",
        ),
        ("access_token_expire_minutes", settings.access_token_expire_minutes),
        ("cors_origins", settings.cors_origins[:88] + ("…" if len(settings.cors_origins) > 88 else "")),
        ("rate_limit_default", settings.rate_limit_default),
        ("log_level", settings.log_level),
        ("log_compact", settings.log_compact),
        ("log_http_access", settings.log_http_access),
        ("log_lifecycle", settings.log_lifecycle),
        ("log_http_slow_warning_ms", settings.log_http_slow_warning_ms),
        ("log_rich_http_panel", settings.log_rich_http_panel),
        ("log_ws_enabled", settings.log_ws_enabled),
        ("uvicorn_bind", f"{settings.uvicorn_host}:{settings.uvicorn_port}"),
        (
            "seed_admin",
            "yes" if (settings.seed_admin_email and settings.seed_admin_password) else "no",
        ),
    ]
    log.log(logging.INFO, "startup_configuration", extra={"config_table": rows})


def configure_logging(*, log_dir: Path, level: str = "INFO", log_ws_stream: bool = False) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    root = logging.getLogger()
    if root.handlers:
        return

    lvl = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(lvl)

    rich_traceback_install(show_locals=False, width=min(120, shutil.get_terminal_size((100, 20)).columns))

    file_fmt = DetailedFileFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%d-%m-%Y %H:%M:%S",
    )
    fh = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(file_fmt)
    fh.setLevel(lvl)
    root.addHandler(fh)

    ch = BeautifulConsoleHandler(level=lvl)
    root.addHandler(ch)

    if log_ws_stream:
        ws_fmt = DetailedFileFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%d-%m-%Y %H:%M:%S",
        )
        wsh = WebSocketLogHandler(level=lvl)
        wsh.setFormatter(ws_fmt)
        root.addHandler(wsh)

    for noisy in ("httpx", "httpcore", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
