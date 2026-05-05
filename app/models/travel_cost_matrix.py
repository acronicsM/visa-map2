import uuid
from datetime import datetime

from sqlalchemy import func, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, NUMERIC

from app.database import Base


class TravelCostMatrix(Base):
    __tablename__ = "travel_cost_matrix"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    home_iso2: Mapped[str] = mapped_column(
        String(2), nullable=False, index=True
    )
    dest_iso2: Mapped[str] = mapped_column(
        String(2), nullable=False, index=True
    )
    score_cheap: Mapped[float | None] = mapped_column(
        NUMERIC(10, 4), nullable=True
    )
    score_normal: Mapped[float | None] = mapped_column(
        NUMERIC(10, 4), nullable=True
    )
    score_expensive: Mapped[float | None] = mapped_column(
        NUMERIC(10, 4), nullable=True
    )
    daily_cost_cheap: Mapped[float | None] = mapped_column(
        NUMERIC(10, 4), nullable=True
    )
    daily_cost_normal: Mapped[float | None] = mapped_column(
        NUMERIC(10, 4), nullable=True
    )
    daily_cost_expensive: Mapped[float | None] = mapped_column(
        NUMERIC(10, 4), nullable=True
    )
    home_currency: Mapped[str | None] = mapped_column(
        String(3), nullable=True
    )
    income_daily: Mapped[float | None] = mapped_column(
        NUMERIC(12, 4), nullable=True
    )
    income_daily_usd: Mapped[float | None] = mapped_column(
        NUMERIC(12, 4), nullable=True
    )
    usd_to_home_rate: Mapped[float | None] = mapped_column(
        NUMERIC(18, 8), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )