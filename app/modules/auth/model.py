import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, String, func

from app.db.columns import pk_bigint
from sqlmodel import Field, SQLModel


class UserRole(str, enum.Enum):
    learner = "learner"
    author = "author"
    admin = "admin"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, sa_column=pk_bigint())
    email: str = Field(sa_column=Column(String(320), unique=True, index=True, nullable=False))
    hashed_password: str = Field(sa_column=Column(String(255), nullable=False))
    full_name: str | None = Field(default=None, sa_column=Column(String(200), nullable=True))
    role: UserRole = Field(
        default=UserRole.learner,
        sa_column=Column(SAEnum(UserRole), nullable=False),
    )
    is_active: bool = Field(default=True)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
