import uuid
from datetime import datetime

from geoalchemy2 import Geometry

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    iso2: Mapped[str] = mapped_column(String(2), unique=True, nullable=False, index=True)
    iso3: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)
    numeric_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_native: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    subregion: Mapped[str | None] = mapped_column(String(50), nullable=True)
    capital: Mapped[str | None] = mapped_column(String(100), nullable=True)
    flag_emoji: Mapped[str | None] = mapped_column(String(10), nullable=True)
    flag_svg_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    bbox_min_lat: Mapped[float | None] = mapped_column(nullable=True)
    bbox_max_lat: Mapped[float | None] = mapped_column(nullable=True)
    bbox_min_lng: Mapped[float | None] = mapped_column(nullable=True)
    bbox_max_lng: Mapped[float | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    passports = relationship("Passport", back_populates="country")
    visa_policies_dest = relationship("VisaPolicy", back_populates="destination")

    geom: Mapped[object] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        nullable=True,
    )
    center_point: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )