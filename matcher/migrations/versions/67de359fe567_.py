"""Drop the person.id column and move Role.person FK

Revision ID: 67de359fe567
Revises: 38ae01f9bab2
Create Date: 2017-10-05 22:11:52.767457

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '67de359fe567'
down_revision = '38ae01f9bab2'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('role_person_id_fkey', 'role', type_='foreignkey')
    op.drop_column('person', 'id')
    op.create_foreign_key('role_person_id_fkey', 'role', 'external_object', ['person_id'], ['id'])


def downgrade():
    op.drop_constraint('role_person_id_fkey', 'role', type_='foreignkey')
    op.add_column('person', sa.Column('id', sa.INTEGER(),
                                      server_default=sa.text("nextval('person_id_seq'::regclass)"),
                                      nullable=False))
    op.create_foreign_key('role_person_id_fkey', 'role', 'person', ['person_id'], ['id'])
