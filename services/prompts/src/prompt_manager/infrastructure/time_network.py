import threading
import time
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

import httpx
from zoneinfo import ZoneInfo

IS_ONLINE: bool = False
_offset: timedelta = timedelta(0)
_lock = threading.Lock()
_stop_event = threading.Event()
_thread: Optional[threading.Thread] = None


def check_connectivity() -> bool:
    global IS_ONLINE
    try:
        resp = httpx.head("https://www.baidu.com", timeout=3)
        online = resp.status_code < 500
    except Exception:
        online = False
    with _lock:
        IS_ONLINE = online
    return online


def _parse_http_date(date_str: str) -> Optional[datetime]:
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _fetch_server_time_via_http() -> Optional[datetime]:
    try:
        r = httpx.head("https://www.baidu.com", timeout=3)
        date_hdr = r.headers.get("Date")
        if not date_hdr:
            return None
        return _parse_http_date(date_hdr)
    except Exception:
        return None


def refresh_time_offset() -> Optional[timedelta]:
    global _offset
    if not IS_ONLINE and not check_connectivity():
        return None
    server_dt = _fetch_server_time_via_http()
    if not server_dt:
        return None
    now_utc = datetime.now(timezone.utc)
    with _lock:
        _offset = server_dt - now_utc
    return _offset


async def refresh_time_offset_with_supabase(supabase: Any) -> Optional[timedelta]:
    global _offset
    if not IS_ONLINE and not check_connectivity():
        return None
    try:
        result = await supabase.rpc("get_server_time")
        server_dt: Optional[datetime] = None
        if isinstance(result, datetime):
            server_dt = result.astimezone(timezone.utc)
        elif isinstance(result, str):
            try:
                server_dt = datetime.fromisoformat(result.replace("Z", "+00:00")).astimezone(timezone.utc)
            except Exception:
                server_dt = None
        elif isinstance(result, dict):
            v = result.get("server_time")
            if isinstance(v, str):
                try:
                    server_dt = datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(timezone.utc)
                except Exception:
                    server_dt = None
        if not server_dt:
            return None
        now_utc = datetime.now(timezone.utc)
        with _lock:
            _offset = server_dt - now_utc
        return _offset
    except Exception:
        return None


def get_precise_time() -> datetime:
    with _lock:
        off = _offset
    return datetime.now(timezone.utc) + off


def to_shanghai_time(dt: datetime) -> datetime:
    return dt.astimezone(ZoneInfo("Asia/Shanghai"))


def _monitor_loop(interval_seconds: int):
    while not _stop_event.is_set():
        try:
            check_connectivity()
            refresh_time_offset()
        except Exception:
            pass
        _stop_event.wait(interval_seconds)


def start_background_monitor(interval_seconds: int = 45):
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_monitor_loop, args=(interval_seconds,), daemon=True)
    _thread.start()


def stop_background_monitor(timeout: Optional[float] = 2.0):
    _stop_event.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=timeout)


async def _supabase_time_loop(supabase: Any, interval_seconds: int):
    while True:
        try:
            await refresh_time_offset_with_supabase(supabase)
        except Exception:
            pass
        await asyncio.sleep(interval_seconds)


def start_supabase_time_task(supabase: Any, interval_seconds: int = 60) -> asyncio.Task:
    return asyncio.create_task(_supabase_time_loop(supabase, interval_seconds))


def stop_supabase_time_task(task: Optional[asyncio.Task]):
    if task and not task.done():
        task.cancel()
