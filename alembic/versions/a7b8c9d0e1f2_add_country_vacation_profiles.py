"""add country vacation profiles and exotic scores

Revision ID: a7b8c9d0e1f2
Revises: f4b9a7c1d2e3
Create Date: 2026-05-19 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f4b9a7c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "country_vacation_profiles",
        sa.Column("iso2", sa.String(length=2), nullable=False),
        sa.Column(
            "beach_score",
            sa.Numeric(precision=10, scale=6),
            nullable=True,
        ),
        sa.Column(
            "ski_score",
            sa.Numeric(precision=10, scale=6),
            nullable=True,
        ),
        sa.Column(
            "food_score",
            sa.Numeric(precision=10, scale=6),
            nullable=True,
        ),
        sa.Column(
            "natural_score",
            sa.Numeric(precision=10, scale=6),
            nullable=True,
        ),
        sa.Column(
            "culture_score",
            sa.Numeric(precision=10, scale=6),
            nullable=True,
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
            ["iso2"],
            ["countries.iso2"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("iso2"),
    )

    op.create_table(
        "country_vacation_exotic_scores",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("home_iso2", sa.String(length=2), nullable=False),
        sa.Column("dest_iso2", sa.String(length=2), nullable=False),
        sa.Column(
            "score",
            sa.Numeric(precision=10, scale=6),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("home_iso2", "dest_iso2"),
    )
    op.create_index(
        "ix_country_vacation_exotic_home_iso2",
        "country_vacation_exotic_scores",
        ["home_iso2"],
    )
    op.create_index(
        "ix_country_vacation_exotic_dest_iso2",
        "country_vacation_exotic_scores",
        ["dest_iso2"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_country_vacation_exotic_dest_iso2",
        table_name="country_vacation_exotic_scores",
    )
    op.drop_index(
        "ix_country_vacation_exotic_home_iso2",
        table_name="country_vacation_exotic_scores",
    )
    op.drop_table("country_vacation_exotic_scores")
    op.drop_table("country_vacation_profiles")
