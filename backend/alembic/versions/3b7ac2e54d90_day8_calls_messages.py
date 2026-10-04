"""day8: calls + messages

Revision ID: 3b7ac2e54d90
Revises: 1227cbe4301e
Create Date: 2026-10-04 10:55:25.842084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3b7ac2e54d90'
down_revision: Union[str, None] = '1227cbe4301e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
