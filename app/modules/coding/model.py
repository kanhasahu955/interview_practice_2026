from sqlalchemy import Column, Integer, String, Text

from app.db.columns import fk_bigint, pk_bigint
from sqlmodel import Field, SQLModel


class CodingProblem(SQLModel, table=True):
    __tablename__ = "coding_problems"

    id: int | None = Field(default=None, sa_column=pk_bigint())
    topic_id: int | None = Field(
        default=None,
        sa_column=fk_bigint("learning_topics.id", nullable=True, ondelete="SET NULL"),
    )
    title: str = Field(sa_column=Column(String(500), nullable=False))
    problem_md: str = Field(sa_column=Column(Text, nullable=False))
    difficulty: str = Field(default="medium", sa_column=Column(String(32), nullable=False))
    starter_code: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    hints_md: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
