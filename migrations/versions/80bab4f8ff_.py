"""empty message

Revision ID: 80bab4f8ff
Revises: 30ac6becb99
Create Date: 2015-12-15 17:35:52.561638

"""

# revision identifiers, used by Alembic.
revision = '80bab4f8ff'
down_revision = '30ac6becb99'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('sample_property', sa.Column('unit', sa.String(), nullable=True))
    op.drop_column('sample_property', 'datatype')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('sample_property', sa.Column('datatype', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('sample_property', 'unit')
    ### end Alembic commands ###