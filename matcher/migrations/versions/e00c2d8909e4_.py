"""Create value_score and attributes views

Revision ID: e00c2d8909e4
Revises: a862b5ec1efb
Create Date: 2018-06-25 14:49:18.666022

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e00c2d8909e4'
down_revision = 'a862b5ec1efb'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS tablefunc")
    op.execute("""\
        CREATE MATERIALIZED VIEW vw_value_score AS
        SELECT
            value_source.value_id,
            sum(value_source.score_factor * (
                SELECT platform.base_score
                FROM platform
                WHERE platform.id = value_source.platform_id
            )) AS score
        FROM value_source
        GROUP BY value_source.value_id
    """)
    op.execute("""\
        CREATE MATERIALIZED VIEW vw_attributes AS
        SELECT crosstab.external_object_id,
               crosstab.titles,
               crosstab.dates,
               crosstab.genres,
               crosstab.durations,
               crosstab.names,
               crosstab.countries
        FROM crosstab($$
            SELECT value.external_object_id,
                   value.type,
                   array_agg(value.text ORDER BY vw_value_score.score) AS array_agg_1
            FROM value
            JOIN vw_value_score ON value.id = vw_value_score.value_id
            WHERE value.type = 'TITLE'
               OR value.type = 'DATE' AND (value.text ~ '^[1-2]\d\d\d$')
               OR value.type = 'GENRES'
               OR value.type = 'DURATION' AND (value.text ~ '^[0-9.]+$')
               OR value.type = 'NAME'
               OR value.type = 'COUNTRY' AND (value.text ~ '^[A-Z][A-Z]$')
            GROUP BY value.external_object_id, value.type
        $$, $$
            SELECT unnest(ARRAY['TITLE', 'DATE', 'GENRES', 'DURATION', 'NAME', 'COUNTRY']) AS unnest_1
        $$) crosstab(external_object_id integer,
                     titles text[],
                     dates integer[],
                     genres text[],
                     durations double precision[],
                     names text[],
                     countries character(2)[])
    """)

    op.create_index('vw_value_score_pkey', 'vw_value_score', ['value_id'], unique=True)
    op.create_index('vw_attributes_pkey', 'vw_attributes', ['external_object_id'], unique=True)


def downgrade():
    op.drop_index('vw_value_score_pkey')
    op.drop_index('vw_attributes')
    op.execute("DROP MATERIALIZED vw_attributes")
    op.execute("DROP MATERIALIZED vw_value_score")
