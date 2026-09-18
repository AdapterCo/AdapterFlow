"""pricing_engine

Revision ID: 002_pricing_engine
Revises: 001_initial_phase1
Create Date: 2026-09-18 09:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_pricing_engine'
down_revision: Union[str, None] = '001_initial_phase1'
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pricing_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('channel', sa.String(length=50), server_default=sa.text("'CUSTOM'"), nullable=False),
        sa.Column('marketplace_commission_percent', sa.Numeric(precision=6, scale=4), server_default=sa.text('0.0'), nullable=False),
        sa.Column('fixed_fee', sa.Numeric(precision=10, scale=2), server_default=sa.text('0.0'), nullable=False),
        sa.Column('fixed_fee_threshold', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('tax_percent', sa.Numeric(precision=6, scale=4), server_default=sa.text('0.0'), nullable=False),
        sa.Column('operating_cost_percent', sa.Numeric(precision=6, scale=4), server_default=sa.text('0.0'), nullable=False),
        sa.Column('fixed_cost', sa.Numeric(precision=10, scale=2), server_default=sa.text('0.0'), nullable=False),
        sa.Column('target_margin_percent', sa.Numeric(precision=6, scale=4), server_default=sa.text('15.0'), nullable=False),
        sa.Column('free_shipping_threshold', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('free_shipping_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('rounding_rule', sa.String(length=30), server_default=sa.text("'ENDS_90'"), nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_pricing_profiles'))
    )

    op.create_table(
        'product_channel_prices',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pricing_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('calculated_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('cost_basis', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('channel_commission', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('taxes', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('operating_costs', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('shipping_cost', sa.Numeric(precision=12, scale=2), server_default=sa.text('0.0'), nullable=False),
        sa.Column('fixed_fee', sa.Numeric(precision=12, scale=2), server_default=sa.text('0.0'), nullable=False),
        sa.Column('net_margin_value', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('net_margin_percent', sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column('breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_manual_override', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('manual_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['pricing_profile_id'], ['pricing_profiles.id'], name=op.f('fk_product_channel_prices_pricing_profile_id_pricing_profiles'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_channel_prices_product_id_products'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_product_channel_prices')),
        sa.UniqueConstraint('product_id', 'pricing_profile_id', name=op.f('uq_product_channel_prices_product_id_pricing_profile_id'))
    )


def downgrade() -> None:
    op.drop_table('product_channel_prices')
    op.drop_table('pricing_profiles')
