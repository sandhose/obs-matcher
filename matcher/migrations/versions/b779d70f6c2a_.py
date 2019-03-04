"""Add metadatas on provider platforms

Revision ID: b779d70f6c2a
Revises: 990f9d007c11
Create Date: 2019-02-22 12:58:04.997839

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b779d70f6c2a"
down_revision = "990f9d007c11"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("provider_platform", sa.Column("home_url", sa.Text(), nullable=True))
    op.add_column(
        "provider_platform",
        sa.Column("public", sa.Boolean(), nullable=False, server_default="t"),
    )


def downgrade():
    op.drop_column("provider_platform", "public")
    op.drop_column("provider_platform", "home_url")
