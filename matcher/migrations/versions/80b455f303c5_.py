"""Rename indexes to match the naming convention

Revision ID: 80b455f303c5
Revises: e00c2d8909e4
Create Date: 2018-07-09 13:16:19.742943

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "80b455f303c5"
down_revision = "e00c2d8909e4"
branch_labels = None
depends_on = None

primary_keys = [
    "episode",
    "external_object",
    "object_link",
    "platform_group",
    "platform",
    "role",
    "scrap_link",
    "scrap",
    "value",
    "value_source",
    "vw_attributes",
    "vw_value_score",
]

foreign_keys = [
    ("episode", "external_object_id", "external_object"),
    ("episode", "series_id", "external_object"),
    ("object_link", "external_object_id", "external_object"),
    ("object_link", "platform_id", "platform"),
    ("person", "external_object_id", "external_object"),
    ("platform", "group_id", "platform_group"),
    ("role", "external_object_id", "external_object"),
    ("role", "person_id", "external_object"),
    ("scrap", "platform_id", "platform"),
    ("scrap_link", "object_link_id", "object_link"),
    ("scrap_link", "scrap_id", "scrap"),
    ("value", "external_object_id", "external_object"),
    ("value_source", "platform_id", "platform"),
    ("value_source", "value_id", "value"),
]


def upgrade():
    for table in primary_keys:
        op.execute("ALTER INDEX {table}_pkey RENAME TO pk_{table}".format(table=table))

    for table, column, foreign_table in foreign_keys:
        op.execute(
            "ALTER TABLE {table} RENAME CONSTRAINT {table}_{column}_fkey TO fk_{table}_{column}_{foreign_table}".format(
                table=table, column=column, foreign_table=foreign_table
            )
        )


def downgrade():
    for table in primary_keys:
        op.execute("ALTER INDEX pk_{table} RENAME TO {table}_pkey".format(table=table))

    for table, column, foreign_table in foreign_keys:
        op.execute(
            "ALTER TABLE {table} RENAME CONSTRAINT fk_{table}_{column}_{foreign_table} TO {table}_{column}_fkey".format(
                table=table, column=column, foreign_table=foreign_table
            )
        )
