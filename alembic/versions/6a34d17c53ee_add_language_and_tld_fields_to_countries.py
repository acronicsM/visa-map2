"""add language and tld fields to countries

Revision ID: 6a34d17c53ee
Revises: 9a80b20cab00
Create Date: 2026-03-20 12:31:33.290735

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '6a34d17c53ee'
down_revision: Union[str, None] = '9a80b20cab00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('countries', sa.Column('primary_language', sa.String(50), nullable=True))
    op.add_column('countries', sa.Column('language_code', sa.String(10), nullable=True))
    op.add_column('countries', sa.Column('country_tld', sa.String(10), nullable=True))
    op.add_column('countries', sa.Column('search_keywords', postgresql.JSONB(), nullable=True))
    op.add_column('countries', sa.Column('confidence_level', sa.Integer(), nullable=False, server_default='3'))


def downgrade() -> None:
    op.drop_column('countries', 'confidence_level')
    op.drop_column('countries', 'search_keywords')
    op.drop_column('countries', 'country_tld')
    op.drop_column('countries', 'language_code')
    op.drop_column('countries', 'primary_language')
