from pydantic import ConfigDict
from sqlmodel import Field, SQLModel


class TopicCreate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "### Purpose\n"
                "Create a **topic** — the taxonomy label shared by blog posts, coding problems, references, and Q&A.\n\n"
                "### Request body\n"
                "All fields below; **slug** is a URL-safe unique key, **title** is human-readable.\n\n"
                "### What the API does\n"
                "Inserts a topic row after checking **slug** uniqueness (**409** if taken)."
            ),
        }
    )

    slug: str = Field(max_length=200, description="Unique URL-safe identifier (e.g. `system-design`).")
    title: str = Field(max_length=500, description="Display name shown in UI and docs.")
    summary: str | None = Field(default=None, description="Optional short blurb for listings.")
    sort_order: int = Field(default=0, description="Lower numbers list first when ordering by this field.")


class TopicOut(SQLModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "description": (
                "### Purpose\n"
                "Single topic as stored in the database — use **id** as **topic_id** on other resources."
            ),
        },
    )

    id: int = Field(description="Primary key; reference from blog, coding, references, QA.")
    slug: str = Field(description="Stable slug matching create request.")
    title: str = Field(description="Human-readable title.")
    summary: str | None = Field(description="Optional summary text.")
    sort_order: int = Field(description="Sort position for curated lists.")
