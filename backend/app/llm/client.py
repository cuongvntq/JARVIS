"""
LLM client with 2-tier fallback chain.

Primary: Gemini 2.5 Flash (FREE 1500 req/day)
Fallback: OpenAI gpt-4o-mini ($0.15/$0.60 per 1M tokens)
"""

import asyncio
import os

import litellm
import structlog
from litellm.exceptions import (
    BadRequestError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()

# Set provider API keys in environment for LiteLLM auto-discovery
os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
os.environ["OPENAI_API_KEY"] = settings.openai_api_key
if settings.anthropic_api_key:
    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

# Suppress LiteLLM verbose logs
litellm.suppress_debug_info = True


async def chat_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
    stream: bool = False,
    max_tokens: int | None = None,
) -> tuple[str, str, int, int]:
    """
    Try primary model, fall back to gpt-4o-mini if it fails.

    Returns:
        Tuple of (response_content, model_name_used, tokens_in, tokens_out).
    """
    chain = [settings.llm_primary, settings.llm_fallback]
    last_error: Exception | None = None

    for attempt, model in enumerate(chain):
        try:
            log.info(
                "llm.call",
                model=model,
                attempt=attempt,
                message_count=len(messages),
                has_tools=tools is not None,
            )
            response = await asyncio.wait_for(
                litellm.acompletion(
                    model=model,
                    messages=messages,
                    tools=tools,
                    stream=stream,
                    max_tokens=max_tokens or settings.llm_max_tokens_out,
                    temperature=0.7,
                ),
                timeout=settings.llm_timeout_seconds,
            )
            content = response.choices[0].message.content or ""
            usage = response.usage
            tokens_in = getattr(usage, "prompt_tokens", 0) or 0
            tokens_out = getattr(usage, "completion_tokens", 0) or 0
            log.info(
                "llm.success",
                model=model,
                response_len=len(content),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
            return content, model, tokens_in, tokens_out

        except (TimeoutError, RateLimitError, Timeout, ServiceUnavailableError) as e:
            log.warning("llm.transient_error", model=model, error=str(e))
            last_error = e
            continue
        except BadRequestError as e:
            log.error("llm.bad_request", model=model, error=str(e))
            last_error = e
            continue
        except Exception as e:
            log.exception("llm.unexpected_error", model=model)
            last_error = e
            continue

    raise RuntimeError(f"All LLM providers failed: {last_error}")
