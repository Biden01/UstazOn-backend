"""Add teaching_materials table

Revision ID: b7e3f5c2d1a8
Revises: 52e9946ea0cc
Create Date: 2026-01-29 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e3f5c2d1a8'
down_revision: Union[str, Sequence[str], None] = '52e9946ea0cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('teaching_materials',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('material_type', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('subject', sa.String(length=100), nullable=False),
        sa.Column('grade', sa.String(length=50), nullable=False),
        sa.Column('topic', sa.String(length=300), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('ai_model', sa.String(length=50), nullable=True),
        sa.Column('difficulty_level', sa.String(length=20), nullable=True),
        sa.Column('estimated_time', sa.Integer(), nullable=True),
        sa.Column('question_count', sa.Integer(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_teaching_materials_id'), 'teaching_materials', ['id'], unique=False)
    op.create_index(op.f('ix_teaching_materials_user_id'), 'teaching_materials', ['user_id'], unique=False)
    op.create_index(op.f('ix_teaching_materials_material_type'), 'teaching_materials', ['material_type'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_teaching_materials_material_type'), table_name='teaching_materials')
    op.drop_index(op.f('ix_teaching_materials_user_id'), table_name='teaching_materials')
    op.drop_index(op.f('ix_teaching_materials_id'), table_name='teaching_materials')
    op.drop_table('teaching_materials')
