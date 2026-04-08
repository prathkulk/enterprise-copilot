from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import BaseModel, TimestampMixin


class Collection(TimestampMixin, BaseModel):
    __tablename__ = "collections"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_collections_tenant_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant = relationship("Tenant", back_populates="collections")
    documents = relationship(
        "Document", back_populates="collection", cascade="all, delete-orphan"
    )
