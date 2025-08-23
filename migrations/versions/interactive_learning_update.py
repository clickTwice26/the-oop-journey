"""Add interactive learning features

Revision ID: interactive_learning_update
Revises: 295d6cb788c8
Create Date: 2024-08-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'interactive_learning_update'
down_revision = '295d6cb788c8'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to message table
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.add_column(sa.Column('message_type', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('interactive_data', sa.JSON(), nullable=True))
    
    # Create interactive_learning_session table
    op.create_table('interactive_learning_session',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('question_type', sa.String(length=20), nullable=False),
        sa.Column('question_data', sa.JSON(), nullable=False),
        sa.Column('user_answer', sa.String(length=100), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('answered_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversation.id'], ),
        sa.ForeignKeyConstraint(['message_id'], ['message.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Update existing messages to have default message_type
    op.execute("UPDATE message SET message_type = 'text' WHERE message_type IS NULL")


def downgrade():
    # Drop interactive_learning_session table
    op.drop_table('interactive_learning_session')
    
    # Remove columns from message table
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.drop_column('interactive_data')
        batch_op.drop_column('message_type')
