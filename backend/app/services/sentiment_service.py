"""
市场情绪数据同步服务

负责市场情绪数据的采集、同步和查询。
"""

import asyncio
import json
import math
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from loguru import logger
from src.sentiment.fetcher import SentimentDataFetcher
from src.database.connection_pool_manager import ConnectionPoolManager

from app.core.exceptions import DatabaseError, ExternalAPIError
from app.services.config_service import ConfigService


class MarketSentimentService:
    """
    市场情绪数据服务

    职责:
    - 每日情绪数据同步（17:30定时任务）
    - 交易日历管理
    - 情绪数据查询
    - 统计分析
    """

    def __init__(self):
        """初始化市场情绪服务"""
        self.config_service = ConfigService()
        self._fetcher = None
        self._pool_manager = None

    def _get_fetcher(self) -> SentimentDataFetcher:
        """获取数据抓取器实例（懒加载）"""
        if self._fetcher is None:
            # 获取数据库配置
            db_config = {
                'host': os.getenv('DATABASE_HOST', 'timescaledb'),
                'port': int(os.getenv('DATABASE_PORT', '5432')),
                'database': os.getenv('DATABASE_NAME', 'stock_analysis'),
                'user': os.getenv('DATABASE_USER', 'stock_user'),
                'password': os.getenv('DATABASE_PASSWORD', 'stock_password_123')
            }
            self._pool_manager = ConnectionPoolManager(db_config)
            self._fetcher = SentimentDataFetcher(self._pool_manager)
        return self._fetcher

    @staticmethod
    def _sanitize_float_value(value):
        """
        清理特殊浮点数值，使其符合 JSON 标准

        PostgreSQL 的 numeric 类型支持存储 NaN 和 Infinity，
        但这些值不符合 JSON 标准，会导致序列化失败。
        此方法将特殊浮点数转换为 None (JSON 中的 null)。

        Args:
            value: 任意值

        Returns:
            清理后的值（NaN/Infinity -> None）
        """
        # 处理 Decimal 类型（PostgreSQL numeric 类型）
        if isinstance(value, Decimal):
            # 检查 Decimal 是否为 NaN 或 Infinity
            if value.is_nan() or value.is_infinite():
                return None
            # 正常的 Decimal 保持不变，让 FastAPI 处理
            return value

        # 处理 float 类型
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None

        return value

    @staticmethod
    def _sanitize_dict(data: Dict) -> Dict:
        """
        递归清理字典中的特殊浮点数值

        Args:
            data: 字典数据

        Returns:
            清理后的字典
        """
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            if isinstance(value, dict):
                sanitized[key] = MarketSentimentService._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    MarketSentimentService._sanitize_dict(item) if isinstance(item, dict)
                    else MarketSentimentService._sanitize_float_value(item)
                    for item in value
                ]
            else:
                sanitized[key] = MarketSentimentService._sanitize_float_value(value)
        return sanitized

    # ========== 1. 数据同步相关 ==========

    async def sync_daily_sentiment(self, date: Optional[str] = None) -> Dict:
        """
        同步每日情绪数据（17:30定时任务调用）

        Args:
            date: 日期字符串 (YYYY-MM-DD)，None表示今天

        Returns:
            同步结果
        """
        try:
            fetcher = self._get_fetcher()

            # 在线程池中执行同步（避免阻塞异步循环）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                fetcher.sync_daily_sentiment,
                date
            )

            return {
                "success": result.success,
                "is_trading_day": result.is_trading_day,
                "synced_tables": result.synced_tables,
                "error": result.error,
                "details": result.details
            }

        except Exception as e:
            logger.error(f"同步市场情绪数据失败: {e}")
            raise ExternalAPIError(f"数据同步失败: {str(e)}")

    async def sync_trading_calendar_batch(self, years: List[int]) -> int:
        """
        批量同步交易日历

        Args:
            years: 年份列表

        Returns:
            同步的交易日总数
        """
        try:
            fetcher = self._get_fetcher()
            total_count = 0

            loop = asyncio.get_event_loop()
            for year in years:
                count = await loop.run_in_executor(
                    None,
                    fetcher.sync_trading_calendar,
                    year
                )
                total_count += count
                logger.info(f"{year}年交易日历同步完成: {count}条")

            return total_count

        except Exception as e:
            logger.error(f"批量同步交易日历失败: {e}")
            raise ExternalAPIError(f"交易日历同步失败: {str(e)}")

    # ========== 2. 数据查询相关 ==========

    async def get_trading_calendar(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> List[Dict]:
        """
        查询交易日历

        Args:
            year: 年份
            month: 月份

        Returns:
            交易日历列表
        """
        try:
            # 确保连接池已初始化
            self._get_fetcher()

            conn = self._pool_manager.get_connection()
            cursor = conn.cursor()

            where_clauses = []
            params = []

            if year:
                where_clauses.append("EXTRACT(YEAR FROM trade_date) = %s")
                params.append(year)

            if month:
                where_clauses.append("EXTRACT(MONTH FROM trade_date) = %s")
                params.append(month)

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            cursor.execute(f"""
                SELECT * FROM trading_calendar
                {where_sql}
                ORDER BY trade_date
            """, params)

            rows = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]

            items = []
            for row in rows:
                item = dict(zip(col_names, row))
                if 'trade_date' in item and item['trade_date']:
                    item['trade_date'] = item['trade_date'].strftime('%Y-%m-%d')
                items.append(item)

            cursor.close()
            self._pool_manager.release_connection(conn)

            return items

        except Exception as e:
            logger.error(f"查询交易日历失败: {e}")
            raise DatabaseError(f"查询失败: {str(e)}")

    # ========== 辅助方法 ==========

    def _row_to_dict(self, row: tuple, description: list) -> Dict:
        """将数据库行转换为字典"""
        if not row:
            return None

        col_names = [desc[0] for desc in description]
        result = dict(zip(col_names, row))

        # 处理日期格式
        for key, value in result.items():
            if hasattr(value, 'strftime'):
                result[key] = value.strftime('%Y-%m-%d')

        return result

    def __del__(self):
        """清理资源"""
        if self._pool_manager:
            try:
                self._pool_manager.close_all()
            except:
                pass
