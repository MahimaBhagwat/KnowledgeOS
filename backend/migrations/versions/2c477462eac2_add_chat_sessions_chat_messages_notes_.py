"""Add chat sessions, chat messages, notes, and insights schema

Revision ID: 2c477462eac2
Revises: None
Create Date: 2026-08-04 15:03:29.757002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c477462eac2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass