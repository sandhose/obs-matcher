"""Add data providers

Revision ID: 990f9d007c11
Revises: c427ef30f79c
Create Date: 2019-02-15 16:49:51.644684

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "990f9d007c11"
down_revision = "c427ef30f79c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "provider",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider")),
        sa.UniqueConstraint("slug", name=op.f("uq_provider_slug")),
    )
    op.create_table(
        "provider_platform",
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["platform_id"],
            ["platform.id"],
            name=op.f("fk_provider_platform_platform_id_platform"),
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["provider.id"],
            name=op.f("fk_provider_platform_provider_id_provider"),
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "platform_id", "provider_id", name=op.f("pk_provider_platform")
        ),
    )
    op.add_column("import_file", sa.Column("provider_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_import_file_provider_id_provider"),
        "import_file",
        "provider",
        ["provider_id"],
        ["id"],
        onupdate="SET NULL",
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        op.f("fk_import_file_provider_id_provider"), "import_file", type_="foreignkey"
    )
    op.drop_column("import_file", "provider_id")
    op.drop_table("provider_platform")
    op.drop_table("provider")
