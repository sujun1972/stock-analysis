"""
Stock Basic Repository
股票基础信息数据访问层
"""

from typing import Dict, List, Optional
from loguru import logger

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class StockBasicRepository(BaseRepository):
    """
    股票基础信息 Repository

    管理 stock_basic 表的数据访问操作

    主要功能：
    - 批量获取股票名称映射
    - 按代码查询股票信息
    - 按市场、行业、状态查询
    - 股票列表查询
    """

    TABLE_NAME = "stock_basic"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ StockBasicRepository initialized")

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        return {
            'id': row[0],
            'code': row[1],
            'name': row[2],
            'market': row[3],
            'industry': row[4],
            'area': row[5],
            'list_date': row[6],
            'delist_date': row[7],
            'status': row[8],
            'data_source': row[9],
            'updated_at': row[10],
            'created_at': row[11]
        }

    # ==================== 查询操作 ====================

    def get_stock_names(self, codes: List[str]) -> Dict[str, str]:
        """
        批量获取股票名称映射

        Args:
            codes: 股票代码列表（如 ['000001.SZ', '600000.SH']）

        Returns:
            股票代码 -> 名称的映射字典

        Examples:
            >>> repo = StockBasicRepository()
            >>> names = repo.get_stock_names(['000001.SZ', '600000.SH'])
            >>> print(names)
            {'000001.SZ': '平安银行', '600000.SH': '浦发银行'}
        """
        if not codes:
            logger.debug("股票代码列表为空，返回空映射")
            return {}

        try:
            # 使用 ANY 操作符进行批量查询（PostgreSQL 特性）
            query = f"""
                SELECT code, name
                FROM {self.TABLE_NAME}
                WHERE code = ANY(%s)
            """
            result = self.execute_query(query, (codes,))

            # 转换为字典（result 是 List[Tuple]）
            stock_name_map = {row[0]: row[1] for row in result}
            logger.debug(f"已获取 {len(stock_name_map)}/{len(codes)} 个股票名称")

            return stock_name_map

        except Exception as e:
            logger.error(f"批量查询股票名称失败: {e}")
            raise QueryError(
                "批量查询股票名称失败",
                error_code="STOCK_NAMES_QUERY_FAILED",
                reason=str(e)
            )

    def get_by_code(self, code: str) -> Optional[Dict]:
        """
        按股票代码查询单条记录

        Args:
            code: 股票代码（如 '000001.SZ'）

        Returns:
            股票信息字典，不存在则返回 None

        Examples:
            >>> repo = StockBasicRepository()
            >>> stock = repo.get_by_code('000001.SZ')
            >>> print(stock['name'])
            '平安银行'
        """
        try:
            query = f"""
                SELECT id, code, name, market, industry, area, list_date,
                       delist_date, status, data_source, updated_at, created_at
                FROM {self.TABLE_NAME} WHERE code = %s
            """
            result = self.execute_query(query, (code,))

            if result:
                return self._row_to_dict(result[0])
            else:
                logger.debug(f"未找到股票: {code}")
                return None

        except Exception as e:
            logger.error(f"查询股票信息失败: code={code}, error={e}")
            raise QueryError(
                "查询股票信息失败",
                error_code="STOCK_INFO_QUERY_FAILED",
                code=code,
                reason=str(e)
            )

    def get_by_codes(self, codes: List[str]) -> List[Dict]:
        """
        按股票代码列表查询多条记录

        Args:
            codes: 股票代码列表

        Returns:
            股票信息列表

        Examples:
            >>> repo = StockBasicRepository()
            >>> stocks = repo.get_by_codes(['000001.SZ', '600000.SH'])
            >>> print(len(stocks))
            2
        """
        if not codes:
            return []

        try:
            query = f"""
                SELECT id, code, name, market, industry, area, list_date,
                       delist_date, status, data_source, updated_at, created_at
                FROM {self.TABLE_NAME}
                WHERE code = ANY(%s)
                ORDER BY code
            """
            result = self.execute_query(query, (codes,))
            logger.debug(f"查询到 {len(result)} 条股票信息")
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"批量查询股票信息失败: {e}")
            raise QueryError(
                "批量查询股票信息失败",
                error_code="STOCKS_QUERY_FAILED",
                reason=str(e)
            )

    def get_by_market(self, market: str, status: str = 'L') -> List[Dict]:
        """
        按市场查询股票列表

        Args:
            market: 市场类型（主板/科创板/创业板/北交所）
            status: 股票状态，默认 'L'（上市）

        Returns:
            股票列表

        Examples:
            >>> repo = StockBasicRepository()
            >>> stocks = repo.get_by_market('主板', status='L')
            >>> print(f"主板股票数量: {len(stocks)}")
        """
        try:
            query = f"""
                SELECT id, code, name, market, industry, area, list_date,
                       delist_date, status, data_source, updated_at, created_at
                FROM {self.TABLE_NAME}
                WHERE market = %s AND status = %s
                ORDER BY code
            """
            result = self.execute_query(query, (market, status))
            logger.debug(f"查询到 {len(result)} 只{market}股票")
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"按市场查询股票失败: market={market}, error={e}")
            raise QueryError(
                "按市场查询股票失败",
                error_code="STOCKS_BY_MARKET_QUERY_FAILED",
                market=market,
                reason=str(e)
            )

    def get_by_industry(self, industry: str, status: str = 'L') -> List[Dict]:
        """
        按行业查询股票列表

        Args:
            industry: 行业名称
            status: 股票状态，默认 'L'（上市）

        Returns:
            股票列表

        Examples:
            >>> repo = StockBasicRepository()
            >>> stocks = repo.get_by_industry('银行', status='L')
            >>> print(f"银行股数量: {len(stocks)}")
        """
        try:
            query = f"""
                SELECT id, code, name, market, industry, area, list_date,
                       delist_date, status, data_source, updated_at, created_at
                FROM {self.TABLE_NAME}
                WHERE industry = %s AND status = %s
                ORDER BY code
            """
            result = self.execute_query(query, (industry, status))
            logger.debug(f"查询到 {len(result)} 只{industry}行业股票")
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"按行业查询股票失败: industry={industry}, error={e}")
            raise QueryError(
                "按行业查询股票失败",
                error_code="STOCKS_BY_INDUSTRY_QUERY_FAILED",
                industry=industry,
                reason=str(e)
            )

    def get_all(
        self,
        status: Optional[str] = 'L',
        limit: Optional[int] = None,
        offset: Optional[int] = 0
    ) -> List[Dict]:
        """
        获取股票列表（带分页）

        Args:
            status: 股票状态（L=上市, D=退市, P=暂停），None表示全部
            limit: 限制数量
            offset: 偏移量

        Returns:
            股票列表

        Examples:
            >>> repo = StockBasicRepository()
            >>> stocks = repo.get_all(status='L', limit=100)
            >>> print(f"查询到 {len(stocks)} 只股票")
        """
        try:
            base_query = f"""
                SELECT id, code, name, market, industry, area, list_date,
                       delist_date, status, data_source, updated_at, created_at
                FROM {self.TABLE_NAME}
            """

            if status:
                query = base_query + " WHERE status = %s ORDER BY code"
                params = [status]
            else:
                query = base_query + " ORDER BY code"
                params = []

            effective_limit = self._enforce_limit(limit)
            query += " LIMIT %s"
            params.append(effective_limit)

            if offset:
                query += f" OFFSET %s"
                params.append(offset)

            result = self.execute_query(query, tuple(params))
            logger.debug(f"查询到 {len(result)} 只股票")
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询股票列表失败: {e}")
            raise QueryError(
                "查询股票列表失败",
                error_code="STOCKS_LIST_QUERY_FAILED",
                reason=str(e)
            )

    def get_listed_ts_codes(self, status: str = 'L') -> List[str]:
        """
        获取所有指定状态股票的 ts_code 列表

        Args:
            status: 股票状态（L=上市, D=退市, P=暂停），默认上市

        Returns:
            ts_code 列表，如 ['000001.SZ', '600000.SH', ...]

        Examples:
            >>> repo = StockBasicRepository()
            >>> codes = repo.get_listed_ts_codes(status='L')
            >>> print(f"上市股票数: {len(codes)}")
        """
        try:
            query = f"""
                SELECT ts_code
                FROM {self.TABLE_NAME}
                WHERE list_status = %s AND ts_code IS NOT NULL
                ORDER BY ts_code
            """
            result = self.execute_query(query, (status,))
            codes = [row[0] for row in result if row[0]]
            logger.debug(f"查询到 {len(codes)} 只 list_status={status} 的股票 ts_code")
            return codes

        except Exception as e:
            logger.error(f"查询股票 ts_code 列表失败: {e}")
            raise QueryError(
                "查询股票 ts_code 列表失败",
                error_code="STOCK_TS_CODES_QUERY_FAILED",
                reason=str(e)
            )

    # ==================== 统计操作 ====================

    def count_by_status(self, status: str = 'L') -> int:
        """
        按状态统计股票数量

        Args:
            status: 股票状态

        Returns:
            股票数量

        Examples:
            >>> repo = StockBasicRepository()
            >>> count = repo.count_by_status('L')
            >>> print(f"上市股票数量: {count}")
        """
        try:
            query = f"""
                SELECT COUNT(*) as count
                FROM {self.TABLE_NAME}
                WHERE status = %s
            """
            result = self.execute_query(query, (status,))
            count = result[0][0] if result else 0  # result[0][0] 表示第一行第一列
            logger.debug(f"状态为 {status} 的股票数量: {count}")
            return count

        except Exception as e:
            logger.error(f"统计股票数量失败: status={status}, error={e}")
            raise QueryError(
                "统计股票数量失败",
                error_code="STOCKS_COUNT_FAILED",
                status=status,
                reason=str(e)
            )

    def count_by_market(self) -> Dict[str, int]:
        """
        按市场统计股票数量

        Returns:
            市场 -> 数量的映射字典

        Examples:
            >>> repo = StockBasicRepository()
            >>> stats = repo.count_by_market()
            >>> print(stats)
            {'主板': 2000, '科创板': 500, '创业板': 1000}
        """
        try:
            query = f"""
                SELECT market, COUNT(*) as count
                FROM {self.TABLE_NAME}
                WHERE status = 'L'
                GROUP BY market
                ORDER BY count DESC
            """
            result = self.execute_query(query)

            market_stats = {row[0]: row[1] for row in result}  # row[0]=market, row[1]=count
            logger.debug(f"市场分布统计: {market_stats}")
            return market_stats

        except Exception as e:
            logger.error(f"按市场统计股票失败: {e}")
            raise QueryError(
                "按市场统计股票失败",
                error_code="STOCKS_COUNT_BY_MARKET_FAILED",
                reason=str(e)
            )

    # ==================== 新股查询操作 ====================

    def get_new_stocks(
        self,
        start_date: str,
        end_date: str,
        market: Optional[str] = None,
        limit: Optional[int] = 30,
        offset: Optional[int] = 0
    ) -> List[Dict]:
        """
        查询指定日期范围内上市的新股

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            market: 市场类型筛选（可选）
            limit: 返回记录数
            offset: 偏移量

        Returns:
            新股列表（按上市日期倒序）

        Examples:
            >>> repo = StockBasicRepository()
            >>> new_stocks = repo.get_new_stocks('2024-01-01', '2024-12-31')
            >>> print(f"2024年新上市股票: {len(new_stocks)}只")
        """
        try:
            base_query = f"""
                SELECT code, name, market, industry, area, list_date, status, data_source
                FROM {self.TABLE_NAME}
                WHERE list_date >= %s AND list_date <= %s
            """
            params = [start_date, end_date]

            if market:
                base_query += " AND market = %s"
                params.append(market)

            base_query += " ORDER BY list_date DESC, code"

            if limit:
                base_query += " LIMIT %s"
                params.append(limit)

            if offset:
                base_query += " OFFSET %s"
                params.append(offset)

            result = self.execute_query(base_query, tuple(params))
            logger.debug(f"查询到 {len(result)} 只新股 ({start_date} ~ {end_date})")

            # 转换为字典列表
            items = []
            for row in result:
                items.append({
                    'code': row[0],
                    'name': row[1],
                    'market': row[2],
                    'industry': row[3],
                    'area': row[4],
                    'list_date': row[5].strftime('%Y-%m-%d') if row[5] else None,
                    'status': row[6],
                    'data_source': row[7]
                })

            return items

        except Exception as e:
            logger.error(f"查询新股列表失败: {e}")
            raise QueryError(
                "查询新股列表失败",
                error_code="NEW_STOCKS_QUERY_FAILED",
                reason=str(e)
            )

    def count_new_stocks(
        self,
        start_date: str,
        end_date: str,
        market: Optional[str] = None
    ) -> int:
        """
        统计指定日期范围内上市的新股数量

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            market: 市场类型筛选（可选）

        Returns:
            新股数量

        Examples:
            >>> repo = StockBasicRepository()
            >>> count = repo.count_new_stocks('2024-01-01', '2024-12-31')
            >>> print(f"2024年新上市股票: {count}只")
        """
        try:
            query = f"""
                SELECT COUNT(*) as count
                FROM {self.TABLE_NAME}
                WHERE list_date >= %s AND list_date <= %s
            """
            params = [start_date, end_date]

            if market:
                query += " AND market = %s"
                params.append(market)

            result = self.execute_query(query, tuple(params))
            count = result[0][0] if result else 0
            logger.debug(f"新股数量: {count} ({start_date} ~ {end_date})")
            return count

        except Exception as e:
            logger.error(f"统计新股数量失败: {e}")
            raise QueryError(
                "统计新股数量失败",
                error_code="NEW_STOCKS_COUNT_FAILED",
                reason=str(e)
            )

    def get_new_stocks_statistics(
        self,
        start_date: str,
        end_date: str
    ) -> Dict:
        """
        获取新股统计信息

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            统计信息字典

        Examples:
            >>> repo = StockBasicRepository()
            >>> stats = repo.get_new_stocks_statistics('2024-01-01', '2024-12-31')
            >>> print(f"市场分布: {stats['market_distribution']}")
        """
        try:
            from datetime import datetime, timedelta

            # 总数
            total_count = self.count_new_stocks(start_date, end_date)

            # 市场分布
            market_query = f"""
                SELECT market, COUNT(*) as count
                FROM {self.TABLE_NAME}
                WHERE list_date >= %s AND list_date <= %s
                GROUP BY market
                ORDER BY count DESC
            """
            market_result = self.execute_query(market_query, (start_date, end_date))
            market_distribution = {row[0]: row[1] for row in market_result}

            # 行业分布（取前10）
            industry_query = f"""
                SELECT industry, COUNT(*) as count
                FROM {self.TABLE_NAME}
                WHERE list_date >= %s AND list_date <= %s
                  AND industry IS NOT NULL
                GROUP BY industry
                ORDER BY count DESC
                LIMIT 10
            """
            industry_result = self.execute_query(industry_query, (start_date, end_date))
            industry_distribution = {row[0]: row[1] for row in industry_result}

            # 计算不同时间段的新股数量
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

            # 最近7天
            recent_7_start = (end_date_obj - timedelta(days=7)).strftime('%Y-%m-%d')
            recent_7_days = self.count_new_stocks(recent_7_start, end_date)

            # 最近30天
            recent_30_start = (end_date_obj - timedelta(days=30)).strftime('%Y-%m-%d')
            recent_30_days = self.count_new_stocks(recent_30_start, end_date)

            # 最近90天
            recent_90_start = (end_date_obj - timedelta(days=90)).strftime('%Y-%m-%d')
            recent_90_days = self.count_new_stocks(recent_90_start, end_date)

            stats = {
                'total_count': total_count,
                'market_distribution': market_distribution,
                'industry_distribution': industry_distribution,
                'recent_7_days': recent_7_days,
                'recent_30_days': recent_30_days,
                'recent_90_days': recent_90_days
            }

            logger.debug(f"新股统计: 总数={total_count}, 市场分布={len(market_distribution)}, "
                        f"最近7天={recent_7_days}, 最近30天={recent_30_days}")

            return stats

        except Exception as e:
            logger.error(f"获取新股统计信息失败: {e}")
            raise QueryError(
                "获取新股统计信息失败",
                error_code="NEW_STOCKS_STATISTICS_FAILED",
                reason=str(e)
            )

    def get_full_by_ts_code(self, ts_code: str) -> Optional[Dict]:
        """
        按 ts_code 查询股票完整信息（含 Tushare 扩展字段）

        Args:
            ts_code: Tushare 标准代码（如 '000001.SZ'）

        Returns:
            含全部字段的股票信息字典，不存在则返回 None

        Examples:
            >>> repo = StockBasicRepository()
            >>> stock = repo.get_full_by_ts_code('000001.SZ')
            >>> print(stock['fullname'])
            '平安银行股份有限公司'
        """
        try:
            query = f"""
                SELECT id, code, name, market, industry, area,
                       list_date, delist_date, status, data_source,
                       ts_code, symbol, fullname, enname, cnspell,
                       exchange, curr_type, list_status, is_hs,
                       act_name, act_ent_type,
                       updated_at, created_at
                FROM {self.TABLE_NAME}
                WHERE ts_code = %s
            """
            result = self.execute_query(query, (ts_code,))
            if result:
                return self._row_to_full_dict(result[0])
            # 尝试用 code 字段匹配（兼容纯数字格式）
            pure_code = ts_code.split('.')[0] if '.' in ts_code else ts_code
            query2 = f"""
                SELECT id, code, name, market, industry, area,
                       list_date, delist_date, status, data_source,
                       ts_code, symbol, fullname, enname, cnspell,
                       exchange, curr_type, list_status, is_hs,
                       act_name, act_ent_type,
                       updated_at, created_at
                FROM {self.TABLE_NAME}
                WHERE code = %s
            """
            result2 = self.execute_query(query2, (pure_code,))
            if result2:
                return self._row_to_full_dict(result2[0])
            logger.debug(f"未找到股票: {ts_code}")
            return None

        except Exception as e:
            logger.error(f"查询股票完整信息失败: ts_code={ts_code}, error={e}")
            raise QueryError(
                "查询股票完整信息失败",
                error_code="STOCK_FULL_INFO_QUERY_FAILED",
                reason=str(e)
            )

    def _row_to_full_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为含完整字段的字典"""
        def fmt_date(v):
            if v is None:
                return None
            if hasattr(v, 'strftime'):
                return v.strftime('%Y-%m-%d')
            return str(v)

        return {
            'id': row[0],
            'code': row[1],
            'name': row[2],
            'market': row[3],
            'industry': row[4],
            'area': row[5],
            'list_date': fmt_date(row[6]),
            'delist_date': fmt_date(row[7]),
            'status': row[8],
            'data_source': row[9],
            'ts_code': row[10],
            'symbol': row[11],
            'fullname': row[12],
            'enname': row[13],
            'cnspell': row[14],
            'exchange': row[15],
            'curr_type': row[16],
            'list_status': row[17],
            'is_hs': row[18],
            'act_name': row[19],
            'act_ent_type': row[20],
            'updated_at': str(row[21]) if row[21] else None,
            'created_at': str(row[22]) if row[22] else None,
        }

    # ==================== 检查操作 ====================

    def exists(self, code: str) -> bool:
        """
        检查股票是否存在

        Args:
            code: 股票代码

        Returns:
            是否存在

        Examples:
            >>> repo = StockBasicRepository()
            >>> exists = repo.exists('000001.SZ')
            >>> print(exists)  # True or False
        """
        try:
            query = f"""
                SELECT EXISTS(
                    SELECT 1 FROM {self.TABLE_NAME} WHERE code = %s
                ) as exists
            """
            result = self.execute_query(query, (code,))
            exists = result[0][0] if result else False  # result[0][0] 表示第一行第一列（EXISTS结果）
            logger.debug(f"股票 {code} 存在: {exists}")
            return exists

        except Exception as e:
            logger.error(f"检查股票存在性失败: code={code}, error={e}")
            raise QueryError(
                "检查股票存在性失败",
                error_code="STOCK_EXISTS_CHECK_FAILED",
                code=code,
                reason=str(e)
            )
