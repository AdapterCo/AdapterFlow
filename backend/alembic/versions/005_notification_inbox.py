"""Persist unverified Mercado Livre notification receipts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "005_notification_inbox"
down_revision = "004_audit_hardening"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "marketplace_notifications",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("deduplication_key", sa.String(64), nullable=False, unique=True),
        sa.Column("payload", pg.JSONB(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="RECEIVED_UNVERIFIED"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    raise RuntimeError("A caixa de notificações contém histórico real; faça backup e planeje a remoção explicitamente.")
