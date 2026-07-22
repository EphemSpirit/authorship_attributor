"""split author style profiles into profile and feature tables

Revision ID: bbd51a826f9f
Revises: 8ed256c8c1de
Create Date: 2026-07-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bbd51a826f9f'
down_revision: Union[str, Sequence[str], None] = '8ed256c8c1de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # A profile used to be one row per (author, feature_type, model_version).
    # This drops that shape in favor of one profile row per (author, model_version)
    # with a child author_style_features row per feature_type. Any existing
    # profile data is discarded rather than migrated.
    op.drop_index(op.f('ix_author_style_profiles_id'), table_name='author_style_profiles')
    op.drop_index(op.f('ix_author_style_profiles_author_id'), table_name='author_style_profiles')
    op.drop_table('author_style_profiles')

    op.create_table('author_style_profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.Column('num_documents_used', sa.Integer(), nullable=False),
    sa.Column('model_version', sa.String(length=50), nullable=False),
    sa.Column('computed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['authors.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('author_id', 'model_version', name='uq_author_style_profile_author_model_version')
    )
    op.create_index(op.f('ix_author_style_profiles_author_id'), 'author_style_profiles', ['author_id'], unique=False)
    op.create_index(op.f('ix_author_style_profiles_id'), 'author_style_profiles', ['id'], unique=False)

    op.create_table('author_style_features',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('feature_type', sa.String(length=50), nullable=False),
    sa.Column('profile_vector', sa.JSON(), nullable=False),
    sa.Column('feature_names', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['author_style_profiles.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('profile_id', 'feature_type', name='uq_author_style_feature_profile_type')
    )
    op.create_index(op.f('ix_author_style_features_profile_id'), 'author_style_features', ['profile_id'], unique=False)
    op.create_index(op.f('ix_author_style_features_id'), 'author_style_features', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_author_style_features_id'), table_name='author_style_features')
    op.drop_index(op.f('ix_author_style_features_profile_id'), table_name='author_style_features')
    op.drop_table('author_style_features')

    op.drop_index(op.f('ix_author_style_profiles_id'), table_name='author_style_profiles')
    op.drop_index(op.f('ix_author_style_profiles_author_id'), table_name='author_style_profiles')
    op.drop_table('author_style_profiles')

    op.create_table('author_style_profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.Column('feature_type', sa.String(length=50), nullable=False),
    sa.Column('profile_vector', sa.JSON(), nullable=False),
    sa.Column('feature_names', sa.JSON(), nullable=False),
    sa.Column('num_documents_used', sa.Integer(), nullable=False),
    sa.Column('model_version', sa.String(length=50), nullable=False),
    sa.Column('computed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['authors.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('author_id', 'feature_type', 'model_version', name='uq_author_style_profile_triple')
    )
    op.create_index(op.f('ix_author_style_profiles_author_id'), 'author_style_profiles', ['author_id'], unique=False)
    op.create_index(op.f('ix_author_style_profiles_id'), 'author_style_profiles', ['id'], unique=False)
