"""empty message

Revision ID: 7343a182b1dc
Revises: b8b92c266e00
Create Date: 2017-02-19 20:22:19.009873

"""

# revision identifiers, used by Alembic.
revision = '7343a182b1dc'
down_revision = 'b8b92c266e00'

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
    sa.Column('fare', sa.Numeric(), nullable=True),
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
