import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VisaPolicy(Base):
    __tablename__ = "visa_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    passport_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("passports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visa_category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    max_stay_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visa_validity_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fee_usd: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    confidence_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3
    )
    
    confidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    passport = relationship("Passport", back_populates="visa_policies")
    destination = relationship("Country", back_populates="visa_policies_dest")
    history = relationship("VisaPolicyHistory", back_populates="policy")