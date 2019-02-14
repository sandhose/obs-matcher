"""Remove SEASON ExternalObjectType

Revision ID: eafcc26b16be
Revises: 188554831ef1
Create Date: 2017-12-04 13:40:47.245150

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "eafcc26b16be"
down_revision = "188554831ef1"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("season")
    op.add_column("episode", sa.Column("episode", sa.Integer(), nullable=True))
    op.add_column("episode", sa.Column("season", sa.Integer(), nullable=True))
    op.add_column("episode", sa.Column("serie_id", sa.Integer(), nullable=True))
    op.drop_constraint("episode_season_id_fkey", "episode", type_="foreignkey")
    op.create_foreign_key(
        "episode_serie_id_fkey", "episode", "external_object", ["serie_id"], ["id"]
    )
    op.drop_column("episode", "season_id")
    op.drop_column("episode", "number")


def downgrade():
    op.add_column(
        "episode", sa.Column("number", sa.INTEGER(), autoincrement=False, nullable=True)
    )
    op.add_column(
        "episode",
        sa.Column("season_id", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.drop_constraint("episode_serie_id_fkey", "episode", type_="foreignkey")
    op.create_foreign_key(
        "episode_season_id_fkey", "episode", "external_object", ["season_id"], ["id"]
    )
    op.drop_column("episode", "serie_id")
    op.drop_column("episode", "season")
    op.drop_column("episode", "episode")
    op.create_table(
        "season",
        sa.Column(
            "external_object_id", sa.INTEGER(), autoincrement=False, nullable=False
        ),
        sa.Column("serie_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("number", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["external_object_id"],
            ["external_object.id"],
            name="season_external_object_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["serie_id"], ["external_object.id"], name="season_serie_id_fkey"
        ),
        sa.PrimaryKeyConstraint("external_object_id", name="external_object_id_pkey"),
    )
