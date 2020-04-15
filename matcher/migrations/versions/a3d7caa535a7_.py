"""Add AVOD service type

Revision ID: a3d7caa535a7
Revises: 01cc4353c886
Create Date: 2020-03-30 14:59:39.130111

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "a3d7caa535a7"
down_revision = "01cc4353c886"
branch_labels = None
depends_on = None


def upgrade():
    op.sync_enum_values(
        "public",
        "platformtype",
        ["GLOBAL", "INFO", "SVOD", "TVOD"],
        ["AVOD", "GLOBAL", "INFO", "SVOD", "TVOD"],
    )


def downgrade():
    op.sync_enum_values(
        "public",
        "platformtype",
        ["AVOD", "GLOBAL", "INFO", "SVOD", "TVOD"],
        ["GLOBAL", "INFO", "SVOD", "TVOD"],
    )
