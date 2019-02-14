"""empty message

Revision ID: 50396abcbfe3
Revises: ca76ae58f2ab
Create Date: 2018-08-07 09:41:43.333323

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "50396abcbfe3"
down_revision = "ca76ae58f2ab"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "import_file",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "UPLOADED", "PROCESSING", "DONE", "FAILED", name="importfilestatus"
            ),
            nullable=False,
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("fields", postgresql.HSTORE(text_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_import_file"),
    )
    op.create_table(
        "import_file_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_file_id", sa.Integer(), nullable=False),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "UPLOADED", "PROCESSING", "DONE", "FAILED", name="importfilestatus"
            ),
            nullable=False,
        ),
        sa.Column("message", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["import_file_id"],
            ["import_file.id"],
            name="fk_import_file_log_import_file_id_import_file",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_import_file_log"),
    )


def downgrade():
    op.drop_table("import_file_log")
    op.drop_table("import_file")
