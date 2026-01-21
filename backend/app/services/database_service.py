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


class DatabaseService:
    """数据库服务类"""

    def __init__(self):
        """初始化数据库连接"""
        self.db = DatabaseManager()
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
                import math
                def clean_value(val):
                    """清理值，将 NaN/Infinity 替换为 None"""
                    if val is None:
                        return None
                    if isinstance(val, float):
                        if math.isnan(val) or math.isinf(val):
                            return None
                    return val

                # 清理每条记录中的所有值
                data = [
                    {k: clean_value(v) for k, v in record.items()}
                    for record in data
                ]

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

    def get_connection(self):
        """获取数据库连接"""
        return self.db.get_connection()

    def release_connection(self, conn):
        """释放数据库连接"""
        return self.db.release_connection(conn)

    def __del__(self):
        """析构函数"""
        if hasattr(self, 'db'):
            self.db.close_all_connections()
