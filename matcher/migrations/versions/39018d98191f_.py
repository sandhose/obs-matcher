"""Add more platforms metadata

Revision ID: 39018d98191f
Revises: eafcc26b16be
Create Date: 2018-01-15 14:30:13.037014

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "39018d98191f"
down_revision = "eafcc26b16be"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "platform",
        sa.Column(
            "allow_links_overlap", sa.Boolean(), server_default="FALSE", nullable=False
        ),
    )
    op.add_column(
        "platform",
        sa.Column(
            "ignore_in_exports", sa.Boolean(), server_default="FALSE", nullable=False
        ),
    )


def downgrade():
    op.drop_column("platform", "ignore_in_exports")
    op.drop_column("platform", "allow_links_overlap")
