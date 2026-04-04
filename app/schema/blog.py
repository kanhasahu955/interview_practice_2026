from datetime import datetime

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel


class BlogPostCreate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "### Purpose\n"
                "Create a **blog post** authored by the authenticated **author** or **admin**.\n\n"
                "### Request body\n"
                "**body_md** is Markdown; **slug** must be unique across posts.\n\n"
                "### What the API does\n"
                "Persists the post, ties it to the caller as author, returns the saved record (**201**). "
                "**409** if **slug** collides."
            ),
        }
    )

    title: str = Field(max_length=500, description="Post headline.")
    slug: str = Field(max_length=500, description="Unique per post; used in URLs and APIs.")
    body_md: str = Field(description="Full article body in **Markdown**.")
    published: bool = Field(default=False, description="If false, treat as draft (visibility rules depend on service).")


class BlogPostOut(SQLModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "description": (
                "### Purpose\n"
                "Blog post returned from list/detail/create — includes author linkage and timestamps."
            ),
        },
    )

    id: int = Field(description="Post primary key.")
    author_id: int | None = Field(description="User id of author; null if legacy data.")
    title: str = Field(description="Post title.")
    slug: str = Field(description="Unique slug.")
    body_md: str = Field(description="Markdown body as stored.")
    published: bool = Field(description="Published vs draft flag.")
    created_at: datetime = Field(description="Creation time (UTC).")
