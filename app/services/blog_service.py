from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.auth.model import User, UserRole
from app.modules.blog.model import BlogPost
from app.schema.blog import BlogPostCreate


class BlogService:
    async def list_posts(self, session: AsyncSession, *, user: User | None) -> list[BlogPost]:
        stmt = select(BlogPost).order_by(BlogPost.created_at.desc())
        if user is None or user.role == UserRole.learner:
            stmt = stmt.where(BlogPost.published.is_(True))
        r = await session.exec(stmt)
        return r.all()

    async def get_post(self, session: AsyncSession, post_id: int, *, user: User | None) -> BlogPost | None:
        post = await session.get(BlogPost, post_id)
        if not post:
            return None
        if post.published:
            return post
        if user is None:
            return None
        if user.role == UserRole.admin or post.author_id == user.id:
            return post
        return None

    async def get_post_by_slug(self, session: AsyncSession, slug: str, *, user: User | None) -> BlogPost | None:
        stmt = select(BlogPost).where(BlogPost.slug == slug)
        post = (await session.exec(stmt)).first()
        if not post:
            return None
        if post.published:
            return post
        if user is None:
            return None
        if user.role == UserRole.admin or post.author_id == user.id:
            return post
        return None

    async def create_post(self, session: AsyncSession, body: BlogPostCreate, *, author: User) -> BlogPost:
        r = await session.exec(select(BlogPost).where(BlogPost.slug == body.slug))
        if r.first():
            raise ValueError("slug_exists")
        post = BlogPost(
            author_id=author.id,
            title=body.title,
            slug=body.slug,
            body_md=body.body_md,
            published=body.published,
        )
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post


_blog: BlogService | None = None


def get_blog_service() -> BlogService:
    global _blog
    if _blog is None:
        _blog = BlogService()
    return _blog
