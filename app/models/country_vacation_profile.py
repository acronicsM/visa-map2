import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import NUMERIC, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CountryVacationProfile(Base):
    __tablename__ = "country_vacation_profiles"

    iso2: Mapped[str] = mapped_column(
        String(2),
        ForeignKey("countries.iso2", ondelete="CASCADE"),
        primary_key=True,
    )
    beach_score: Mapped[float | None] = mapped_column(
        NUMERIC(10, 6),
        nullable=True,
    )
    ski_score: Mapped[float | None] = mapped_column(
        NUMERIC(10, 6),
        nullable=True,
    )
    food_score: Mapped[float | None] = mapped_column(
        NUMERIC(10, 6),
        nullable=True,
    )
    natural_score: Mapped[float | None] = mapped_column(
        NUMERIC(10, 6),
        nullable=True,
    )
    culture_score: Mapped[float | None] = mapped_column(
        NUMERIC(10, 6),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CountryVacationExoticScore(Base):
    __tablename__ = "country_vacation_exotic_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    home_iso2: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True,
    )
    dest_iso2: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True,
    )
    score: Mapped[float] = mapped_column(NUMERIC(10, 6), nullable=False)
