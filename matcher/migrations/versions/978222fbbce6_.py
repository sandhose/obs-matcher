"""Change platform.url type to JSONB

Revision ID: 978222fbbce6
Revises: 1698fc05fa83
Create Date: 2017-11-16 14:13:46.024989

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '978222fbbce6'
down_revision = '1698fc05fa83'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('platform', 'url')
    op.add_column('platform', sa.Column('url', JSONB(), nullable=True))


def downgrade():
    op.drop_column('platform', 'url')
    op.add_column('platform', sa.Column('url', sa.String(), nullable=True))
