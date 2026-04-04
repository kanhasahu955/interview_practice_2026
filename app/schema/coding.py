from pydantic import ConfigDict
from sqlmodel import Field, SQLModel


class CodingProblemCreate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "### Purpose\n"
                "Create a **coding interview problem** (statement, difficulty, optional starter code).\n\n"
                "### Request body\n"
                "**topic_id** links the problem to a **TOPICS** entry (must exist or **400**).\n\n"
                "### What the API does\n"
                "Stores **problem_md** and metadata; **author**/**admin** only."
            ),
        }
    )

    topic_id: int | None = Field(default=None, description="Optional FK to **topics.id**; required to exist when set.")
    title: str = Field(description="Short problem name.")
    problem_md: str = Field(description="Full problem statement in **Markdown** (examples, constraints).")
    difficulty: str = Field(default="medium", description="Label such as `easy`, `medium`, `hard` (storage string).")
    starter_code: str | None = Field(default=None, description="Optional scaffold code for the candidate.")
    hints_md: str | None = Field(default=None, description="Optional Markdown hints.")


class CodingProblemOut(SQLModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"description": "Coding problem as returned by the API (read or create)."},
    )

    id: int = Field(description="Problem id.")
    topic_id: int | None = Field(description="Linked topic, if any.")
    title: str = Field(description="Problem title.")
    problem_md: str = Field(description="Markdown statement.")
    difficulty: str = Field(description="Difficulty label.")
    starter_code: str | None = Field(description="Starter code snippet if set.")
    hints_md: str | None = Field(description="Hints Markdown if set.")
