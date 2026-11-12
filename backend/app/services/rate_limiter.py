"""Strict rate limiting for LLM and Embedding calls using Redis and in-memory fallback.

Prevents HTTP 429 (RESOURCE_EXHAUSTED) by enforcing RPM (Requests Per Minute),
TPM (Tokens Per Minute), and RPD (Requests Per Day) thresholds before sending requests.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Tuple
import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Known official rate limits from Google AI Studio / Provider specs
KNOWN_MODEL_LIMITS = {
    "gemini-3.8-flash": {"rpm": 5, "tpm": 250_000, "rpd": 20},
    "gemini-3.6-flash": {"rpm": 5, "tpm": 250_000, "rpd": 20},
    "gemini-3.5-flash-lite": {"rpm": 15, "tpm": 250_000, "rpd": 500},
    "gemini-embedding-2": {"rpm": 100, "tpm": 30_000, "rpd": 1_000},
    "gpt-4o-mini": {"rpm": 60, "tpm": 150_000, "rpd": 1_000},
    "claude-3-5-haiku-20241022": {"rpm": 50, "tpm": 100_000, "rpd": 1_000},
    "llama-3.3-70b-versatile": {"rpm": 30, "tpm": 100_000, "rpd": 1_000},
}


class QuotaExceededError(Exception):
    """Raised when a model has exhausted its daily or minute request quota."""
    pass


class LLMRateLimiter:
    def __init__(self):
        settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            self.redis_client.ping()
        except Exception as exc:
            logger.warning("Redis indisponible pour le rate limiter, repli sur la mémoire locale: %s", exc)
            self.redis_client = None

        self._local_counts = {}

    def _get_keys(self, provider: str, model: str) -> Tuple[str, str, str]:
        now = datetime.now(timezone.utc)
        min_key = now.strftime("%Y%m%d%H%M")
        day_key = now.strftime("%Y%m%d")
        safe_model = model.replace(":", "_").replace("/", "_")
        return (
            f"ece:ratelimit:rpm:{provider}:{safe_model}:{min_key}",
            f"ece:ratelimit:rpd:{provider}:{safe_model}:{day_key}",
            f"ece:ratelimit:tpm:{provider}:{safe_model}:{min_key}",
        )

    async def acquire_slot(
        self,
        provider: str,
        model: str,
        rpm_limit: Optional[int] = None,
        rpd_limit: Optional[int] = None,
        tpm_limit: Optional[int] = None,
        estimated_tokens: int = 500,
        max_wait_seconds: float = 30.0,
    ) -> bool:
        """Verify quota before calling LLM. Throws QuotaExceededError if daily quota is reached,

        or smoothly pauses if RPM limit is momentarily reached.
        """
        # Look up known defaults if not provided in DB config
        known = KNOWN_MODEL_LIMITS.get(model, {})
        effective_rpm = rpm_limit or known.get("rpm")
        effective_rpd = rpd_limit or known.get("rpd")
        effective_tpm = tpm_limit or known.get("tpm")

        rpm_key, rpd_key, tpm_key = self._get_keys(provider, model)

        # 1. Check daily limit (RPD)
        if effective_rpd and self.redis_client:
            try:
                current_rpd = int(self.redis_client.get(rpd_key) or 0)
                if current_rpd >= effective_rpd:
                    raise QuotaExceededError(
                        f"Limite quotidienne RPD ({effective_rpd} req/jour) atteinte pour {model} "
                        f"(actuel: {current_rpd}). Bascule immédiate sur le modèle suivant."
                    )
            except redis.RedisError:
                pass

        # 2. Check and pace per-minute limit (RPM)
        if effective_rpm:
            start_wait = time.time()
            while True:
                current_rpm = 0
                if self.redis_client:
                    try:
                        current_rpm = int(self.redis_client.get(rpm_key) or 0)
                    except redis.RedisError:
                        pass
                else:
                    current_rpm = self._local_counts.get(rpm_key, 0)

                if current_rpm < effective_rpm:
                    break

                elapsed = time.time() - start_wait
                if elapsed >= max_wait_seconds:
                    logger.warning(
                        "Délai d'attente RPM dépassé (%ss) pour %s (limite %s req/min)",
                        max_wait_seconds, model, effective_rpm
                    )
                    raise QuotaExceededError(
                        f"Limite RPM ({effective_rpm}/min) saturée pour {model}. Bascule fallback."
                    )

                # Wait 2 seconds before retrying current minute slot
                await asyncio.sleep(2.0)

        # 3. Check and pace tokens per-minute (TPM)
        if effective_tpm and self.redis_client:
            try:
                current_tpm = int(self.redis_client.get(tpm_key) or 0)
                if current_tpm + estimated_tokens > effective_tpm:
                    logger.info("Plafond TPM (%s) approché pour %s, temporisation 3s...", effective_tpm, model)
                    await asyncio.sleep(3.0)
            except redis.RedisError:
                pass

        # 4. Increment usage
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                pipe.incr(rpm_key)
                pipe.expire(rpm_key, 120)
                pipe.incr(rpd_key)
                pipe.expire(rpd_key, 86400 * 2)
                pipe.incrby(tpm_key, estimated_tokens)
                pipe.expire(tpm_key, 120)
                pipe.execute()
            except redis.RedisError as err:
                logger.debug("Erreur incrémentation Redis rate limit: %s", err)
        else:
            self._local_counts[rpm_key] = self._local_counts.get(rpm_key, 0) + 1

        return True


# Global singleton instance
rate_limiter = LLMRateLimiter()
