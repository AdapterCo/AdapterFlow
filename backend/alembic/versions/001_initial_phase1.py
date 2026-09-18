"""initial_phase1

Revision ID: 001_initial_phase1
Revises: 
Create Date: 2026-09-17 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_phase1'
down_revision: Union[str, None] = None
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # 1. Suppliers
    op.create_table(
        'suppliers',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=True),
        sa.Column('contact_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_suppliers')),
        sa.UniqueConstraint('code', name=op.f('uq_suppliers_code'))
    )

    # 2. Products
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('brand', sa.String(length=255), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('ean', sa.String(length=20), nullable=True),
        sa.Column('gtin', sa.String(length=20), nullable=True),
        sa.Column('color', sa.String(length=100), nullable=True),
        sa.Column('weight', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('height', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('width', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('length', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='DRAFT', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_products')),
        sa.UniqueConstraint('sku', name=op.f('uq_products_sku'))
    )

    # 3. Import Jobs
    op.create_table(
        'import_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('importer_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='UPLOADED', nullable=False),
        sa.Column('total_detected', sa.Integer(), nullable=True),
        sa.Column('total_imported', sa.Integer(), nullable=True),
        sa.Column('total_errors', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_log', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], name=op.f('fk_import_jobs_supplier_id_suppliers'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_import_jobs'))
    )

    # 4. Product Supplier Data
    op.create_table(
        'product_supplier_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_code', sa.String(length=100), nullable=False),
        sa.Column('supplier_name', sa.String(length=500), nullable=True),
        sa.Column('pcs_per_box', sa.Integer(), nullable=True),
        sa.Column('current_cost', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('raw_cost_value', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_supplier_data_product_id_products'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], name=op.f('fk_product_supplier_data_supplier_id_suppliers'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_product_supplier_data')),
        sa.UniqueConstraint('supplier_id', 'supplier_code', name=op.f('uq_product_supplier_data_supplier_id'))
    )

    # 5. Supplier Product Prices (Price History)
    op.create_table(
        'supplier_product_prices',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('product_supplier_data_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('price', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('raw_value', sa.String(length=50), nullable=True),
        sa.Column('effective_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('import_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['import_id'], ['import_jobs.id'], name=op.f('fk_supplier_product_prices_import_id_import_jobs'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_supplier_data_id'], ['product_supplier_data.id'], name=op.f('fk_supplier_product_prices_product_supplier_data_id_product_supplier_data'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_supplier_product_prices'))
    )

    # 6. Product Images
    op.create_table(
        'product_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('mime_type', sa.String(length=50), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.Column('source', sa.String(length=50), server_default='IMPORT', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_images_product_id_products'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_product_images'))
    )

    # 7. Import Items
    op.create_table(
        'import_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('import_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('normalized_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='DETECTED', nullable=False),
        sa.Column('confidence', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('image_path', sa.String(length=500), nullable=True),
        sa.Column('duplicate_of_product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_edits', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['import_id'], ['import_jobs.id'], name=op.f('fk_import_items_import_id_import_jobs'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_import_items_product_id_products'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_import_items'))
    )


def downgrade() -> None:
    op.drop_table('import_items')
    op.drop_table('product_images')
    op.drop_table('supplier_product_prices')
    op.drop_table('product_supplier_data')
    op.drop_table('import_jobs')
    op.drop_table('products')
    op.drop_table('suppliers')
