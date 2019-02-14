"""Adjust ExportFileStatus type

Revision ID: a7655b33b7d1
Revises: f9cf022e4e05
Create Date: 2018-07-24 08:21:31.272963

"""
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a7655b33b7d1"
down_revision = "f9cf022e4e05"
branch_labels = None
depends_on = None


def upgrade():
    # Rename the old type
    op.execute("ALTER TYPE exportfilestatus RENAME TO exportfilestatus_old")

    # Create the new one
    exportfilestatus = postgresql.ENUM(
        "SCHEDULED", "QUERYING", "PROCESSING", "DONE", "FAILED", name="exportfilestatus"
    )
    exportfilestatus.create(op.get_bind())

    # Adjust the column
    op.execute(
        """
        ALTER TABLE export_file
        ALTER COLUMN status
        DROP DEFAULT,
        ALTER COLUMN status
        TYPE exportfilestatus
        USING
          CASE
              WHEN status='PROCESSING'::exportfilestatus_old THEN 'SCHEDULED'::exportfilestatus
              WHEN status='DONE'::exportfilestatus_old THEN 'DONE'::exportfilestatus
          END,
        ALTER COLUMN status
        SET DEFAULT 'SCHEDULED'::exportfilestatus
    """
    )

    # Drop the old type
    op.execute("DROP TYPE exportfilestatus_old")


def downgrade():
    # Re-create the old type
    exportfilestatus = postgresql.ENUM(
        "SCHEDULED", "PROCESSING", name="exportfilestatus_old"
    )
    exportfilestatus.create(op.get_bind())

    # Adjust the column
    op.execute(
        """
        ALTER TABLE export_file
        ALTER COLUMN status
        DROP DEFAULT,
        ALTER COLUMN status
        TYPE exportfilestatus_old
        USING
          CASE
            WHEN status='DONE' THEN 'DONE'::exportfilestatus_old
            ELSE 'PROCESSING'::exportfilestatus_old
          END,
        ALTER COLUMN status
        SET DEFAULT 'PROCESSING'::exportfilestatus_old
    """
    )

    # Drop the new type
    op.execute("DROP TYPE exportfilestatus")

    # Rename back the old one
    op.execute("ALTER TYPE exportfilestatus_old RENAME TO exportfilestatus")
