"""
LLM client with 4-tier fallback chain.

Tier 1: Gemini 2.5 Flash (FREE 1500 req/day)
Tier 2: gpt-4o-mini
Tier 3: gpt-5.4-nano
Tier 4: gpt-5-mini
"""

import asyncio
import json
import os
from typing import Any

import litellm
import structlog
from litellm.exceptions import (
    BadRequestError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from app.config import get_settings
from app.llm.models import LLMResponse, ToolCall

log = structlog.get_logger()
settings = get_settings()

# Set provider API keys in environment for LiteLLM auto-discovery
os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
os.environ["OPENAI_API_KEY"] = settings.openai_api_key
if settings.anthropic_api_key:
    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

# Suppress LiteLLM verbose logs
litellm.suppress_debug_info = True


def _parse_tool_calls(raw_tool_calls: list[Any] | None) -> list[ToolCall]:
    """Convert LiteLLM tool_calls into ToolCall dataclasses."""
    if not raw_tool_calls:
        return []
    result = []
    for tc in raw_tool_calls:
        try:
            args = json.loads(tc.function.arguments) if tc.function.arguments else {}
        except (json.JSONDecodeError, AttributeError):
            args = {}
        result.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
    return result


async def chat_completion(
    messages: list[dict[str, object]],
    model: str | None = None,
    tools: list[dict[str, object]] | None = None,
    stream: bool = False,
    max_tokens: int | None = None,
) -> LLMResponse:
    """
    Call LLM using a 4-tier fallback chain.

    If model is None, the full chain [primary, fallback, tier3, tier4] is used.
    If model is specified, the chain starts from that model and continues through
    the remaining tiers — so non-primary routes still get tier3/tier4 fallback.

    Returns an LLMResponse with content, tool_calls, model, and token counts.
    """
    _all_tiers = [
        settings.llm_primary,
        settings.llm_fallback,
        settings.llm_tier3,
        settings.llm_tier4,
    ]
    if model is None:
        chain = _all_tiers
    else:
        try:
            start = _all_tiers.index(model)
            chain = _all_tiers[start:]
        except ValueError:
            chain = [model]  # unknown model, use as single-entry chain

    last_error: Exception | None = None

    for attempt, m in enumerate(chain):
        try:
            log.info(
                "llm.call",
                model=m,
                attempt=attempt,
                message_count=len(messages),
                has_tools=tools is not None,
            )
            response = await asyncio.wait_for(
                litellm.acompletion(
                    model=m,
                    messages=messages,
                    tools=tools or None,
                    stream=stream,
                    max_tokens=max_tokens or settings.llm_max_tokens_out,
                    temperature=0.7,
                ),
                timeout=settings.llm_timeout_seconds,
            )
            msg = response.choices[0].message
            content = msg.content or ""
            tool_calls = _parse_tool_calls(getattr(msg, "tool_calls", None))
            usage = response.usage
            tokens_in = getattr(usage, "prompt_tokens", 0) or 0
            tokens_out = getattr(usage, "completion_tokens", 0) or 0
            log.info(
                "llm.success",
                model=m,
                response_len=len(content),
                tool_call_count=len(tool_calls),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
            return LLMResponse(
                content=content,
                model=m,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                tool_calls=tool_calls,
            )

        except (TimeoutError, RateLimitError, Timeout, ServiceUnavailableError) as e:
            log.warning("llm.transient_error", model=m, error=str(e))
            last_error = e
            continue
        except BadRequestError as e:
            log.error("llm.bad_request", model=m, error=str(e))
            last_error = e
            continue
        except Exception as e:
            log.exception("llm.unexpected_error", model=m)
            last_error = e
            continue

    raise RuntimeError(f"All LLM providers failed: {last_error}")
