"""add flight tables for direct routes

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-05-22 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "airports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("openflights_id", sa.Integer(), nullable=True),
        sa.Column("iata", sa.String(length=3), nullable=True),
        sa.Column("icao", sa.String(length=4), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("city_normalized", sa.String(length=100), nullable=False),
        sa.Column("country_name", sa.String(length=100), nullable=True),
        sa.Column("country_iso2", sa.String(length=2), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
            ["country_iso2"],
            ["countries.iso2"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_airports_iata", "airports", ["iata"], unique=True)
    op.create_index("ix_airports_city_normalized", "airports", ["city_normalized"])
    op.create_index("ix_airports_country_iso2", "airports", ["country_iso2"])
    op.create_index(
        "ix_airports_country_city",
        "airports",
        ["country_iso2", "city_normalized"],
    )

    op.create_table(
        "flight_routes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source_iata", sa.String(length=3), nullable=False),
        sa.Column("dest_iata", sa.String(length=3), nullable=False),
        sa.Column("airline", sa.String(length=10), nullable=True),
        sa.Column("stops", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_codeshare",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_iata",
            "dest_iata",
            "airline",
            name="uq_flight_routes_source_dest_airline",
        ),
    )
    op.create_index("ix_flight_routes_source_iata", "flight_routes", ["source_iata"])
    op.create_index("ix_flight_routes_dest_iata", "flight_routes", ["dest_iata"])

    op.create_table(
        "country_hub_airports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("country_iso2", sa.String(length=2), nullable=False),
        sa.Column("iata", sa.String(length=3), nullable=False),
        sa.Column("route_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(
            ["country_iso2"],
            ["countries.iso2"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "country_iso2",
            "iata",
            name="uq_country_hub_airports",
        ),
    )
    op.create_index(
        "ix_country_hub_airports_country_iso2",
        "country_hub_airports",
        ["country_iso2"],
    )

    op.create_table(
        "flight_direct_cache",
        sa.Column("city_key", sa.String(length=200), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("country_iso2", sa.String(length=2), nullable=False),
        sa.Column("origin_airports", postgresql.JSONB(), nullable=False),
        sa.Column("direct_countries", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("city_key", "source"),
    )
    op.create_index(
        "ix_flight_direct_cache_expires_at",
        "flight_direct_cache",
        ["expires_at"],
    )

    op.create_table(
        "flight_city_request_stats",
        sa.Column("city_key", sa.String(length=200), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("country_iso2", sa.String(length=2), nullable=False),
        sa.Column(
            "request_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("last_requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("city_key"),
    )


def downgrade() -> None:
    op.drop_table("flight_city_request_stats")
    op.drop_index("ix_flight_direct_cache_expires_at", table_name="flight_direct_cache")
    op.drop_table("flight_direct_cache")
    op.drop_index(
        "ix_country_hub_airports_country_iso2",
        table_name="country_hub_airports",
    )
    op.drop_table("country_hub_airports")
    op.drop_index("ix_flight_routes_dest_iata", table_name="flight_routes")
    op.drop_index("ix_flight_routes_source_iata", table_name="flight_routes")
    op.drop_table("flight_routes")
    op.drop_index("ix_airports_country_city", table_name="airports")
    op.drop_index("ix_airports_country_iso2", table_name="airports")
    op.drop_index("ix_airports_city_normalized", table_name="airports")
    op.drop_index("ix_airports_iata", table_name="airports")
    op.drop_table("airports")
