"""ToolExecutionLog repository — write-only (analytics + debug)."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool_log import ToolExecutionLog


async def log_execution(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tool_name: str,
    input: dict[str, Any],
    output: dict[str, Any] | None,
    status: str,
    duration_ms: int,
    message_id: uuid.UUID | None = None,
    error_message: str | None = None,
) -> ToolExecutionLog:
    """
    Insert a ToolExecutionLog row and flush (no commit — caller owns the transaction).

    status must be one of: 'success', 'failed', 'timeout'.
    """
    entry = ToolExecutionLog(
        user_id=user_id,
        message_id=message_id,
        tool_name=tool_name,
        input=input,
        output=output,
        status=status,
        error_message=error_message,
        duration_ms=duration_ms,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry
