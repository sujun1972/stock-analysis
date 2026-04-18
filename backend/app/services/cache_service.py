"""
Redis缓存服务
提供数据缓存、查询缓存、热点数据管理等功能
"""

import json
import pickle
import hashlib
import logging
from typing import Any, Optional, Dict, List, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
import asyncio
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
import pandas as pd

from app.core.config import settings as _settings

logger = logging.getLogger(__name__)


class CacheService:
    """缓存服务"""

    def __init__(self):
        self.settings = _settings
        self._init_redis()
        self._init_cache_config()

    def _init_redis(self):
        """初始化Redis连接"""
        try:
            # 创建连接池
            self.pool = ConnectionPool(
                host=self.settings.REDIS_HOST,
                port=self.settings.REDIS_PORT,
                db=0,
                max_connections=50,
                decode_responses=False  # 使用二进制模式以支持pickle
            )
            self.redis_client = redis.Redis(connection_pool=self.pool)
            logger.info("Redis缓存服务初始化成功")
        except Exception as e:
            logger.error(f"Redis初始化失败: {e}")
            self.redis_client = None

    def _init_cache_config(self):
        """初始化缓存配置（TTL 来自 settings.cache_ttl）"""
        ttl = self.settings.cache_ttl
        self.cache_ttl = {
            'realtime': ttl.realtime,
            'minute': ttl.minute,
            'daily': ttl.daily,
            'static': ttl.static,
            'analysis': ttl.analysis,
            'hot': ttl.hot,
        }

        # 缓存键前缀
        self.key_prefix = {
            'stock': 'stock:',
            'market': 'market:',
            'analysis': 'analysis:',
            'query': 'query:',
            'user': 'user:',
            'system': 'system:',
        }

    def _generate_key(self, prefix: str, identifier: str) -> str:
        """生成缓存键"""
        return f"{self.key_prefix.get(prefix, prefix)}:{identifier}"

    def _hash_params(self, params: Dict[str, Any]) -> str:
        """哈希参数生成唯一标识"""
        params_str = json.dumps(params, sort_keys=True, default=str)
        return hashlib.md5(params_str.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.redis_client:
            return None

        try:
            data = await self.redis_client.get(key)
            if data:
                try:
                    # 尝试pickle反序列化
                    return pickle.loads(data)
                except:
                    # 尝试JSON反序列化
                    return json.loads(data.decode('utf-8'))
            return None
        except Exception as e:
            logger.debug(f"缓存读取失败 {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        cache_type: str = 'daily'
    ) -> bool:
        """设置缓存"""
        if not self.redis_client:
            return False

        try:
            # 确定过期时间
            if ttl is None:
                ttl = self.cache_ttl.get(cache_type, 300)

            # 序列化数据
            if isinstance(value, (dict, list, str, int, float, bool)):
                data = json.dumps(value, default=str).encode('utf-8')
            else:
                data = pickle.dumps(value)

            # 设置缓存
            await self.redis_client.setex(key, ttl, data)
            return True

        except Exception as e:
            logger.debug(f"缓存设置失败 {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.redis_client:
            return False

        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.debug(f"缓存删除失败 {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的缓存"""
        if not self.redis_client:
            return 0

        try:
            keys = []
            async for key in self.redis_client.scan_iter(pattern):
                keys.append(key)

            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"删除了 {deleted} 个缓存键（模式: {pattern}）")
                return deleted
            return 0

        except Exception as e:
            logger.debug(f"批量删除失败 {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if not self.redis_client:
            return False

        try:
            return await self.redis_client.exists(key) > 0
        except:
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """设置过期时间"""
        if not self.redis_client:
            return False

        try:
            return await self.redis_client.expire(key, ttl)
        except:
            return False

    async def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        if not self.redis_client:
            return -1

        try:
            return await self.redis_client.ttl(key)
        except:
            return -1

    # 股票数据缓存

    async def cache_stock_data(
        self,
        ts_code: str,
        data_type: str,
        data: Any,
        trade_date: Optional[str] = None
    ) -> bool:
        """缓存股票数据"""
        if trade_date:
            key = self._generate_key('stock', f"{ts_code}:{data_type}:{trade_date}")
        else:
            key = self._generate_key('stock', f"{ts_code}:{data_type}")

        cache_type = 'realtime' if data_type == 'realtime' else 'daily'
        return await self.set(key, data, cache_type=cache_type)

    async def get_stock_data(
        self,
        ts_code: str,
        data_type: str,
        trade_date: Optional[str] = None
    ) -> Optional[Any]:
        """获取股票数据缓存"""
        if trade_date:
            key = self._generate_key('stock', f"{ts_code}:{data_type}:{trade_date}")
        else:
            key = self._generate_key('stock', f"{ts_code}:{data_type}")

        return await self.get(key)

    # 查询结果缓存

    async def cache_query_result(
        self,
        query: str,
        params: Dict[str, Any],
        result: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """缓存查询结果"""
        params_hash = self._hash_params({'query': query, 'params': params})
        key = self._generate_key('query', params_hash)
        return await self.set(key, result, ttl=ttl)

    async def get_query_result(
        self,
        query: str,
        params: Dict[str, Any]
    ) -> Optional[Any]:
        """获取查询结果缓存"""
        params_hash = self._hash_params({'query': query, 'params': params})
        key = self._generate_key('query', params_hash)
        return await self.get(key)

    # 热点数据管理

    async def add_to_hot_list(
        self,
        list_name: str,
        items: List[Dict[str, Any]],
        max_size: int = 100
    ) -> bool:
        """添加到热点列表"""
        if not self.redis_client:
            return False

        try:
            key = self._generate_key('market', f"hot:{list_name}")

            # 使用有序集合存储
            pipeline = self.redis_client.pipeline()

            for item in items:
                # 使用时间戳作为分数
                score = datetime.now().timestamp()
                member = json.dumps(item, default=str)
                pipeline.zadd(key, {member: score})

            # 保留最新的max_size个
            pipeline.zremrangebyrank(key, 0, -(max_size + 1))

            # 设置过期时间
            pipeline.expire(key, self.cache_ttl['hot'])

            await pipeline.execute()
            return True

        except Exception as e:
            logger.debug(f"添加热点数据失败: {e}")
            return False

    async def get_hot_list(
        self,
        list_name: str,
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """获取热点列表"""
        if not self.redis_client:
            return []

        try:
            key = self._generate_key('market', f"hot:{list_name}")

            # 获取最新的count个
            members = await self.redis_client.zrevrange(key, 0, count - 1)

            result = []
            for member in members:
                try:
                    item = json.loads(member.decode('utf-8'))
                    result.append(item)
                except:
                    pass

            return result

        except Exception as e:
            logger.debug(f"获取热点数据失败: {e}")
            return []

    # 分布式锁

    async def acquire_lock(
        self,
        lock_name: str,
        timeout: int = 10,
        blocking: bool = True,
        blocking_timeout: int = 5
    ) -> bool:
        """获取分布式锁"""
        if not self.redis_client:
            return True  # 无Redis时不使用锁

        try:
            key = self._generate_key('system', f"lock:{lock_name}")
            identifier = str(datetime.now().timestamp())

            if blocking:
                # 阻塞等待锁
                end_time = datetime.now() + timedelta(seconds=blocking_timeout)
                while datetime.now() < end_time:
                    if await self.redis_client.set(
                        key, identifier, nx=True, ex=timeout
                    ):
                        return True
                    await asyncio.sleep(0.1)
                return False
            else:
                # 非阻塞
                return await self.redis_client.set(
                    key, identifier, nx=True, ex=timeout
                )

        except Exception as e:
            logger.debug(f"获取锁失败: {e}")
            return False

    async def release_lock(self, lock_name: str) -> bool:
        """释放分布式锁"""
        if not self.redis_client:
            return True

        try:
            key = self._generate_key('system', f"lock:{lock_name}")
            return await self.delete(key)
        except:
            return False

    # 缓存装饰器

    def cache_result(
        self,
        cache_type: str = 'daily',
        ttl: Optional[int] = None,
        key_prefix: Optional[str] = None
    ):
        """
        缓存装饰器

        Args:
            cache_type: 缓存类型
            ttl: 过期时间
            key_prefix: 键前缀
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 生成缓存键
                func_name = func.__name__
                params = {'args': args, 'kwargs': kwargs}
                params_hash = self._hash_params(params)

                if key_prefix:
                    cache_key = f"{key_prefix}:{func_name}:{params_hash}"
                else:
                    cache_key = f"func:{func_name}:{params_hash}"

                # 尝试从缓存获取
                cached = await self.get(cache_key)
                if cached is not None:
                    logger.debug(f"命中缓存: {func_name}")
                    return cached

                # 执行函数
                result = await func(*args, **kwargs)

                # 保存到缓存
                await self.set(cache_key, result, ttl=ttl, cache_type=cache_type)

                return result

            return wrapper
        return decorator

    # 缓存预热

    async def warmup_cache(self, warmup_tasks: List[Dict[str, Any]]):
        """
        缓存预热

        Args:
            warmup_tasks: 预热任务列表
                [
                    {
                        'type': 'stock_data',
                        'params': {'ts_code': '000001.SZ', 'data_type': 'daily'}
                    }
                ]
        """
        logger.info(f"开始缓存预热，任务数: {len(warmup_tasks)}")

        for task in warmup_tasks:
            try:
                task_type = task.get('type')
                params = task.get('params', {})

                if task_type == 'stock_data':
                    # 预热股票数据
                    ts_code = params.get('ts_code')
                    data_type = params.get('data_type')
                    # 这里应该调用实际的数据获取函数
                    # data = await get_stock_data_from_db(ts_code, data_type)
                    # await self.cache_stock_data(ts_code, data_type, data)

                await asyncio.sleep(0.01)  # 避免过载

            except Exception as e:
                logger.debug(f"预热任务失败: {e}")

        logger.info("缓存预热完成")

    # 缓存统计

    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        if not self.redis_client:
            return {'status': 'disabled'}

        try:
            info = await self.redis_client.info('stats')
            memory = await self.redis_client.info('memory')

            return {
                'status': 'active',
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': memory.get('used_memory_human', 'N/A'),
                'used_memory_peak': memory.get('used_memory_peak_human', 'N/A'),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            }
        except Exception as e:
            logger.debug(f"获取缓存统计失败: {e}")
            return {'status': 'error', 'message': str(e)}

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """计算缓存命中率"""
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100

    async def clear_all_cache(self) -> bool:
        """清空所有缓存（谨慎使用）"""
        if not self.redis_client:
            return False

        try:
            await self.redis_client.flushdb()
            logger.warning("已清空所有缓存")
            return True
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False


# 单例模式
_cache_service = None


def get_cache_service() -> CacheService:
    """获取缓存服务实例"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service