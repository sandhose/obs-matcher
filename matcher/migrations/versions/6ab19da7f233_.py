"""Fix attributes order in vw_attributes view

Revision ID: 6ab19da7f233
Revises: f4e943024114
Create Date: 2018-07-24 16:32:00.584979

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "6ab19da7f233"
down_revision = "f4e943024114"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP MATERIALIZED VIEW vw_attributes")
    op.execute(
        """\
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
                   array_agg(value.text ORDER BY vw_value_score.score DESC) AS array_agg_1
            FROM value
            JOIN vw_value_score ON value.id = vw_value_score.value_id
            WHERE value.type = 'TITLE'
               OR value.type = 'DATE' AND (value.text ~ '^[1-2]\\d\\d\\d$')
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
    """
    )


def downgrade():
    pass
