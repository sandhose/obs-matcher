"""Add stats field to scraps

Revision ID: b92cc5e6eb8d
Revises: 978222fbbce6
Create Date: 2017-11-18 00:33:05.360416

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b92cc5e6eb8d"
down_revision = "978222fbbce6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "scrap",
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade():
    op.drop_column("scrap", "stats")
