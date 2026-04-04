from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, UniqueConstraint, func

from app.db.columns import fk_bigint, pk_bigint
from sqlmodel import Field, SQLModel


class BlogPost(SQLModel, table=True):
    __tablename__ = "blog_posts"
    __table_args__ = (UniqueConstraint("slug", name="uq_blog_slug"),)

    id: int | None = Field(default=None, sa_column=pk_bigint())
    author_id: int | None = Field(
        default=None,
        sa_column=fk_bigint("users.id", nullable=True, ondelete="SET NULL"),
    )
    title: str = Field(sa_column=Column(String(500), nullable=False))
    slug: str = Field(sa_column=Column(String(500), nullable=False, index=True))
    body_md: str = Field(sa_column=Column(Text, nullable=False))
    published: bool = Field(default=False)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )
