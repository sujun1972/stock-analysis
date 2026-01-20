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
        skip: int = 0,
        limit: int = 100
    ) -> Dict:
        """
        获取股票列表

        Args:
            market: 市场类型
            status: 股票状态
            skip: 跳过记录数
            limit: 返回记录数

        Returns:
            {total: int, data: List[Dict]}
        """
        try:
            df = self.db.get_stock_list(market=market, status=status)
            total = len(df)

            # 分页
            df_page = df.iloc[skip:skip + limit]

            return {
                "total": total,
                "skip": skip,
                "limit": limit,
                "data": df_page.to_dict('records')
            }
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

    def __del__(self):
        """析构函数"""
        if hasattr(self, 'db'):
            self.db.close_all_connections()
