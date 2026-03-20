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

            if limit:
                query += f" LIMIT %s"
                params.append(limit)

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
