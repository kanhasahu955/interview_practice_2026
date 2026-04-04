from pydantic import ConfigDict
from sqlmodel import Field, SQLModel


class ReferenceCreate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "### Purpose\n"
                "Add a curated **reference** (link + notes) tied to an optional **topic**.\n\n"
                "### Request body\n"
                "**url** is required (max length enforced); **topic_id** must exist if set (**400**).\n\n"
                "### What the API does\n"
                "Persists the reference for readers; **author**/**admin** only."
            ),
        }
    )

    topic_id: int | None = Field(default=None, description="Optional **topics.id** for grouping.")
    title: str = Field(description="Short label for the link.")
    url: str = Field(max_length=2000, description="Full URL to article, video, or doc.")
    description: str | None = Field(default=None, description="Optional Markdown or plain note about the link.")


class ReferenceOut(SQLModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"description": "Stored reference returned from list/detail/create."},
    )

    id: int = Field(description="Reference id.")
    topic_id: int | None = Field(description="Topic grouping.")
    title: str = Field(description="Link title.")
    url: str = Field(description="Target URL.")
    description: str | None = Field(description="Optional description.")
