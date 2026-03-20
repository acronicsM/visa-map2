"""add source_discovery_log table

Revision ID: 739c122ab692
Revises: f8534a0e191c
Create Date: 2026-03-20 13:44:42.551458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '739c122ab692'
down_revision: Union[str, None] = 'f8534a0e191c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'source_discovery_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('country_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('discovered_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('query_used', sa.Text(), nullable=True),
        sa.Column('total_results', sa.Integer(), nullable=True),
        sa.Column('domains_found', postgresql.JSONB(), nullable=True),
        sa.Column('top_domains', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='done'),
        sa.ForeignKeyConstraint(['country_id'], ['countries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_source_discovery_country', 'source_discovery_log', ['country_id'])


def downgrade() -> None:
    op.drop_index('ix_source_discovery_country', table_name='source_discovery_log')
    op.drop_table('source_discovery_log')
