# Copyright (c) Kirky.X. 2025. All rights reserved.
from __future__ import annotations

import time
from collections import OrderedDict
from datetime import timedelta
from typing import Any, Optional


class _CacheImpl:
    def __init__(self, max_capacity: int, ttl: Optional[float], tti: Optional[float]):
        self.max_capacity = max_capacity
        self.ttl = ttl
        self.tti = tti
        self.store: OrderedDict[str, tuple[Any, float, float]] = OrderedDict()

    def _now(self) -> float:
        return time.monotonic()

    def _expired(self, created_at: float, last_access: float) -> bool:
        now = self._now()
        if self.ttl is not None and now - created_at > self.ttl:
            return True
        if self.tti is not None and now - last_access > self.tti:
            return True
        return False

    def _evict_if_needed(self):
        while len(self.store) > self.max_capacity:
            self.store.popitem(last=False)

    def get(self, key: str) -> Optional[Any]:
        item = self.store.get(key)
        if item is None:
            return None
        value, created_at, last_access = item
        if self._expired(created_at, last_access):
            self.invalidate(key)
            return None
        # update order and access time for LRU/TTI
        now = self._now()
        self.store.move_to_end(key)
        self.store[key] = (value, created_at, now)
        return value

    def insert(self, key: str, value: Any) -> None:
        now = self._now()
        created_at = now
        self.store[key] = (value, created_at, now)
        self.store.move_to_end(key)
        self._evict_if_needed()

    def invalidate(self, key: str) -> None:
        if key in self.store:
            del self.store[key]


class Cache:
    def __init__(self, impl: _CacheImpl):
        self._impl = impl

    @classmethod
    def builder(cls) -> "CacheBuilder":
        return CacheBuilder()

    def get(self, key: str) -> Optional[Any]:
        return self._impl.get(key)

    def insert(self, key: str, value: Any) -> None:
        self._impl.insert(key, value)

    def invalidate(self, key: str) -> None:
        self._impl.invalidate(key)


class CacheBuilder:
    def __init__(self):
        self._max_capacity: int = 1000
        self._ttl_seconds: Optional[float] = None
        self._tti_seconds: Optional[float] = None

    def max_capacity(self, cap: int) -> "CacheBuilder":
        self._max_capacity = max(1, int(cap))
        return self

    def time_to_live(self, ttl: timedelta) -> "CacheBuilder":
        self._ttl_seconds = ttl.total_seconds()
        return self

    def time_to_idle(self, tti: timedelta) -> "CacheBuilder":
        self._tti_seconds = tti.total_seconds()
        return self

    def build(self) -> Cache:
        impl = _CacheImpl(self._max_capacity, self._ttl_seconds, self._tti_seconds)
        return Cache(impl)
