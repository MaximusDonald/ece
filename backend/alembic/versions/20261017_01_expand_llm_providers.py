"""Allow the code registry to own provider identifiers and seed its models."""

from datetime import datetime
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "20261017_01"
down_revision = None
branch_labels = None
depends_on = None

PROVIDERS = (
    ("anthropic", "Anthropic Claude Haiku", "claude-3-5-haiku-20241022"),
    ("gemini", "Google Gemini Flash", "gemini-1.5-flash"),
    ("groq", "Groq Llama 3.3", "llama-3.3-70b-versatile"),
)
SYSTEM_PROMPT = (
    "You are a legal expert specialized in ECOWAS, WAEMU, OHADA and Beninese law. "
    "Answer precisely and never invent legal references."
)


def upgrade() -> None:
    bind = op.get_bind()
    provider_type = bind.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'llmprovider'")
    ).scalar_one_or_none()
    if provider_type:
        op.execute(
            "ALTER TABLE llm_config ALTER COLUMN provider TYPE VARCHAR(20) "
            "USING lower(provider::text)"
        )
        op.execute("DROP TYPE llmprovider")

    now = datetime.utcnow()
    for provider, display_name, model in PROVIDERS:
        exists = bind.execute(
            sa.text("SELECT 1 FROM llm_config WHERE provider = :provider AND model = :model LIMIT 1"),
            {"provider": provider, "model": model},
        ).scalar_one_or_none()
        if exists:
            continue
        bind.execute(
            sa.text(
                """INSERT INTO llm_config
                (id, name, provider, model, temperature, max_tokens,
                 system_prompt_version, system_prompt, is_active, is_default,
                 created_at, updated_at)
                VALUES (:id, :name, :provider, :model, 0.1, 4000,
                        'v1', :system_prompt, TRUE, FALSE, :created_at, :updated_at)"""
            ),
            {
                "id": str(uuid4()),
                "name": display_name,
                "provider": provider,
                "model": model,
                "system_prompt": SYSTEM_PROMPT,
                "created_at": now,
                "updated_at": now,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    unsupported_count = bind.execute(
        sa.text("SELECT count(*) FROM llm_config WHERE provider NOT IN ('openai', 'anthropic')")
    ).scalar_one()
    if unsupported_count:
        raise RuntimeError(
            "Downgrade stopped without data loss: llm_config contains Gemini/Groq rows. "
            "Export or remove those configurations explicitly, then retry."
        )

    op.execute("CREATE TYPE llmprovider AS ENUM ('OPENAI', 'ANTHROPIC')")
    op.execute(
        "ALTER TABLE llm_config ALTER COLUMN provider TYPE llmprovider "
        "USING upper(provider)::llmprovider"
    )
