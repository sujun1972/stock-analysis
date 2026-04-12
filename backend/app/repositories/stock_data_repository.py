"""
股票数据Repository
统一股票数据访问层

职责：
1. 股票列表的CRUD操作
2. K线数据的CRUD操作
3. 技术指标数据的访问
4. 数据查询和统计

重构说明：
- 从 DataDownloadService 和 DatabaseManager 提取数据访问逻辑
- 提供统一的股票数据访问接口
- 支持批量操作和事务管理
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError
from src.database.db_manager import DatabaseManager

from app.core.cache import cache
from app.core.config import settings
from app.core.exceptions import DatabaseError
from app.repositories.base_repository import BaseRepository


class StockDataRepository(BaseRepository):
    """
    股票数据Repository

    职责：
    - 股票列表管理
    - 日线数据管理
    - 分时数据管理
    - 实时数据管理
    - 数据统计和查询
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化股票数据Repository

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        super().__init__(db)
        logger.debug("✓ StockDataRepository initialized")

    # ==================== 股票列表操作 ====================

    async def get_stock_list_cached(self, market: Optional[str] = None) -> pd.DataFrame:
        """
        获取股票列表（带缓存）

        Args:
            market: 市场类型（可选，如 '上海主板'、'深圳主板'、'创业板'等）

        Returns:
            股票列表 DataFrame

        Raises:
            DatabaseError: 数据库操作失败
        """
        import asyncio

        # 生成缓存键
        cache_key = f"stock_list:{market or 'all'}"

        # 尝试从缓存获取
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"从缓存获取股票列表 (market={market})")
            return pd.DataFrame(cached_data)

        # 缓存未命中，从数据库获取
        logger.debug(f"从数据库获取股票列表 (market={market})")
        df = await asyncio.to_thread(self.get_stock_list, market)

        # 保存到缓存（DataFrame 转为字典列表）
        if not df.empty:
            await cache.set(
                cache_key,
                df.to_dict('records'),
                ttl=settings.CACHE_STOCK_LIST_TTL
            )

        return df

    def get_stock_list(self, market: Optional[str] = None) -> pd.DataFrame:
        """
        获取股票列表（无缓存）

        Args:
            market: 市场类型（可选，如 '上海主板'、'深圳主板'、'创业板'等）

        Returns:
            股票列表 DataFrame

        Raises:
            DatabaseError: 数据库操作失败
        """
        try:
            if market:
                # 验证市场参数
                self._validate_identifier(market, "market")
                return self.db.get_stock_list(market=market)
            else:
                return self.db.get_stock_list()

        except PsycopgDatabaseError as e:
            logger.error(f"获取股票列表失败 (market={market}): {e}")
            raise DatabaseError(
                "股票列表查询失败",
                error_code="STOCK_LIST_QUERY_FAILED",
                market=market,
                reason=str(e)
            )

    async def save_stock_list_and_clear_cache(self, stock_df: pd.DataFrame) -> int:
        """
        保存股票列表到数据库并清除缓存

        Args:
            stock_df: 股票列表 DataFrame，必须包含列: code, name, market

        Returns:
            保存的股票数量

        Raises:
            ValueError: DataFrame格式不正确
            DatabaseError: 数据库操作失败
        """
        import asyncio

        # 保存到数据库
        count = await asyncio.to_thread(self.save_stock_list, stock_df)

        # 清除相关缓存
        await cache.delete_pattern("stock_list:*")
        logger.debug("已清除股票列表缓存")
        return count

    def save_stock_list(self, stock_df: pd.DataFrame) -> int:
        """
        保存股票列表到数据库

        Args:
            stock_df: 股票列表 DataFrame，必须包含列: code, name, market

        Returns:
            保存的股票数量

        Raises:
            ValueError: DataFrame格式不正确
            DatabaseError: 数据库操作失败

        Examples:
            >>> stock_df = pd.DataFrame({
            ...     'code': ['000001', '600000'],
            ...     'name': ['平安银行', '浦发银行'],
            ...     'market': ['深圳主板', '上海主板']
            ... })
            >>> count = repo.save_stock_list(stock_df)
            >>> print(f"保存了 {count} 只股票")
        """
        try:
            # 验证 DataFrame 格式
            required_columns = {'code', 'name', 'market'}
            if not required_columns.issubset(stock_df.columns):
                missing = required_columns - set(stock_df.columns)
                raise ValueError(
                    f"股票列表 DataFrame 缺少必需列: {', '.join(missing)}\n"
                    f"当前列: {', '.join(stock_df.columns)}"
                )

            count = self.db.save_stock_list(stock_df)
            logger.info(f"✓ 保存股票列表: {count} 只")
            return count

        except ValueError:
            # 格式验证错误，直接向上传播
            raise
        except PsycopgDatabaseError as e:
            logger.error(f"保存股票列表失败: {e}")
            raise DatabaseError(
                "股票列表保存失败",
                error_code="STOCK_LIST_SAVE_FAILED",
                count=len(stock_df) if stock_df is not None else 0,
                reason=str(e)
            )

    def get_stock_by_code(self, code: str) -> Optional[Dict]:
        """
        根据股票代码获取股票信息

        Args:
            code: 股票代码

        Returns:
            股票信息字典，如果不存在则返回 None

        Examples:
            >>> stock = repo.get_stock_by_code('000001')
            >>> if stock:
            ...     print(f"{stock['name']} ({stock['code']})")
        """
        try:
            query = """
                SELECT code, name, market
                FROM stock_list
                WHERE code = %s
            """
            result = self.execute_query(query, (code,))

            if not result:
                return None

            row = result[0]
            return {
                "code": row[0],
                "name": row[1],
                "market": row[2]
            }

        except Exception as e:
            logger.error(f"查询股票信息失败 (code={code}): {e}")
            raise DatabaseError(
                f"股票 {code} 信息查询失败",
                error_code="STOCK_INFO_QUERY_FAILED",
                stock_code=code,
                reason=str(e)
            )

    def stock_exists(self, code: str) -> bool:
        """
        检查股票是否存在

        Args:
            code: 股票代码

        Returns:
            是否存在
        """
        try:
            return self.exists("stock_list", "code = %s", (code,))
        except Exception as e:
            logger.error(f"检查股票是否存在失败 (code={code}): {e}")
            return False

    def get_stock_count(self, market: Optional[str] = None) -> int:
        """
        获取股票数量

        Args:
            market: 市场类型（可选）

        Returns:
            股票数量
        """
        try:
            if market:
                self._validate_identifier(market, "market")
                return self.count("stock_list", "market = %s", (market,))
            else:
                return self.count("stock_list")
        except Exception as e:
            logger.error(f"获取股票数量失败 (market={market}): {e}")
            raise DatabaseError(
                "股票数量统计失败",
                error_code="STOCK_COUNT_FAILED",
                market=market,
                reason=str(e)
            )

    # ==================== 日线数据操作 ====================

    async def get_daily_data_cached(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        获取日线数据（带缓存）

        Args:
            code: 股票代码
            start_date: 起始日期（格式：YYYY-MM-DD，可选）
            end_date: 结束日期（格式：YYYY-MM-DD，可选）
            limit: 最大记录数（可选）

        Returns:
            日线数据 DataFrame
        """
        import asyncio
        import hashlib

        # 生成缓存键（基于参数哈希）
        params_str = f"{code}:{start_date}:{end_date}:{limit}"
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        cache_key = f"daily_data:{code}:{params_hash}"

        # 尝试从缓存获取
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"从缓存获取日线数据 (code={code})")
            return pd.DataFrame(cached_data)

        # 缓存未命中，从数据库获取
        logger.debug(f"从数据库获取日线数据 (code={code})")
        df = await asyncio.to_thread(
            self.get_daily_data,
            code,
            start_date,
            end_date,
            limit
        )

        # 保存到缓存
        if not df.empty:
            # 重置索引以便序列化
            df_to_cache = df.reset_index()
            await cache.set(
                cache_key,
                df_to_cache.to_dict('records'),
                ttl=settings.CACHE_DAILY_DATA_TTL
            )

        return df

    def get_daily_data(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None  # 保留参数签名兼容性，实际由调用方做客户端分页
    ) -> pd.DataFrame:
        """
        获取单只股票日线数据

        Args:
            code: 股票代码（完整 ts_code，如 000001.SZ）
            start_date: 起始日期（YYYY-MM-DD，可选）
            end_date: 结束日期（YYYY-MM-DD，可选）
            limit: 保留参数，当前不传给底层（由 Service 层做客户端分页）

        Returns:
            日线数据 DataFrame，以 date 为 index，升序排列

        Examples:
            >>> df = repo.get_daily_data('000001.SZ', '2024-01-01', '2024-12-31')
        """
        try:
            return self.db.load_daily_data(
                stock_code=code,
                start_date=start_date,
                end_date=end_date
            )
        except PsycopgDatabaseError as e:
            logger.error(f"获取日线数据失败 (code={code}): {e}")
            raise DatabaseError(
                f"股票 {code} 日线数据查询失败",
                error_code="DAILY_DATA_QUERY_FAILED",
                stock_code=code,
                start_date=start_date,
                end_date=end_date,
                reason=str(e)
            )

    async def save_daily_data_and_clear_cache(self, data: pd.DataFrame, code: str) -> int:
        """
        保存日线数据并清除缓存

        Args:
            data: 日线数据 DataFrame
            code: 股票代码

        Returns:
            保存的记录数
        """
        import asyncio

        # 保存到数据库
        count = await asyncio.to_thread(self.save_daily_data, data, code)

        # 清除该股票的缓存
        await cache.delete_pattern(f"daily_data:{code}:*")
        logger.debug(f"已清除 {code} 的日线数据缓存")
        return count

    def save_daily_data(self, data: pd.DataFrame, code: str) -> int:
        """
        保存日线数据

        Args:
            data: 日线数据 DataFrame，必须包含列: date, open, high, low, close, volume
            code: 股票代码

        Returns:
            保存的记录数

        Raises:
            ValueError: DataFrame格式不正确
            DatabaseError: 数据库操作失败
        """
        try:
            # 验证 DataFrame 格式
            required_columns = {'open', 'high', 'low', 'close', 'volume'}
            if not required_columns.issubset(data.columns):
                missing = required_columns - set(data.columns)
                raise ValueError(
                    f"日线数据 DataFrame 缺少必需列: {', '.join(missing)}\n"
                    f"当前列: {', '.join(data.columns)}"
                )

            # 验证 date 索引
            if not isinstance(data.index, pd.DatetimeIndex):
                raise ValueError(
                    "日线数据 DataFrame 必须使用 DatetimeIndex 作为索引\n"
                    f"当前索引类型: {type(data.index).__name__}"
                )

            count = self.db.save_daily_data(data, code)
            logger.info(f"✓ 保存日线数据: {code} - {count} 条记录")
            return count

        except ValueError:
            # 格式验证错误，直接向上传播
            raise
        except PsycopgDatabaseError as e:
            logger.error(f"保存日线数据失败 (code={code}): {e}")
            raise DatabaseError(
                f"股票 {code} 日线数据保存失败",
                error_code="DAILY_DATA_SAVE_FAILED",
                stock_code=code,
                count=len(data) if data is not None else 0,
                reason=str(e)
            )

    def delete_daily_data(self, code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> int:
        """
        删除日线数据

        Args:
            code: 股票代码
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            删除的记录数

        Examples:
            >>> # 删除所有数据
            >>> count = repo.delete_daily_data('000001')
            >>>
            >>> # 删除指定日期范围数据
            >>> count = repo.delete_daily_data('000001', '2024-01-01', '2024-12-31')
        """
        try:
            conditions = ["code = %s"]
            params = [code]

            if start_date:
                conditions.append("date >= %s")
                params.append(start_date)

            if end_date:
                conditions.append("date <= %s")
                params.append(end_date)

            query = f"DELETE FROM daily_data WHERE {' AND '.join(conditions)}"
            count = self.execute_update(query, tuple(params))

            logger.info(f"✓ 删除日线数据: {code} - {count} 条记录")
            return count

        except Exception as e:
            logger.error(f"删除日线数据失败 (code={code}): {e}")
            raise DatabaseError(
                f"股票 {code} 日线数据删除失败",
                error_code="DAILY_DATA_DELETE_FAILED",
                stock_code=code,
                reason=str(e)
            )

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量写入日线数据（供 TushareSyncBase 使用）。

        接受 convert_daily_data 输出的 DataFrame：含 ts_code + trade_date 列（trade_date 为 date 对象）。
        按 ts_code 分组后调用 save_daily_data，返回写入总条数。
        """
        if df is None or df.empty:
            return 0

        if 'ts_code' not in df.columns or 'trade_date' not in df.columns:
            raise ValueError("bulk_upsert 需要 ts_code 和 trade_date 列")

        df = df.copy()
        df['trade_date'] = pd.to_datetime(df['trade_date'])

        total = 0
        for ts_code, group in df.groupby('ts_code'):
            stock_df = group.drop(columns=['ts_code']).set_index('trade_date')
            total += self.save_daily_data(stock_df, ts_code)
        return total

    def get_latest_date(self, code: str) -> Optional[datetime]:
        """
        获取股票最新数据日期

        Args:
            code: 股票代码

        Returns:
            最新日期，如果没有数据则返回 None

        Examples:
            >>> latest = repo.get_latest_date('000001')
            >>> if latest:
            ...     print(f"最新数据: {latest.strftime('%Y-%m-%d')}")
        """
        try:
            query = """
                SELECT MAX(date) as latest_date
                FROM daily_data
                WHERE code = %s
            """
            result = self.execute_query(query, (code,))

            if result and result[0][0]:
                return result[0][0]
            return None

        except Exception as e:
            logger.error(f"获取最新日期失败 (code={code}): {e}")
            return None

    def get_data_range(self, code: str) -> Optional[Tuple[datetime, datetime]]:
        """
        获取股票数据日期范围

        Args:
            code: 股票代码

        Returns:
            (最早日期, 最晚日期) 元组，如果没有数据则返回 None
        """
        try:
            query = """
                SELECT MIN(date) as min_date, MAX(date) as max_date
                FROM daily_data
                WHERE code = %s
            """
            result = self.execute_query(query, (code,))

            if result and result[0][0] and result[0][1]:
                return (result[0][0], result[0][1])
            return None

        except Exception as e:
            logger.error(f"获取数据范围失败 (code={code}): {e}")
            return None

    # ==================== 批量操作 ====================

    def get_stocks_with_data(self) -> List[str]:
        """
        获取有日线数据的股票代码列表

        Returns:
            股票代码列表

        Examples:
            >>> codes = repo.get_stocks_with_data()
            >>> print(f"共有 {len(codes)} 只股票有数据")
        """
        try:
            query = """
                SELECT DISTINCT code
                FROM daily_data
                ORDER BY code
            """
            result = self.execute_query(query)
            return [row[0] for row in result]

        except Exception as e:
            logger.error(f"获取有数据的股票列表失败: {e}")
            raise DatabaseError(
                "获取有数据的股票列表失败",
                error_code="STOCKS_WITH_DATA_QUERY_FAILED",
                reason=str(e)
            )

    def get_stocks_without_data(self) -> List[Dict]:
        """
        获取没有日线数据的股票列表

        Returns:
            股票信息列表 [{code, name, market}, ...]

        Examples:
            >>> stocks = repo.get_stocks_without_data()
            >>> for stock in stocks:
            ...     print(f"{stock['name']} ({stock['code']}) 缺少数据")
        """
        try:
            query = """
                SELECT sl.code, sl.name, sl.market
                FROM stock_list sl
                LEFT JOIN daily_data dd ON sl.code = dd.code
                WHERE dd.code IS NULL
                ORDER BY sl.code
            """
            result = self.execute_query(query)
            return [
                {"code": row[0], "name": row[1], "market": row[2]}
                for row in result
            ]

        except Exception as e:
            logger.error(f"获取无数据的股票列表失败: {e}")
            raise DatabaseError(
                "获取无数据的股票列表失败",
                error_code="STOCKS_WITHOUT_DATA_QUERY_FAILED",
                reason=str(e)
            )

    def get_data_statistics(self) -> Dict:
        """
        获取数据统计信息

        Returns:
            统计信息字典 {
                total_stocks: 总股票数,
                stocks_with_data: 有数据的股票数,
                stocks_without_data: 无数据的股票数,
                total_records: 总记录数,
                avg_records_per_stock: 平均每只股票记录数
            }

        Examples:
            >>> stats = repo.get_data_statistics()
            >>> print(f"数据覆盖率: {stats['stocks_with_data']}/{stats['total_stocks']}")
        """
        try:
            query = """
                SELECT
                    (SELECT COUNT(*) FROM stock_list) as total_stocks,
                    (SELECT COUNT(DISTINCT code) FROM daily_data) as stocks_with_data,
                    (SELECT COUNT(*) FROM daily_data) as total_records
            """
            result = self.execute_query(query)

            if result:
                row = result[0]
                total_stocks = row[0] or 0
                stocks_with_data = row[1] or 0
                total_records = row[2] or 0

                return {
                    "total_stocks": total_stocks,
                    "stocks_with_data": stocks_with_data,
                    "stocks_without_data": total_stocks - stocks_with_data,
                    "total_records": total_records,
                    "avg_records_per_stock": (
                        round(total_records / stocks_with_data, 2)
                        if stocks_with_data > 0 else 0
                    )
                }

            return {
                "total_stocks": 0,
                "stocks_with_data": 0,
                "stocks_without_data": 0,
                "total_records": 0,
                "avg_records_per_stock": 0
            }

        except Exception as e:
            logger.error(f"获取数据统计信息失败: {e}")
            raise DatabaseError(
                "数据统计查询失败",
                error_code="DATA_STATISTICS_FAILED",
                reason=str(e)
            )

    # ==================== 数据验证 ====================

    def validate_stock_data(self, code: str) -> Dict:
        """
        验证股票数据完整性

        Args:
            code: 股票代码

        Returns:
            验证结果字典 {
                is_valid: bool,
                record_count: int,
                date_range: (start, end) or None,
                missing_dates: int,
                issues: List[str]
            }

        Examples:
            >>> validation = repo.validate_stock_data('000001')
            >>> if not validation['is_valid']:
            ...     print(f"数据问题: {', '.join(validation['issues'])}")
        """
        try:
            issues = []

            # 检查是否有数据
            data_range = self.get_data_range(code)
            if not data_range:
                return {
                    "is_valid": False,
                    "record_count": 0,
                    "date_range": None,
                    "missing_dates": 0,
                    "issues": ["没有数据"]
                }

            # 获取记录数
            query = "SELECT COUNT(*) FROM daily_data WHERE code = %s"
            result = self.execute_query(query, (code,))
            record_count = result[0][0] if result else 0

            # 检查数据量是否合理（至少30条）
            if record_count < 30:
                issues.append(f"数据量过少 ({record_count} 条)")

            # 检查是否有空值
            query = """
                SELECT COUNT(*)
                FROM daily_data
                WHERE code = %s
                  AND (open IS NULL OR high IS NULL OR low IS NULL
                       OR close IS NULL OR volume IS NULL)
            """
            result = self.execute_query(query, (code,))
            null_count = result[0][0] if result else 0
            if null_count > 0:
                issues.append(f"存在 {null_count} 条空值记录")

            return {
                "is_valid": len(issues) == 0,
                "record_count": record_count,
                "date_range": data_range,
                "missing_dates": 0,  # TODO: 计算实际缺失的交易日
                "issues": issues
            }

        except Exception as e:
            logger.error(f"验证股票数据失败 (code={code}): {e}")
            return {
                "is_valid": False,
                "record_count": 0,
                "date_range": None,
                "missing_dates": 0,
                "issues": [f"验证失败: {str(e)}"]
            }
