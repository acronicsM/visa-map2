from geoalchemy2 import Geometry

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NaturalEarthAdmin0(Base):
    """Границы административных единиц Natural Earth 10m (admin_0)."""

    __tablename__ = "natural_earth_admin0"

    adm0_a3: Mapped[str] = mapped_column(String(10), primary_key=True)
    iso2: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bbox_min_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_max_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_min_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_max_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    geom: Mapped[object] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        nullable=True,
    )
    center_point: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )
