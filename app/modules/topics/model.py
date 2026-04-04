from sqlalchemy import Column, Integer, String, Text, UniqueConstraint

from app.db.columns import pk_bigint
from sqlmodel import Field, SQLModel


class LearningTopic(SQLModel, table=True):
    __tablename__ = "learning_topics"
    __table_args__ = (UniqueConstraint("slug", name="uq_topic_slug"),)

    id: int | None = Field(default=None, sa_column=pk_bigint())
    slug: str = Field(sa_column=Column(String(200), nullable=False, index=True))
    title: str = Field(sa_column=Column(String(500), nullable=False))
    summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    sort_order: int = Field(default=0, sa_column=Column(Integer, nullable=False))
