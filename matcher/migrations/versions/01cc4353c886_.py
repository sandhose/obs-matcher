"""Add cascades on some foreign keys

Revision ID: 01cc4353c886
Revises: 2a72a6b54510
Create Date: 2019-06-14 11:52:01.580856

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "01cc4353c886"
down_revision = "2a72a6b54510"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        "fk_export_file_log_export_file_id_export_file",
        "export_file_log",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_export_file_log_export_file_id_export_file"),
        "export_file_log",
        "export_file",
        ["export_file_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_import_file_platform_id_platform", "import_file", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_import_file_platform_id_platform"),
        "import_file",
        "platform",
        ["platform_id"],
        ["id"],
        onupdate="CASCADE",
    )
    op.drop_constraint(
        "fk_import_file_log_import_file_id_import_file",
        "import_file_log",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_import_file_log_import_file_id_import_file"),
        "import_file_log",
        "import_file",
        ["import_file_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_object_link_platform_id_platform", "object_link", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_object_link_platform_id_platform"),
        "object_link",
        "platform",
        ["platform_id"],
        ["id"],
        onupdate="CASCADE",
    )
    op.drop_constraint("fk_scrap_platform_id_platform", "scrap", type_="foreignkey")
    op.create_foreign_key(
        op.f("fk_scrap_platform_id_platform"),
        "scrap",
        "platform",
        ["platform_id"],
        ["id"],
        onupdate="CASCADE",
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        op.f("fk_scrap_platform_id_platform"), "scrap", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_scrap_platform_id_platform", "scrap", "platform", ["platform_id"], ["id"]
    )
    op.drop_constraint(
        op.f("fk_object_link_platform_id_platform"), "object_link", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_object_link_platform_id_platform",
        "object_link",
        "platform",
        ["platform_id"],
        ["id"],
    )
    op.drop_constraint(
        op.f("fk_import_file_log_import_file_id_import_file"),
        "import_file_log",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_import_file_log_import_file_id_import_file",
        "import_file_log",
        "import_file",
        ["import_file_id"],
        ["id"],
    )
    op.drop_constraint(
        op.f("fk_import_file_platform_id_platform"), "import_file", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_import_file_platform_id_platform",
        "import_file",
        "platform",
        ["platform_id"],
        ["id"],
    )
    op.drop_constraint(
        op.f("fk_export_file_log_export_file_id_export_file"),
        "export_file_log",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_export_file_log_export_file_id_export_file",
        "export_file_log",
        "export_file",
        ["export_file_id"],
        ["id"],
    )
    # ### end Alembic commands ###
