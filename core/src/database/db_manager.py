#!/usr/bin/env python3
"""
数据库管理模块 (重构版本)

使用单例模式确保全局只有一个数据库连接池实例。
采用单一职责原则，将功能拆分为多个专门的管理器。
"""

import logging
import os
import threading
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import pandas as pd
from loguru import logger
import psycopg2

# 导入专门的管理器
from .connection_pool_manager import ConnectionPoolManager

if TYPE_CHECKING:
    from psycopg2.extensions import connection
from .table_manager import TableManager
from .data_insert_manager import DataInsertManager
from .data_query_manager import DataQueryManager

# 导入异常类
try:
    from ..exceptions import DatabaseError
except ImportError:
    from src.exceptions import DatabaseError

# 尝试加载配置
try:
    from ..config import DATABASE_CONFIG
except ImportError:
    try:
        from config import DATABASE_CONFIG
    except ImportError:
        # 默认配置（从环境变量读取，支持 Docker 环境）
        DATABASE_CONFIG = {
            'host': os.getenv('DATABASE_HOST', 'localhost'),
            'port': int(os.getenv('DATABASE_PORT', '5432')),
            'database': os.getenv('DATABASE_NAME', 'stock_analysis'),
            'user': os.getenv('DATABASE_USER', 'stock_user'),
            'password': os.getenv('DATABASE_PASSWORD', 'stock_password_123')
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

    def __new__(cls, config: Optional[Dict[str, Any]] = None) -> 'DatabaseManager':
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

    def get_connection(self) -> 'connection':
        """从连接池获取连接"""
        return self.pool_manager.get_connection()

    def release_connection(self, conn: 'connection') -> None:
        """释放连接回连接池"""
        self.pool_manager.release_connection(conn)

    def close_all_connections(self) -> None:
        """关闭所有连接"""
        self.pool_manager.close_all_connections()

    def get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态信息"""
        return self.pool_manager.get_pool_status()

    # ==================== 通用查询方法 ====================

    def _execute_query(self, query: str, params: tuple = ()) -> List[tuple]:
        """
        执行查询并返回结果

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            查询结果列表（tuple列表）

        Raises:
            DatabaseError: 数据库操作失败
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()

        except psycopg2.OperationalError as e:
            # 连接错误(网络中断、数据库宕机等)
            logger.error(f"数据库连接错误: {e}")
            raise DatabaseError(
                "数据库连接失败",
                error_code="DB_CONNECTION_ERROR",
                query=query[:100],
                error_detail=str(e)
            ) from e

        except psycopg2.ProgrammingError as e:
            # SQL语法错误
            logger.error(f"SQL语法错误: {e}")
            raise DatabaseError(
                "SQL语句错误",
                error_code="DB_SYNTAX_ERROR",
                query=query[:100],
                error_detail=str(e)
            ) from e

        except psycopg2.DataError as e:
            # 数据类型错误
            logger.error(f"数据类型错误: {e}")
            raise DatabaseError(
                "数据类型不匹配",
                error_code="DB_DATA_TYPE_ERROR",
                query=query[:100],
                params=str(params),
                error_detail=str(e)
            ) from e

        except DatabaseError:
            # 已知的业务异常,直接向上传播
            raise

        except Exception as e:
            # 未预期的异常,转换为DatabaseError
            logger.error(f"查询执行失败(未预期异常): {e}")
            raise DatabaseError(
                f"数据库查询失败: {str(e)}",
                error_code="DB_QUERY_FAILED",
                query=query[:100]
            ) from e

        finally:
            if conn:
                self.release_connection(conn)

    def _execute_update(self, query: str, params: tuple = ()) -> int:
        """
        执行更新操作（INSERT, UPDATE, DELETE）

        Args:
            query: SQL语句
            params: 参数

        Returns:
            受影响的行数

        Raises:
            DatabaseError: 数据库操作失败
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount

        except psycopg2.OperationalError as e:
            # 连接错误
            if conn:
                conn.rollback()
            logger.error(f"数据库连接错误: {e}")
            raise DatabaseError(
                "数据库连接失败",
                error_code="DB_CONNECTION_ERROR",
                query=query[:100],
                error_detail=str(e)
            ) from e

        except psycopg2.ProgrammingError as e:
            # SQL语法错误
            if conn:
                conn.rollback()
            logger.error(f"SQL语法错误: {e}")
            raise DatabaseError(
                "SQL语句错误",
                error_code="DB_SYNTAX_ERROR",
                query=query[:100],
                error_detail=str(e)
            ) from e

        except psycopg2.IntegrityError as e:
            # 完整性约束错误（违反唯一性、外键等）
            if conn:
                conn.rollback()
            logger.error(f"数据完整性错误: {e}")
            raise DatabaseError(
                "数据完整性约束违反",
                error_code="DB_INTEGRITY_ERROR",
                query=query[:100],
                error_detail=str(e)
            ) from e

        except psycopg2.DataError as e:
            # 数据类型错误
            if conn:
                conn.rollback()
            logger.error(f"数据类型错误: {e}")
            raise DatabaseError(
                "数据类型不匹配",
                error_code="DB_DATA_TYPE_ERROR",
                query=query[:100],
                params=str(params),
                error_detail=str(e)
            ) from e

        except DatabaseError:
            # 已知的业务异常,先回滚再向上传播
            if conn:
                conn.rollback()
            raise

        except Exception as e:
            # 未预期的异常
            if conn:
                conn.rollback()
            logger.error(f"更新执行失败(未预期异常): {e}")
            raise DatabaseError(
                f"数据库更新失败: {str(e)}",
                error_code="DB_UPDATE_FAILED",
                query=query[:100]
            ) from e

        finally:
            if conn:
                self.release_connection(conn)

    # ==================== 表结构管理（委托给 TableManager） ====================

    def init_database(self) -> None:
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
    def reset_instance(cls) -> None:
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
    logger.info("\n" + "="*60)
    logger.info("测试数据库管理模块（重构版本 - 单例模式）")
    logger.info("="*60)

    try:
        # 测试单例模式
        logger.info("\n1. 测试单例模式...")
        db1 = DatabaseManager()
        db2 = DatabaseManager()
        db3 = get_database()

        assert db1 is db2, "DatabaseManager 应该是单例"
        assert db2 is db3, "get_database() 应返回同一实例"
        logger.success("   ✓ 单例模式测试通过（db1 is db2 is db3）")

        logger.info("\n2. 测试连接池状态...")
        status = db1.get_pool_status()
        logger.success(f"   ✓ 连接池状态: {status}")

        logger.info("\n3. 初始化数据库表结构...")
        db1.init_database()
        logger.success("   ✓ 表结构初始化成功")

        logger.success("\n✅ 数据库管理模块测试通过（重构版本）")
        logger.info("   - 单例模式正常工作")
        logger.info("   - 全局只有一个连接池实例")
        logger.info("   - 功能已拆分为4个专门的管理器")
        logger.info("   - 避免了连接资源浪费")

    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
