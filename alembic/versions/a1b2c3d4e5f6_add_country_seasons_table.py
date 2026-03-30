"""add country_seasons table

Revision ID: a1b2c3d4e5f6
Revises: ee9d6012051f
Create Date: 2026-03-30 16:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
from geoalchemy2 import Geometry
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "ee9d6012051f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "country_seasons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("country_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("iso2", sa.String(length=2), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=32), nullable=False),
        sa.Column(
            "geom",
            Geometry(geometry_type="MULTIPOLYGON", srid=4326),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["country_id"], ["countries.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("iso2", "month", name="uq_country_seasons_iso2_month"),
        sa.CheckConstraint(
            "month BETWEEN 1 AND 12",
            name="ck_country_seasons_month_range",
        ),
    )
    op.create_index(
        op.f("ix_country_seasons_country_id"),
        "country_seasons",
        ["country_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_country_seasons_iso2"),
        "country_seasons",
        ["iso2"],
        unique=False,
    )
    op.create_index(
        op.f("ix_country_seasons_season"),
        "country_seasons",
        ["season"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_country_seasons_season"), table_name="country_seasons")
    op.drop_index(op.f("ix_country_seasons_iso2"), table_name="country_seasons")
    op.drop_index(op.f("ix_country_seasons_country_id"), table_name="country_seasons")
    op.drop_table("country_seasons")
