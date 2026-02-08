"""
Enhanced Redis cache integration with connection pooling and monitoring.

Provides production-ready Redis caching with:
- Connection pooling
- Automatic reconnection
- Performance monitoring
- Circuit breaker pattern
"""

import pickle
import time
from typing import Any, Optional, Dict
from datetime import timedelta
from loguru import logger

try:
    import redis
    from redis.connection import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - install with: pip install redis")


class RedisCache:
    """
    Production-ready Redis cache with advanced features.

    Features:
    - Connection pooling for better performance
    - Automatic reconnection on failures
    - Circuit breaker to prevent cascading failures
    - Hit/miss rate tracking
    - Configurable TTL per key
    """

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 1800,  # 30 minutes
        max_connections: int = 50,
        socket_timeout: int = 5,
        enable_circuit_breaker: bool = True,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        """
        Initialize Redis cache.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            default_ttl: Default TTL in seconds
            max_connections: Maximum connection pool size
            socket_timeout: Socket timeout in seconds
            enable_circuit_breaker: Enable circuit breaker pattern
            circuit_breaker_threshold: Failures before opening circuit
            circuit_breaker_timeout: Seconds before attempting to close circuit
        """
        if not REDIS_AVAILABLE:
            raise ImportError("Redis is not installed. Install with: pip install redis")

        self.default_ttl = default_ttl
        self.enable_circuit_breaker = enable_circuit_breaker

        # Circuit breaker state
        self._circuit_open = False
        self._failure_count = 0
        self._circuit_breaker_threshold = circuit_breaker_threshold
        self._circuit_breaker_timeout = circuit_breaker_timeout
        self._circuit_open_time: Optional[float] = None

        # Create connection pool
        self.pool = ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_timeout,
            decode_responses=False,  # We use pickle for serialization
        )

        # Create Redis client
        self.client = redis.Redis(connection_pool=self.pool)

        # Performance metrics
        self._hits = 0
        self._misses = 0
        self._errors = 0
        self._total_get_time = 0.0
        self._total_set_time = 0.0

        # Test connection
        try:
            self.client.ping()
            logger.info(f"Redis cache initialized: {host}:{port} (db={db})")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            if self.enable_circuit_breaker:
                self._open_circuit()
            raise

    def get(self, key: str, prefix: str = "strategy") -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key
            prefix: Key prefix (default: "strategy")

        Returns:
            Cached value or None if not found
        """
        # Check circuit breaker
        if self._is_circuit_open():
            logger.debug("Circuit breaker is open, skipping Redis get")
            return None

        full_key = f"{prefix}:{key}"
        start_time = time.time()

        try:
            cached = self.client.get(full_key)

            # Record metrics
            duration = (time.time() - start_time) * 1000
            self._total_get_time += duration

            if cached:
                self._hits += 1
                value = pickle.loads(cached)
                logger.debug(f"Redis cache hit: {key} ({duration:.2f}ms)")
                self._reset_circuit()
                return value
            else:
                self._misses += 1
                logger.debug(f"Redis cache miss: {key}")
                return None

        except Exception as e:
            self._errors += 1
            logger.warning(f"Redis get error for key '{key}': {e}")
            self._handle_error()
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        prefix: str = "strategy"
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = use default)
            prefix: Key prefix (default: "strategy")

        Returns:
            True if successful, False otherwise
        """
        # Check circuit breaker
        if self._is_circuit_open():
            logger.debug("Circuit breaker is open, skipping Redis set")
            return False

        full_key = f"{prefix}:{key}"
        ttl = ttl or self.default_ttl
        start_time = time.time()

        try:
            serialized = pickle.dumps(value)
            self.client.setex(full_key, ttl, serialized)

            # Record metrics
            duration = (time.time() - start_time) * 1000
            self._total_set_time += duration

            logger.debug(f"Redis cache set: {key} (ttl={ttl}s, {duration:.2f}ms)")
            self._reset_circuit()
            return True

        except Exception as e:
            self._errors += 1
            logger.warning(f"Redis set error for key '{key}': {e}")
            self._handle_error()
            return False

    def delete(self, key: str, prefix: str = "strategy") -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key
            prefix: Key prefix

        Returns:
            True if key was deleted, False otherwise
        """
        if self._is_circuit_open():
            return False

        full_key = f"{prefix}:{key}"

        try:
            result = self.client.delete(full_key)
            logger.debug(f"Redis cache delete: {key}")
            self._reset_circuit()
            return result > 0

        except Exception as e:
            logger.warning(f"Redis delete error for key '{key}': {e}")
            self._handle_error()
            return False

    def clear(self, prefix: str = "strategy") -> int:
        """
        Clear all keys with given prefix.

        Args:
            prefix: Key prefix to clear

        Returns:
            Number of keys deleted
        """
        if self._is_circuit_open():
            return 0

        try:
            pattern = f"{prefix}:*"
            keys = self.client.keys(pattern)

            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"Cleared {deleted} Redis keys with prefix '{prefix}'")
                self._reset_circuit()
                return deleted
            else:
                return 0

        except Exception as e:
            logger.warning(f"Redis clear error: {e}")
            self._handle_error()
            return 0

    def exists(self, key: str, prefix: str = "strategy") -> bool:
        """Check if key exists in cache."""
        if self._is_circuit_open():
            return False

        full_key = f"{prefix}:{key}"

        try:
            result = self.client.exists(full_key)
            return result > 0
        except Exception as e:
            logger.warning(f"Redis exists error: {e}")
            self._handle_error()
            return False

    def get_ttl(self, key: str, prefix: str = "strategy") -> Optional[int]:
        """Get remaining TTL for a key in seconds."""
        if self._is_circuit_open():
            return None

        full_key = f"{prefix}:{key}"

        try:
            ttl = self.client.ttl(full_key)
            return ttl if ttl >= 0 else None
        except Exception as e:
            logger.warning(f"Redis TTL error: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with performance metrics
        """
        total_requests = self._hits + self._misses

        return {
            'hits': self._hits,
            'misses': self._misses,
            'errors': self._errors,
            'total_requests': total_requests,
            'hit_rate': self._hits / total_requests if total_requests > 0 else 0.0,
            'miss_rate': self._misses / total_requests if total_requests > 0 else 0.0,
            'avg_get_time_ms': (
                self._total_get_time / total_requests if total_requests > 0 else 0.0
            ),
            'avg_set_time_ms': (
                self._total_set_time / self._hits if self._hits > 0 else 0.0
            ),
            'circuit_open': self._circuit_open,
            'failure_count': self._failure_count,
        }

    def reset_stats(self):
        """Reset performance statistics."""
        self._hits = 0
        self._misses = 0
        self._errors = 0
        self._total_get_time = 0.0
        self._total_set_time = 0.0
        logger.info("Redis cache statistics reset")

    def ping(self) -> bool:
        """Check if Redis is available."""
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    def close(self):
        """Close Redis connection pool."""
        try:
            self.pool.disconnect()
            logger.info("Redis connection pool closed")
        except Exception as e:
            logger.warning(f"Error closing Redis pool: {e}")

    # Circuit breaker methods

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        if not self.enable_circuit_breaker:
            return False

        if not self._circuit_open:
            return False

        # Check if timeout has elapsed
        if self._circuit_open_time is not None:
            elapsed = time.time() - self._circuit_open_time

            if elapsed >= self._circuit_breaker_timeout:
                logger.info("Circuit breaker timeout elapsed, attempting to close circuit")
                self._circuit_open = False
                self._circuit_open_time = None
                self._failure_count = 0
                return False

        return True

    def _open_circuit(self):
        """Open the circuit breaker."""
        if not self._circuit_open:
            self._circuit_open = True
            self._circuit_open_time = time.time()
            logger.warning(
                f"Circuit breaker OPENED after {self._failure_count} failures. "
                f"Will retry after {self._circuit_breaker_timeout}s"
            )

    def _reset_circuit(self):
        """Reset circuit breaker after successful operation."""
        if self._failure_count > 0:
            self._failure_count = 0

        if self._circuit_open:
            self._circuit_open = False
            self._circuit_open_time = None
            logger.info("Circuit breaker CLOSED after successful operation")

    def _handle_error(self):
        """Handle errors and update circuit breaker state."""
        if not self.enable_circuit_breaker:
            return

        self._failure_count += 1

        if self._failure_count >= self._circuit_breaker_threshold:
            self._open_circuit()

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"RedisCache("
            f"hits={stats['hits']}, "
            f"misses={stats['misses']}, "
            f"hit_rate={stats['hit_rate']:.2%}, "
            f"circuit_open={stats['circuit_open']})"
        )
