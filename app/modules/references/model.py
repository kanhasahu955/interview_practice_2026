from sqlalchemy import Column, Integer, String, Text

from app.db.columns import fk_bigint, pk_bigint
from sqlmodel import Field, SQLModel


class Reference(SQLModel, table=True):
    __tablename__ = "references_tbl"

    id: int | None = Field(default=None, sa_column=pk_bigint())
    topic_id: int | None = Field(
        default=None,
        sa_column=fk_bigint("learning_topics.id", nullable=True, ondelete="SET NULL"),
    )
    title: str = Field(sa_column=Column(String(500), nullable=False))
    url: str = Field(sa_column=Column(String(2000), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
