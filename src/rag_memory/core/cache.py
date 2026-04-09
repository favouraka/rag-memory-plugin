"""
Caching layer for RAG operations
"""

import hashlib
import logging
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class QueryCache:
    """LRU cache for search queries"""

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        Initialize query cache

        Args:
            max_size: Max cached queries
            ttl: Time-to-live in seconds (default 5 min)
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}

    def _make_key(self, query: str, namespace: Optional[str], mode: str) -> str:
        """Create cache key"""
        key = f"{mode}:{namespace or 'all'}:{query}"
        return hashlib.md5(key.encode()).hexdigest()

    def get(self, query: str, namespace: Optional[str], mode: str) -> Optional[Any]:
        """Get cached result"""
        key = self._make_key(query, namespace, mode)
        if key in self._cache:
            result, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                return result
            else:
                del self._cache[key]
        return None

    def set(self, query: str, namespace: Optional[str], mode: str, result: Any):
        """Cache result"""
        key = self._make_key(query, namespace, mode)
        self._cache[key] = (result, time.time())

        # Evict old entries if too large
        if len(self._cache) > self.max_size:
            oldest = min(self._cache.items(), key=lambda x: x[1][1])
            del self._cache[oldest[0]]

    def clear(self):
        """Clear cache"""
        self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Cache statistics"""
        return {"size": len(self._cache), "max_size": self.max_size, "ttl": self.ttl}


class PerformanceMetrics:
    """Track RAG performance"""

    def __init__(self):
        self._metrics: Dict[str, list] = {
            "search_times": [],
            "index_times": [],
            "cache_hits": 0,
            "cache_misses": 0,
        }
        self._max_samples = 1000

    def record_search(self, duration: float, cached: bool = False):
        """Record search operation"""
        self._metrics["search_times"].append(duration)
        if len(self._metrics["search_times"]) > self._max_samples:
            self._metrics["search_times"].pop(0)

        if cached:
            self._metrics["cache_hits"] += 1
        else:
            self._metrics["cache_misses"] += 1

    def record_index(self, duration: float):
        """Record index operation"""
        self._metrics["index_times"].append(duration)
        if len(self._metrics["index_times"]) > self._max_samples:
            self._metrics["index_times"].pop(0)

    def get_stats(self) -> Dict[str, Any]:
        """Get performance stats"""
        search_times = self._metrics["search_times"]
        index_times = self._metrics["index_times"]

        stats = {
            "search_count": len(search_times),
            "index_count": len(index_times),
            "cache_hits": self._metrics["cache_hits"],
            "cache_misses": self._metrics["cache_misses"],
        }

        if search_times:
            stats["avg_search_time"] = sum(search_times) / len(search_times)
            stats["min_search_time"] = min(search_times)
            stats["max_search_time"] = max(search_times)

        if index_times:
            stats["avg_index_time"] = sum(index_times) / len(index_times)

        total = self._metrics["cache_hits"] + self._metrics["cache_misses"]
        if total > 0:
            stats["cache_hit_rate"] = self._metrics["cache_hits"] / total

        return stats

    def reset(self):
        """Reset metrics"""
        for key in self._metrics:
            if isinstance(self._metrics[key], list):
                self._metrics[key] = []
            else:
                self._metrics[key] = 0
