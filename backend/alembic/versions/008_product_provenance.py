"""External product identity is separate from supplier codes and internal SKUs."""
from alembic import op
import sqlalchemy as sa
revision = "008_product_provenance"
down_revision = "007_admin_sessions"
branch_labels = depends_on = None


def upgrade():
    op.add_column("products", sa.Column("source_marketplace", sa.String(50)))
    op.add_column("products", sa.Column("source_external_id", sa.String(100)))
    op.create_unique_constraint("uq_products_external_source", "products", ["source_marketplace", "source_external_id"])


def downgrade():
    op.drop_constraint("uq_products_external_source", "products", type_="unique")
    op.drop_column("products", "source_external_id")
    op.drop_column("products", "source_marketplace")
