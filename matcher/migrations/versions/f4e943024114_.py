"""Add ExportFileLog table

Revision ID: f4e943024114
Revises: a7655b33b7d1
Create Date: 2018-07-24 09:28:48.201642

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f4e943024114"
down_revision = "a7655b33b7d1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "export_file_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("export_file_id", sa.Integer(), nullable=False),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "SCHEDULED",
                "QUERYING",
                "PROCESSING",
                "DONE",
                "FAILED",
                name="exportfilestatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("message", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["export_file_id"],
            ["export_file.id"],
            name="fk_export_file_log_export_file_id_export_file",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_export_file_log"),
    )


def downgrade():
    op.drop_table("export_file_log")
