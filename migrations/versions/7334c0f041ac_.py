"""empty message

Revision ID: 7334c0f041ac
Revises: 7343a182b1dc
Create Date: 2017-02-19 23:10:26.085826

"""

# revision identifiers, used by Alembic.
revision = '7334c0f041ac'
down_revision = '7343a182b1dc'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('pending_ride',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=True),
    sa.Column('user_integration_id', sa.Integer(), nullable=False),
    sa.Column('start_coord', postgresql.JSON(), nullable=True),
    sa.Column('end_coord', postgresql.JSON(), nullable=True),
    sa.Column('fare', postgresql.JSON(), nullable=True),
    sa.Column('meta', postgresql.JSON(), nullable=True),
    sa.Column('status', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pending_ride_uid'), 'pending_ride', ['uid'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_pending_ride_uid'), table_name='pending_ride')
    op.drop_table('pending_ride')
    ### end Alembic commands ###