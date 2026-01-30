"""Add presentation type and file_path

Revision ID: d8f2c91a4e3b
Revises: cbaa805748b1
Create Date: 2026-01-30 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8f2c91a4e3b'
down_revision: Union[str, Sequence[str], None] = '52e9946ea0cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add file_path column to teaching_materials table
    op.add_column('teaching_materials', sa.Column('file_path', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove file_path column from teaching_materials table
    op.drop_column('teaching_materials', 'file_path')
