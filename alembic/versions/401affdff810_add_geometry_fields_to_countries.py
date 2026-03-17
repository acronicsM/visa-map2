"""add geometry fields to countries

Revision ID: 401affdff810
Revises: c3c18482598f
Create Date: 2026-03-17 13:14:36.995387

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = '401affdff810'
down_revision: Union[str, None] = 'c3c18482598f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('countries', sa.Column('geom',
        geoalchemy2.types.Geometry(
            geometry_type='MULTIPOLYGON', srid=4326,
            from_text='ST_GeomFromEWKT', name='geometry'
        ), nullable=True)
    )
    op.add_column('countries', sa.Column('center_point',
        geoalchemy2.types.Geometry(
            geometry_type='POINT', srid=4326,
            from_text='ST_GeomFromEWKT', name='geometry'
        ), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('countries', 'center_point')
    op.drop_column('countries', 'geom')
    # ### end Alembic commands ###
