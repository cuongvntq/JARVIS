"""Embedding service — wraps LiteLLM aembedding."""

import litellm
import structlog

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()


async def embed_text(text: str) -> list[float]:
    """Embed a text string via LiteLLM. Returns a 1536-dim float vector."""
    response = await litellm.aembedding(
        model=settings.embedding_model,
        input=[text],
    )
    vec: list[float] = response.data[0]["embedding"]
    log.debug("embedding.done", model=settings.embedding_model, dim=len(vec))
    return vec
