from pydantic import ConfigDict
from sqlmodel import Field, SQLModel


class AnswerCreate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "### Purpose\n"
                "Post an **answer** on an existing question (authenticated user).\n\n"
                "### Request body\n"
                "**body_md** is Markdown; **is_official** marks curated answers when applicable.\n\n"
                "### What the API does\n"
                "Creates an answer row linked to **question_id** from the URL; **404** if question missing."
            ),
        }
    )

    body_md: str = Field(description="Answer text in **Markdown**.")
    is_official: bool = Field(default=False, description="Curated/official answer flag.")


class AnswerOut(SQLModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"description": "Answer row including acceptance state."},
    )

    id: int = Field(description="Answer id.")
    question_id: int = Field(description="Parent question id.")
    author_id: int | None = Field(description="Author user id if known.")
    body_md: str = Field(description="Markdown body.")
    is_official: bool = Field(description="Official/curated flag.")
    accepted: bool = Field(description="True if question owner accepted this answer.")


class QuestionCreate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "### Purpose\n"
                "Ask a new **interview-style question** (authenticated).\n\n"
                "### Request body\n"
                "**topic_id** must reference a real topic when provided (**400** otherwise).\n\n"
                "### What the API does\n"
                "Creates the question owned by the caller; returns it with empty **answers** until posted."
            ),
        }
    )

    topic_id: int | None = Field(default=None, description="Optional **topics.id** for categorization.")
    title: str = Field(description="Short question title.")
    body_md: str = Field(description="Full question text in **Markdown**.")
    difficulty: str = Field(default="medium", description="e.g. easy / medium / hard.")


class QuestionOut(SQLModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "description": "Question with nested **answers** list when the service loads them.",
        },
    )

    id: int = Field(description="Question id.")
    author_id: int | None = Field(description="Asking user id.")
    topic_id: int | None = Field(description="Linked topic id.")
    title: str = Field(description="Question title.")
    body_md: str = Field(description="Markdown body.")
    difficulty: str = Field(description="Difficulty label.")
    answers: list[AnswerOut] = Field(default_factory=list, description="Answers; may be empty on create.")
