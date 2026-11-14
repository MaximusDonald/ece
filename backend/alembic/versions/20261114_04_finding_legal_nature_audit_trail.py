"""Add legal_nature and human review audit trail fields to risk_finding."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "20261114_04"
down_revision = "20261112_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("risk_finding")}

    if "legal_nature" not in existing_cols:
        op.add_column(
            "risk_finding",
            sa.Column(
                "legal_nature",
                sa.String(length=40),
                nullable=False,
                server_default="non_conformite_imperative",
            ),
        )
    if "review_status" not in existing_cols:
        op.add_column(
            "risk_finding",
            sa.Column(
                "review_status",
                sa.String(length=30),
                nullable=False,
                server_default="pending",
            ),
        )
        op.create_index("ix_risk_finding_review_status", "risk_finding", ["review_status"])
    if "reviewed_by" not in existing_cols:
        op.add_column(
            "risk_finding",
            sa.Column(
                "reviewed_by",
                PGUUID(as_uuid=True),
                sa.ForeignKey("user.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if "reviewed_at" not in existing_cols:
        op.add_column(
            "risk_finding",
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        )
    if "review_note" not in existing_cols:
        op.add_column(
            "risk_finding",
            sa.Column("review_note", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("risk_finding", "review_note")
    op.drop_column("risk_finding", "reviewed_at")
    op.drop_column("risk_finding", "reviewed_by")
    op.drop_index("ix_risk_finding_review_status", table_name="risk_finding")
    op.drop_column("risk_finding", "review_status")
    op.drop_column("risk_finding", "legal_nature")
