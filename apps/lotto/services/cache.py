from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from django.core.cache import cache


class AnalysisCache:
    def build_key(self, name: str, params: dict) -> str:
        payload = json.dumps(params, sort_keys=True, default=str)
        digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()[:12]
        return f"analysis:{name}:{digest}"

    def get_or_set(self, name: str, params: dict, factory: Callable[[], Any], ttl: int | None = None) -> Any:
        key = self.build_key(name, params)
        cached = cache.get(key)
        if cached is not None:
            return cached
        value = factory()
        cache.set(key, value, ttl)
        return value
