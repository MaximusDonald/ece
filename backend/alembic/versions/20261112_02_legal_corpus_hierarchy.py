"""Add hierarchical legal corpus tables (legal_text, legal_section, legal_article) and hybrid search indexes."""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "20261112_02"
down_revision = "20261017_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    if not bind.execute(sa.text("SELECT to_regclass('public.legal_text')")).scalar():
        op.create_table(
            "legal_text",
            sa.Column("id", PGUUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("code", sa.String(length=60), nullable=False),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("jurisdiction", sa.String(length=32), nullable=False),
            sa.Column("authority", sa.String(length=255), nullable=False),
            sa.Column("level", sa.String(length=50), nullable=False, server_default="loi"),
            sa.Column("publication_date", sa.Date(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="in_force"),
            sa.Column("official_url", sa.String(length=1000), nullable=True),
            sa.Column("minio_bucket", sa.String(length=100), nullable=False, server_default="legal-corpus"),
            sa.Column("pdf_path", sa.String(length=500), nullable=True),
            sa.Column("text_path", sa.String(length=500), nullable=True),
            sa.Column("sha256_hash", sa.String(length=64), nullable=True),
            sa.Column("total_articles", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_legal_text_code", "legal_text", ["code"], unique=True)
        op.create_index("ix_legal_text_jurisdiction", "legal_text", ["jurisdiction"], unique=False)
        op.create_index("ix_legal_text_level", "legal_text", ["level"], unique=False)
        op.create_index("ix_legal_text_status", "legal_text", ["status"], unique=False)
        op.create_index("ix_legal_text_sha256_hash", "legal_text", ["sha256_hash"], unique=False)

    if not bind.execute(sa.text("SELECT to_regclass('public.legal_section')")).scalar():
        op.create_table(
            "legal_section",
            sa.Column("id", PGUUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("text_id", PGUUID(as_uuid=True), sa.ForeignKey("legal_text.id", ondelete="CASCADE"), nullable=False),
            sa.Column("parent_section_id", PGUUID(as_uuid=True), sa.ForeignKey("legal_section.id", ondelete="CASCADE"), nullable=True),
            sa.Column("level_name", sa.String(length=120), nullable=False),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("breadcrumb", sa.String(length=1000), nullable=False, server_default=""),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("text_id", "order_index", name="uq_legal_section_text_order"),
        )
        op.create_index("ix_legal_section_text_id", "legal_section", ["text_id"], unique=False)
        op.create_index("ix_legal_section_parent_section_id", "legal_section", ["parent_section_id"], unique=False)
        op.create_index("ix_legal_section_order_index", "legal_section", ["order_index"], unique=False)

    if not bind.execute(sa.text("SELECT to_regclass('public.legal_article')")).scalar():
        op.create_table(
            "legal_article",
            sa.Column("id", PGUUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("text_id", PGUUID(as_uuid=True), sa.ForeignKey("legal_text.id", ondelete="CASCADE"), nullable=False),
            sa.Column("section_id", PGUUID(as_uuid=True), sa.ForeignKey("legal_section.id", ondelete="SET NULL"), nullable=True),
            sa.Column("article_number", sa.String(length=80), nullable=False),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("title", sa.String(length=500), nullable=True),
            sa.Column("full_text", sa.Text(), nullable=False),
            sa.Column("topics", sa.JSON(), nullable=False),
            sa.Column("actors", sa.JSON(), nullable=False),
            sa.Column("has_sanction", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("sanction_details", sa.Text(), nullable=True),
            sa.Column("compliance_rule_type", sa.String(length=30), nullable=True),
            sa.Column("ai_tagged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("embedding", Vector(1536), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("text_id", "order_index", name="uq_legal_article_text_order"),
        )
        op.create_index("ix_legal_article_text_id", "legal_article", ["text_id"], unique=False)
        op.create_index("ix_legal_article_section_id", "legal_article", ["section_id"], unique=False)
        op.create_index("ix_legal_article_article_number", "legal_article", ["article_number"], unique=False)
        op.create_index("ix_legal_article_order_index", "legal_article", ["order_index"], unique=False)
        op.create_index("ix_legal_article_has_sanction", "legal_article", ["has_sanction"], unique=False)
        op.create_index("ix_legal_article_compliance_rule_type", "legal_article", ["compliance_rule_type"], unique=False)
        op.create_index("ix_legal_article_ai_tagged", "legal_article", ["ai_tagged"], unique=False)

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_legal_article_embedding_hnsw "
        "ON legal_article USING hnsw (embedding vector_cosine_ops);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_legal_article_fulltext_gin "
        "ON legal_article USING gin (to_tsvector('french', coalesce(title, '') || ' ' || article_number || ' ' || full_text));"
    )

    if bind.execute(sa.text("SELECT to_regclass('public.risk_finding')")).scalar():
        op.execute(
            "ALTER TABLE risk_finding ADD COLUMN IF NOT EXISTS matched_articles JSON NOT NULL DEFAULT '[]'::json;"
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_legal_article_fulltext_gin;")
    op.execute("DROP INDEX IF EXISTS ix_legal_article_embedding_hnsw;")
    op.drop_table("legal_article")
    op.drop_table("legal_section")
    op.drop_table("legal_text")
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT to_regclass('public.risk_finding')")).scalar():
        op.execute("ALTER TABLE risk_finding DROP COLUMN IF EXISTS matched_articles;")
