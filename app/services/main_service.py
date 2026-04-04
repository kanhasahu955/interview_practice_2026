"""
Central import surface for domain services (singletons).

Use `get_*_service()` from each module for FastAPI Depends, or import this
registry when you want a single object holding all domains.
"""

from app.services.auth_service import AuthService, get_auth_service
from app.services.blog_service import BlogService, get_blog_service
from app.services.coding_service import CodingService, get_coding_service
from app.services.meta_service import MetaService, get_meta_service
from app.services.qa_service import QAService, get_qa_service
from app.services.references_service import ReferencesService, get_references_service
from app.services.syllabus_service import SyllabusService, get_syllabus_service
from app.services.topics_service import TopicsService, get_topics_service


class ServiceRegistry:
    __slots__ = (
        "auth",
        "blog",
        "coding",
        "meta",
        "qa",
        "references",
        "syllabus",
        "topics",
    )

    def __init__(self) -> None:
        self.auth = get_auth_service()
        self.blog = get_blog_service()
        self.topics = get_topics_service()
        self.syllabus = get_syllabus_service()
        self.coding = get_coding_service()
        self.qa = get_qa_service()
        self.references = get_references_service()
        self.meta = get_meta_service()


_registry: ServiceRegistry | None = None


def get_registry() -> ServiceRegistry:
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry


__all__ = [
    "AuthService",
    "BlogService",
    "CodingService",
    "MetaService",
    "QAService",
    "ReferencesService",
    "ServiceRegistry",
    "SyllabusService",
    "TopicsService",
    "get_auth_service",
    "get_blog_service",
    "get_coding_service",
    "get_meta_service",
    "get_qa_service",
    "get_references_service",
    "get_registry",
    "get_syllabus_service",
    "get_topics_service",
]
