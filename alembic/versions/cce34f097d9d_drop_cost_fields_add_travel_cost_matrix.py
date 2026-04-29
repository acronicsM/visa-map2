"""drop cost fields add travel cost matrix

Revision ID: cce34f097d9d
Revises: b2c3d4e5f6a1
Create Date: 2026-04-29 13:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "cce34f097d9d"
down_revision: Union[str, None] = "b2c3d4e5f6a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop obsolete scalar cost columns from countries
    op.drop_column("countries", "cost_updated_at")
    op.drop_column("countries", "cost_per_day_usd")
    op.drop_column("countries", "cost_level")

    # Create travel_cost_matrix table
    op.create_table(
        "travel_cost_matrix",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("home_iso2", sa.String(length=2), nullable=False),
        sa.Column("dest_iso2", sa.String(length=2), nullable=False),
        sa.Column("score_cheap", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("score_normal", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("score_expensive", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column(
            "daily_cost_cheap", sa.Numeric(precision=10, scale=4), nullable=True
        ),
        sa.Column(
            "daily_cost_normal", sa.Numeric(precision=10, scale=4), nullable=True
        ),
        sa.Column(
            "daily_cost_expensive", sa.Numeric(precision=10, scale=4), nullable=True
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("home_iso2", "dest_iso2"),
    )
    op.create_index(
        "ix_travel_cost_matrix_home_iso2",
        "travel_cost_matrix",
        ["home_iso2"],
    )
    op.create_index(
        "ix_travel_cost_matrix_dest_iso2",
        "travel_cost_matrix",
        ["dest_iso2"],
    )


def downgrade() -> None:
    op.drop_index("ix_travel_cost_matrix_dest_iso2", table_name="travel_cost_matrix")
    op.drop_index("ix_travel_cost_matrix_home_iso2", table_name="travel_cost_matrix")
    op.drop_table("travel_cost_matrix")

    op.add_column(
        "countries",
        sa.Column(
            "cost_level",
            sa.String(length=20),
            nullable=True,
        ),
    )
    op.add_column(
        "countries",
        sa.Column("cost_per_day_usd", sa.Integer(), nullable=True),
    )
    op.add_column(
        "countries",
        sa.Column("cost_updated_at", sa.DateTime(timezone=True), nullable=True),
    )