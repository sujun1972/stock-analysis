"""
性能优化服务
提供批量插入、查询优化、缓存管理等性能优化功能
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from io import StringIO
import redis
import json
import hashlib
from contextlib import asynccontextmanager

from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine
from sqlalchemy.dialects.postgresql import insert

from app.core.config import get_settings
# from app.core.database import get_db  # Not needed for mock service

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """性能优化器"""

    def __init__(self):
        self.settings = get_settings()
        self.batch_size = 5000  # 批量插入大小
        self.cache_ttl = 300  # 缓存过期时间（秒）
        self._init_redis()
        self._init_db_pool()

    def _init_redis(self):
        """初始化Redis连接"""
        try:
            self.redis_client = redis.Redis(
                host=self.settings.REDIS_HOST,
                port=self.settings.REDIS_PORT,
                db=0,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.warning(f"Redis连接失败: {e}，将不使用缓存")
            self.redis_client = None

    def _init_db_pool(self):
        """初始化数据库连接池"""
        # 创建专门用于批量操作的连接池
        self.engine = create_async_engine(
            self.settings.DATABASE_URL,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600
        )

    async def batch_insert_with_copy(
        self,
        table_name: str,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None
    ) -> int:
        """
        使用COPY协议批量插入数据（最高性能）

        Args:
            table_name: 表名
            df: 数据DataFrame
            columns: 列名列表，如果为None则使用df的列

        Returns:
            插入的记录数
        """
        if df is None or df.empty:
            return 0

        if columns is None:
            columns = df.columns.tolist()

        try:
            # 准备CSV数据
            csv_buffer = StringIO()
            df[columns].to_csv(csv_buffer, index=False, header=False)
            csv_buffer.seek(0)

            async with self.engine.begin() as conn:
                # 使用COPY FROM进行批量插入
                copy_sql = f"""
                    COPY {table_name} ({','.join(columns)})
                    FROM STDIN WITH CSV
                """

                # PostgreSQL的异步COPY支持
                raw_conn = await conn.get_raw_connection()
                await raw_conn._connection.copy_expert(
                    copy_sql,
                    csv_buffer
                )

            logger.info(f"批量插入 {len(df)} 条记录到 {table_name}")
            return len(df)

        except Exception as e:
            logger.error(f"批量插入失败: {e}")
            # 降级到普通批量插入
            return await self.batch_insert_fallback(table_name, df, columns)

    async def batch_insert_fallback(
        self,
        table_name: str,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None
    ) -> int:
        """
        批量插入的降级方案（使用INSERT VALUES）

        Args:
            table_name: 表名
            df: 数据DataFrame
            columns: 列名列表

        Returns:
            插入的记录数
        """
        if df is None or df.empty:
            return 0

        if columns is None:
            columns = df.columns.tolist()

        total_inserted = 0

        try:
            async with self.engine.begin() as conn:
                # 分批插入
                for i in range(0, len(df), self.batch_size):
                    batch_df = df.iloc[i:i + self.batch_size]

                    # 构建INSERT语句
                    values_list = []
                    for _, row in batch_df.iterrows():
                        values = [self._format_value(row[col]) for col in columns]
                        values_str = f"({','.join(values)})"
                        values_list.append(values_str)

                    insert_sql = f"""
                        INSERT INTO {table_name} ({','.join(columns)})
                        VALUES {','.join(values_list)}
                        ON CONFLICT DO NOTHING
                    """

                    await conn.execute(text(insert_sql))
                    total_inserted += len(batch_df)

                    logger.debug(f"插入批次 {i // self.batch_size + 1}, 记录数: {len(batch_df)}")

            return total_inserted

        except Exception as e:
            logger.error(f"批量插入降级方案失败: {e}")
            raise

    def _format_value(self, value) -> str:
        """格式化SQL值"""
        if pd.isna(value):
            return 'NULL'
        elif isinstance(value, str):
            # 转义单引号
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, datetime):
            return f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'"
        else:
            return f"'{str(value)}'"

    async def batch_upsert(
        self,
        table_name: str,
        df: pd.DataFrame,
        conflict_columns: List[str],
        update_columns: Optional[List[str]] = None
    ) -> int:
        """
        批量更新插入（UPSERT）

        Args:
            table_name: 表名
            df: 数据DataFrame
            conflict_columns: 冲突检测列
            update_columns: 更新的列，如果为None则更新所有列

        Returns:
            影响的记录数
        """
        if df is None or df.empty:
            return 0

        columns = df.columns.tolist()
        if update_columns is None:
            update_columns = [col for col in columns if col not in conflict_columns]

        total_affected = 0

        try:
            async with self.engine.begin() as conn:
                for i in range(0, len(df), self.batch_size):
                    batch_df = df.iloc[i:i + self.batch_size]

                    # 构建UPSERT语句
                    values_list = []
                    for _, row in batch_df.iterrows():
                        values = [self._format_value(row[col]) for col in columns]
                        values_str = f"({','.join(values)})"
                        values_list.append(values_str)

                    update_set = ','.join([f"{col}=EXCLUDED.{col}" for col in update_columns])

                    upsert_sql = f"""
                        INSERT INTO {table_name} ({','.join(columns)})
                        VALUES {','.join(values_list)}
                        ON CONFLICT ({','.join(conflict_columns)})
                        DO UPDATE SET {update_set}
                    """

                    result = await conn.execute(text(upsert_sql))
                    total_affected += result.rowcount

            logger.info(f"批量UPSERT {total_affected} 条记录到 {table_name}")
            return total_affected

        except Exception as e:
            logger.error(f"批量UPSERT失败: {e}")
            raise

    # Redis缓存相关方法

    def _get_cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """生成缓存键"""
        # 将参数转换为稳定的字符串
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        return f"{prefix}:{params_hash}"

    async def get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.redis_client:
            return None

        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.debug(f"缓存读取失败: {e}")
            return None

    async def set_cache(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存"""
        if not self.redis_client:
            return

        try:
            if ttl is None:
                ttl = self.cache_ttl

            self.redis_client.setex(
                key,
                ttl,
                json.dumps(value, default=str)
            )
        except Exception as e:
            logger.debug(f"缓存设置失败: {e}")

    async def delete_cache_pattern(self, pattern: str):
        """删除匹配模式的缓存"""
        if not self.redis_client:
            return

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"删除了 {len(keys)} 个缓存键")
        except Exception as e:
            logger.debug(f"缓存删除失败: {e}")

    # 查询优化相关方法

    async def optimize_query_with_cache(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        cache_key: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> pd.DataFrame:
        """
        带缓存的查询优化

        Args:
            query: SQL查询
            params: 查询参数
            cache_key: 缓存键，如果为None则自动生成
            ttl: 缓存过期时间

        Returns:
            查询结果DataFrame
        """
        # 生成缓存键
        if cache_key is None:
            cache_key = self._get_cache_key("query", {"sql": query, "params": params})

        # 尝试从缓存获取
        cached_data = await self.get_from_cache(cache_key)
        if cached_data:
            logger.debug(f"从缓存获取数据: {cache_key}")
            return pd.DataFrame(cached_data)

        # 执行查询
        async with self.engine.begin() as conn:
            if params:
                result = await conn.execute(text(query), params)
            else:
                result = await conn.execute(text(query))

            rows = result.fetchall()
            columns = result.keys()

            df = pd.DataFrame(rows, columns=columns)

        # 保存到缓存
        await self.set_cache(cache_key, df.to_dict('records'), ttl)

        return df

    async def parallel_query_execution(
        self,
        queries: List[Tuple[str, Optional[Dict[str, Any]]]]
    ) -> List[pd.DataFrame]:
        """
        并行执行多个查询

        Args:
            queries: [(query, params), ...] 查询列表

        Returns:
            查询结果列表
        """
        tasks = []
        for query, params in queries:
            task = self.optimize_query_with_cache(query, params)
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return results

    # 索引管理

    async def create_indexes(self, index_definitions: List[Dict[str, Any]]):
        """
        创建索引

        Args:
            index_definitions: 索引定义列表
                [
                    {
                        "table": "daily_basic",
                        "columns": ["ts_code", "trade_date"],
                        "unique": False,
                        "name": "idx_daily_basic_code_date"
                    }
                ]
        """
        async with self.engine.begin() as conn:
            for index_def in index_definitions:
                table = index_def["table"]
                columns = index_def["columns"]
                unique = index_def.get("unique", False)
                name = index_def.get("name", f"idx_{table}_{'_'.join(columns)}")

                unique_str = "UNIQUE" if unique else ""
                columns_str = ",".join(columns)

                create_sql = f"""
                    CREATE {unique_str} INDEX IF NOT EXISTS {name}
                    ON {table} ({columns_str})
                """

                try:
                    await conn.execute(text(create_sql))
                    logger.info(f"创建索引: {name}")
                except Exception as e:
                    logger.warning(f"创建索引失败 {name}: {e}")

    async def analyze_tables(self, tables: List[str]):
        """
        分析表以更新统计信息

        Args:
            tables: 表名列表
        """
        async with self.engine.begin() as conn:
            for table in tables:
                try:
                    await conn.execute(text(f"ANALYZE {table}"))
                    logger.info(f"分析表: {table}")
                except Exception as e:
                    logger.warning(f"分析表失败 {table}: {e}")

    async def vacuum_tables(self, tables: List[str]):
        """
        清理表以回收空间

        Args:
            tables: 表名列表
        """
        # VACUUM需要在自动提交模式下运行
        for table in tables:
            try:
                async with self.engine.connect() as conn:
                    await conn.execute(text("COMMIT"))  # 确保没有活跃事务
                    await conn.execute(text(f"VACUUM ANALYZE {table}"))
                    logger.info(f"清理表: {table}")
            except Exception as e:
                logger.warning(f"清理表失败 {table}: {e}")

    @asynccontextmanager
    async def bulk_operation_context(self):
        """批量操作上下文管理器"""
        # 暂时调整数据库参数以优化批量操作
        async with self.engine.begin() as conn:
            try:
                # 提高工作内存
                await conn.execute(text("SET work_mem = '256MB'"))
                # 关闭同步提交（提高性能但降低安全性）
                await conn.execute(text("SET synchronous_commit = OFF"))

                yield conn

            finally:
                # 恢复默认设置
                await conn.execute(text("RESET work_mem"))
                await conn.execute(text("RESET synchronous_commit"))


# 单例模式
_performance_optimizer = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """获取性能优化器实例"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer