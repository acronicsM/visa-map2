from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f02359424756'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'countries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('iso2', sa.String(2), nullable=False),
        sa.Column('iso3', sa.String(3), nullable=False),
        sa.Column('numeric_code', sa.Integer(), nullable=True),
        sa.Column('name_ru', sa.String(100), nullable=False),
        sa.Column('name_en', sa.String(100), nullable=False),
        sa.Column('name_native', sa.String(100), nullable=True),
        sa.Column('region', sa.String(50), nullable=True),
        sa.Column('subregion', sa.String(50), nullable=True),
        sa.Column('capital', sa.String(100), nullable=True),
        sa.Column('flag_emoji', sa.String(10), nullable=True),
        sa.Column('flag_svg_url', sa.String(255), nullable=True),
        sa.Column('description_ru', sa.Text(), nullable=True),
        sa.Column('description_en', sa.Text(), nullable=True),
        sa.Column('bbox_min_lat', sa.Float(), nullable=True),
        sa.Column('bbox_max_lat', sa.Float(), nullable=True),
        sa.Column('bbox_min_lng', sa.Float(), nullable=True),
        sa.Column('bbox_max_lng', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iso2'),
        sa.UniqueConstraint('iso3'),
    )
    op.create_index('ix_countries_iso2', 'countries', ['iso2'])


def downgrade() -> None:
    op.drop_index('ix_countries_iso2', table_name='countries')
    op.drop_table('countries')