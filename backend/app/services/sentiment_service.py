"""
市场情绪数据同步服务

负责市场情绪数据的采集、同步和查询。
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
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

    async def get_sentiment_report(self, date: str) -> Dict:
        """
        获取指定日期的完整情绪报告

        Args:
            date: 日期字符串 (YYYY-MM-DD)

        Returns:
            情绪报告数据
        """
        try:
            # 确保连接池已初始化
            self._get_fetcher()

            conn = self._pool_manager.get_connection()
            cursor = conn.cursor()

            # 查询大盘数据
            cursor.execute("""
                SELECT * FROM market_sentiment_daily WHERE trade_date = %s
            """, (date,))
            market_data = cursor.fetchone()

            # 查询涨停板池
            cursor.execute("""
                SELECT * FROM limit_up_pool WHERE trade_date = %s
            """, (date,))
            limit_up_data = cursor.fetchone()

            # 查询龙虎榜统计
            cursor.execute("""
                SELECT COUNT(*) as count,
                       SUM(CASE WHEN has_institution THEN 1 ELSE 0 END) as institution_count
                FROM dragon_tiger_list WHERE trade_date = %s
            """, (date,))
            dragon_tiger_stats = cursor.fetchone()

            cursor.close()
            self._pool_manager.release_connection(conn)

            return {
                "date": date,
                "market_data": self._row_to_dict(market_data, cursor.description) if market_data else None,
                "limit_up_data": self._row_to_dict(limit_up_data, cursor.description) if limit_up_data else None,
                "dragon_tiger_stats": {
                    "total_count": dragon_tiger_stats[0] if dragon_tiger_stats else 0,
                    "institution_count": dragon_tiger_stats[1] if dragon_tiger_stats else 0
                }
            }

        except Exception as e:
            logger.error(f"查询情绪报告失败: {e}")
            raise DatabaseError(f"查询失败: {str(e)}")

    async def get_sentiment_list(
        self,
        page: int = 1,
        limit: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        分页查询情绪数据列表（Admin用）

        Args:
            page: 页码
            limit: 每页数量
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            分页数据
        """
        try:
            # 确保连接池已初始化
            self._get_fetcher()

            conn = self._pool_manager.get_connection()
            cursor = conn.cursor()

            # 构建查询条件
            where_clauses = []
            params = []

            if start_date:
                where_clauses.append("trade_date >= %s")
                params.append(start_date)

            if end_date:
                where_clauses.append("trade_date <= %s")
                params.append(end_date)

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            # 查询总数
            cursor.execute(f"""
                SELECT COUNT(*) FROM market_sentiment_daily {where_sql}
            """, params)
            total = cursor.fetchone()[0]

            # 查询数据
            offset = (page - 1) * limit
            params.extend([limit, offset])

            cursor.execute(f"""
                SELECT m.*, l.limit_up_count, l.limit_down_count, l.blast_rate, l.max_continuous_days
                FROM market_sentiment_daily m
                LEFT JOIN limit_up_pool l ON m.trade_date = l.trade_date
                {where_sql}
                ORDER BY m.trade_date DESC
                LIMIT %s OFFSET %s
            """, params)

            rows = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]

            items = []
            for row in rows:
                item = dict(zip(col_names, row))
                # 处理日期格式
                if 'trade_date' in item and item['trade_date']:
                    item['trade_date'] = item['trade_date'].strftime('%Y-%m-%d')
                items.append(item)

            cursor.close()
            self._pool_manager.release_connection(conn)

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": limit,
                "total_pages": (total + limit - 1) // limit
            }

        except Exception as e:
            logger.error(f"查询情绪列表失败: {e}")
            raise DatabaseError(f"查询失败: {str(e)}")

    async def get_limit_up_detail(self, date: str) -> Dict:
        """
        获取涨停板详细数据

        Args:
            date: 日期字符串

        Returns:
            涨停板详细数据
        """
        try:
            # 确保连接池已初始化
            self._get_fetcher()

            conn = self._pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM limit_up_pool WHERE trade_date = %s
            """, (date,))

            row = cursor.fetchone()
            cursor.close()
            self._pool_manager.release_connection(conn)

            if not row:
                return None

            data = self._row_to_dict(row, cursor.description)

            # 解析JSONB字段
            if 'continuous_ladder' in data and isinstance(data['continuous_ladder'], str):
                data['continuous_ladder'] = json.loads(data['continuous_ladder'])
            if 'limit_up_stocks' in data and isinstance(data['limit_up_stocks'], str):
                data['limit_up_stocks'] = json.loads(data['limit_up_stocks'])
            if 'blast_stocks' in data and isinstance(data['blast_stocks'], str):
                data['blast_stocks'] = json.loads(data['blast_stocks'])

            return data

        except Exception as e:
            logger.error(f"查询涨停板详情失败: {e}")
            raise DatabaseError(f"查询失败: {str(e)}")

    async def get_dragon_tiger_list(
        self,
        date: Optional[str] = None,
        stock_code: Optional[str] = None,
        has_institution: Optional[bool] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict:
        """
        查询龙虎榜数据（支持多条件筛选）

        Args:
            date: 日期
            stock_code: 股票代码
            has_institution: 是否有机构
            page: 页码
            limit: 每页数量

        Returns:
            分页数据
        """
        try:
            # 确保连接池已初始化
            self._get_fetcher()

            conn = self._pool_manager.get_connection()
            cursor = conn.cursor()

            # 构建查询条件
            where_clauses = []
            params = []

            if date:
                where_clauses.append("trade_date = %s")
                params.append(date)

            if stock_code:
                where_clauses.append("stock_code = %s")
                params.append(stock_code)

            if has_institution is not None:
                where_clauses.append("has_institution = %s")
                params.append(has_institution)

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            # 查询总数
            cursor.execute(f"""
                SELECT COUNT(*) FROM dragon_tiger_list {where_sql}
            """, params)
            total = cursor.fetchone()[0]

            # 查询数据
            offset = (page - 1) * limit
            params.extend([limit, offset])

            cursor.execute(f"""
                SELECT * FROM dragon_tiger_list
                {where_sql}
                ORDER BY trade_date DESC, net_amount DESC
                LIMIT %s OFFSET %s
            """, params)

            rows = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]

            items = []
            for row in rows:
                item = dict(zip(col_names, row))
                # 处理日期格式
                if 'trade_date' in item and item['trade_date']:
                    item['trade_date'] = item['trade_date'].strftime('%Y-%m-%d')
                # 解析JSONB
                if 'top_buyers' in item and isinstance(item['top_buyers'], str):
                    item['top_buyers'] = json.loads(item['top_buyers'])
                if 'top_sellers' in item and isinstance(item['top_sellers'], str):
                    item['top_sellers'] = json.loads(item['top_sellers'])
                items.append(item)

            cursor.close()
            self._pool_manager.release_connection(conn)

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": limit,
                "total_pages": (total + limit - 1) // limit
            }

        except Exception as e:
            logger.error(f"查询龙虎榜失败: {e}")
            raise DatabaseError(f"查询失败: {str(e)}")

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

    async def get_sentiment_statistics(
        self,
        start_date: str,
        end_date: str
    ) -> Dict:
        """
        统计分析（Admin看板用）

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            统计数据
        """
        try:
            # 确保连接池已初始化
            self._get_fetcher()

            conn = self._pool_manager.get_connection()
            cursor = conn.cursor()

            # 统计涨停板数据
            cursor.execute("""
                SELECT
                    AVG(blast_rate) as avg_blast_rate,
                    AVG(limit_up_count) as avg_limit_up,
                    MAX(max_continuous_days) as max_continuous
                FROM limit_up_pool
                WHERE trade_date BETWEEN %s AND %s
            """, (start_date, end_date))

            stats_row = cursor.fetchone()

            # 统计龙虎榜活跃度
            cursor.execute("""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT stock_code) as unique_stocks,
                    SUM(CASE WHEN has_institution THEN 1 ELSE 0 END) as institution_records
                FROM dragon_tiger_list
                WHERE trade_date BETWEEN %s AND %s
            """, (start_date, end_date))

            lhb_row = cursor.fetchone()

            # 涨跌趋势
            cursor.execute("""
                SELECT trade_date, limit_up_count, limit_down_count, blast_rate
                FROM limit_up_pool
                WHERE trade_date BETWEEN %s AND %s
                ORDER BY trade_date
            """, (start_date, end_date))

            trend_rows = cursor.fetchall()

            cursor.close()
            self._pool_manager.release_connection(conn)

            return {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "limit_up_stats": {
                    "avg_blast_rate": float(stats_row[0]) if stats_row[0] else 0,
                    "avg_limit_up": float(stats_row[1]) if stats_row[1] else 0,
                    "max_continuous": int(stats_row[2]) if stats_row[2] else 0
                },
                "dragon_tiger_stats": {
                    "total_records": int(lhb_row[0]) if lhb_row else 0,
                    "unique_stocks": int(lhb_row[1]) if lhb_row else 0,
                    "institution_records": int(lhb_row[2]) if lhb_row else 0
                },
                "trend": [
                    {
                        "date": row[0].strftime('%Y-%m-%d'),
                        "limit_up": int(row[1]),
                        "limit_down": int(row[2]),
                        "blast_rate": float(row[3]) if row[3] else 0
                    }
                    for row in trend_rows
                ]
            }

        except Exception as e:
            logger.error(f"统计分析失败: {e}")
            raise DatabaseError(f"统计失败: {str(e)}")

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
