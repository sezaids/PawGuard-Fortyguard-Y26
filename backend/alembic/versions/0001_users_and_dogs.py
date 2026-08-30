"""create users and dogs tables

Revision ID: 0001_users_and_dogs
Revises:
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_users_and_dogs"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_table(
        "dogs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("breed", sa.String(length=120), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("body_size", sa.String(length=20), nullable=False),
        sa.Column("coat_color", sa.String(length=80), nullable=True),
        sa.Column("coat_length", sa.String(length=20), nullable=False),
        sa.Column("brachycephalic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("activity_level", sa.String(length=20), nullable=False),
        sa.Column("fitness_level", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dogs_owner_id", "dogs", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_dogs_owner_id", table_name="dogs")
    op.drop_table("dogs")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
