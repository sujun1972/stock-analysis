#!/usr/bin/env python3
"""
数据库管理模块 (重构版本)

使用单例模式确保全局只有一个数据库连接池实例。
采用单一职责原则，将功能拆分为多个专门的管理器。
"""

import logging
import threading
from typing import Optional, List, Dict, Any
import pandas as pd

# 导入专门的管理器
from .connection_pool_manager import ConnectionPoolManager
from .table_manager import TableManager
from .data_insert_manager import DataInsertManager
from .data_query_manager import DataQueryManager

# 尝试加载配置
try:
    from ..config.config import DATABASE_CONFIG
except ImportError:
    try:
        from config.config import DATABASE_CONFIG
    except ImportError:
        # 默认配置（仅在无法导入时使用）
        DATABASE_CONFIG = {
            'host': 'localhost',
            'port': 5432,
            'database': 'stock_analysis',
            'user': 'stock_user',
            'password': 'stock_password_123'
        }

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    数据库管理器（重构版本 - 单例模式）

    采用组合模式，将功能委托给专门的管理器：
    - ConnectionPoolManager: 连接池管理
    - TableManager: 表结构管理
    - DataInsertManager: 数据插入操作
    - DataQueryManager: 数据查询操作

    全局只创建一个实例和一个连接池，避免连接资源浪费。
    线程安全，支持多线程并发访问。
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, config: Optional[Dict[str, Any]] = None):
        """
        单例模式实现

        确保全局只有一个 DatabaseManager 实例
        """
        if cls._instance is None:
            with cls._lock:
                # 双重检查锁定模式
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据库管理器

        注意：由于单例模式，此方法在全局只执行一次

        Args:
            config: 数据库配置字典，如果为None则使用默认配置
        """
        # 避免重复初始化
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            self.config = config or DATABASE_CONFIG

            # 初始化各个管理器
            self.pool_manager = ConnectionPoolManager(self.config)
            self.table_manager = TableManager(self.pool_manager)
            self.insert_manager = DataInsertManager(self.pool_manager)
            self.query_manager = DataQueryManager(self.pool_manager)

            self._initialized = True
            logger.info("DatabaseManager 单例已创建（重构版本）")

    # ==================== 连接池管理（委托给 ConnectionPoolManager） ====================

    def get_connection(self):
        """从连接池获取连接"""
        return self.pool_manager.get_connection()

    def release_connection(self, conn):
        """释放连接回连接池"""
        self.pool_manager.release_connection(conn)

    def close_all_connections(self):
        """关闭所有连接"""
        self.pool_manager.close_all_connections()

    def get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态信息"""
        return self.pool_manager.get_pool_status()

    # ==================== 表结构管理（委托给 TableManager） ====================

    def init_database(self):
        """初始化数据库表结构"""
        self.table_manager.init_all_tables()

    # ==================== 数据插入操作（委托给 DataInsertManager） ====================

    def save_stock_list(self, df: pd.DataFrame, data_source: str = 'akshare') -> int:
        """保存股票列表到数据库"""
        return self.insert_manager.save_stock_list(df, data_source)

    def save_daily_data(self, df: pd.DataFrame, stock_code: str) -> int:
        """保存股票日线数据到数据库"""
        return self.insert_manager.save_daily_data(df, stock_code)

    def save_realtime_quote_single(self, quote: dict, data_source: str = 'akshare') -> int:
        """保存单条实时行情数据到数据库"""
        return self.insert_manager.save_realtime_quote_single(quote, data_source)

    def save_realtime_quotes(self, df: pd.DataFrame, data_source: str = 'akshare') -> int:
        """保存实时行情数据到数据库"""
        return self.insert_manager.save_realtime_quotes(df, data_source)

    def save_minute_data(self, df: pd.DataFrame, code: str, period: str, trade_date: str) -> int:
        """保存分时数据到数据库"""
        return self.insert_manager.save_minute_data(df, code, period, trade_date)

    # ==================== 数据查询操作（委托给 DataQueryManager） ====================

    def load_daily_data(self, stock_code: str,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """从数据库加载股票日线数据"""
        return self.query_manager.load_daily_data(stock_code, start_date, end_date)

    def get_stock_list(self, market: Optional[str] = None,
                      status: str = '正常') -> pd.DataFrame:
        """获取股票列表"""
        return self.query_manager.get_stock_list(market, status)

    def get_oldest_realtime_stocks(self, limit: int = 100) -> List[str]:
        """获取更新时间最早的N只股票代码"""
        return self.query_manager.get_oldest_realtime_stocks(limit)

    def check_daily_data_completeness(self, code: str, start_date: str, end_date: str,
                                     min_expected_days: int = None) -> Dict[str, Any]:
        """检查股票的日线数据是否完整"""
        return self.query_manager.check_daily_data_completeness(code, start_date, end_date, min_expected_days)

    def load_minute_data(self, code: str, period: str, trade_date: str) -> pd.DataFrame:
        """从数据库加载分时数据"""
        return self.query_manager.load_minute_data(code, period, trade_date)

    def check_minute_data_complete(self, code: str, period: str, trade_date: str) -> dict:
        """检查分时数据是否完整"""
        return self.query_manager.check_minute_data_complete(code, period, trade_date)

    def is_trading_day(self, trade_date: str) -> bool:
        """检查是否为交易日"""
        return self.query_manager.is_trading_day(trade_date)

    # ==================== 单例管理 ====================

    def __del__(self):
        """析构函数（单例模式下很少触发）"""
        # 单例模式下不应频繁触发析构
        # 连接池由单例实例管理，不在此处关闭
        pass

    @classmethod
    def reset_instance(cls):
        """
        重置单例实例（仅用于测试）

        警告：此方法仅应在测试环境中使用，
        生产环境中调用可能导致连接泄漏
        """
        with cls._lock:
            if cls._instance is not None:
                # 关闭现有连接池
                if hasattr(cls._instance, 'pool_manager') and cls._instance.pool_manager:
                    cls._instance.pool_manager.close_all_connections()

                cls._instance = None
                cls._initialized = False
                logger.info("DatabaseManager 单例已重置")

    @classmethod
    def get_instance(cls, config: Optional[Dict[str, Any]] = None) -> 'DatabaseManager':
        """
        获取 DatabaseManager 单例实例（推荐使用）

        Args:
            config: 数据库配置（仅在首次调用时生效）

        Returns:
            DatabaseManager 实例
        """
        return cls(config)


# ==================== 便捷函数 ====================

def get_db_manager() -> DatabaseManager:
    """
    获取数据库管理器实例（已废弃，建议使用 get_database）

    Returns:
        DatabaseManager 单例实例
    """
    return DatabaseManager()


def get_database(config: Optional[Dict[str, Any]] = None) -> DatabaseManager:
    """
    获取数据库管理器单例实例（推荐使用）

    Args:
        config: 数据库配置（仅在首次调用时生效）

    Returns:
        DatabaseManager 实例

    Example:
        from database.db_manager import get_database

        db = get_database()
        stocks = db.load_daily_data('000001', '20200101', '20231231')
    """
    return DatabaseManager.get_instance(config)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试数据库连接和初始化
    print("\n" + "="*60)
    print("测试数据库管理模块（重构版本 - 单例模式）")
    print("="*60)

    try:
        # 测试单例模式
        print("\n1. 测试单例模式...")
        db1 = DatabaseManager()
        db2 = DatabaseManager()
        db3 = get_database()

        assert db1 is db2, "DatabaseManager 应该是单例"
        assert db2 is db3, "get_database() 应返回同一实例"
        print("   ✓ 单例模式测试通过（db1 is db2 is db3）")

        print("\n2. 测试连接池状态...")
        status = db1.get_pool_status()
        print(f"   ✓ 连接池状态: {status}")

        print("\n3. 初始化数据库表结构...")
        db1.init_database()
        print("   ✓ 表结构初始化成功")

        print("\n✅ 数据库管理模块测试通过（重构版本）")
        print("   - 单例模式正常工作")
        print("   - 全局只有一个连接池实例")
        print("   - 功能已拆分为4个专门的管理器")
        print("   - 避免了连接资源浪费")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
