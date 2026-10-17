from abc import ABC, abstractmethod
from typing import Optional

from app.core.config import get_settings

settings = get_settings()
DEFAULT_SYSTEM_PROMPT = (
    "You are a legal expert specialized in ECOWAS, WAEMU, OHADA and Beninese law. "
    "Answer precisely and never invent legal references."
)


class LLMClient(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        prompt: str,
        response_format: Optional[str] = None,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def aclose(self) -> None:
        client = getattr(self, "client", None)
        if client is None:
            return
        close = getattr(client, "aclose", None) or getattr(client, "close", None)
        if close:
            result = close()
            if hasattr(result, "__await__"):
                await result


class OpenAIClient(LLMClient):
    def __init__(self, model: Optional[str] = None, timeout: float = 20.0):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=timeout)
        self.model = model or "gpt-4o-mini"
        self.embedding_model = "text-embedding-3-small"

    async def chat_completion(self, prompt: str, response_format: Optional[str] = None, *, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, system_prompt: Optional[str] = None) -> str:
        kwargs = {
            "model": model or self.model,
            "messages": [
                {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1 if temperature is None else temperature,
            "max_tokens": 4000 if max_tokens is None else max_tokens,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(model=self.embedding_model, input=texts)
        return [item.embedding for item in response.data]


class AnthropicClient(LLMClient):
    def __init__(self, model: Optional[str] = None, timeout: float = 20.0):
        from anthropic import AsyncAnthropic

        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=timeout)
        self.model = model or "claude-3-5-haiku-20241022"

    async def chat_completion(self, prompt: str, response_format: Optional[str] = None, *, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, system_prompt: Optional[str] = None) -> str:
        if response_format == "json":
            prompt = f"{prompt}\n\nReply with valid JSON only."
        response = await self.client.messages.create(
            model=model or self.model,
            system=system_prompt or DEFAULT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1 if temperature is None else temperature,
            max_tokens=4000 if max_tokens is None else max_tokens,
        )
        return response.content[0].text

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        if settings.openai_api_key and settings.openai_api_key.strip():
            return await OpenAIClient().get_embeddings(texts)
        raise NotImplementedError("Anthropic does not provide embeddings; configure OpenAI for embeddings.")


class GroqClient(LLMClient):
    def __init__(self, model: Optional[str] = None, timeout: float = 20.0):
        from groq import AsyncGroq

        self.client = AsyncGroq(api_key=settings.groq_api_key, timeout=timeout)
        self.model = model or settings.groq_model or "llama-3.3-70b-versatile"

    async def chat_completion(self, prompt: str, response_format: Optional[str] = None, *, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, system_prompt: Optional[str] = None) -> str:
        kwargs = {
            "model": model or self.model,
            "messages": [
                {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1 if temperature is None else temperature,
            "max_tokens": 4000 if max_tokens is None else max_tokens,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        if settings.openai_api_key and settings.openai_api_key.strip():
            return await OpenAIClient().get_embeddings(texts)
        raise NotImplementedError("Groq does not provide embeddings; configure OpenAI for embeddings.")


class GeminiClient(LLMClient):
    def __init__(self, model: Optional[str] = None, timeout: float = 20.0):
        from google import genai
        from google.genai import types

        self.client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(timeout * 1000)),
        )
        self.model = model or settings.gemini_model or "gemini-1.5-flash"
        self.embedding_model = "gemini-embedding-2"

    async def chat_completion(self, prompt: str, response_format: Optional[str] = None, *, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, system_prompt: Optional[str] = None) -> str:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_prompt or DEFAULT_SYSTEM_PROMPT,
            temperature=0.1 if temperature is None else temperature,
            max_output_tokens=4000 if max_tokens is None else max_tokens,
            response_mime_type="application/json" if response_format == "json" else None,
        )
        response = await self.client.aio.models.generate_content(
            model=model or self.model,
            contents=prompt,
            config=config,
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        return response.text

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        from google.genai import types

        response = await self.client.aio.models.embed_content(
            model=self.embedding_model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=1536,
            ),
        )
        return [embedding.values for embedding in response.embeddings]

    async def aclose(self) -> None:
        client = getattr(self.client, "aio", None)
        close = getattr(client, "aclose", None) if client else None
        if close:
            result = close()
            if hasattr(result, "__await__"):
                await result


def get_llm_client() -> LLMClient:
    """Return a router that resolves active, available DB configurations per call."""
    from app.services.llm_router import ConfiguredLLMRouter

    return ConfiguredLLMRouter()


class MockLLMClient(LLMClient):
    """Deterministic fallback for embeddings and explicit local mock calls."""

    async def chat_completion(self, prompt: str, response_format: Optional[str] = None, **kwargs) -> str:
        if "vague" in prompt.lower() or "classif" in prompt.lower():
            return '{"clauses": [{"ref": "section 1.1", "type": "data_protection", "content": "Personal data collected", "is_vague": true, "missing_fields": ["hosting_location"]}]}'
        if "consensus" in prompt.lower() or "juridique" in prompt.lower():
            return '{"findings": [{"clause_ref": "section 1.1", "risk_level": "modere", "confidence": "medium", "matched_sources": [], "recommendation": "Specify hosting location"}]}'
        return '{"result": "mock response"}'

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 1536 for _ in texts]
