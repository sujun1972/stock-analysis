"""
数据库服务
封装DatabaseManager，提供数据库操作接口
"""

from typing import Optional, List, Dict
import pandas as pd
from datetime import date
from loguru import logger

# 导入旧代码的DatabaseManager
# 使用docker-compose挂载的/app/src目录
from src.database.db_manager import DatabaseManager

# 导入工具函数
from app.utils.data_cleaning import clean_value, clean_records


class DatabaseService:
    """数据库服务类"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化数据库服务

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        self.db = db or DatabaseManager()
        logger.info("✓ DatabaseService initialized")

    def get_stock_list(
        self,
        market: Optional[str] = None,
        status: str = "正常",
        search: Optional[str] = None,
        sort_by: str = "pct_change",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 100
    ) -> Dict:
        """
        获取股票列表（包含实时价格信息）

        Args:
            market: 市场类型
            status: 股票状态
            search: 搜索关键词（股票代码或名称）
            sort_by: 排序字段
            sort_order: 排序方向（asc/desc）
            skip: 跳过记录数
            limit: 返回记录数

        Returns:
            {total: int, data: List[Dict]}
        """
        try:
            # 构建 SQL 查询，左连接实时行情表
            query = """
                SELECT
                    s.code,
                    s.name,
                    s.market,
                    s.industry,
                    s.area,
                    s.list_date,
                    s.status,
                    r.latest_price,
                    r.pct_change,
                    r.change_amount,
                    r.volume,
                    r.amount,
                    r.turnover,
                    r.trade_time
                FROM stock_basic s
                LEFT JOIN stock_realtime r ON s.code = r.code
                WHERE s.status = %s
            """
            params = [status]

            if market:
                query += " AND s.market = %s"
                params.append(market)

            # 添加搜索条件（支持股票代码或名称模糊搜索）
            if search:
                query += " AND (s.code LIKE %s OR s.name LIKE %s)"
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern])

            # 添加排序（防止SQL注入，只允许特定字段）
            allowed_sort_fields = {
                'code': 's.code',
                'name': 's.name',
                'market': 's.market',
                'latest_price': 'r.latest_price',
                'pct_change': 'r.pct_change',
                'change_amount': 'r.change_amount',
                'volume': 'r.volume',
                'amount': 'r.amount'
            }

            sort_field = allowed_sort_fields.get(sort_by, 'r.pct_change')
            sort_direction = 'DESC' if sort_order.lower() == 'desc' else 'ASC'

            # 对于可能为NULL的字段，使用NULLS LAST确保NULL值排在最后
            query += f" ORDER BY {sort_field} {sort_direction} NULLS LAST, s.code ASC"
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, skip])

            # 获取数据
            conn = self.db.get_connection()
            try:
                import pandas as pd
                df = pd.read_sql(query, conn, params=params)

                # 获取总数
                count_query = "SELECT COUNT(*) FROM stock_basic WHERE status = %s"
                count_params = [status]
                if market:
                    count_query += " AND market = %s"
                    count_params.append(market)
                if search:
                    count_query += " AND (code LIKE %s OR name LIKE %s)"
                    count_params.extend([search_pattern, search_pattern])

                cursor = conn.cursor()
                cursor.execute(count_query, count_params)
                total = cursor.fetchone()[0]
                cursor.close()

                # 转换为字典列表
                data = df.to_dict('records')

                # 清理所有 NaN 和 Infinity 值，确保 JSON 可序列化
                data = clean_records(data)

                return {
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                    "data": data
                }
            finally:
                self.db.release_connection(conn)
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise

    def get_stock_info(self, code: str) -> Optional[Dict]:
        """
        获取单只股票信息

        Args:
            code: 股票代码

        Returns:
            股票信息字典
        """
        try:
            df = self.db.get_stock_list()
            stock = df[df['code'] == code]

            if stock.empty:
                return None

            return stock.iloc[0].to_dict()
        except Exception as e:
            logger.error(f"获取股票信息失败 {code}: {e}")
            raise

    def get_daily_data(
        self,
        code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        获取股票日线数据

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            日线数据DataFrame
        """
        try:
            start_str = start_date.strftime('%Y-%m-%d') if start_date else None
            end_str = end_date.strftime('%Y-%m-%d') if end_date else None

            df = self.db.load_daily_data(
                code,
                start_date=start_str,
                end_date=end_str
            )

            logger.info(f"✓ 加载 {code} 日线数据: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取日线数据失败 {code}: {e}")
            raise

    def save_stock_list(self, df: pd.DataFrame) -> int:
        """
        保存股票列表

        Args:
            df: 股票列表DataFrame

        Returns:
            保存的记录数
        """
        try:
            count = self.db.save_stock_list(df)
            logger.info(f"✓ 保存股票列表: {count} 条")
            return count
        except Exception as e:
            logger.error(f"保存股票列表失败: {e}")
            raise

    def save_daily_data(self, df: pd.DataFrame, code: str) -> int:
        """
        保存日线数据

        Args:
            df: 日线数据DataFrame
            code: 股票代码

        Returns:
            保存的记录数
        """
        try:
            count = self.db.save_daily_data(df, code)
            logger.info(f"✓ 保存 {code} 日线数据: {count} 条")
            return count
        except Exception as e:
            logger.error(f"保存日线数据失败 {code}: {e}")
            raise

    # ========== 分时数据相关方法 ==========

    def save_minute_data(self, df: pd.DataFrame, code: str, period: str, trade_date: str) -> int:
        """
        保存分时数据到数据库

        Args:
            df: 包含分时数据的DataFrame
            code: 股票代码
            period: 分时周期
            trade_date: 交易日期

        Returns:
            插入的记录数
        """
        try:
            count = self.db.save_minute_data(df, code, period, trade_date)
            logger.info(f"✓ 保存 {code} {period}分钟数据: {count} 条")
            return count
        except Exception as e:
            logger.error(f"保存分时数据失败 {code}: {e}")
            raise

    def load_minute_data(self, code: str, period: str, trade_date: str) -> pd.DataFrame:
        """
        从数据库加载分时数据

        Args:
            code: 股票代码
            period: 分时周期
            trade_date: 交易日期

        Returns:
            包含分时数据的DataFrame
        """
        try:
            df = self.db.load_minute_data(code, period, trade_date)
            logger.info(f"✓ 加载 {code} {period}分钟数据: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"加载分时数据失败 {code}: {e}")
            raise

    def check_minute_data_complete(self, code: str, period: str, trade_date: str) -> dict:
        """
        检查分时数据是否完整

        Returns:
            {
                'is_complete': bool,
                'record_count': int,
                'expected_count': int,
                'completeness': float
            }
        """
        try:
            return self.db.check_minute_data_complete(code, period, trade_date)
        except Exception as e:
            logger.error(f"检查数据完整性失败 {code}: {e}")
            return {
                'is_complete': False,
                'record_count': 0,
                'expected_count': 0,
                'completeness': 0
            }

    def is_trading_day(self, trade_date: str) -> bool:
        """
        检查是否为交易日

        Args:
            trade_date: 日期字符串 (YYYY-MM-DD)

        Returns:
            是否为交易日
        """
        try:
            return self.db.is_trading_day(trade_date)
        except Exception as e:
            logger.warning(f"检查交易日失败: {e}")
            return True  # 默认为交易日

    async def get_stock_realtime(self, code: str) -> Optional[Dict]:
        """
        获取单只股票的实时行情数据

        Args:
            code: 股票代码

        Returns:
            实时行情数据字典，不存在则返回None
        """
        try:
            import asyncio

            query = """
                SELECT
                    code, name, latest_price, open, high, low, pre_close,
                    volume, amount, pct_change, change_amount, turnover,
                    amplitude, trade_time, updated_at
                FROM stock_realtime
                WHERE code = %s
            """

            result = await asyncio.to_thread(
                self.db._execute_query,
                query,
                (code,)
            )

            if result and len(result) > 0:
                row = result[0]
                return {
                    'code': row[0],
                    'name': row[1],
                    'latest_price': float(row[2]) if row[2] else None,
                    'open': float(row[3]) if row[3] else None,
                    'high': float(row[4]) if row[4] else None,
                    'low': float(row[5]) if row[5] else None,
                    'pre_close': float(row[6]) if row[6] else None,
                    'volume': int(row[7]) if row[7] else None,
                    'amount': float(row[8]) if row[8] else None,
                    'pct_change': float(row[9]) if row[9] else None,
                    'change_amount': float(row[10]) if row[10] else None,
                    'turnover': float(row[11]) if row[11] else None,
                    'amplitude': float(row[12]) if row[12] else None,
                    'trade_time': row[13],
                    'updated_at': row[14]
                }

            return None

        except Exception as e:
            logger.error(f"获取股票实时数据失败 ({code}): {e}")
            raise

    async def get_realtime_oldest_update(self, codes: Optional[List[str]] = None):
        """
        获取实时数据表中最旧的更新时间

        注意：只返回有效数据的更新时间（latest_price > 0）
        如果数据存在但价格为0或NULL，视为无效数据，返回None以触发刷新

        Args:
            codes: 股票代码列表（可选），如果提供则只查询这些股票

        Returns:
            datetime: 最旧的更新时间，如果没有数据则返回None
        """
        try:
            import asyncio

            if codes and len(codes) > 0:
                # 查询指定股票的最旧更新时间（只统计有效数据）
                placeholders = ','.join(['%s'] * len(codes))
                query = f"""
                    SELECT MIN(updated_at)
                    FROM stock_realtime
                    WHERE code IN ({placeholders})
                      AND latest_price IS NOT NULL
                      AND latest_price > 0
                """
                result = await asyncio.to_thread(
                    self.db._execute_query,
                    query,
                    tuple(codes)
                )
            else:
                # 查询所有股票的最旧更新时间（只统计有效数据）
                query = """
                    SELECT MIN(updated_at)
                    FROM stock_realtime
                    WHERE latest_price IS NOT NULL
                      AND latest_price > 0
                """
                result = await asyncio.to_thread(
                    self.db._execute_query,
                    query
                )

            if result and len(result) > 0 and result[0][0]:
                return result[0][0]

            return None

        except Exception as e:
            logger.error(f"获取最旧更新时间失败: {e}")
            return None

    def get_connection(self):
        """获取数据库连接"""
        return self.db.get_connection()

    def release_connection(self, conn):
        """释放数据库连接"""
        return self.db.release_connection(conn)

    # 注意：不应该在 __del__ 中关闭连接池
    # DatabaseManager 是单例，每个请求创建 DatabaseService 实例时共享同一连接池。
    # 如果在 __del__ 中关闭连接池，会导致后续请求无法使用数据库连接。
    # 连接池应该在整个应用生命周期中保持打开，由应用关闭时统一清理。
    # def __del__(self):
    #     """析构函数"""
    #     if hasattr(self, 'db'):
    #         self.db.close_all_connections()
