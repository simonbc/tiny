"""add page layout, is_post, published_at

Revision ID: a1b2c3d4e5f6
Revises: 9285a557077a
Create Date: 2026-05-11 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "9285a557077a"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("pages") as batch:
        batch.add_column(
            sa.Column(
                "layout",
                sa.String(length=16),
                nullable=False,
                server_default="page",
            )
        )
        batch.add_column(
            sa.Column(
                "is_post",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch.add_column(sa.Column("published_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("pages") as batch:
        batch.drop_column("published_at")
        batch.drop_column("is_post")
        batch.drop_column("layout")
