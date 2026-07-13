"""add_unique_active_seat_per_show_index

Revision ID: d719f771d6d4
Revises: a7c51f816b9f
Create Date: 2026-07-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd719f771d6d4'
down_revision: Union[str, Sequence[str], None] = 'a7c51f816b9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        'uq_booked_seats_map_show_seat_active',
        'booked_seats_map',
        ['show_id', 'seats_number'],
        unique=True,
        postgresql_where=sa.text('is_cancelled = false'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'uq_booked_seats_map_show_seat_active',
        table_name='booked_seats_map',
    )
