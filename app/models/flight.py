import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Airport(Base):
    __tablename__ = "airports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    openflights_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    iata: Mapped[str | None] = mapped_column(
        String(3), nullable=True, unique=True, index=True
    )
    icao: Mapped[str | None] = mapped_column(String(4), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    city_normalized: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country_iso2: Mapped[str | None] = mapped_column(
        String(2),
        ForeignKey("countries.iso2", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    latitude: Mapped[float | None] = mapped_column(NUMERIC(10, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(NUMERIC(10, 6), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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


class FlightRoute(Base):
    __tablename__ = "flight_routes"
    __table_args__ = (
        UniqueConstraint(
            "source_iata",
            "dest_iata",
            "airline",
            name="uq_flight_routes_source_dest_airline",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_iata: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    dest_iata: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    airline: Mapped[str | None] = mapped_column(String(10), nullable=True)
    stops: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_codeshare: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class CountryHubAirport(Base):
    __tablename__ = "country_hub_airports"
    __table_args__ = (
        UniqueConstraint("country_iso2", "iata", name="uq_country_hub_airports"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    country_iso2: Mapped[str] = mapped_column(
        String(2),
        ForeignKey("countries.iso2", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    iata: Mapped[str] = mapped_column(String(3), nullable=False)
    route_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class FlightDirectCache(Base):
    __tablename__ = "flight_direct_cache"

    city_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    source: Mapped[str] = mapped_column(String(32), primary_key=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country_iso2: Mapped[str] = mapped_column(String(2), nullable=False)
    origin_airports: Mapped[list] = mapped_column(JSONB, nullable=False)
    direct_countries: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )


class FlightCityRequestStats(Base):
    __tablename__ = "flight_city_request_stats"

    city_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country_iso2: Mapped[str] = mapped_column(String(2), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
