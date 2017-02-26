"""empty message

Revision ID: 3088dcf95e92
Revises: 0a0bf059f762
Create Date: 2017-02-25 21:24:25.752377

"""

# revision identifiers, used by Alembic.
revision = '3088dcf95e92'
down_revision = '0a0bf059f762'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('pending_ride', sa.Column('external_ride_id', sa.String(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('pending_ride', 'external_ride_id')
    ### end Alembic commands ###
