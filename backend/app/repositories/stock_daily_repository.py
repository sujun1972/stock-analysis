"""
Stock Daily Repository
管理股票日线数据的数据访问
"""

from typing import List, Optional

import pandas as pd
from loguru import logger

from app.core.exceptions import DataQueryError

from .base_repository import BaseRepository


class StockDailyRepository(BaseRepository):
    """股票日线数据访问层"""

    TABLE_NAME = "stock_daily"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ StockDailyRepository initialized")

    def get_by_code_and_date_range(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        按股票代码和日期范围查询日线数据

        Args:
            stock_code: 股票代码（不带交易所后缀）
            start_date: 开始日期，格式：YYYY-MM-DD（可选）
            end_date: 结束日期，格式：YYYY-MM-DD（可选）

        Returns:
            日线数据 DataFrame（以 date 为索引）

        Raises:
            DataQueryError: 数据查询失败

        Examples:
            >>> repo = StockDailyRepository()
            >>> df = repo.get_by_code_and_date_range('000001', '2024-01-01', '2024-12-31')
            >>> print(f"数据行数: {len(df)}")
        """
        try:
            query = """
                SELECT date, open, high, low, close, volume, amount,
                       amplitude, pct_change, change, turnover
                FROM stock_daily
                WHERE code = %s
            """
            params = [stock_code]

            if start_date:
                query += " AND date >= %s"
                params.append(start_date)

            if end_date:
                query += " AND date <= %s"
                params.append(end_date)

            query += " ORDER BY date ASC"

            # 使用 pandas read_sql_query（保持与原 DatabaseManager 一致）
            import warnings

            conn = self.db.get_connection()
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy')
                    df = pd.read_sql_query(
                        query, conn, params=params, index_col='date', parse_dates=['date']
                    )

                # 确保数值列是正确的类型
                numeric_columns = [
                    'open',
                    'high',
                    'low',
                    'close',
                    'volume',
                    'amount',
                    'amplitude',
                    'pct_change',
                    'change',
                    'turnover',
                ]
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                return df

            finally:
                self.db.release_connection(conn)

        except Exception as e:
            logger.error(f"查询股票 {stock_code} 日线数据失败: {e}")
            raise DataQueryError(
                f"查询股票日线数据失败: {stock_code}",
                error_code="STOCK_DAILY_QUERY_FAILED",
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                reason=str(e),
            )

    def get_stock_list(
        self, market: Optional[str] = None, status: str = '正常'
    ) -> pd.DataFrame:
        """
        获取股票列表

        Args:
            market: 市场类型（如 '上海主板', '深圳主板'），可选
            status: 股票状态（默认 '正常'）

        Returns:
            股票列表 DataFrame

        Raises:
            DataQueryError: 数据查询失败

        Examples:
            >>> repo = StockDailyRepository()
            >>> stocks = repo.get_stock_list(market='上海主板', status='正常')
            >>> print(f"股票数量: {len(stocks)}")
        """
        try:
            query = "SELECT code, name, market, status FROM stock_list WHERE status = %s"
            params = [status]

            if market:
                query += " AND market = %s"
                params.append(market)

            query += " ORDER BY code"

            conn = self.db.get_connection()
            try:
                import warnings

                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy')
                    df = pd.read_sql_query(query, conn, params=params)

                return df

            finally:
                self.db.release_connection(conn)

        except Exception as e:
            logger.error(f"查询股票列表失败: {e}")
            raise DataQueryError(
                "查询股票列表失败",
                error_code="STOCK_LIST_QUERY_FAILED",
                market=market,
                status=status,
                reason=str(e),
            )

    def check_data_completeness(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        min_expected_days: Optional[int] = None,
    ) -> dict:
        """
        检查股票日线数据的完整性

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            min_expected_days: 最小预期天数（可选）

        Returns:
            完整性检查结果字典:
            {
                'is_complete': bool,
                'actual_days': int,
                'expected_days': int,
                'missing_rate': float,
                'first_date': str,
                'last_date': str
            }

        Examples:
            >>> repo = StockDailyRepository()
            >>> result = repo.check_data_completeness('000001', '2024-01-01', '2024-12-31')
            >>> if not result['is_complete']:
            >>>     print(f"数据缺失率: {result['missing_rate']:.2%}")
        """
        try:
            df = self.get_by_code_and_date_range(stock_code, start_date, end_date)

            if df.empty:
                return {
                    'is_complete': False,
                    'actual_days': 0,
                    'expected_days': min_expected_days or 0,
                    'missing_rate': 1.0,
                    'first_date': None,
                    'last_date': None,
                }

            actual_days = len(df)

            # 计算预期天数（简化版：基于时间范围估算）
            if min_expected_days is None:
                # 粗略估算：工作日约占 250/365
                from datetime import datetime

                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                days_range = (end - start).days + 1
                min_expected_days = int(days_range * 250 / 365)

            is_complete = actual_days >= min_expected_days
            missing_rate = max(0, (min_expected_days - actual_days) / min_expected_days)

            return {
                'is_complete': is_complete,
                'actual_days': actual_days,
                'expected_days': min_expected_days,
                'missing_rate': missing_rate,
                'first_date': str(df.index.min().date()),
                'last_date': str(df.index.max().date()),
            }

        except DataQueryError:
            raise
        except Exception as e:
            logger.error(f"检查股票 {stock_code} 数据完整性失败: {e}")
            raise DataQueryError(
                f"检查数据完整性失败: {stock_code}",
                error_code="DATA_COMPLETENESS_CHECK_FAILED",
                stock_code=stock_code,
                reason=str(e),
            )

    def get_latest_trade_date(self, stock_code: str) -> Optional[str]:
        """
        获取股票的最新交易日期

        Args:
            stock_code: 股票代码

        Returns:
            最新交易日期（YYYY-MM-DD），无数据返回 None

        Examples:
            >>> repo = StockDailyRepository()
            >>> latest_date = repo.get_latest_trade_date('000001')
            >>> print(f"最新交易日: {latest_date}")
        """
        query = """
            SELECT MAX(date) FROM stock_daily WHERE code = %s
        """
        result = self.execute_query(query, (stock_code,))

        if result and result[0][0]:
            return str(result[0][0])
        return None

    def get_records_count(
        self, stock_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> int:
        """
        获取股票日线数据记录数

        Args:
            stock_code: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            记录数

        Examples:
            >>> repo = StockDailyRepository()
            >>> count = repo.get_records_count('000001', '2024-01-01', '2024-12-31')
            >>> print(f"记录数: {count}")
        """
        query = "SELECT COUNT(*) FROM stock_daily WHERE code = %s"
        params = [stock_code]

        if start_date:
            query += " AND date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND date <= %s"
            params.append(end_date)

        result = self.execute_query(query, tuple(params))
        return result[0][0] if result else 0

    def batch_get_by_codes(
        self, stock_codes: List[str], start_date: str, end_date: str
    ) -> dict:
        """
        批量获取多只股票的日线数据

        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            {stock_code: DataFrame} 字典

        Examples:
            >>> repo = StockDailyRepository()
            >>> data_dict = repo.batch_get_by_codes(['000001', '000002'], '2024-01-01', '2024-12-31')
            >>> print(f"成功获取 {len(data_dict)} 只股票数据")
        """
        result = {}

        for code in stock_codes:
            try:
                df = self.get_by_code_and_date_range(code, start_date, end_date)
                if not df.empty:
                    result[code] = df
                else:
                    logger.warning(f"股票 {code} 无数据")
            except DataQueryError as e:
                logger.error(f"获取股票 {code} 数据失败: {e}")
                # 批量操作时，单个失败不影响整体
                continue

        return result
