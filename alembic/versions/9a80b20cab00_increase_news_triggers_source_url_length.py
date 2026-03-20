"""increase news_triggers source_url length

Revision ID: 9a80b20cab00
Revises: ecd035397484
Create Date: 2026-03-19 18:50:23.233162

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a80b20cab00'
down_revision: Union[str, None] = 'ecd035397484'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'news_triggers',
        'source_url',
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'news_triggers',
        'source_url',
        type_=sa.String(500),
        existing_nullable=True,
    )
