"""
FastAPI application shell: lifespan, static mounts, middleware stack, routers.
Packages live under `app/` (`app.routes`, `app.services`, `app.modules`, …).
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.config.openapi_documentation import (
    attach_standard_error_openapi_schema,
    build_openapi_description,
    openapi_contact,
    openapi_license,
    openapi_servers,
    openapi_tags_metadata,
    read_package_version,
    swagger_ui_modern_parameters,
)
from app.config.logging_setup import configure_logging, database_name_from_url, log_configuration_status
from app.constant import ApiConstants
from app.db import AsyncSessionLocal, create_db_and_tables, engine
from app.db.health import ping_database
from app.middlewares import register_middleware_stack
from app.logging.stream_hub import attach_log_stream_loop, detach_log_stream_loop
from app.routes.logs_ws_route import router as logs_ws_router
from app.routes.main_route import mount_routes
from app.routes.scalar_reference import router as scalar_reference_router
from app.services.auth_service import get_auth_service
from app.utils.concurrency import shutdown_executor

log = logging.getLogger(__name__)
lifecycle = logging.getLogger("app.lifecycle")


def _application_label(settings: Settings) -> str:
    return settings.service_display_name.strip() or settings.app_name


def _ensure_runtime_dirs(settings: Settings) -> None:
    for p in (
        settings.media_root,
        settings.upload_root,
        settings.logs_root,
        settings.topics_root,
        settings.static_root,
        settings.templates_root,
    ):
        p.mkdir(parents=True, exist_ok=True)


def create_app() -> FastAPI:
    settings = get_settings()

    async def application_startup() -> None:
        """Runs once before the server accepts traffic: dirs, logging, DB, seed, lifecycle lines."""
        log_configuration_status(settings)

        if settings.log_lifecycle and not settings.log_compact:
            lifecycle.info(
                "boot",
                extra={"lifecycle_event": "start", "lifecycle_title": settings.app_name},
            )

        await create_db_and_tables()

        db_ok, db_ms, db_err = await ping_database(engine)

        if settings.seed_admin_email and settings.seed_admin_password:
            async with AsyncSessionLocal() as session:
                await get_auth_service().seed_admin_if_needed(
                    session,
                    email=settings.seed_admin_email,
                    password=settings.seed_admin_password,
                )

        listen_url = f"http://{settings.uvicorn_host}:{settings.uvicorn_port}"
        db_name = database_name_from_url(settings.database_url_async)

        if settings.log_lifecycle:
            if settings.log_compact:
                lifecycle.info(
                    "startup",
                    extra={
                        "startup_summary": {
                            "application": _application_label(settings),
                            "listen_url": listen_url,
                            "database": db_name,
                            "db_connected": db_ok,
                            "db_ping_ms": db_ms,
                            "db_error": db_err,
                        }
                    },
                )
            else:
                if db_ok:
                    lifecycle.info(
                        "database ping ok",
                        extra={"lifecycle_event": "db_ok", "lifecycle_db_ms": db_ms},
                    )
                else:
                    lifecycle.error(
                        "database ping failed",
                        extra={
                            "lifecycle_event": "db_err",
                            "lifecycle_db_err": db_err or "unknown",
                        },
                    )
                lifecycle.info(
                    "listening",
                    extra={
                        "lifecycle_event": "ready",
                        "lifecycle_host": settings.uvicorn_host,
                        "lifecycle_port": settings.uvicorn_port,
                    },
                )

    async def application_shutdown() -> None:
        """Runs when the process is stopping: log shutdown, close DB pool, background executor."""
        if settings.log_lifecycle:
            if settings.log_compact:
                lifecycle.info(
                    "shutdown",
                    extra={"shutdown_line": {"application": _application_label(settings)}},
                )
            else:
                lifecycle.info("shutdown", extra={"lifecycle_event": "stop"})

        await engine.dispose()

        if settings.log_lifecycle and not settings.log_compact:
            lifecycle.info("engine disposed", extra={"lifecycle_event": "engine_down"})

        shutdown_executor()

        if settings.log_lifecycle and not settings.log_compact:
            lifecycle.info("exit", extra={"lifecycle_event": "stopped"})

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Pre-loop: filesystem + logging + WebSocket log hub (must run before any log fan-out).
        _ensure_runtime_dirs(settings)
        configure_logging(
            log_dir=settings.logs_root,
            level=settings.log_level,
            log_ws_stream=settings.log_ws_enabled,
        )
        if settings.log_ws_enabled:
            attach_log_stream_loop(asyncio.get_running_loop())
        try:
            await application_startup()
            yield
            await application_shutdown()
        finally:
            detach_log_stream_loop()

    app = FastAPI(
        title=settings.app_name,
        summary="Learning platform HTTP API",
        description=build_openapi_description(settings),
        version=read_package_version(),
        openapi_tags=openapi_tags_metadata(),
        contact=openapi_contact(),
        license_info=openapi_license(),
        servers=openapi_servers(settings),
        swagger_ui_parameters=swagger_ui_modern_parameters(),
        lifespan=lifespan,
    )
    register_middleware_stack(app, settings)

    @app.get(
        ApiConstants.HEALTH_PATH,
        tags=["HEALTH"],
        summary="Liveness probe",
        description='Returns JSON {"status": "ok"} while the ASGI worker is running. Does not check the database.',
        response_description="Static JSON payload for proxies and orchestrators.",
    )
    async def root_health():
        return {"status": "ok"}

    docs_path = settings.project_root / "documents"
    if docs_path.is_dir():
        app.mount(
            ApiConstants.DOCUMENTS_MOUNT_PATH,
            StaticFiles(directory=str(docs_path)),
            name="documents_md",
        )

    if settings.static_root.is_dir():
        app.mount(
            ApiConstants.STATIC_MOUNT_PATH,
            StaticFiles(directory=str(settings.static_root)),
            name="site_static",
        )

    if settings.media_root.is_dir():
        app.mount(
            ApiConstants.MEDIA_MOUNT_PATH,
            StaticFiles(directory=str(settings.media_root)),
            name="media_pdfs",
        )

    if settings.topics_root.is_dir():
        app.mount(
            ApiConstants.STUDY_TOPICS_MOUNT_PATH,
            StaticFiles(directory=str(settings.topics_root)),
            name="study_topics",
        )

    mount_routes(app, settings)
    if settings.log_ws_enabled:
        app.include_router(logs_ws_router)
    app.include_router(scalar_reference_router)
    attach_standard_error_openapi_schema(app)
    return app
