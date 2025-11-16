"""Caching utilities with Redis and in-memory fallback."""

import json
import os
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional, Union
from functools import wraps

from .logging import get_logger

logger = get_logger(__name__)


class Cache:
    """Base cache interface."""

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL in seconds."""
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        raise NotImplementedError

    def clear(self) -> bool:
        """Clear all cache entries."""
        raise NotImplementedError

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        raise NotImplementedError

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values."""
        return {key: self.get(key) for key in keys}

    def set_many(self, mapping: dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values."""
        return all(self.set(key, value, ttl) for key, value in mapping.items())


class InMemoryCache(Cache):
    """In-memory cache implementation (for development)."""

    def __init__(self):
        """Initialize in-memory cache."""
        self._cache: dict[str, tuple[Any, Optional[datetime]]] = {}
        logger.info("Initialized in-memory cache")

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            return None

        value, expires_at = self._cache[key]

        # Check if expired
        if expires_at and datetime.utcnow() > expires_at:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        expires_at = None
        if ttl:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)

        self._cache[key] = (value, expires_at)
        return True

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return self.get(key) is not None

    def clear(self) -> bool:
        """Clear all cache entries."""
        self._cache.clear()
        return True

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        current = self.get(key) or 0
        new_value = current + amount
        self.set(key, new_value)
        return new_value


class RedisCache(Cache):
    """Redis cache implementation."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "dataforge:",
    ):
        """Initialize Redis cache.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            prefix: Key prefix for namespacing
        """
        try:
            import redis
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=False,  # We'll handle encoding
            )
            self.prefix = prefix
            # Test connection
            self.redis.ping()
            logger.info(f"Connected to Redis at {host}:{port}")
        except ImportError:
            raise ImportError("redis package required. Install with: pip install redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.prefix}{key}"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        return pickle.dumps(value)

    def _deserialize(self, value: bytes) -> Any:
        """Deserialize value from storage."""
        if value is None:
            return None
        return pickle.loads(value)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = self.redis.get(self._make_key(key))
            return self._deserialize(value)
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            serialized = self._serialize(value)
            if ttl:
                return bool(self.redis.setex(self._make_key(key), ttl, serialized))
            else:
                return bool(self.redis.set(self._make_key(key), serialized))
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            return bool(self.redis.delete(self._make_key(key)))
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return bool(self.redis.exists(self._make_key(key)))
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False

    def clear(self) -> bool:
        """Clear all cache entries with prefix."""
        try:
            keys = self.redis.keys(f"{self.prefix}*")
            if keys:
                self.redis.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        try:
            return int(self.redis.incrby(self._make_key(key), amount))
        except Exception as e:
            logger.error(f"Redis increment error for key {key}: {e}")
            return 0

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values efficiently."""
        try:
            prefixed_keys = [self._make_key(k) for k in keys]
            values = self.redis.mget(prefixed_keys)
            return {
                keys[i]: self._deserialize(v)
                for i, v in enumerate(values)
                if v is not None
            }
        except Exception as e:
            logger.error(f"Redis get_many error: {e}")
            return {}

    def set_many(self, mapping: dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values using pipeline."""
        try:
            pipe = self.redis.pipeline()
            for key, value in mapping.items():
                serialized = self._serialize(value)
                if ttl:
                    pipe.setex(self._make_key(key), ttl, serialized)
                else:
                    pipe.set(self._make_key(key), serialized)
            pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Redis set_many error: {e}")
            return False


# Global cache instance
_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Get global cache instance.

    Returns:
        Cache instance (Redis or in-memory fallback)
    """
    global _cache

    if _cache is None:
        # Try to use Redis if configured
        redis_url = os.getenv("REDIS_URL")
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD")

        try:
            if redis_url or redis_host:
                _cache = RedisCache(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                )
            else:
                logger.info("Redis not configured, using in-memory cache")
                _cache = InMemoryCache()
        except Exception as e:
            logger.warning(f"Failed to initialize Redis, falling back to in-memory cache: {e}")
            _cache = InMemoryCache()

    return _cache


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """Decorator to cache function results.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key

    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}{func.__name__}:{args}:{kwargs}"

            # Try to get from cache
            cache = get_cache()
            cached_value = cache.get(cache_key)

            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {cache_key}")

            return result

        return wrapper
    return decorator


def cache_clear(pattern: str = "*"):
    """Clear cache entries matching pattern.

    Args:
        pattern: Key pattern to match
    """
    cache = get_cache()
    if isinstance(cache, RedisCache):
        try:
            keys = cache.redis.keys(f"{cache.prefix}{pattern}")
            if keys:
                cache.redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries matching {pattern}")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    else:
        cache.clear()
        logger.info("Cleared in-memory cache")
