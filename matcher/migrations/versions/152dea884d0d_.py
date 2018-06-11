"""Adjust the ExternalObject type enum

This renames 'SERIE' to 'SERIES' in the enum and drops the 'SEASON' value

Revision ID: 152dea884d0d
Revises: 39018d98191f
Create Date: 2018-06-11 13:29:53.345622

"""
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '152dea884d0d'
down_revision = '39018d98191f'
branch_labels = None
depends_on = None


def upgrade():
    # Rename the old type
    op.execute("ALTER TYPE externalobjecttype RENAME TO externalobjecttype_old")

    # Create the new one
    externalobjecttype = postgresql.ENUM('PERSON', 'MOVIE', 'SERIES', 'EPISODE',
                                         name='externalobjecttype')
    externalobjecttype.create(op.get_bind())

    # Adjust the column
    op.execute("""
        ALTER TABLE external_object
        ALTER COLUMN type
        TYPE externalobjecttype
        USING
          CASE
            WHEN type='MOVIE' THEN 'MOVIE'::externalobjecttype
            WHEN type='SERIE' THEN 'SERIES'::externalobjecttype
            WHEN type='EPISODE' THEN 'EPISODE'::externalobjecttype
            WHEN type='PERSON' THEN 'PERSON'::externalobjecttype
          END
    """)

    # Drop the old type
    op.execute("DROP TYPE externalobjecttype_old")


def downgrade():
    # Re-create the old type
    externalobjecttype = postgresql.ENUM('PERSON', 'MOVIE', 'SERIE', 'SEASON',
                                         'EPISODE',
                                         name='externalobjecttype_old')
    externalobjecttype.create(op.get_bind())

    # Adjust the column
    op.execute("""
        ALTER TABLE external_object
        ALTER COLUMN type
        TYPE externalobjecttype_old
        USING
          CASE
            WHEN type='MOVIE' THEN 'MOVIE'::externalobjecttype_old
            WHEN type='SERIES' THEN 'SERIE'::externalobjecttype_old
            WHEN type='EPISODE' THEN 'EPISODE'::externalobjecttype_old
            WHEN type='PERSON' THEN 'PERSON'::externalobjecttype_old
          END
    """)

    # Drop the new type
    op.execute("DROP TYPE externalobjecttype")

    # Rename back the old one
    op.execute("ALTER TYPE externalobjecttype_old RENAME TO externalobjecttype")
