"""align users email uniqueness with SQLAlchemy metadata

Revision ID: 0003_align_users_email_index
Revises: 0002_walk_history
Create Date: 2026-08-31
"""
from alembic import op


revision = "0003_align_users_email_index"
down_revision = "0002_walk_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0001 created both a UNIQUE constraint and a non-unique index. The model
    # declares a unique indexed field, so retain one unique index only.
    op.drop_constraint("users_email_key", "users", type_="unique")
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.create_unique_constraint("users_email_key", "users", ["email"])
    op.create_index("ix_users_email", "users", ["email"], unique=False)
