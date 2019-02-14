"""Create import_link table

Revision ID: d8226cc7fcaf
Revises: e6cbb1d71a3d
Create Date: 2018-08-31 08:18:52.895486

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d8226cc7fcaf"
down_revision = "e6cbb1d71a3d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "import_link",
        sa.Column("import_file_id", sa.Integer(), nullable=False),
        sa.Column("object_link_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_file_id"],
            ["import_file.id"],
            name=op.f("fk_import_link_import_file_id_import_file"),
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["object_link_id"],
            ["object_link.id"],
            name=op.f("fk_import_link_object_link_id_object_link"),
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "import_file_id", "object_link_id", name=op.f("pk_import_link")
        ),
    )


def downgrade():
    op.drop_table("import_link")
