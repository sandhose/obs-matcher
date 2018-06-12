"""Fix inconsistency in value_source columns name

Revision ID: 112c65f421d9
Revises: 152dea884d0d
Create Date: 2018-06-11 15:19:39.712443

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '112c65f421d9'
down_revision = '152dea884d0d'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('episode', 'serie_id', new_column_name='series_id')
    op.drop_constraint('episode_serie_id_fkey', 'episode', type_='foreignkey')
    op.create_foreign_key(None, 'episode', 'external_object', ['series_id'], ['id'])

    op.alter_column('value_source', 'id_platform', new_column_name='platform_id')
    op.alter_column('value_source', 'id_value', new_column_name='value_id')
    op.drop_constraint('value_source_id_value_fkey', 'value_source', type_='foreignkey')
    op.drop_constraint('value_source_id_platform_fkey', 'value_source', type_='foreignkey')
    op.create_foreign_key(None, 'value_source', 'platform', ['platform_id'], ['id'])
    op.create_foreign_key(None, 'value_source', 'value', ['value_id'], ['id'])


def downgrade():
    op.alter_column('episode', 'series_id', new_column_name='serie_id')
    op.drop_constraint('episode_series_id_fkey', 'episode', type_='foreignkey')
    op.create_foreign_key(None, 'episode', 'external_object', ['serie_id'], ['id'])

    op.alter_column('value_source', 'platform_id', new_column_name='id_platform')
    op.alter_column('value_source', 'value_id', new_column_name='id_value')
    op.drop_constraint('value_source_value_id_fkey', 'value_source', type_='foreignkey')
    op.drop_constraint('value_source_platform_id_fkey', 'value_source', type_='foreignkey')
    op.create_foreign_key(None, 'value_source', 'platform', ['id_platform'], ['id'])
    op.create_foreign_key(None, 'value_source', 'value', ['id_value'], ['id'])
