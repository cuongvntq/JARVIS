"""LLMCallLog repository — write-only (cost tracking + analytics)."""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool_log import LLMCallLog

# Cost per 1M tokens (in_rate, out_rate) in USD
_COST_PER_M: dict[str, tuple[float, float]] = {
    "gemini/gemini-2.5-flash": (0.0, 0.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-5.4-nano": (0.075, 0.30),
    "gpt-5-mini": (0.25, 2.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
}


def _calc_cost(model: str, tokens_in: int, tokens_out: int) -> Decimal:
    in_rate, out_rate = _COST_PER_M.get(model, (0.0, 0.0))
    cost = (tokens_in * in_rate + tokens_out * out_rate) / 1_000_000
    return Decimal(str(round(cost, 6)))


async def log_call(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    message_id: uuid.UUID | None,
    intent: str,
    classify_source: str,
    model_used: str,
    tokens_in: int,
    tokens_out: int,
    duration_ms: int,
    success: bool,
    error_code: str | None = None,
) -> LLMCallLog:
    """
    Insert an LLMCallLog row and flush (no commit — caller owns the transaction).
    """
    entry = LLMCallLog(
        user_id=user_id,
        message_id=message_id,
        intent=intent,
        classify_source=classify_source,
        model_used=model_used,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=_calc_cost(model_used, tokens_in, tokens_out),
        duration_ms=duration_ms,
        success=success,
        error_code=error_code,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry
