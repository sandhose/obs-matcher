"""Update a lot of constraints (essentially cascades)

Revision ID: a862b5ec1efb
Revises: 72e7453c5efe
Create Date: 2018-06-18 08:45:31.461704

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "a862b5ec1efb"
down_revision = "72e7453c5efe"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("episode_external_object_id_fkey", "episode", type_="foreignkey")
    op.drop_constraint("episode_series_id_fkey", "episode", type_="foreignkey")

    op.create_foreign_key(
        "episode_external_object_id_fkey",
        "episode",
        "external_object",
        ["external_object_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "episode_series_id_fkey",
        "episode",
        "external_object",
        ["series_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )

    op.drop_constraint("person_external_object_id_fkey", "person", type_="foreignkey")
    op.create_foreign_key(
        "person_external_object_id_fkey",
        "person",
        "external_object",
        ["external_object_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )

    op.create_unique_constraint("uq_platform_slug", "platform", ["slug"])

    op.drop_constraint("scrap_link_scrap_id_fkey", "scrap_link", type_="foreignkey")
    op.drop_constraint(
        "scrap_link_object_link_id_fkey", "scrap_link", type_="foreignkey"
    )

    op.create_foreign_key(
        "scrap_link_object_link_id_fkey",
        "scrap_link",
        "object_link",
        ["object_link_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "scrap_link_scrap_id_fkey",
        "scrap_link",
        "scrap",
        ["scrap_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint("scrap_link_scrap_id_fkey", "scrap_link", type_="foreignkey")
    op.drop_constraint(
        "scrap_link_object_link_id_fkey", "scrap_link", type_="foreignkey"
    )
    op.create_foreign_key(
        "scrap_link_object_link_id_fkey",
        "scrap_link",
        "object_link",
        ["object_link_id"],
        ["id"],
    )
    op.create_foreign_key(
        "scrap_link_scrap_id_fkey", "scrap_link", "scrap", ["scrap_id"], ["id"]
    )
    op.drop_constraint("uq_platform_slug", "platform", type_="unique")
    op.drop_constraint("person_external_object_id_fkey", "person", type_="foreignkey")
    op.create_foreign_key(
        "person_external_object_id_fkey",
        "person",
        "external_object",
        ["external_object_id"],
        ["id"],
    )
    op.drop_constraint("episode_series_id_fkey", "episode", type_="foreignkey")
    op.drop_constraint("episode_external_object_id_fkey", "episode", type_="foreignkey")
    op.create_foreign_key(
        "episode_series_id_fkey", "episode", "external_object", ["series_id"], ["id"]
    )
    op.create_foreign_key(
        "episode_external_object_id_fkey",
        "episode",
        "external_object",
        ["external_object_id"],
        ["id"],
    )
