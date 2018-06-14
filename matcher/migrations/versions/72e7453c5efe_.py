"""Remove unused tables and columns

Revision ID: 72e7453c5efe
Revises: 112c65f421d9
Create Date: 2018-06-14 11:42:10.045586

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '72e7453c5efe'
down_revision = '112c65f421d9'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('object_link_work_meta')
    op.drop_column('platform', 'max_rating')


def downgrade():
    op.add_column('platform',
                  sa.Column('max_rating', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_table(
        'object_link_work_meta', sa.Column('id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('original_content', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('rating', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['id'], ['object_link.id'], name='object_link_work_meta_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='object_link_work_meta_pkey'))
