from abc import ABC, abstractmethod
from typing import Optional
from app.core.config import get_settings

settings = get_settings()


class LLMClient(ABC):
    @abstractmethod
    async def chat_completion(self, prompt: str, response_format: Optional[str] = None) -> str:
        pass
    
    @abstractmethod
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        pass


class OpenAIClient(LLMClient):
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o-mini"  # Cost-effective for POC
        self.embedding_model = "text-embedding-3-small"
    
    async def chat_completion(self, prompt: str, response_format: Optional[str] = None) -> str:
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Tu es un expert juridique spécialisé en droit CEDEAO/UEMOA/OHADA et droit béninois. Réponds de manière précise et structurée."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 4000,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        
        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        return [d.embedding for d in response.data]


class AnthropicClient(LLMClient):
    def __init__(self):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-3-5-haiku-20241022"  # Cost-effective for POC
    
    async def chat_completion(self, prompt: str, response_format: Optional[str] = None) -> str:
        system_prompt = "Tu es un expert juridique spécialisé en droit CEDEAO/UEMOA/OHADA et droit béninois. Réponds de manière précise et structurée."
        
        if response_format == "json":
            prompt = f"{prompt}\n\nRéponds UNIQUEMENT en JSON valide."
        
        response = await self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4000,
        )
        return response.content[0].text
    
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        # Anthropic doesn't have embeddings API - fallback to OpenAI if available
        if settings.openai_api_key:
            openai_client = OpenAIClient()
            return await openai_client.get_embeddings(texts)
        raise NotImplementedError("Anthropic doesn't provide embeddings. Set OPENAI_API_KEY for embeddings.")


def get_llm_client() -> LLMClient:
    """Get LLM client based on available API keys."""
    if settings.anthropic_api_key:
        return AnthropicClient()
    elif settings.openai_api_key:
        return OpenAIClient()
    else:
        # Return mock client for testing without API keys
        return MockLLMClient()


class MockLLMClient(LLMClient):
    """Mock client for development without API keys."""
    
    async def chat_completion(self, prompt: str, response_format: Optional[str] = None) -> str:
        if "vague" in prompt.lower() or "classif" in prompt.lower():
            return '{"clauses": [{"ref": "section 1.1", "type": "data_protection", "content": "Données personnelles collectées", "is_vague": true, "missing_fields": ["localisation_hebergement"]}]}'
        elif "consensus" in prompt.lower() or "juridique" in prompt.lower():
            return '{"findings": [{"clause_ref": "section 1.1", "risk_level": "modere", "confidence": "medium", "matched_sources": [], "recommendation": "Préciser la localisation d\\'hébergement"}]}'
        return '{"result": "mock response"}'
    
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        # Return dummy embeddings (1536 dimensions)
        return [[0.0] * 1536 for _ in texts]