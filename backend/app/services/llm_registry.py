"""Code-owned registry for the providers accepted by the application."""

from dataclasses import dataclass
from typing import Callable

from app.core.config import Settings, get_settings
from app.models.admin import LLMProvider
from app.services.llm_client import (
    AnthropicClient,
    GeminiClient,
    GroqClient,
    LLMClient,
    OpenAIClient,
)


@dataclass(frozen=True)
class ProviderDefinition:
    provider: LLMProvider
    label: str
    key_attribute: str
    default_model: str
    client_factory: Callable[..., LLMClient]

    def is_available(self, settings: Settings) -> bool:
        value = getattr(settings, self.key_attribute, None)
        return isinstance(value, str) and bool(value.strip())

    def build_client(self, model: str, timeout: float = 20.0) -> LLMClient:
        return self.client_factory(model, timeout)

    async def test_model(self, model: str) -> None:
        client = self.build_client(model, timeout=8.0)
        try:
            response = await client.chat_completion(
                "Reply only with OK.",
                temperature=0,
                max_tokens=5,
                system_prompt="Reply only with OK.",
            )
            if not response.strip():
                raise RuntimeError("Le fournisseur a renvoyé une réponse vide.")
        finally:
            await client.aclose()


PROVIDER_REGISTRY: dict[LLMProvider, ProviderDefinition] = {
    LLMProvider.OPENAI: ProviderDefinition(
        LLMProvider.OPENAI, "OpenAI", "openai_api_key", "gpt-4o-mini", OpenAIClient
    ),
    LLMProvider.ANTHROPIC: ProviderDefinition(
        LLMProvider.ANTHROPIC,
        "Anthropic",
        "anthropic_api_key",
        "claude-3-5-haiku-20241022",
        AnthropicClient,
    ),
    LLMProvider.GEMINI: ProviderDefinition(
        LLMProvider.GEMINI,
        "Google Gemini",
        "gemini_api_key",
        "gemini-3.8-flash",
        GeminiClient,
    ),
    LLMProvider.GROQ: ProviderDefinition(
        LLMProvider.GROQ,
        "Groq",
        "groq_api_key",
        "llama-3.3-70b-versatile",
        GroqClient,
    ),
}


def get_provider(provider: str | LLMProvider) -> ProviderDefinition:
    try:
        key = provider if isinstance(provider, LLMProvider) else LLMProvider(provider)
        return PROVIDER_REGISTRY[key]
    except (ValueError, KeyError) as exc:
        raise ValueError("Ce fournisseur n'est pas déclaré dans le registre de l'application.") from exc


def provider_availability(provider: str | LLMProvider) -> bool:
    return get_provider(provider).is_available(get_settings())


def list_provider_availability() -> list[dict[str, object]]:
    settings = get_settings()
    return [
        {
            "provider": provider.value,
            "label": definition.label,
            "available": definition.is_available(settings),
            "default_model": definition.default_model,
        }
        for provider, definition in PROVIDER_REGISTRY.items()
    ]


def classify_provider_error(exc: Exception) -> str | None:
    """Return a retry category only for explicitly recoverable provider failures."""
    status_code = (
        getattr(exc, "status_code", None)
        or getattr(exc, "status", None)
        or getattr(exc, "code", None)
    )
    try:
        status_code = int(status_code) if status_code is not None else None
    except (TypeError, ValueError):
        status_code = None

    class_name = type(exc).__name__.lower()
    message_lower = str(exc).lower()
    if "timeout" in class_name or isinstance(exc, TimeoutError):
        return "timeout"
    if status_code == 429 or "ratelimit" in class_name or "resource_exhausted" in message_lower:
        return "rate_limit"
    if status_code in {401, 403} or any(
        token in class_name for token in ("authentication", "permissiondenied", "unauthorized")
    ):
        return "authentication"
    if (
        (status_code is not None and status_code >= 500)
        or any(token in class_name for token in ("internalserver", "serviceunavailable", "servererror"))
        or "503 unavailable" in message_lower
    ):
        return "server_error"
    if "connection" in class_name or "connecterror" in class_name:
        return "connection"
    return None


def provider_error_message(exc: Exception) -> str:
    category = classify_provider_error(exc)
    if category == "timeout":
        return "Le fournisseur n'a pas répondu à temps."
    if category == "rate_limit":
        return "Le fournisseur limite temporairement les requêtes."
    if category == "authentication":
        return "La clé ou les droits du fournisseur sont refusés."
    if category == "server_error":
        return "Le fournisseur rencontre une erreur serveur."
    if category == "connection":
        return "Le fournisseur est momentanément inaccessible."
    status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if status_code:
        return f"Le fournisseur a refusé le modèle ou la requête (HTTP {status_code})."
    return "Le test du modèle a échoué. Vérifiez son identifiant et la réponse du fournisseur."
