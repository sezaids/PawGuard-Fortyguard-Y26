"""add persisted walks

Revision ID: 0002_walk_history
Revises: 0001_users_and_dogs
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_walk_history"
down_revision = "0001_users_and_dogs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "walks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("dog_id", sa.Uuid(), nullable=True),
        sa.Column("dog_name", sa.String(length=100), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("surface", sa.String(length=20), nullable=False),
        sa.Column("heat_risk_score", sa.Integer(), nullable=True),
        sa.Column("heat_risk_status", sa.String(length=20), nullable=True),
        sa.Column("surface_risk_score", sa.Integer(), nullable=True),
        sa.Column("surface_risk_status", sa.String(length=20), nullable=True),
        sa.Column("route_distance_meters", sa.Integer(), nullable=True),
        sa.Column("route_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("route_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dog_id"], ["dogs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_walks_owner_id", "walks", ["owner_id"])
    op.create_index("ix_walks_dog_id", "walks", ["dog_id"])
    op.create_index("ix_walks_completed_at", "walks", ["completed_at"])


def downgrade() -> None:
    op.drop_index("ix_walks_completed_at", table_name="walks")
    op.drop_index("ix_walks_dog_id", table_name="walks")
    op.drop_index("ix_walks_owner_id", table_name="walks")
    op.drop_table("walks")
