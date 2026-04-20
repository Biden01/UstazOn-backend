"""empty message

Revision ID: 113b439ea145
Revises: ca2304852dd4
Create Date: 2026-01-06 14:49:40.129355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '113b439ea145'
down_revision: Union[str, Sequence[str], None] = 'ca2304852dd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
