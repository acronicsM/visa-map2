"""update rss_sources add source_type keywords frequency

Revision ID: ecd035397484
Revises: dc6bca580272
Create Date: 2026-03-19 18:32:11.459207

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ecd035397484'
down_revision: Union[str, None] = 'dc6bca580272'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('rss_sources',
        sa.Column('source_type',
            sa.String(20),
            nullable=False,
            server_default='news_agency'
        )
    )
    op.add_column('rss_sources',
        sa.Column('requires_filter',
            sa.Boolean(),
            nullable=False,
            server_default='true'
        )
    )
    op.add_column('rss_sources',
        sa.Column('fetch_frequency',
            sa.String(10),
            nullable=False,
            server_default='daily'
        )
    )
    op.add_column('rss_sources',
        sa.Column('keywords',
            postgresql.JSONB(),
            nullable=True
        )
    )
    op.add_column('rss_sources',
        sa.Column('query_template',
            sa.Text(),
            nullable=True
        )
    )


def downgrade() -> None:
    op.drop_column('rss_sources', 'query_template')
    op.drop_column('rss_sources', 'keywords')
    op.drop_column('rss_sources', 'fetch_frequency')
    op.drop_column('rss_sources', 'requires_filter')
    op.drop_column('rss_sources', 'source_type')
