"""redesign country language fields

Revision ID: 21f7f1f2e7e2
Revises: 6a34d17c53ee
Create Date: 2026-03-20 12:46:53.099390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '21f7f1f2e7e2'
down_revision: Union[str, None] = '6a34d17c53ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('countries', sa.Column('language_name', sa.String(50), nullable=True))
    op.add_column('countries', sa.Column('all_languages', postgresql.JSONB(), nullable=True))
    op.add_column('countries', sa.Column('name_translations', postgresql.JSONB(), nullable=True))
    op.alter_column('countries', 'primary_language',
        existing_type=sa.String(50),
        type_=sa.String(10),
    )


def downgrade() -> None:
    op.drop_column('countries', 'name_translations')
    op.drop_column('countries', 'all_languages')
    op.drop_column('countries', 'language_name')
    op.alter_column('countries', 'primary_language',
        existing_type=sa.String(10),
        type_=sa.String(50),
    )
