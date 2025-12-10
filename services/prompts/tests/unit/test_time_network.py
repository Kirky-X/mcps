import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

import prompt_manager.infrastructure.time_network as tn


def test_check_connectivity_updates_state():
    with patch("httpx.head") as mock_head:
        resp = MagicMock()
        resp.status_code = 200
        mock_head.return_value = resp
        ok = tn.check_connectivity()
        assert ok is True
        assert tn.IS_ONLINE is True


def test_refresh_time_offset_with_http_date():
    dt = datetime.now(timezone.utc)
    http_date = dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
    with patch("httpx.head") as mock_head:
        resp = MagicMock()
        resp.headers = {"Date": http_date}
        resp.status_code = 200
        mock_head.return_value = resp
        off = tn.refresh_time_offset()
        assert off is not None
        precise = tn.get_precise_time()
        assert isinstance(precise, datetime)
        assert precise.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_refresh_time_offset_with_supabase_iso_string():
    class DummySupabase:
        async def rpc(self, name):
            return datetime.now(timezone.utc).isoformat()

    with patch("httpx.head") as mock_head:
        resp = MagicMock()
        resp.status_code = 200
        mock_head.return_value = resp
        off = await tn.refresh_time_offset_with_supabase(DummySupabase())
        assert off is not None
        now = tn.get_precise_time()
        assert isinstance(now, datetime)
