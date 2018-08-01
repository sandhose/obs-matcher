"""Add search_vector to vw_attributes

Revision ID: ca76ae58f2ab
Revises: c5a121398c36
Create Date: 2018-08-01 15:27:37.583118

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'ca76ae58f2ab'
down_revision = 'c5a121398c36'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP MATERIALIZED VIEW vw_attributes")
    op.execute("""\
        CREATE MATERIALIZED VIEW vw_attributes AS
        SELECT crosstab.external_object_id,
               crosstab.titles,
               crosstab.dates,
               crosstab.genres,
               crosstab.durations,
               crosstab.names,
               crosstab.countries,
               setweight(to_tsvector(COALESCE(crosstab.titles[0], '')), 'A') ||
               setweight(to_tsvector(COALESCE(crosstab.titles[1], '')), 'B') ||
               setweight(to_tsvector(COALESCE(crosstab.titles[2], '')), 'C') ||
               setweight(to_tsvector(COALESCE(crosstab.titles[3], '')), 'D') AS search_vector
        FROM crosstab($$
            SELECT value.external_object_id,
                   value.type,
                   array_agg(value.text ORDER BY vw_value_score.score DESC) AS array_agg_1
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


def downgrade():
    pass
