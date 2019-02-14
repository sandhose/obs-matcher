"""CREATE TABLE session_import_file

Revision ID: 78900b2402ca
Revises: d8226cc7fcaf
Create Date: 2018-09-23 21:54:37.893453

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "78900b2402ca"
down_revision = "d8226cc7fcaf"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "session_import_file",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("import_file_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_file_id"],
            ["import_file.id"],
            name="fk_session_import_file_import_file_id_import_file",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["session.id"],
            name="fk_session_import_file_session_id_session",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "session_id", "import_file_id", name="pk_session_import_file"
        ),
    )


def downgrade():
    op.drop_table("session_import_file")
