"""Initial database initialisation

Revision ID: 38ae01f9bab2
Create Date: 2017-07-26 10:31:24.122264

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '38ae01f9bab2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('external_object',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('type',
                              sa.Enum('PERSON', 'MOVIE', 'EPISODE', 'SEASON',
                                      'SERIE', name='externalobjecttype'),
                              nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('platform_group',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('episode',
                    sa.Column('external_object_id',
                              sa.Integer(), nullable=False),
                    sa.Column('season_id', sa.Integer(), nullable=True),
                    sa.Column('number', sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(['external_object_id'], [
                        'external_object.id'], ),
                    sa.ForeignKeyConstraint(
                        ['season_id'], ['external_object.id'], ),
                    sa.PrimaryKeyConstraint('external_object_id')
                    )
    op.create_table('person',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('external_object_id',
                              sa.Integer(), nullable=False),
                    sa.Column('gender',
                              sa.Enum('NOT_KNOWN', 'MALE', 'FEMALE',
                                      'NOT_APPLICABLE', name='gender'),
                              nullable=False),
                    sa.ForeignKeyConstraint(['external_object_id'], [
                        'external_object.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('platform',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(), nullable=False),
                    sa.Column('slug', sa.String(), nullable=False),
                    sa.Column('group_id', sa.Integer(), nullable=True),
                    sa.Column('url', sa.String(), nullable=True),
                    sa.Column('country', sa.String(length=2), nullable=True),
                    sa.Column('max_rating', sa.Integer(), nullable=True),
                    sa.Column('base_score', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['group_id'], ['platform_group.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('season',
                    sa.Column('external_object_id',
                              sa.Integer(), nullable=False),
                    sa.Column('serie_id', sa.Integer(), nullable=True),
                    sa.Column('number', sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(['external_object_id'], [
                        'external_object.id'], ),
                    sa.ForeignKeyConstraint(
                        ['serie_id'], ['external_object.id'], ),
                    sa.PrimaryKeyConstraint('external_object_id')
                    )
    op.create_table('value',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('type',
                              sa.Enum('TITLE', 'DATE', 'GENRES', 'DURATION',
                                      'NAME', 'COUNTRY', name='value_type'),
                              nullable=False),
                    sa.Column('external_object_id',
                              sa.Integer(), nullable=False),
                    sa.Column('text', sa.String(), nullable=False),
                    sa.ForeignKeyConstraint(['external_object_id'], [
                        'external_object.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('object_link',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('external_object_id',
                              sa.Integer(), nullable=False),
                    sa.Column('platform_id', sa.Integer(), nullable=False),
                    sa.Column('external_id', sa.String(), nullable=True),
                    sa.ForeignKeyConstraint(['external_object_id'], [
                        'external_object.id'], ),
                    sa.ForeignKeyConstraint(
                        ['platform_id'], ['platform.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('role',
                    sa.Column('person_id', sa.Integer(), nullable=False),
                    sa.Column('external_object_id',
                              sa.Integer(), nullable=False),
                    sa.Column('role',
                              sa.Enum('DIRECTOR', 'ACTOR',
                                      'WRITER', name='roletype'),
                              nullable=True),
                    sa.ForeignKeyConstraint(['external_object_id'], [
                        'external_object.id'], ),
                    sa.ForeignKeyConstraint(['person_id'], ['person.id'], ),
                    sa.PrimaryKeyConstraint('person_id', 'external_object_id')
                    )
    op.create_table('scrap',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('platform_id', sa.Integer(), nullable=False),
                    sa.Column('date', sa.DateTime(), nullable=True),
                    sa.Column('status',
                              sa.Enum('SCHEDULED', 'RUNNING', 'ABORTED',
                                      'SUCCESS', 'FAILED', name='scrapstatus'),
                              nullable=False),
                    sa.ForeignKeyConstraint(
                        ['platform_id'], ['platform.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('value_source',
                    sa.Column('id_value', sa.Integer(), nullable=False),
                    sa.Column('id_platform', sa.Integer(), nullable=False),
                    sa.Column('score_factor', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['id_platform'], ['platform.id'], ),
                    sa.ForeignKeyConstraint(['id_value'], ['value.id'], ),
                    sa.PrimaryKeyConstraint('id_value', 'id_platform')
                    )
    op.create_table('object_link_work_meta',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('original_content', sa.Boolean(), nullable=True),
                    sa.Column('rating', sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(['id'], ['object_link.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('scrap_link',
                    sa.Column('scrap_id', sa.Integer(), nullable=False),
                    sa.Column('object_link_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['object_link_id'], [
                                            'object_link.id'], ),
                    sa.ForeignKeyConstraint(['scrap_id'], ['scrap.id'], ),
                    sa.PrimaryKeyConstraint('scrap_id', 'object_link_id')
                    )


def downgrade():
    op.drop_table('scrap_link')
    op.drop_table('object_link_work_meta')
    op.drop_table('value_source')
    op.drop_table('scrap')
    op.drop_table('role')
    op.drop_table('object_link')
    op.drop_table('value')
    op.drop_table('season')
    op.drop_table('platform')
    op.drop_table('person')
    op.drop_table('episode')
    op.drop_table('platform_group')
    op.drop_table('external_object')
