"""Vietnamese datetime parser — dict replace → regex → LLM fallback."""

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import structlog

log = structlog.get_logger()

_DICT_PATH = Path(__file__).parent.parent / "vi_time_dict.json"
_VI_DICT: list[list[str]] = json.loads(_DICT_PATH.read_text(encoding="utf-8"))


class ParseDatetimeError(Exception):
    """Raised when a Vietnamese datetime expression cannot be parsed."""


def _apply_dict(text: str) -> str:
    """Apply vi_time_dict.json replacements in order on lowercased text."""
    result = text.lower()
    for pattern, replacement in _VI_DICT:
        result = result.replace(pattern, replacement)
    return result


def _hour_minute(text: str) -> tuple[int, int] | None:
    """Extract (hour, minute) from normalized text. Returns None if not found."""
    # "9h30", "9h" — Vietnamese hour notation
    m = re.search(r"\b(\d{1,2})h(\d{2})?\b", text)
    if m:
        return int(m.group(1)), int(m.group(2) or 0)
    # "09:30", "15:00" — colon notation
    m = re.search(r"\b(\d{1,2}):(\d{2})\b", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


_WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _parse_step2(text: str, now_local: datetime) -> datetime | None:
    """
    Try to extract a datetime from normalized (post-dict) text.

    Returns a timezone-aware datetime in the user's local timezone, or None.
    """
    # 1. Explicit "today HH:MM" or "tomorrow HH:MM" from dict replacement
    m = re.search(r"\btoday\s+(\d{1,2}):(\d{2})\b", text)
    if m:
        return now_local.replace(
            hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0
        )

    m = re.search(r"\btomorrow\s+(\d{1,2}):(\d{2})\b", text)
    if m:
        return (now_local + timedelta(days=1)).replace(
            hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0
        )

    # 2. Extract freeform time (e.g., "9h", "14:00")
    hm = _hour_minute(text)
    h, m_min = (hm[0], hm[1]) if hm else (None, 0)

    def _at(base: datetime) -> datetime:
        """Return base at the extracted time (or noon if no time given)."""
        if h is not None:
            return base.replace(hour=h, minute=m_min, second=0, microsecond=0)
        return base.replace(hour=12, minute=0, second=0, microsecond=0)

    # 3. Named day references
    if "today" in text:
        return _at(now_local)
    if "tomorrow" in text:
        return _at(now_local + timedelta(days=1))
    if "yesterday" in text:
        return _at(now_local - timedelta(days=1))

    # 4. "+N days" (e.g., from "ngày kia" → "+2 days")
    m2 = re.search(r"\+(\d+)\s*days?", text)
    if m2:
        return _at(now_local + timedelta(days=int(m2.group(1))))

    # 5. Weekday references ("next friday", "this saturday")
    today_wd = now_local.weekday()
    for name, wd in _WEEKDAY_MAP.items():
        if f"next {name}" in text:
            days_ahead = wd - today_wd
            if days_ahead <= 0:
                days_ahead += 7
            return _at(now_local + timedelta(days=days_ahead))
        if f"this {name}" in text:
            days_ahead = wd - today_wd
            if days_ahead < 0:
                days_ahead += 7
            return _at(now_local + timedelta(days=days_ahead))

    # 6. "first next month"
    if "first next month" in text:
        year, month = now_local.year, now_local.month + 1
        if month > 12:
            month, year = 1, year + 1
        try:
            return _at(now_local.replace(year=year, month=month, day=1))
        except ValueError:
            return None

    # 7. DD/MM or DD/MM/YYYY (with optional extracted time)
    m2 = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b", text)
    if m2:
        day_v = int(m2.group(1))
        month_v = int(m2.group(2))
        year_v = int(m2.group(3)) if m2.group(3) else now_local.year
        try:
            base = now_local.replace(year=year_v, month=month_v, day=day_v)
            if not m2.group(3) and base.date() < now_local.date():
                base = base.replace(year=year_v + 1)
            return _at(base)
        except ValueError:
            return None

    # 8. Time only → today if in future, else tomorrow
    if h is not None:
        candidate = now_local.replace(hour=h, minute=m_min, second=0, microsecond=0)
        if candidate <= now_local:
            candidate += timedelta(days=1)
        return candidate

    return None


async def parse_datetime(
    text: str,
    user_tz: str = "Asia/Ho_Chi_Minh",
    now_utc: datetime | None = None,
) -> datetime:
    """
    Parse a Vietnamese datetime expression to UTC datetime.

    Pipeline:
      1. ISO 8601 fast path
      2. Dict replace → regex parse
      3. LLM fallback

    Raises:
        ParseDatetimeError: when all steps fail.
    """
    if now_utc is None:
        now_utc = datetime.now(UTC)

    # Fast path: already ISO 8601
    try:
        dt = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
        return dt.astimezone(UTC)
    except ValueError:
        pass

    tz = ZoneInfo(user_tz)
    now_local = now_utc.astimezone(tz)

    # Step 1: dict replace
    normalized = _apply_dict(text)
    log.debug("datetime_parser.normalized", original=text, normalized=normalized)

    # Step 2: regex parse
    result = _parse_step2(normalized, now_local)
    if result is not None:
        return result.astimezone(UTC)

    # Step 3: LLM fallback
    log.info("datetime_parser.llm_fallback", text=text)
    result_utc = await _llm_fallback(text, now_utc, user_tz)
    if result_utc is not None:
        return result_utc

    raise ParseDatetimeError(f"Cannot parse datetime from: '{text}'")


async def _llm_fallback(
    text: str,
    now_utc: datetime,
    user_tz: str,
) -> datetime | None:
    """Call LLM with a minimal prompt to parse datetime as last resort."""
    from app.llm.client import chat_completion

    prompt = (
        f"Parse this Vietnamese datetime expression to ISO 8601 UTC.\n"
        f'Expression: "{text}"\n'
        f"Current UTC: {now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
        f"User timezone: {user_tz}\n"
        f"Reply ONLY with ISO 8601 UTC (e.g. '2026-05-18T11:00:00Z') or 'CANNOT_PARSE'."
    )
    try:
        resp = await chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
        )
        content = resp.content.strip().strip('"').strip("'")
        if content == "CANNOT_PARSE":
            return None
        dt = datetime.fromisoformat(content.replace("Z", "+00:00"))
        return dt.astimezone(UTC)
    except Exception as e:
        log.warning("datetime_parser.llm_fallback_failed", error=str(e))
        return None
