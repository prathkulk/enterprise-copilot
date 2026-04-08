from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import BaseModel, TimestampMixin


class Collection(TimestampMixin, BaseModel):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    documents = relationship(
        "Document", back_populates="collection", cascade="all, delete-orphan"
    )
