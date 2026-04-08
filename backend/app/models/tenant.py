from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import BaseModel, TimestampMixin


class Tenant(TimestampMixin, BaseModel):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    collections = relationship(
        "Collection", back_populates="tenant", cascade="all, delete-orphan"
    )
    chat_sessions = relationship(
        "ChatSession", back_populates="tenant", cascade="all, delete-orphan"
    )
