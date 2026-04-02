"""drop country_seasons iso2+month unique; add composite index

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-04-01 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "b2c3d4e5f6a1"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_country_seasons_iso2_month",
        "country_seasons",
        type_="unique",
    )
    op.create_index(
        "ix_country_seasons_iso2_month",
        "country_seasons",
        ["iso2", "month"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_country_seasons_iso2_month", table_name="country_seasons")
    op.create_unique_constraint(
        "uq_country_seasons_iso2_month",
        "country_seasons",
        ["iso2", "month"],
    )
