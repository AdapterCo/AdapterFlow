"""Integrity, source provenance, durable OAuth and publication attempts.

Revision ID: 004_audit_hardening
Revises: 003_mercadolivre_integration
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "004_audit_hardening"
down_revision = "003_mercadolivre_integration"
branch_labels = None
depends_on = None

RATE_COLUMNS = ("marketplace_commission_percent", "tax_percent", "operating_cost_percent", "target_margin_percent")
OPTIONAL_COSTS = ("fixed_fee", "fixed_cost")


def upgrade():
    op.alter_column("marketplace_listings", "available_quantity", server_default=None)
    op.alter_column("marketplace_listings", "listing_type_id", server_default=None)
    op.alter_column("pricing_profiles", "rounding_rule", server_default=sa.text("'EXACT'"))
    op.add_column("product_supplier_data", sa.Column("activation_reason", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("dimensions", sa.Text(), nullable=True))
    op.alter_column("product_supplier_data", "raw_cost_value", type_=sa.Text())
    op.alter_column("supplier_product_prices", "raw_value", type_=sa.Text())
    for column in RATE_COLUMNS:
        op.alter_column("pricing_profiles", column, type_=sa.Numeric(12, 4), nullable=True, server_default=None)
    for column in OPTIONAL_COSTS:
        op.alter_column("pricing_profiles", column, nullable=True, server_default=None)
    op.alter_column("product_channel_prices", "net_margin_percent", type_=sa.Numeric(20, 4))
    op.add_column("pricing_profiles", sa.Column("source_notes", sa.Text(), nullable=True))
    op.add_column("pricing_profiles", sa.Column("listing_type_id", sa.String(50), nullable=True))
    op.add_column("product_channel_prices", sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("product_channel_prices", sa.Column("supplier_data_id", pg.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(op.f("fk_product_channel_prices_supplier_data_id_product_supplier_data"), "product_channel_prices", "product_supplier_data", ["supplier_data_id"], ["id"], ondelete="SET NULL")
    op.add_column("marketplace_accounts", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("marketplace_accounts", sa.Column("connection_error", sa.Text(), nullable=True))
    op.alter_column("marketplace_accounts", "access_token", nullable=True)
    op.alter_column("marketplace_accounts", "refresh_token", nullable=True)
    op.add_column("marketplace_listings", sa.Column("request_id", pg.UUID(as_uuid=True), nullable=True))
    op.create_unique_constraint("uq_marketplace_listings_request_id", "marketplace_listings", ["request_id"])
    op.create_table("oauth_attempts",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("state_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("browser_hash", sa.String(64), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Legacy ambiguous defaults are not silently resolved. The application clears a
    # channel's previous default under an advisory transaction lock when selected.
    for table, column in (("import_items", "import_id"), ("import_jobs", "status"), ("product_supplier_data", "product_id"),
                           ("product_images", "product_id"), ("marketplace_listings", "product_id"), ("marketplace_listings", "account_id")):
        op.create_index(f"ix_{table}_{column}", table, [column])
    for table, name, condition in (
        ("import_jobs", "status", "status IN ('UPLOADED','PROCESSING','REVIEW_REQUIRED','IMPORTED','FAILED')"),
        ("import_items", "status", "status IN ('DETECTED','APPROVED','REJECTED','IGNORED','ERROR','IMPORTED')"),
        ("products", "status", "status IN ('ACTIVE','INACTIVE','DRAFT')"),
        ("product_supplier_data", "cost_nonnegative", "current_cost IS NULL OR current_cost >= 0"),
        ("supplier_product_prices", "price_nonnegative", "price >= 0"),
    ):
        op.execute(f"ALTER TABLE {table} ADD CONSTRAINT ck_{table}_{name} CHECK ({condition}) NOT VALID")


def downgrade():
    # Removing safety/provenance columns is intentionally not an automatic rollback.
    raise RuntimeError("Restaure backup compatível; esta migration preserva histórico e não tem downgrade destrutivo automático.")
