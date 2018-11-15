"""Update the vw_attributes MATERIALIZED VIEW

Revision ID: fb5e68f0a454
Revises: 78900b2402ca
Create Date: 2018-11-15 16:06:58.523989

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "fb5e68f0a454"
down_revision = "78900b2402ca"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS vw_attributes")
    op.execute(
        "DROP MATERIALIZED VIEW IF EXISTS vw_platform_source_order_by_value_type"
    )
    op.execute("""
        CREATE MATERIALIZED VIEW vw_platform_source_order_by_value_type AS
        SELECT value.external_object_id AS val_eo_id,
               value.type AS val_type,
               platform.id AS pl_id,
               platform.name AS pl_name,
               platform.type AS pl_type,
               max(platform.base_score) AS pl_max_score,
               row_number() OVER (
                PARTITION BY value.external_object_id, value.type
                ORDER BY platform.base_score DESC
               ) AS pl_order
           FROM value
             LEFT JOIN value_source ON value.id = value_source.value_id
             LEFT JOIN platform ON value_source.platform_id = platform.id
          WHERE (
            value.type = 'TITLE'
            OR value.type = 'DATE' AND value.text ~ '^[1-2]\\d\\d\\d$'
            OR value.type = 'GENRES'
            OR value.type = 'DURATION' AND value.text ~ '^[0-9.]+$'
            OR value.type = 'NAME'
            OR value.type = 'COUNTRY' AND value.text ~ '^[A-Z]{2}$'
          ) AND value_source.value_id IS NOT NULL
          GROUP BY value.external_object_id,
                   value.type,
                   platform.id,
                   platform.name,
                   platform.type
    """)
    op.execute("""
        CREATE UNIQUE INDEX
        IF NOT EXISTS ix_vw_platform_source_order_by_value_type_eo_type_pl
        ON vw_platform_source_order_by_value_type
        USING btree (val_eo_id, val_type, pl_id)
    """)
    op.execute("""
        CREATE INDEX
        IF NOT EXISTS ix_vw_platform_source_order_by_value_type_order_type_eo
        ON vw_platform_source_order_by_value_type
        USING btree (pl_order, val_type, val_eo_id)
    """)
    op.execute("""
        CREATE MATERIALIZED VIEW vw_attributes AS
        SELECT crosstab.external_object_id,
            crosstab.titles,
            crosstab.dates,
            crosstab.genres,
            crosstab.durations,
            crosstab.names,
            crosstab.countries,
            (setweight(to_tsvector(COALESCE(crosstab.titles[0], '')), 'A') ||
             setweight(to_tsvector(COALESCE(crosstab.titles[1], '')), 'B') ||
             setweight(to_tsvector(COALESCE(crosstab.titles[2], '')), 'C') ||
             setweight(to_tsvector(COALESCE(crosstab.titles[3], '')), 'D')) AS search_vector
        FROM crosstab($$
            SELECT value.external_object_id,
                   value.type,
                   coalesce(array_agg(value.text ORDER BY vw_value_score.score DESC),
                            CAST('{}' AS TEXT[])) AS coalesce_1
            FROM value
            JOIN vw_value_score ON value.id = vw_value_score.value_id
            JOIN value_source ON value.id = value_source.value_id
            WHERE (
                value.type = 'TITLE'
                OR value.type = 'DATE' AND (value.text ~ '^[1-2]\\d\\d\\d$')
                OR value.type = 'GENRES'
                OR value.type = 'DURATION' AND (value.text ~ '^[0-9.]+$')
                OR value.type = 'NAME'
                OR value.type = 'COUNTRY' AND (value.text ~ '^[A-Z]{2}$')
            ) AND (value.external_object_id,
                   value.type,
                   value_source.platform_id) IN (
                SELECT vw_platform_source_order_by_value_type.val_eo_id,
                       vw_platform_source_order_by_value_type.val_type,
                       vw_platform_source_order_by_value_type.pl_id
            FROM vw_platform_source_order_by_value_type
            WHERE vw_platform_source_order_by_value_type.pl_order = 1
              AND (vw_platform_source_order_by_value_type.pl_type = 'INFO'
                   OR vw_platform_source_order_by_value_type.val_type = 'TITLE')
            )
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
    op.execute("""
        CREATE UNIQUE INDEX
        IF NOT EXISTS pk_vw_attributes
        ON vw_attributes
        USING btree (external_object_id)
    """)


def downgrade():
    pass
