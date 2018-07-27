"""Adjust the ExportFileStatus

Revision ID: c5a121398c36
Revises: 6ab19da7f233
Create Date: 2018-07-27 09:52:59.905388

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c5a121398c36'
down_revision = '6ab19da7f233'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('export_file', 'status',
                    existing_type=postgresql.ENUM('SCHEDULED', 'QUERYING', 'PROCESSING', 'DONE', 'FAILED',
                                                  name='exportfilestatus'),
                    nullable=False,
                    existing_server_default=sa.text("'SCHEDULED'::exportfilestatus"))
    op.alter_column('export_template', 'fields',
                    existing_type=postgresql.JSONB(astext_type=sa.Text()),
                    nullable=False)
    op.sync_enum_values('public', 'exportfilestatus',
                        ['DONE', 'FAILED', 'PROCESSING', 'QUERYING', 'SCHEDULED'],
                        ['ABSENT', 'DONE', 'FAILED', 'PROCESSING', 'QUERYING', 'SCHEDULED'])


def downgrade():
    # FIXME: downgrade probably does not work
    op.sync_enum_values('public', 'exportfilestatus',
                        ['ABSENT', 'DONE', 'FAILED', 'PROCESSING', 'QUERYING', 'SCHEDULED'],
                        ['DONE', 'FAILED', 'PROCESSING', 'QUERYING', 'SCHEDULED'])
    op.alter_column('export_template', 'fields',
                    existing_type=postgresql.JSONB(astext_type=sa.Text()),
                    nullable=True)
    op.alter_column('export_file', 'status',
                    existing_type=postgresql.ENUM('SCHEDULED', 'QUERYING', 'PROCESSING',
                                                  'DONE', 'FAILED', name='exportfilestatus'),
                    nullable=True,
                    existing_server_default=sa.text("'SCHEDULED'::exportfilestatus"))
