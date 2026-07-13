"""add plan_details to tasks (Manager Agent)

Revision ID: d4e8a1b2c3f0
Revises: c3d9e8f1a2b0
Create Date: 2026-07-13 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e8a1b2c3f0"
down_revision: Union[str, Sequence[str], None] = "c3d9e8f1a2b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("plan_details", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tasks", "plan_details")
