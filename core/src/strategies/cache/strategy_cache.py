"""
策略缓存模块

提供多级缓存机制以提升策略加载性能
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pickle
from loguru import logger


class StrategyCache:
    """
    策略缓存

    多级缓存策略:
    1. 内存缓存 (进程级) - 最快，但进程重启后失效
    2. Redis缓存 (应用级) - 可选，需要Redis服务
    3. 数据库 (持久化) - 最慢，但永久保存

    当前实现: 主要使用内存缓存
    未来扩展: 可添加Redis支持
    """

    def __init__(self, redis_client=None, ttl_minutes: int = 30):
        """
        初始化缓存

        Args:
            redis_client: Redis客户端（可选）
            ttl_minutes: 缓存有效期（分钟）
        """
        self._memory_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self.redis = redis_client
        self.ttl = timedelta(minutes=ttl_minutes)

        logger.info(f"StrategyCache 初始化: TTL={ttl_minutes}分钟")

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存的值，如果不存在或过期则返回None
        """
        # 1. 检查内存缓存
        if key in self._memory_cache:
            if self._is_valid(key):
                logger.debug(f"命中内存缓存: {key}")
                return self._memory_cache[key]
            else:
                # 过期，删除
                logger.debug(f"内存缓存过期: {key}")
                del self._memory_cache[key]
                del self._cache_timestamps[key]

        # 2. 检查Redis缓存（如果可用）
        if self.redis:
            try:
                cached = self.redis.get(f"strategy:{key}")
                if cached:
                    logger.debug(f"命中Redis缓存: {key}")
                    value = pickle.loads(cached)
                    # 写回内存缓存
                    self._memory_cache[key] = value
                    self._cache_timestamps[key] = datetime.now()
                    return value
            except Exception as e:
                logger.warning(f"Redis读取失败: {e}")

        logger.debug(f"缓存未命中: {key}")
        return None

    def set(self, key: str, value: Any):
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
        """
        # 1. 写入内存
        self._memory_cache[key] = value
        self._cache_timestamps[key] = datetime.now()
        logger.debug(f"写入内存缓存: {key}")

        # 2. 写入Redis（如果可用）
        if self.redis:
            try:
                self.redis.setex(
                    f"strategy:{key}",
                    int(self.ttl.total_seconds()),
                    pickle.dumps(value)
                )
                logger.debug(f"写入Redis缓存: {key}")
            except Exception as e:
                logger.warning(f"Redis写入失败: {e}")

    def invalidate(self, key: str):
        """
        使缓存失效

        Args:
            key: 缓存键
        """
        # 删除内存缓存
        self._memory_cache.pop(key, None)
        self._cache_timestamps.pop(key, None)

        # 删除Redis缓存
        if self.redis:
            try:
                self.redis.delete(f"strategy:{key}")
                logger.debug(f"删除Redis缓存: {key}")
            except Exception as e:
                logger.warning(f"Redis删除失败: {e}")

        logger.info(f"缓存已失效: {key}")

    def clear(self):
        """清除所有缓存"""
        # 清除内存缓存
        self._memory_cache.clear()
        self._cache_timestamps.clear()

        # 清除Redis缓存（如果可用）
        if self.redis:
            try:
                # 删除所有以 strategy: 开头的键
                pattern = "strategy:*"
                keys = self.redis.keys(pattern)
                if keys:
                    self.redis.delete(*keys)
                    logger.debug(f"删除 {len(keys)} 个Redis缓存")
            except Exception as e:
                logger.warning(f"Redis清除失败: {e}")

        logger.info("所有缓存已清除")

    def _is_valid(self, key: str) -> bool:
        """
        检查缓存是否有效

        Args:
            key: 缓存键

        Returns:
            是否有效
        """
        if key not in self._cache_timestamps:
            return False

        elapsed = datetime.now() - self._cache_timestamps[key]
        return elapsed < self.ttl

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        # 统计有效缓存
        valid_count = sum(
            1 for key in self._memory_cache
            if self._is_valid(key)
        )

        # 统计过期缓存
        expired_count = len(self._memory_cache) - valid_count

        return {
            'total_keys': len(self._memory_cache),
            'valid_keys': valid_count,
            'expired_keys': expired_count,
            'ttl_minutes': self.ttl.total_seconds() / 60,
            'redis_enabled': self.redis is not None,
        }

    def cleanup_expired(self):
        """清理过期缓存"""
        expired_keys = [
            key for key in self._memory_cache
            if not self._is_valid(key)
        ]

        for key in expired_keys:
            del self._memory_cache[key]
            del self._cache_timestamps[key]

        if expired_keys:
            logger.info(f"清理了 {len(expired_keys)} 个过期缓存")

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"StrategyCache("
            f"valid={stats['valid_keys']}, "
            f"expired={stats['expired_keys']}, "
            f"ttl={stats['ttl_minutes']}min)"
        )


class CodeCache:
    """
    代码缓存

    专门用于缓存动态编译的代码模块
    避免重复编译相同的代码
    """

    def __init__(self, max_size: int = 100):
        """
        初始化代码缓存

        Args:
            max_size: 最大缓存数量
        """
        self._cache: Dict[str, Any] = {}
        self._access_count: Dict[str, int] = {}
        self.max_size = max_size

        logger.info(f"CodeCache 初始化: 最大容量={max_size}")

    def get(self, code_hash: str) -> Optional[Any]:
        """
        获取缓存的编译模块

        Args:
            code_hash: 代码哈希

        Returns:
            编译后的模块，如果不存在则返回None
        """
        if code_hash in self._cache:
            self._access_count[code_hash] = self._access_count.get(code_hash, 0) + 1
            logger.debug(f"命中代码缓存: {code_hash[:8]}...")
            return self._cache[code_hash]

        return None

    def set(self, code_hash: str, module: Any):
        """
        设置缓存

        Args:
            code_hash: 代码哈希
            module: 编译后的模块
        """
        # 如果缓存已满，删除最少使用的
        if len(self._cache) >= self.max_size:
            self._evict_least_used()

        self._cache[code_hash] = module
        self._access_count[code_hash] = 1

        logger.debug(f"写入代码缓存: {code_hash[:8]}...")

    def invalidate(self, code_hash: str):
        """
        使缓存失效

        Args:
            code_hash: 代码哈希
        """
        self._cache.pop(code_hash, None)
        self._access_count.pop(code_hash, None)

        logger.debug(f"代码缓存已失效: {code_hash[:8]}...")

    def clear(self):
        """清除所有缓存"""
        self._cache.clear()
        self._access_count.clear()

        logger.info("所有代码缓存已清除")

    def _evict_least_used(self):
        """删除最少使用的缓存项"""
        if not self._access_count:
            return

        # 找到访问次数最少的键
        least_used = min(self._access_count, key=self._access_count.get)

        # 删除
        del self._cache[least_used]
        del self._access_count[least_used]

        logger.debug(f"删除最少使用的缓存: {least_used[:8]}...")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        return {
            'total_modules': len(self._cache),
            'max_size': self.max_size,
            'usage_rate': len(self._cache) / self.max_size if self.max_size > 0 else 0,
            'total_accesses': sum(self._access_count.values()),
        }

    def __repr__(self) -> str:
        return f"CodeCache(size={len(self._cache)}/{self.max_size})"


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 示例1: 策略缓存
    cache = StrategyCache(ttl_minutes=30)

    # 设置缓存
    cache.set("strategy_1", {"name": "MomentumStrategy", "config": {}})
    cache.set("strategy_2", {"name": "MeanReversionStrategy", "config": {}})

    # 获取缓存
    strategy = cache.get("strategy_1")
    print(f"获取策略: {strategy}")

    # 查看统计
    stats = cache.get_stats()
    print(f"缓存统计: {stats}")

    # 清理过期缓存
    cache.cleanup_expired()

    # 示例2: 代码缓存
    code_cache = CodeCache(max_size=10)

    # 模拟代码哈希
    code_hash = "abc123def456"
    module = type('DynamicModule', (), {})()

    code_cache.set(code_hash, module)

    # 获取
    cached_module = code_cache.get(code_hash)
    print(f"获取模块: {cached_module}")

    # 统计
    print(f"代码缓存统计: {code_cache.get_stats()}")
