"""Rename materialized view

Revision ID: 3e39f93ee858
Revises: a3d7caa535a7
Create Date: 2020-04-08 15:21:43.670771

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3e39f93ee858"
down_revision = "a3d7caa535a7"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER MATERIALIZED VIEW " \
        "vw_platform_source_order_by_value_type " \
        "RENAME TO " \
        "vw_000_platform_source_order_by_value_type"
    )


def downgrade():
    op.execute(
        "ALTER MATERIALIZED VIEW " \
        "vw_000_platform_source_order_by_value_type " \
        "RENAME TO " \
        "vw_platform_source_order_by_value_type"
    )
