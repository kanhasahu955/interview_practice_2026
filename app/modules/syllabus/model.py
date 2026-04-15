from typing import List, Optional
from sqlalchemy import Column, Integer, String, Text

from app.db.columns import fk_bigint, pk_bigint
from sqlmodel import Field, Relationship, SQLModel


class SyllabusModule(SQLModel, table=True):
    __tablename__ = "syllabus_modules"

    id: int | None = Field(default=None, sa_column=pk_bigint())
    title: str = Field(sa_column=Column(String(500), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    sort_order: int = Field(default=0, sa_column=Column(Integer, nullable=False))

    items: List["SyllabusItem"] = Relationship(
        back_populates="module",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "SyllabusItem.sort_order",
        },
    )


class SyllabusItem(SQLModel, table=True):
    __tablename__ = "syllabus_items"

    id: int | None = Field(default=None, sa_column=pk_bigint())
    module_id: int = Field(
        sa_column=fk_bigint("syllabus_modules.id", nullable=False, ondelete="CASCADE"),
    )
    title: str = Field(sa_column=Column(String(500), nullable=False))
    content_md: str = Field(sa_column=Column(Text, nullable=False))
    sort_order: int = Field(default=0, sa_column=Column(Integer, nullable=False))

    module: Optional[SyllabusModule] = Relationship(back_populates="items")
