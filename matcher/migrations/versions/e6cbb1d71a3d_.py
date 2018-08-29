"""Add ImportFile.platform_id & imported_external_object_type

Revision ID: e6cbb1d71a3d
Revises: 50396abcbfe3
Create Date: 2018-08-27 13:46:40.908958

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e6cbb1d71a3d'
down_revision = '50396abcbfe3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('import_file', sa.Column('platform_id', sa.Integer(), nullable=True))
    op.create_foreign_key(op.f('fk_import_file_platform_id_platform'),
                          'import_file', 'platform', ['platform_id'], ['id'])
    op.add_column('import_file',
                  sa.Column('imported_external_object_type',
                            sa.Enum('PERSON', 'MOVIE', 'EPISODE', 'SERIES',
                                    name='externalobjecttype'),
                            nullable=True))


def downgrade():
    op.drop_constraint(op.f('fk_import_file_platform_id_platform'), 'import_file', type_='foreignkey')
    op.drop_column('import_file', 'platform_id')
    op.drop_column('import_file', 'imported_external_object_type')
