"""mercadolivre_integration

Revision ID: 003_mercadolivre_integration
Revises: 002_pricing_engine
Create Date: 2026-09-18 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_mercadolivre_integration'
down_revision: Union[str, None] = '002_pricing_engine'
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'marketplace_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('marketplace', sa.String(length=50), server_default=sa.text("'MERCADO_LIVRE'"), nullable=False),
        sa.Column('account_name', sa.String(length=255), nullable=False),
        sa.Column('seller_id', sa.String(length=100), nullable=False),
        sa.Column('site_id', sa.String(length=20), server_default=sa.text("'MLB'"), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_marketplace_accounts')),
        sa.UniqueConstraint('marketplace', 'seller_id', name=op.f('uq_marketplace_accounts_seller'))
    )

    op.create_table(
        'marketplace_listings',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('marketplace', sa.String(length=50), server_default=sa.text("'MERCADO_LIVRE'"), nullable=False),
        sa.Column('external_listing_id', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('available_quantity', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('category_id', sa.String(length=100), nullable=False),
        sa.Column('listing_type_id', sa.String(length=50), server_default=sa.text("'gold_special'"), nullable=False),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'DRAFT'"), nullable=False),
        sa.Column('permalink', sa.String(length=1000), nullable=True),
        sa.Column('raw_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['marketplace_accounts.id'], name=op.f('fk_marketplace_listings_account_id_marketplace_accounts'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_marketplace_listings_product_id_products'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_marketplace_listings')),
        sa.UniqueConstraint('account_id', 'external_listing_id', name=op.f('uq_marketplace_listings_external'))
    )


def downgrade() -> None:
    op.drop_table('marketplace_listings')
    op.drop_table('marketplace_accounts')
