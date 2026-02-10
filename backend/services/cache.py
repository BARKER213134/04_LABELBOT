# Fast in-memory cache for user data
from typing import Dict, Any, Optional
import time

class FastCache:
    """Ultra-fast in-memory cache with TTL"""
    
    def __init__(self, ttl: int = 300):  # 5 min default TTL
        self._cache: Dict[str, tuple] = {}  # key -> (value, expire_time)
        self._ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self._cache:
            value, expire_time = self._cache[key]
            if time.time() < expire_time:
                return value
            del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache"""
        expire_time = time.time() + (ttl or self._ttl)
        self._cache[key] = (value, expire_time)
    
    def delete(self, key: str):
        """Delete from cache"""
        self._cache.pop(key, None)
    
    def clear(self):
        """Clear all cache"""
        self._cache.clear()

# Global caches
user_cache = FastCache(ttl=300)      # 5 min for user data
balance_cache = FastCache(ttl=60)    # 1 min for balance
banned_cache = FastCache(ttl=600)    # 10 min for ban status
