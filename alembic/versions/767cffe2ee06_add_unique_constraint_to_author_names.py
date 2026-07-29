"""add unique constraint to author names

Revision ID: 767cffe2ee06
Revises: bbd51a826f9f
Create Date: 2026-07-25 15:32:12.942709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '767cffe2ee06'
down_revision: Union[str, Sequence[str], None] = 'bbd51a826f9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(constraint_name="uq_author_name", table_name="authors", columns=["name"])


def downgrade() -> None:
    op.drop_constraint(constraint_name="uq_author_name", table_name="authors", type_="unique")
