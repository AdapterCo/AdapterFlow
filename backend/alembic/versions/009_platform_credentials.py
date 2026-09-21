"""Marketplace platform credentials stored encrypted in database."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "009_platform_credentials"
down_revision = "008_product_provenance"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "marketplace_platform_credentials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("marketplace", sa.String(50), nullable=False, unique=True),
        sa.Column("app_id", sa.String(255), nullable=True),
        sa.Column("app_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("redirect_uri", sa.String(500), nullable=True),
        sa.Column("api_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("marketplace_platform_credentials")
