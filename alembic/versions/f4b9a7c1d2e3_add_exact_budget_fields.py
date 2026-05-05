"""add exact budget fields to travel cost matrix

Revision ID: f4b9a7c1d2e3
Revises: 812a8b6ae206
Create Date: 2026-05-04 14:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4b9a7c1d2e3"
down_revision: Union[str, None] = "812a8b6ae206"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "travel_cost_matrix",
        sa.Column("home_currency", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "travel_cost_matrix",
        sa.Column("income_daily", sa.Numeric(precision=12, scale=4), nullable=True),
    )
    op.add_column(
        "travel_cost_matrix",
        sa.Column(
            "income_daily_usd",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
        ),
    )
    op.add_column(
        "travel_cost_matrix",
        sa.Column(
            "usd_to_home_rate",
            sa.Numeric(precision=18, scale=8),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("travel_cost_matrix", "usd_to_home_rate")
    op.drop_column("travel_cost_matrix", "income_daily_usd")
    op.drop_column("travel_cost_matrix", "income_daily")
    op.drop_column("travel_cost_matrix", "home_currency")
