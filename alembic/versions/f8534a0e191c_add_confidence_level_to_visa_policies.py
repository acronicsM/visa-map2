"""add confidence_level to visa_policies

Revision ID: f8534a0e191c
Revises: 21f7f1f2e7e2
Create Date: 2026-03-20 12:57:04.290254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8534a0e191c'
down_revision: Union[str, None] = '21f7f1f2e7e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('visa_policies',
        sa.Column(
            'confidence_level',
            sa.Integer(),
            nullable=False,
            server_default='3',
        )
    )
    op.add_column('visa_policies',
        sa.Column('confidence_note', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('visa_policies', 'confidence_note')
    op.drop_column('visa_policies', 'confidence_level')
