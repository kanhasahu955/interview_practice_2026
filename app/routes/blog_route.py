from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_db
from app.openapi_common import R_401, R_403, R_404, R_409, merge_responses
from app.deps import get_current_user_optional, require_author_or_admin
from app.modules.auth.model import User
from app.schema.blog import BlogPostCreate, BlogPostOut
from app.services.blog_service import get_blog_service


class BlogRoutes:
    def __init__(self) -> None:
        self.router = APIRouter()
        self._svc = get_blog_service()
        self._register()

    def _register(self) -> None:
        r = self.router
        svc = self._svc

        @r.get(
            "/posts",
            response_model=list[BlogPostOut],
            summary="List blog posts",
            description=(
                "### Purpose\n"
                "Read the catalog of posts for the home page or archive.\n\n"
                "### What this endpoint does\n"
                "Returns **BlogPostOut** rows. Optional JWT may change which drafts or posts you see (service rules).\n\n"
                "### Response schema\n"
                "Each item includes **body_md**, **published**, **author_id**, **created_at** (see **BlogPostOut**)."
            ),
            response_description="List of **BlogPostOut**.",
        )
        async def list_posts(
            session: AsyncSession = Depends(get_db),
            user: User | None = Depends(get_current_user_optional),
        ):
            return await svc.list_posts(session, user=user)

        @r.get(
            "/posts/{post_id}",
            response_model=BlogPostOut,
            summary="Get blog post",
            description=(
                "### Purpose\n"
                "Fetch one post’s full Markdown body and metadata.\n\n"
                "### What this endpoint does\n"
                "Loads by **post_id**; **404** if deleted, unknown, or not visible to caller."
            ),
            responses=merge_responses(R_404),
            response_description="Single **BlogPostOut**.",
        )
        async def get_post(
            post_id: int,
            session: AsyncSession = Depends(get_db),
            user: User | None = Depends(get_current_user_optional),
        ):
            post = await svc.get_post(session, post_id, user=user)
            if not post:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
            return post

        @r.post(
            "/posts",
            response_model=BlogPostOut,
            status_code=status.HTTP_201_CREATED,
            summary="Create blog post",
            description=(
                "### Purpose\n"
                "Publish or draft a new article.\n\n"
                "### Request body\n"
                "JSON **BlogPostCreate** — **title**, **slug**, **body_md** (Markdown), **published** flag.\n\n"
                "### Auth\n"
                "**Author** or **admin** JWT.\n\n"
                "### What this endpoint does\n"
                "Sets **author_id** from token, saves post, returns **BlogPostOut** (**201**). **409** on duplicate **slug**."
            ),
            responses=merge_responses(R_401, R_403, R_409),
            response_description="Created **BlogPostOut** (201).",
        )
        async def create_post(
            body: BlogPostCreate,
            session: AsyncSession = Depends(get_db),
            user: User = Depends(require_author_or_admin),
        ):
            try:
                return await svc.create_post(session, body, author=user)
            except ValueError as e:
                if str(e) == "slug_exists":
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug exists") from e
                raise
