"""
股票日线数据服务

职责:
- 日线数据查询
- 批量同步日线数据
- 数据统计分析
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from app.repositories.stock_data_repository import StockDataRepository
from app.services.data_provider_service import DataProviderService
from app.services.stock_quote_cache import stock_quote_cache
from src.database.db_manager import DatabaseManager


class StockDailyService:
    """
    股票日线数据服务

    使用 Tushare Provider 获取日线数据
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化服务

        Args:
            db: DatabaseManager 实例（可选）
        """
        self.db = db or DatabaseManager()
        self.stock_repo = StockDataRepository(db=self.db)
        self.provider_service = DataProviderService(db=self.db)
        logger.info("✓ StockDailyService initialized")

    async def get_daily_data(
        self,
        code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        page: int = 1
    ) -> Dict:
        """
        查询日线数据（支持分页）

        Args:
            code: 股票代码（可选）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            limit: 每页数量
            page: 页码

        Returns:
            {items: List[Dict], total: int, page: int, page_size: int}
        """
        try:
            if code:
                # 查询单只股票
                df = await asyncio.to_thread(
                    self.stock_repo.get_daily_data,
                    code=code,
                    start_date=start_date,
                    end_date=end_date
                )

                # 转换为列表
                if not df.empty:
                    df = df.reset_index()
                    df['code'] = code
                    # 从行情缓存获取股票名称
                    quotes = await stock_quote_cache.get_quotes_batch([code])
                    df['name'] = quotes.get(code, {}).get('name', '')

                items = df.to_dict('records') if not df.empty else []
                total = len(items)

                # 客户端分页
                start_idx = (page - 1) * limit
                end_idx = start_idx + limit
                items = items[start_idx:end_idx]

            else:
                # 查询所有股票的最新数据（分页）
                offset = (page - 1) * limit
                items, total = await self._get_latest_daily_data(
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    offset=offset
                )

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": limit,
                "total_pages": (total + limit - 1) // limit
            }

        except Exception as e:
            logger.error(f"查询日线数据失败: {e}")
            raise

    async def _get_latest_daily_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Dict], int]:
        """
        获取最新的日线数据（多只股票）

        Returns:
            (items, total)
        """
        try:
            # 构建查询（不做 LEFT JOIN，名称通过行情缓存注入）
            conn = self.db.pool_manager.get_connection()
            cursor = conn.cursor()

            # 构建 WHERE 条件
            where_conditions = ["sd.code LIKE '%%.%%'"]  # 只查完整 ts_code 格式（如 000001.SZ），%% 为 psycopg2 转义
            params = []

            if start_date:
                where_conditions.append("sd.date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("sd.date <= %s")
                params.append(end_date)

            where_clause = " AND ".join(where_conditions)

            # 查询总数
            count_query = f"""
                SELECT COUNT(DISTINCT sd.code)
                FROM stock_daily sd
                WHERE {where_clause}
            """
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # 查询数据（每只股票取最新一条）
            query = f"""
                SELECT DISTINCT ON (sd.code)
                    sd.code,
                    sd.date,
                    sd.open,
                    sd.high,
                    sd.low,
                    sd.close,
                    sd.volume,
                    sd.amount,
                    sd.amplitude,
                    sd.pct_change,
                    sd.change,
                    sd.turnover
                FROM stock_daily sd
                WHERE {where_clause}
                ORDER BY sd.code, sd.date DESC
                LIMIT %s OFFSET %s
            """
            params_with_limit = params + [limit, offset]
            cursor.execute(query, params_with_limit)

            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            items = []
            ts_codes = []
            for row in rows:
                ts_codes.append(row[0])
                items.append({
                    'code': row[0],
                    'name': '',
                    'date': row[1].strftime('%Y-%m-%d') if row[1] else None,
                    'open': float(row[2]) if row[2] else None,
                    'high': float(row[3]) if row[3] else None,
                    'low': float(row[4]) if row[4] else None,
                    'close': float(row[5]) if row[5] else None,
                    'volume': int(row[6]) if row[6] else None,
                    'amount': float(row[7]) if row[7] else None,
                    'amplitude': float(row[8]) if row[8] else None,
                    'pct_change': float(row[9]) if row[9] else None,
                    'change': float(row[10]) if row[10] else None,
                    'turnover': float(row[11]) if row[11] else None,
                })

            # 从行情缓存批量注入股票名称
            if ts_codes:
                quotes = await stock_quote_cache.get_quotes_batch(ts_codes)
                for item in items:
                    item['name'] = quotes.get(item['code'], {}).get('name', '')

            return items, total

        except Exception as e:
            logger.error(f"查询最新日线数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取日线数据统计

        Returns:
            统计信息字典
        """
        try:
            conn = self.db.pool_manager.get_connection()
            cursor = conn.cursor()

            # 构建 WHERE 条件
            where_conditions = []
            params = []

            if start_date:
                where_conditions.append("date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("date <= %s")
                params.append(end_date)

            where_clause = " AND " + " AND ".join(where_conditions) if where_conditions else ""

            query = f"""
                SELECT
                    COUNT(DISTINCT code) as stock_count,
                    COUNT(*) as record_count,
                    AVG(pct_change) as avg_pct_change,
                    MAX(date) as latest_date,
                    MIN(date) as earliest_date
                FROM stock_daily
                WHERE 1=1 {where_clause}
            """

            cursor.execute(query, params)
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            return {
                'stock_count': row[0] or 0,
                'record_count': row[1] or 0,
                'avg_pct_change': round(float(row[2]), 2) if row[2] else 0.0,
                'latest_date': row[3].strftime('%Y-%m-%d') if row[3] else None,
                'earliest_date': row[4].strftime('%Y-%m-%d') if row[4] else None,
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                'stock_count': 0,
                'record_count': 0,
                'avg_pct_change': 0.0,
                'latest_date': None,
                'earliest_date': None,
            }

    async def sync_single_stock(
        self,
        code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        years: int = 5
    ) -> Dict:
        """
        同步日线数据

        Args:
            code: 股票代码（可选，留空则同步全市场最近交易日数据）
            start_date: 开始日期 (YYYY-MM-DD 或 YYYYMMDD)
            end_date: 结束日期
            years: 年数（当未指定日期时使用）

        Returns:
            同步结果
        """
        try:
            # 如果未指定 code，则同步全市场最近交易日数据
            if not code:
                # 获取最近交易日
                from app.repositories import TradingCalendarRepository
                calendar_repo = TradingCalendarRepository()
                latest_trade_date = await asyncio.to_thread(
                    calendar_repo.get_latest_trading_day
                )

                if not latest_trade_date:
                    # 如果交易日历表为空，使用今天
                    latest_trade_date = datetime.now().strftime("%Y%m%d")

                logger.info(f"同步全市场日线数据，交易日期: {latest_trade_date}")

                # 使用 trade_date 参数而不是 start_date/end_date
                start_date = None
                end_date = None
                trade_date = latest_trade_date
            else:
                # 单只股票同步：计算日期范围
                trade_date = None
                if not end_date:
                    end_date = datetime.now().strftime("%Y%m%d")
                else:
                    # 转换为 YYYYMMDD 格式
                    end_date = end_date.replace('-', '')

                if not start_date:
                    start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y%m%d")
                else:
                    start_date = start_date.replace('-', '')

                logger.info(f"同步 {code} 日线数据: {start_date} - {end_date}")

            # 使用 Tushare Provider
            provider = await self.provider_service.get_provider("main")

            # 构建参数
            params = {'adjust': 'qfq'}  # 前复权
            if code:
                params['code'] = code
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            response = await asyncio.to_thread(
                provider.get_daily_data,
                **params
            )

            if not response.is_success():
                raise ValueError(response.error_message or "获取日线数据失败")

            df = response.data

            task_desc = code if code else f"全市场({trade_date})"

            if df is None or df.empty:
                logger.warning(f"{task_desc}: 无数据")
                return {
                    "status": "success",
                    "code": task_desc,
                    "count": 0,
                    "message": "无数据"
                }

            # 全市场同步时，需要逐只股票保存
            if not code:
                # df 中的 ts_code 列包含多只股票
                total_count = 0
                stock_codes = df['ts_code'].unique() if 'ts_code' in df.columns else []

                for stock_code in stock_codes:
                    stock_df = df[df['ts_code'] == stock_code].copy()

                    # trade_date 列转为 date 索引
                    if 'trade_date' in stock_df.columns:
                        stock_df['trade_date'] = pd.to_datetime(stock_df['trade_date'])
                        stock_df = stock_df.set_index('trade_date')

                    # 保存到数据库
                    count = await asyncio.to_thread(
                        self.stock_repo.save_daily_data,
                        stock_df,
                        stock_code
                    )
                    total_count += count

                logger.info(f"✓ {task_desc}: 同步完成 {total_count} 条记录（{len(stock_codes)}只股票）")

                return {
                    "status": "success",
                    "code": task_desc,
                    "count": total_count,
                    "date_range": trade_date,
                    "message": f"成功同步 {len(stock_codes)} 只股票，{total_count} 条记录"
                }
            else:
                # 单只股票同步
                # trade_date 列转为 date 索引
                if 'trade_date' in df.columns:
                    df['trade_date'] = pd.to_datetime(df['trade_date'])
                    df = df.set_index('trade_date')

                # 保存到数据库
                count = await asyncio.to_thread(
                    self.stock_repo.save_daily_data,
                    df,
                    code
                )

                logger.info(f"✓ {code}: 同步完成 {count} 条记录")

                return {
                    "status": "success",
                    "code": code,
                    "count": count,
                    "date_range": f"{start_date} ~ {end_date}",
                    "message": f"成功同步 {count} 条记录"
                }

        except Exception as e:
            task_desc = code if code else "全市场"
            logger.error(f"同步 {task_desc} 失败: {e}")
            return {
                "status": "failed",
                "code": task_desc,
                "count": 0,
                "error": str(e)
            }
