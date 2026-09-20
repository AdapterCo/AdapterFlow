"""Preserve extraction results and progress for every PDF page."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "006_import_pages"
down_revision = "005_notification_inbox"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("import_jobs", sa.Column("total_pages", sa.Integer(), nullable=True))
    op.add_column("import_jobs", sa.Column("processed_pages", sa.Integer(), nullable=True))
    op.add_column("import_jobs", sa.Column("last_progress_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "import_pages",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("import_id", pg.UUID(as_uuid=True), sa.ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("text_blocks", pg.JSONB(), nullable=False),
        sa.Column("image_paths", pg.JSONB(), nullable=False),
        sa.Column("warnings", pg.JSONB(), nullable=False),
        sa.Column("product_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("import_id", "page_number", name="uq_import_pages_import_id_page_number"),
        sa.CheckConstraint("page_number > 0", name="page_number_positive"),
        sa.CheckConstraint("product_count >= 0", name="product_count_nonnegative"),
        sa.CheckConstraint("status IN ('EXTRACTED','NEEDS_REVIEW','FAILED','EMPTY')", name="status"),
    )


def downgrade():
    raise RuntimeError("As páginas preservam os dados originais das importações; faça backup antes de planejar sua remoção.")
