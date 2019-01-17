"""Allow ExternalObject to cascade-delete correctly

Revision ID: c427ef30f79c
Revises: fb5e68f0a454
Create Date: 2019-01-11 13:33:15.926215

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "c427ef30f79c"
down_revision = "fb5e68f0a454"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "fk_object_link_external_object_id_external_object", "object_link"
    )
    op.create_foreign_key(
        "fk_object_link_external_object_id_external_object",
        "object_link",
        "external_object",
        ["external_object_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )

    op.drop_constraint("fk_value_external_object_id_external_object", "value")
    op.create_foreign_key(
        "fk_value_external_object_id_external_object",
        "value",
        "external_object",
        ["external_object_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )

    op.drop_constraint("fk_value_source_platform_id_platform", "value_source")
    op.create_foreign_key(
        "fk_value_source_platform_id_platform",
        "value_source",
        "platform",
        ["platform_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )

    op.drop_constraint("fk_value_source_value_id_value", "value_source")
    op.create_foreign_key(
        "fk_value_source_value_id_value",
        "value_source",
        "value",
        ["value_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )

    op.drop_constraint("fk_role_external_object_id_external_object", "role")
    op.create_foreign_key(
        "fk_role_external_object_id_external_object",
        "role",
        "external_object",
        ["external_object_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )

    op.drop_constraint("fk_role_person_id_external_object", "role")
    op.create_foreign_key(
        "fk_role_person_id_external_object",
        "role",
        "external_object",
        ["person_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )


def downgrade():
    pass
