from typing import List, Optional
from sqlalchemy import Boolean, Column, Integer, String, Text

from app.db.columns import fk_bigint, pk_bigint
from sqlmodel import Field, Relationship, SQLModel


class Question(SQLModel, table=True):
    __tablename__ = "questions"

    id: int | None = Field(default=None, sa_column=pk_bigint())
    author_id: int | None = Field(
        default=None,
        sa_column=fk_bigint("users.id", nullable=True, ondelete="SET NULL"),
    )
    topic_id: int | None = Field(
        default=None,
        sa_column=fk_bigint("learning_topics.id", nullable=True, ondelete="SET NULL"),
    )
    title: str = Field(sa_column=Column(String(500), nullable=False))
    body_md: str = Field(sa_column=Column(Text, nullable=False))
    difficulty: str = Field(default="medium", sa_column=Column(String(32), nullable=False))

    answers: List["Answer"] = Relationship(
        back_populates="question",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Answer(SQLModel, table=True):
    __tablename__ = "answers"

    id: int | None = Field(default=None, sa_column=pk_bigint())
    question_id: int = Field(
        sa_column=fk_bigint("questions.id", nullable=False, ondelete="CASCADE"),
    )
    author_id: int | None = Field(
        default=None,
        sa_column=fk_bigint("users.id", nullable=True, ondelete="SET NULL"),
    )
    body_md: str = Field(sa_column=Column(Text, nullable=False))
    is_official: bool = Field(default=False, sa_column=Column(Boolean, nullable=False))
    accepted: bool = Field(default=False, sa_column=Column(Boolean, nullable=False))

    question: Optional[Question] = Relationship(back_populates="answers")
