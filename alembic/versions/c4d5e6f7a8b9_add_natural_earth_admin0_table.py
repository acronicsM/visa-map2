"""add natural_earth_admin0 table

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a1
Create Date: 2026-04-06 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import geoalchemy2
import sqlalchemy as sa


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b2c3d4e5f6a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "natural_earth_admin0",
        sa.Column("adm0_a3", sa.String(length=10), nullable=False),
        sa.Column("iso2", sa.String(length=2), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("bbox_min_lat", sa.Float(), nullable=True),
        sa.Column("bbox_max_lat", sa.Float(), nullable=True),
        sa.Column("bbox_min_lng", sa.Float(), nullable=True),
        sa.Column("bbox_max_lng", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "center_point",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("adm0_a3"),
    )
    op.create_index(
        "ix_natural_earth_admin0_iso2",
        "natural_earth_admin0",
        ["iso2"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_natural_earth_admin0_iso2", table_name="natural_earth_admin0")
    op.drop_table("natural_earth_admin0")
