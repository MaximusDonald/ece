"""Add regulatory_alert table for Phase 7 Regulatory Sentinel watch alerts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "20261112_03"
down_revision = "20261112_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not bind.execute(sa.text("SELECT to_regclass('public.regulatory_alert')")).scalar():
        op.create_table(
            "regulatory_alert",
            sa.Column("id", PGUUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column(
                "source_id",
                PGUUID(as_uuid=True),
                sa.ForeignKey("legal_source.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "collection_run_id",
                PGUUID(as_uuid=True),
                sa.ForeignKey("source_collection_run.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("jurisdiction", sa.String(length=32), nullable=False, server_default="BJ"),
            sa.Column("authority", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("detected_url", sa.String(length=1000), nullable=False),
            sa.Column("document_filename", sa.String(length=500), nullable=True),
            sa.Column("previous_hash", sa.String(length=64), nullable=True),
            sa.Column("new_hash", sa.String(length=64), nullable=False),
            sa.Column("etag", sa.String(length=255), nullable=True),
            sa.Column("change_summary", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="pending_review"),
            sa.Column("review_note", sa.Text(), nullable=True),
            sa.Column("reviewed_by", PGUUID(as_uuid=True), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("detected_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_regulatory_alert_source_id", "regulatory_alert", ["source_id"])
        op.create_index("ix_regulatory_alert_status", "regulatory_alert", ["status"])
        op.create_index("ix_regulatory_alert_detected_at", "regulatory_alert", ["detected_at"])


def downgrade() -> None:
    op.drop_table("regulatory_alert")
