"""Resolve active model configs and apply bounded, classified chat fallback."""

import logging

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.admin import LLMConfig
from app.services.llm_client import GeminiClient, LLMClient, MockLLMClient, OpenAIClient
from app.services.llm_registry import (
    classify_provider_error,
    get_provider,
    provider_availability,
)

logger = logging.getLogger(__name__)
MAX_FALLBACK_ATTEMPTS = 3


class LLMUnavailableError(RuntimeError):
    """Raised when no active configured provider can complete a chat request."""


class ConfiguredLLMRouter(LLMClient):
    async def _active_candidates(self) -> list[LLMConfig]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(LLMConfig)
                .where(LLMConfig.is_active.is_(True))
                .order_by(LLMConfig.is_default.desc(), LLMConfig.created_at.asc(), LLMConfig.name.asc())
            )
            return [
                config
                for config in result.scalars().all()
                if provider_availability(config.provider)
            ]

    async def chat_completion(self, prompt: str, response_format: str | None = None, *, model: str | None = None, temperature: float | None = None, max_tokens: int | None = None, system_prompt: str | None = None) -> str:
        candidates = await self._active_candidates()
        if model:
            candidates = [candidate for candidate in candidates if candidate.model == model]
        unique_candidates = []
        seen_models: set[tuple[str, str]] = set()
        for candidate in candidates:
            key = (candidate.provider, candidate.model)
            if key not in seen_models:
                unique_candidates.append(candidate)
                seen_models.add(key)
        candidates = unique_candidates[:MAX_FALLBACK_ATTEMPTS]
        if not candidates:
            raise LLMUnavailableError(
                "Aucun modèle de discussion actif et disponible n'est configuré."
            )

        final_category = "unknown"
        for index, config in enumerate(candidates):
            definition = get_provider(config.provider)
            client = definition.build_client(config.model)
            try:
                return await client.chat_completion(
                    prompt,
                    response_format,
                    model=config.model,
                    temperature=config.temperature if temperature is None else temperature,
                    max_tokens=config.max_tokens if max_tokens is None else max_tokens,
                    system_prompt=system_prompt or config.system_prompt,
                )
            except Exception as exc:
                category = classify_provider_error(exc)
                if category is None:
                    # Invalid user requests and model/configuration errors are not retried.
                    raise
                final_category = category
                if index + 1 >= len(candidates):
                    break
                next_config = candidates[index + 1]
                logger.warning(
                    "LLM fallback: provider=%s model=%s category=%s next_provider=%s next_model=%s",
                    config.provider,
                    config.model,
                    category,
                    next_config.provider,
                    next_config.model,
                )
            finally:
                await client.aclose()

        logger.error(
            "LLM providers exhausted after %s bounded attempts; last_category=%s",
            len(candidates),
            final_category,
        )
        raise LLMUnavailableError(
            f"Les {len(candidates)} modèle(s) actif(s) disponible(s) ont échoué ({final_category})."
        )

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        settings = get_settings()
        if settings.openai_api_key and settings.openai_api_key.strip():
            return await OpenAIClient().get_embeddings(texts)
        if settings.gemini_api_key and settings.gemini_api_key.strip():
            return await GeminiClient().get_embeddings(texts)
        if settings.anthropic_api_key and settings.anthropic_api_key.strip():
            from app.services.llm_client import AnthropicClient

            return await AnthropicClient().get_embeddings(texts)
        if settings.groq_api_key and settings.groq_api_key.strip():
            from app.services.llm_client import GroqClient

            return await GroqClient().get_embeddings(texts)
        return await MockLLMClient().get_embeddings(texts)
