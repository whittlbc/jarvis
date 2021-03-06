"""empty message

Revision ID: 82edf10df5bc
Revises: 94538cbba222
Create Date: 2017-02-04 22:52:25.279228

"""

# revision identifiers, used by Alembic.
revision = '82edf10df5bc'
down_revision = '94538cbba222'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('integration',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=True),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('logo', sa.String(), nullable=True),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('user_specific', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_integration',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('integration_id', sa.Integer(), nullable=False),
    sa.Column('access_token', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_integration_integration_id'), 'user_integration', ['integration_id'], unique=False)
    op.create_index(op.f('ix_user_integration_user_id'), 'user_integration', ['user_id'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_user_integration_user_id'), table_name='user_integration')
    op.drop_index(op.f('ix_user_integration_integration_id'), table_name='user_integration')
    op.drop_table('user_integration')
    op.drop_table('integration')
    ### end Alembic commands ###
