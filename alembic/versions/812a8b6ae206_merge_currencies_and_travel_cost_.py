"""merge currencies and travel_cost branches

Revision ID: 812a8b6ae206
Revises: e1f2a3b4c5d6, cce34f097d9d
Create Date: 2026-04-29 14:16:11.565418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '812a8b6ae206'
down_revision: Union[str, None] = ('e1f2a3b4c5d6', 'cce34f097d9d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
