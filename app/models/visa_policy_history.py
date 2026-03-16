import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VisaPolicyHistory(Base):
    __tablename__ = "visa_policy_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("visa_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visa_category: Mapped[str] = mapped_column(String(20), nullable=False)
    max_stay_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    changed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    policy = relationship("VisaPolicy", back_populates="history")