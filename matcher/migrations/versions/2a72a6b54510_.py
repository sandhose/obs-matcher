"""Add effective_date to import_file

Revision ID: 2a72a6b54510
Revises: b779d70f6c2a
Create Date: 2019-03-12 11:29:13.292811

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select


# revision identifiers, used by Alembic.
revision = "2a72a6b54510"
down_revision = "b779d70f6c2a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("import_file", sa.Column("effective_date", sa.Date(), nullable=True))
    files = table("import_file", column("id"), column("effective_date"))
    logs = table(
        "import_file_log",
        column("import_file_id"),
        column("timestamp"),
        column("status"),
    )
    upload_date = (
        select([logs.c.timestamp])
        .where(files.c.id == logs.c.import_file_id)
        .where(column("status") == "UPLOADED")
        .limit(1)
    )
    update_stmt = files.update().values(effective_date=upload_date)
    op.execute(update_stmt)
    op.alter_column("import_file", "effective_date", nullable=False)


def downgrade():
    op.drop_column("import_file", "effective_date")
