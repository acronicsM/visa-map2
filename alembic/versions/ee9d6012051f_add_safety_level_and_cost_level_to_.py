"""add safety_level and cost_level to countries

Revision ID: ee9d6012051f
Revises: 739c122ab692
Create Date: 2026-03-30 14:31:53.789469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee9d6012051f'
down_revision: Union[str, None] = '739c122ab692'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "countries",
        sa.Column(
            "safety_level",
            sa.String(length=20),
            nullable=True,
            comment="safe / unsafe / dangerous",
        ),
    )
    op.add_column(
        "countries",
        sa.Column("safety_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "countries",
        sa.Column("safety_source", sa.Text(), nullable=True),
    )
    op.add_column(
        "countries",
        sa.Column("safety_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "countries",
        sa.Column(
            "cost_level",
            sa.String(length=20),
            nullable=True,
            comment="low / medium / high",
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


def downgrade() -> None:
    op.drop_column("countries", "cost_updated_at")
    op.drop_column("countries", "cost_per_day_usd")
    op.drop_column("countries", "cost_level")
    op.drop_column("countries", "safety_updated_at")
    op.drop_column("countries", "safety_source")
    op.drop_column("countries", "safety_note")
    op.drop_column("countries", "safety_level")
