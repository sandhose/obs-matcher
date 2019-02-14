"""Export and scrap sessions tables

Revision ID: f9cf022e4e05
Revises: 80b455f303c5
Create Date: 2018-07-12 09:29:12.960286

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f9cf022e4e05"
down_revision = "80b455f303c5"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS hstore")

    op.create_table(
        "session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_session"),
    )

    op.create_table(
        "export_template",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "row_type",
            sa.Enum("EXTERNAL_OBJECT", "OBJECT_LINK", name="exportrowtype"),
            nullable=False,
        ),
        sa.Column(
            "external_object_type",
            postgresql.ENUM(
                "PERSON",
                "MOVIE",
                "EPISODE",
                "SERIES",
                name="externalobjecttype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_export_template"),
    )

    op.create_table(
        "export_factory",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("export_template_id", sa.Integer(), nullable=False),
        sa.Column(
            "iterator",
            sa.Enum("PLATFORMS", "GROUPS", "COUNTRIES", name="exportfilteriterator"),
            nullable=True,
        ),
        sa.Column("file_path_template", sa.String(), nullable=False),
        sa.Column(
            "filters_template", postgresql.HSTORE(text_type=sa.Text()), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["export_template_id"],
            ["export_template.id"],
            name="fk_export_factory_export_template_id_export_template",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_export_factory"),
    )

    op.create_table(
        "export_file",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PROCESSING", "DONE", name="exportfilestatus"),
            server_default="PROCESSING",
            nullable=True,
        ),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("filters", postgresql.HSTORE(text_type=sa.Text()), nullable=False),
        sa.Column("export_template_id", sa.Integer(), nullable=True),
        sa.Column("export_factory_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["export_factory_id"],
            ["export_factory.id"],
            name="fk_export_file_export_factory_id_export_factory",
        ),
        sa.ForeignKeyConstraint(
            ["export_template_id"],
            ["export_template.id"],
            name="fk_export_file_export_template_id_export_template",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["session.id"], name="fk_export_file_session_id_session"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_export_file"),
    )

    op.create_table(
        "session_scrap",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("scrap_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scrap_id"],
            ["scrap.id"],
            name="fk_session_scrap_scrap_id_scrap",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["session.id"],
            name="fk_session_scrap_session_id_session",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("session_id", "scrap_id", name="pk_session_scrap"),
    )


def downgrade():
    op.drop_table("session_scrap")
    op.drop_table("export_file")
    op.drop_table("export_factory")
    op.drop_table("session")
    op.drop_table("export_template")
