from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_db
from app.openapi_common import R_401, R_403, R_404, R_409, merge_responses
from app.deps import require_roles
from app.modules.auth.model import User, UserRole
from app.schema.topics import TopicCreate, TopicOut
from app.services.topics_service import get_topics_service


class TopicsRoutes:
    def __init__(self) -> None:
        self.router = APIRouter()
        self._svc = get_topics_service()
        self._register()

    def _register(self) -> None:
        r = self.router
        svc = self._svc

        @r.get(
            "/topics",
            response_model=list[TopicOut],
            summary="List topics",
            description=(
                "### Purpose\n"
                "Browse every **topic** for UI pickers and navigation.\n\n"
                "### What this endpoint does\n"
                "Returns **TopicOut** objects (see schema: id, slug, title, summary, sort_order). No auth required."
            ),
            response_description="Array of **TopicOut** — use **id** as foreign key elsewhere.",
        )
        async def list_topics(session: AsyncSession = Depends(get_db)):
            return await svc.list_topics(session)

        @r.get(
            "/topics/{topic_id}",
            response_model=TopicOut,
            summary="Get topic by id",
            description=(
                "### Purpose\n"
                "Load one topic by **topic_id** path parameter.\n\n"
                "### What this endpoint does\n"
                "Looks up the row; returns **TopicOut** or **404**."
            ),
            responses=merge_responses(R_404),
            response_description="Single **TopicOut** matching the path id.",
        )
        async def get_topic(topic_id: int, session: AsyncSession = Depends(get_db)):
            t = await svc.get_topic(session, topic_id)
            if not t:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
            return t

        @r.post(
            "/topics",
            response_model=TopicOut,
            status_code=status.HTTP_201_CREATED,
            summary="Create topic",
            description=(
                "### Purpose\n"
                "Define a new taxonomy node used by blog, coding, references, and Q&A.\n\n"
                "### Request body\n"
                "JSON **TopicCreate** — field-level docs are in the schema panel below.\n\n"
                "### Auth\n"
                "**Author** or **admin** JWT required.\n\n"
                "### What this endpoint does\n"
                "Validates **slug** uniqueness, inserts, returns **TopicOut** (**201**). **409** if slug exists."
            ),
            responses=merge_responses(R_401, R_403, R_409),
            response_description="Created **TopicOut** (HTTP 201).",
        )
        async def create_topic(
            body: TopicCreate,
            session: AsyncSession = Depends(get_db),
            _: User = Depends(require_roles(UserRole.author)),
        ):
            try:
                return await svc.create_topic(session, body)
            except ValueError as e:
                if str(e) == "slug_exists":
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug exists") from e
                raise
