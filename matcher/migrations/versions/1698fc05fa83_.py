"""Add comment on ValueSource

Revision ID: 1698fc05fa83
Revises: 67de359fe567
Create Date: 2017-11-13 10:51:22.602694

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1698fc05fa83"
down_revision = "67de359fe567"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("value_source", sa.Column("comment", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("value_source", "comment")
