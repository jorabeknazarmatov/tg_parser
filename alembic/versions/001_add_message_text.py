"""add message_text to users

Revision ID: 001_add_message_text
Revises:
Create Date: 2026-05-30
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "001_add_message_text"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем колонку message_text (nullable, чтобы не сломать существующие строки)
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("message_text", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("message_text")
