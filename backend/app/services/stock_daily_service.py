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
                    # 将 date 列转为纯日期字符串，避免序列化成 datetime ISO 格式
                    if 'date' in df.columns:
                        df['date'] = df['date'].apply(
                            lambda d: d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)[:10]
                        )
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
        获取最近交易日的日线数据（多只股票，分页）

        性能策略：
        - 用 trading_calendar 定位最近交易日（索引查询，< 1ms）
        - 按精确日期查 stock_daily（date 索引命中，< 5ms）
        - 避免原来的 DISTINCT ON 全表扫描（原耗时 10+ 秒）
        - total 用 stock_basic 上市股票数代替 COUNT(DISTINCT)（快 100 倍）

        Returns:
            (items, total) 其中 total 为上市股票总数（近似分页基准）
        """
        conn = self.db.pool_manager.get_connection()
        cursor = conn.cursor()
        try:
            # 从 trading_calendar 找最近交易日（用户指定 end_date 时取不超过该日期的最近交易日）
            cursor.execute(
                "SELECT MAX(trade_date) FROM trading_calendar"
                " WHERE is_trading_day = true AND trade_date <= %s",
                (end_date or 'CURRENT_DATE',)
            ) if end_date else cursor.execute(
                "SELECT MAX(trade_date) FROM trading_calendar"
                " WHERE is_trading_day = true AND trade_date <= CURRENT_DATE"
            )
            latest_date = (cursor.fetchone() or [None])[0]

            if not latest_date:
                return [], 0

            # start_date 过滤：最近交易日早于查询起始日，视为无数据
            if start_date and str(latest_date) < start_date:
                return [], 0

            # total 用上市股票数（stock_basic 索引，避免 COUNT(DISTINCT) 全表扫描）
            cursor.execute("SELECT COUNT(*) FROM stock_basic WHERE list_status = 'L'")
            total = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT sd.code, sd.date, sd.open, sd.high, sd.low, sd.close,
                       sd.volume, sd.amount, sd.amplitude, sd.pct_change, sd.change, sd.turnover
                FROM stock_daily sd
                WHERE sd.date = %s
                  AND sd.code LIKE '%%.%%'
                ORDER BY sd.code
                LIMIT %s OFFSET %s
                """,
                (latest_date, limit, offset)
            )
            rows = cursor.fetchall()

        except Exception as e:
            logger.error(f"查询最新日线数据失败: {e}")
            raise
        finally:
            cursor.close()
            self.db.pool_manager.release_connection(conn)

        items = []
        ts_codes = []
        for row in rows:
            ts_codes.append(row[0])
            items.append({
                'code': row[0],
                'name': '',
                'date': row[1].strftime('%Y-%m-%d') if row[1] else None,
                'open': float(row[2]) if row[2] is not None else None,
                'high': float(row[3]) if row[3] is not None else None,
                'low': float(row[4]) if row[4] is not None else None,
                'close': float(row[5]) if row[5] is not None else None,
                'volume': int(row[6]) if row[6] is not None else None,
                'amount': float(row[7]) if row[7] is not None else None,
                'amplitude': float(row[8]) if row[8] is not None else None,
                'pct_change': float(row[9]) if row[9] is not None else None,
                'change': float(row[10]) if row[10] is not None else None,
                'turnover': float(row[11]) if row[11] is not None else None,
            })

        if ts_codes:
            quotes = await stock_quote_cache.get_quotes_batch(ts_codes)
            for item in items:
                item['name'] = quotes.get(item['code'], {}).get('name', '')

        return items, total

    async def get_statistics(self) -> Dict:
        """
        获取日线数据全局统计（页面初始化时调用一次）

        全部走索引，避免对 stock_daily 做任何聚合扫描：
        - stock_count  : stock_basic WHERE list_status='L'（索引，< 1ms）
        - record_count : stock_count × 自2021年起交易天数（近似估算）
        - latest_date  : trading_calendar MAX(trade_date)（索引，< 1ms）
        - earliest_date: 固定为同步任务起始日 2021-01-04

        Returns:
            统计信息字典
        """
        conn = self.db.pool_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM stock_basic WHERE list_status = 'L'")
            stock_count = cursor.fetchone()[0] or 0

            # 一次查出交易天数和最新交易日，减少一次 round-trip
            cursor.execute(
                """
                SELECT COUNT(*) FILTER (WHERE trade_date >= '2021-01-01'),
                       MAX(trade_date)
                FROM trading_calendar
                WHERE is_trading_day = true
                  AND trade_date <= CURRENT_DATE
                """
            )
            row = cursor.fetchone()
            trading_days = row[0] or 0
            latest_date = row[1].strftime('%Y-%m-%d') if row[1] else None

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {'stock_count': 0, 'record_count': 0, 'latest_date': None, 'earliest_date': None}
        finally:
            cursor.close()
            self.db.pool_manager.release_connection(conn)

        return {
            'stock_count': stock_count,
            'record_count': stock_count * trading_days,  # 近似值：每支股票每个交易日一条记录
            'latest_date': latest_date,
            'earliest_date': '2021-01-04',  # 全量历史同步任务起始日，固定不变
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
            # 如果未指定 code，则同步全市场下一个待补充的交易日数据
            if not code:
                from app.repositories import TradingCalendarRepository
                calendar_repo = TradingCalendarRepository()

                # 先查本地最新已有交易日，再从 trade_cal 找下一个交易日
                # 这样可以避免重复同步已有数据
                local_latest = await asyncio.to_thread(self._get_local_latest_date)
                if local_latest:
                    next_trade_date = await asyncio.to_thread(
                        calendar_repo.get_next_trading_day, local_latest
                    )
                    # 若已是最新交易日（今天数据还未出来），回退到当前最新交易日
                    trade_date = next_trade_date or await asyncio.to_thread(
                        calendar_repo.get_latest_trading_day
                    )
                else:
                    trade_date = await asyncio.to_thread(
                        calendar_repo.get_latest_trading_day
                    )

                if not trade_date:
                    trade_date = datetime.now().strftime("%Y%m%d")

                logger.info(f"同步全市场日线数据，本地最新: {local_latest or '无'}，目标交易日: {trade_date}")
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

            # 构建参数（全市场模式传 trade_date，单股模式传 code + 日期范围）
            # 注意：Tushare daily 接口返回未复权数据，不支持 adj 参数
            kwargs = {}
            if code:
                kwargs['code'] = code
                if start_date:
                    kwargs['start_date'] = start_date
                if end_date:
                    kwargs['end_date'] = end_date
            else:
                kwargs['trade_date'] = trade_date

            response = await asyncio.to_thread(
                provider.get_daily_data,
                **kwargs
            )

            if not response.is_success() and not response.is_warning():
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

    def _get_local_latest_date(self) -> Optional[str]:
        """
        从本地 stock_daily 查最新已有交易日（排除脏数据，只看有大量记录的交易日）

        Returns:
            最新交易日，格式：YYYYMMDD；无数据时返回 None
        """
        conn = self.db.pool_manager.get_connection()
        cursor = conn.cursor()
        try:
            # 只取有大量股票数据的交易日（至少100条），排除测试数据和单条脏数据
            cursor.execute(
                """
                SELECT TO_CHAR(date, 'YYYYMMDD')
                FROM stock_daily
                WHERE code LIKE '%%.%%'
                GROUP BY date
                HAVING COUNT(*) >= 100
                ORDER BY date DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"查询本地最新交易日失败: {e}")
            return None
        finally:
            cursor.close()
            self.db.pool_manager.release_connection(conn)
