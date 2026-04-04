"""Mount all domain routers onto the FastAPI app."""

from fastapi import FastAPI

from app.routes.auth_route import AuthRoutes
from app.routes.blog_route import BlogRoutes
from app.routes.coding_route import CodingRoutes
from app.routes.consent_route import router as consent_router
from app.routes.meta_route import MetaRoutes
from app.routes.pages_route import PagesRoutes
from app.routes.qa_route import QARoutes
from app.routes.references_route import ReferencesRoutes
from app.routes.syllabus_route import SyllabusRoutes
from app.routes.topics_route import TopicsRoutes
from app.config import Settings


def mount_routes(app: FastAPI, settings: Settings) -> None:
    v1 = settings.api_v1_prefix
    app.include_router(PagesRoutes(settings).router)
    app.include_router(AuthRoutes().router, prefix=f"{v1}/auth", tags=["AUTH"])
    app.include_router(MetaRoutes().router, prefix=f"{v1}/meta", tags=["META"])
    app.include_router(BlogRoutes().router, prefix=f"{v1}/blog", tags=["BLOG"])
    app.include_router(TopicsRoutes().router, prefix=v1, tags=["TOPICS"])
    app.include_router(SyllabusRoutes().router, prefix=v1, tags=["SYLLABUS"])
    app.include_router(CodingRoutes().router, prefix=v1, tags=["CODING"])
    app.include_router(QARoutes().router, prefix=f"{v1}/qa", tags=["QA"])
    app.include_router(ReferencesRoutes().router, prefix=v1, tags=["REFERENCES"])
    app.include_router(consent_router, prefix=f"{v1}/consent", tags=["CONSENT"])
