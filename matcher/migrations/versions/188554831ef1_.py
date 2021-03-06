"""Add platform type

Revision ID: 188554831ef1
Revises: b92cc5e6eb8d
Create Date: 2017-11-20 11:57:02.611768

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "188554831ef1"
down_revision = "b92cc5e6eb8d"
branch_labels = None
depends_on = None


def upgrade():
    platformtype = postgresql.ENUM(
        "INFO", "GLOBAL", "TVOD", "SVOD", name="platformtype"
    )
    platformtype.create(op.get_bind())

    op.add_column(
        "platform",
        sa.Column(
            "type",
            sa.Enum("INFO", "GLOBAL", "TVOD", "SVOD", name="platformtype"),
            server_default="INFO",
            nullable=False,
        ),
    )


def downgrade():
    op.drop_column("platform", "type")
