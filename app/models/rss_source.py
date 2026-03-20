import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RssSource(Base):
    __tablename__ = "rss_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    lang: Mapped[str] = mapped_column(String(5), nullable=False, default="en")
    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="news_agency",
    )
    country_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    requires_filter: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    fetch_frequency: Mapped[str] = mapped_column(
        String(10), default="daily", nullable=False
    )
    keywords: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    query_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    country = relationship("Country", back_populates="rss_sources")