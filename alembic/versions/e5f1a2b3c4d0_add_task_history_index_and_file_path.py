"""add task history index and result_file_path

Revision ID: e5f1a2b3c4d0
Revises: d4e8a1b2c3f0
Create Date: 2026-07-13 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f1a2b3c4d0"
down_revision: Union[str, Sequence[str], None] = "d4e8a1b2c3f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("result_file_path", sa.String(length=1024), nullable=True),
    )
    op.create_index(op.f("ix_tasks_user_id"), "tasks", ["user_id"], unique=False)
    op.create_index(
        "ix_tasks_user_id_created_at",
        "tasks",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_user_id_created_at", table_name="tasks")
    op.drop_index(op.f("ix_tasks_user_id"), table_name="tasks")
    op.drop_column("tasks", "result_file_path")
