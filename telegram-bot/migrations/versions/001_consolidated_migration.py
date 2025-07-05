"""Consolidated migration - create users and user_statistics tables with integer book_id

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('telegram_id', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    
    # Create user_statistics table with INTEGER book_id
    # date_booked and expiry_date are nullable - will be set when user picks up the book
    op.create_table('user_statistics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),  # Changed to Integer
        sa.Column('date_booked', sa.DateTime(), nullable=True),  # Nullable - set when picked up
        sa.Column('expiry_date', sa.DateTime(), nullable=True),  # Nullable - set when picked up
        sa.Column('returned', sa.Boolean(), nullable=True),
        sa.Column('returned_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index('idx_user_statistics_user_id', 'user_statistics', ['user_id'])
    op.create_index('idx_user_statistics_book_id', 'user_statistics', ['book_id'])
    op.create_index('idx_user_statistics_date_booked', 'user_statistics', ['date_booked'])
    op.create_index('idx_user_statistics_expiry_date', 'user_statistics', ['expiry_date'])
    op.create_index('idx_user_statistics_returned', 'user_statistics', ['returned'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_user_statistics_returned', table_name='user_statistics')
    op.drop_index('idx_user_statistics_expiry_date', table_name='user_statistics')
    op.drop_index('idx_user_statistics_date_booked', table_name='user_statistics')
    op.drop_index('idx_user_statistics_book_id', table_name='user_statistics')
    op.drop_index('idx_user_statistics_user_id', table_name='user_statistics')
    
    # Drop tables
    op.drop_table('user_statistics')
    op.drop_table('users') 