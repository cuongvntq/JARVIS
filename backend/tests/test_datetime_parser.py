"""Tests for Vietnamese datetime parser — 10 cases covering dict+regex+LLM paths."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

from app.utils.datetime_parser import ParseDatetimeError, parse_datetime

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
# Fixed reference: 2026-05-28 06:00 UTC  =  13:00 Asia/Ho_Chi_Minh (Thursday)
NOW_UTC = datetime(2026, 5, 28, 6, 0, 0, tzinfo=UTC)
NOW_LOCAL = NOW_UTC.astimezone(VN_TZ)


def _vn(year, month, day, hour, minute=0) -> datetime:
    """Build a UTC datetime from a VN local time."""
    local = datetime(year, month, day, hour, minute, 0, tzinfo=VN_TZ)
    return local.astimezone(UTC)


# ── Case 1: "chiều nay" → today 15:00 VN ─────────────────────────────────────
async def test_chieu_nay():
    result = await parse_datetime("chiều nay", now_utc=NOW_UTC)
    assert result == _vn(2026, 5, 28, 15)


# ── Case 2: "sáng mai" → tomorrow 08:00 VN ───────────────────────────────────
async def test_sang_mai():
    result = await parse_datetime("sáng mai", now_utc=NOW_UTC)
    assert result == _vn(2026, 5, 29, 8)


# ── Case 3: "tối nay" → today 20:00 VN ───────────────────────────────────────
async def test_toi_nay():
    result = await parse_datetime("tối nay", now_utc=NOW_UTC)
    assert result == _vn(2026, 5, 28, 20)


# ── Case 4: "ngày mai 9h" → tomorrow 09:00 VN ────────────────────────────────
async def test_ngay_mai_9h():
    result = await parse_datetime("ngày mai 9h", now_utc=NOW_UTC)
    assert result == _vn(2026, 5, 29, 9)


# ── Case 5: "hôm nay 14h" → today 14:00 VN ───────────────────────────────────
async def test_hom_nay_14h():
    result = await parse_datetime("hôm nay 14h", now_utc=NOW_UTC)
    assert result == _vn(2026, 5, 28, 14)


# ── Case 6: "trưa mai" → tomorrow 12:00 VN ───────────────────────────────────
async def test_trua_mai():
    result = await parse_datetime("trưa mai", now_utc=NOW_UTC)
    assert result == _vn(2026, 5, 29, 12)


# ── Case 7: "thứ 6 tới" → next Friday 12:00 VN ───────────────────────────────
async def test_thu_6_toi():
    result = await parse_datetime("thứ 6 tới", now_utc=NOW_UTC)
    # Compute expected next Friday from NOW_LOCAL (Thursday = weekday 3)
    today_wd = NOW_LOCAL.weekday()
    days_ahead = 4 - today_wd  # friday = 4
    if days_ahead <= 0:
        days_ahead += 7
    expected_local = (NOW_LOCAL + timedelta(days=days_ahead)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    assert result == expected_local.astimezone(UTC)


# ── Case 8: "21/06 10h" → 2026-06-21 10:00 VN ───────────────────────────────
async def test_dd_mm_with_hour():
    result = await parse_datetime("21/06 10h", now_utc=NOW_UTC)
    assert result == _vn(2026, 6, 21, 10)


# ── Case 9: "cuối tuần" → this Saturday 12:00 VN ─────────────────────────────
async def test_cuoi_tuan():
    result = await parse_datetime("cuối tuần", now_utc=NOW_UTC)
    # "this saturday" from dict — saturday = weekday 5
    today_wd = NOW_LOCAL.weekday()
    days_ahead = 5 - today_wd
    if days_ahead < 0:
        days_ahead += 7
    expected_local = (NOW_LOCAL + timedelta(days=days_ahead)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    assert result == expected_local.astimezone(UTC)


# ── Case 10: LLM fallback — unparseable text triggers fallback ────────────────
async def test_llm_fallback_success():
    """Text that dict+regex cannot handle → LLM is called and its result used."""
    expected = datetime(2026, 6, 1, 3, 0, 0, tzinfo=UTC)
    with patch(
        "app.utils.datetime_parser._llm_fallback",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_fb:
        result = await parse_datetime("2 ngày nữa", now_utc=NOW_UTC)
    mock_fb.assert_called_once()
    assert result == expected


async def test_llm_fallback_raises_on_none():
    """When LLM also returns None, ParseDatetimeError is raised."""
    with (
        patch(
            "app.utils.datetime_parser._llm_fallback",
            new_callable=AsyncMock,
            return_value=None,
        ),
        pytest.raises(ParseDatetimeError),
    ):
        await parse_datetime("xyz không phải datetime", now_utc=NOW_UTC)


# ── ISO 8601 fast path ────────────────────────────────────────────────────────
async def test_iso8601_fast_path():
    """Already-UTC ISO 8601 string passes through unchanged."""
    iso = "2026-06-15T08:00:00Z"
    result = await parse_datetime(iso, now_utc=NOW_UTC)
    assert result == datetime(2026, 6, 15, 8, 0, 0, tzinfo=UTC)
