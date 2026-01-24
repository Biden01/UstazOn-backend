"""add_parent_topic_to_card_topics

Revision ID: ca2304852dd4
Revises: 70c4128a284e
Create Date: 2025-12-29 14:50:01.574157

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca2304852dd4'
down_revision: Union[str, Sequence[str], None] = '70c4128a284e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add parent_topic_id column to card_topics
    op.add_column('card_topics', sa.Column('parent_topic_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_card_topics_parent_topic_id',
        'card_topics',
        'card_topics',
        ['parent_topic_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_index('ix_card_topics_parent_topic_id', 'card_topics', ['parent_topic_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_card_topics_parent_topic_id', 'card_topics')
    op.drop_constraint('fk_card_topics_parent_topic_id', 'card_topics', type_='foreignkey')
    op.drop_column('card_topics', 'parent_topic_id')
