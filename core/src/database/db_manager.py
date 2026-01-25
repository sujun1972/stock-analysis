#!/usr/bin/env python3
"""
数据库管理模块
负责数据库连接、表创建和数据存储

使用单例模式确保全局只有一个数据库连接池实例，
避免连接池泛滥导致数据库连接耗尽。
"""

import psycopg2
from psycopg2 import pool, extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import logging
import threading

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
    数据库管理器（单例模式）

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
            self.connection_pool = None
            self._init_connection_pool()
            self._initialized = True
            logger.info("DatabaseManager 单例已创建")

    def _init_connection_pool(self):
        """初始化连接池"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password']
            )
            logger.info("数据库连接池创建成功")
        except Exception as e:
            logger.error(f"数据库连接池创建失败: {e}")
            raise

    def get_connection(self):
        """从连接池获取连接"""
        return self.connection_pool.getconn()

    def release_connection(self, conn):
        """释放连接回连接池"""
        self.connection_pool.putconn(conn)

    def close_all_connections(self):
        """关闭所有连接"""
        if self.connection_pool:
            try:
                self.connection_pool.closeall()
                logger.info("所有数据库连接已关闭")
            except Exception as e:
                # 连接池可能已经关闭，忽略错误
                logger.debug(f"关闭连接池时出现异常（可忽略）: {e}")

    def _execute_query(self, query: str, params: Optional[tuple] = None):
        """
        执行查询并返回结果

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            查询结果列表
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            raise
        finally:
            if conn:
                self.release_connection(conn)

    def _execute_update(self, query: str, params: Optional[tuple] = None):
        """
        执行更新操作（INSERT, UPDATE, DELETE）

        Args:
            query: SQL语句
            params: 参数

        Returns:
            影响的行数
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"更新执行失败: {e}")
            raise
        finally:
            if conn:
                self.release_connection(conn)

    def init_database(self):
        """初始化数据库表结构"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 1. 创建股票基本信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_info (
                    code VARCHAR(20) PRIMARY KEY,
                    name VARCHAR(100),
                    market VARCHAR(20),
                    list_date DATE,
                    industry VARCHAR(100),
                    area VARCHAR(100),
                    status VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("✓ 股票基本信息表创建/验证完成")

            # 2. 创建股票日线数据表（时序数据）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_daily (
                    code VARCHAR(20) NOT NULL,
                    date DATE NOT NULL,
                    open DECIMAL(10, 2),
                    high DECIMAL(10, 2),
                    low DECIMAL(10, 2),
                    close DECIMAL(10, 2),
                    volume BIGINT,
                    amount DECIMAL(20, 2),
                    amplitude DECIMAL(10, 2),
                    pct_change DECIMAL(10, 2),
                    change DECIMAL(10, 2),
                    turnover DECIMAL(10, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (code, date)
                );
            """)
            logger.info("✓ 股票日线数据表创建/验证完成")

            # 3. 创建时序优化索引（如果使用TimescaleDB）
            try:
                # 检查是否支持TimescaleDB
                cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'timescaledb';")
                if cursor.fetchone():
                    # 将stock_daily转换为时序表
                    cursor.execute("""
                        SELECT create_hypertable('stock_daily', 'date',
                            if_not_exists => TRUE,
                            migrate_data => TRUE
                        );
                    """)
                    logger.info("✓ TimescaleDB时序表优化完成")
            except Exception as e:
                logger.warning(f"TimescaleDB优化跳过: {e}")

            # 4. 创建股票特征表（用于存储计算后的技术指标）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_features (
                    code VARCHAR(20) NOT NULL,
                    date DATE NOT NULL,
                    feature_type VARCHAR(50) NOT NULL,
                    feature_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (code, date, feature_type)
                );
            """)
            logger.info("✓ 股票特征表创建/验证完成")

            # 5. 创建模型预测表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_predictions (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(20) NOT NULL,
                    pred_date DATE NOT NULL,
                    model_name VARCHAR(100),
                    model_version VARCHAR(50),
                    prediction DECIMAL(10, 4),
                    confidence DECIMAL(5, 4),
                    actual_return DECIMAL(10, 4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (code, pred_date, model_name, model_version)
                );
            """)
            logger.info("✓ 模型预测表创建/验证完成")

            # 6. 创建回测结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id SERIAL PRIMARY KEY,
                    strategy_name VARCHAR(100),
                    start_date DATE,
                    end_date DATE,
                    initial_capital DECIMAL(20, 2),
                    final_value DECIMAL(20, 2),
                    total_return DECIMAL(10, 4),
                    sharpe_ratio DECIMAL(10, 4),
                    max_drawdown DECIMAL(10, 4),
                    win_rate DECIMAL(10, 4),
                    config JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("✓ 回测结果表创建/验证完成")

            # 7. 创建分时数据表（新增）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_minute (
                    code VARCHAR(20) NOT NULL,
                    trade_time TIMESTAMP NOT NULL,
                    period VARCHAR(10) NOT NULL,
                    open DECIMAL(10, 3),
                    high DECIMAL(10, 3),
                    low DECIMAL(10, 3),
                    close DECIMAL(10, 3),
                    volume BIGINT,
                    amount DECIMAL(20, 2),
                    pct_change DECIMAL(10, 3),
                    change_amount DECIMAL(10, 3),
                    data_source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (code, trade_time, period)
                );
            """)
            logger.info("✓ 分时数据表创建/验证完成")

            # 8. 创建分时数据元数据表（用于完整性检查）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_minute_meta (
                    code VARCHAR(20) NOT NULL,
                    trade_date DATE NOT NULL,
                    period VARCHAR(10) NOT NULL,
                    is_complete BOOLEAN DEFAULT FALSE,
                    record_count INTEGER DEFAULT 0,
                    expected_count INTEGER,
                    first_time TIMESTAMP,
                    last_time TIMESTAMP,
                    data_source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (code, trade_date, period)
                );
            """)
            logger.info("✓ 分时数据元数据表创建/验证完成")

            # 9. 创建交易日历表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_calendar (
                    trade_date DATE PRIMARY KEY,
                    is_trading_day BOOLEAN DEFAULT TRUE,
                    market VARCHAR(20) DEFAULT 'A股',
                    reason VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("✓ 交易日历表创建/验证完成")

            # 10. 创建实时行情表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_realtime (
                    code VARCHAR(20) PRIMARY KEY,
                    name VARCHAR(100),
                    latest_price DECIMAL(10, 2),
                    open DECIMAL(10, 2),
                    high DECIMAL(10, 2),
                    low DECIMAL(10, 2),
                    pre_close DECIMAL(10, 2),
                    volume BIGINT,
                    amount DECIMAL(20, 2),
                    pct_change DECIMAL(10, 2),
                    change_amount DECIMAL(10, 2),
                    turnover DECIMAL(10, 2),
                    amplitude DECIMAL(10, 2),
                    data_source VARCHAR(50),
                    trade_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("✓ 实时行情表创建/验证完成")

            # 11. 创建常用索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_daily_code ON stock_daily(code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_daily_date ON stock_daily(date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_features_code_date ON stock_features(code, date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_code_date ON stock_predictions(code, pred_date);")

            # 分时数据索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_minute_code_time ON stock_minute(code, trade_time DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_minute_time ON stock_minute(trade_time DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_minute_period ON stock_minute(period);")

            # 分时元数据索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_minute_meta_date ON stock_minute_meta(trade_date DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_minute_meta_complete ON stock_minute_meta(is_complete);")

            # 交易日历索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_date ON trading_calendar(trade_date DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_trading ON trading_calendar(is_trading_day);")

            logger.info("✓ 索引创建完成")

            # 12. TimescaleDB优化分时数据表（可选）
            try:
                cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'timescaledb';")
                if cursor.fetchone():
                    # 将stock_minute转换为时序表
                    cursor.execute("""
                        SELECT create_hypertable('stock_minute', 'trade_time',
                            chunk_time_interval => INTERVAL '7 days',
                            if_not_exists => TRUE,
                            migrate_data => TRUE
                        );
                    """)
                    logger.info("✓ 分时数据TimescaleDB优化完成")

                    # 设置压缩策略
                    cursor.execute("""
                        ALTER TABLE stock_minute SET (
                            timescaledb.compress,
                            timescaledb.compress_segmentby = 'code, period',
                            timescaledb.compress_orderby = 'trade_time DESC'
                        );
                    """)

                    # 自动压缩30天前的数据
                    cursor.execute("""
                        SELECT add_compression_policy('stock_minute', INTERVAL '30 days');
                    """)
                    logger.info("✓ 分时数据压缩策略设置完成")
            except Exception as e:
                logger.warning(f"TimescaleDB分时数据优化跳过: {e}")

            conn.commit()
            logger.info("\n✅ 数据库初始化完成！")

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ 数据库初始化失败: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self.release_connection(conn)

    def save_stock_list(self, df: pd.DataFrame, data_source: str = 'akshare') -> int:
        """
        保存股票列表到数据库

        Args:
            df: 包含股票信息的DataFrame
            data_source: 数据源名称 (akshare 或 tushare)

        Returns:
            插入/更新的记录数
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 准备数据
            records = []
            for _, row in df.iterrows():
                records.append((
                    row.get('code', row.get('股票代码')),
                    row.get('name', row.get('股票名称')),
                    row.get('market', row.get('市场类型')),
                    row.get('industry', row.get('行业')),
                    row.get('area', row.get('地域')),
                    row.get('list_date', row.get('上市日期')),
                    row.get('delist_date', row.get('退市日期')),
                    row.get('status', '正常'),
                    data_source
                ))

            # 批量插入（冲突时更新）- 使用 stock_basic 表
            insert_query = """
                INSERT INTO stock_basic (code, name, market, industry, area, list_date, delist_date, status, data_source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    market = EXCLUDED.market,
                    industry = EXCLUDED.industry,
                    area = EXCLUDED.area,
                    list_date = EXCLUDED.list_date,
                    delist_date = EXCLUDED.delist_date,
                    status = EXCLUDED.status,
                    data_source = EXCLUDED.data_source,
                    updated_at = CURRENT_TIMESTAMP;
            """

            extras.execute_batch(cursor, insert_query, records, page_size=1000)
            conn.commit()

            count = len(records)
            logger.info(f"✓ 保存股票列表到 stock_basic: {count} 条记录")
            return count

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ 保存股票列表失败: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self.release_connection(conn)

    def save_daily_data(self, df: pd.DataFrame, stock_code: str) -> int:
        """
        保存股票日线数据到数据库

        Args:
            df: 包含OHLCV数据的DataFrame，可能有 trade_date 列或日期索引
            stock_code: 股票代码

        Returns:
            插入/更新的记录数
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 准备数据
            records = []
            for idx, row in df.iterrows():
                # 处理日期 - 优先使用 trade_date 列
                if 'trade_date' in row:
                    date_val = row['trade_date']
                    if isinstance(date_val, str):
                        date_val = datetime.strptime(date_val, '%Y-%m-%d').date()
                    elif isinstance(date_val, pd.Timestamp):
                        date_val = date_val.date()
                    elif not isinstance(date_val, date):
                        # 如果已经是 date 类型，直接使用
                        date_val = pd.to_datetime(date_val).date()
                else:
                    # 使用索引作为日期
                    if isinstance(idx, str):
                        date_val = datetime.strptime(idx, '%Y-%m-%d').date()
                    elif isinstance(idx, pd.Timestamp):
                        date_val = idx.date()
                    else:
                        date_val = idx

                records.append((
                    stock_code,
                    date_val,
                    float(row.get('open', row.get('开盘', 0))),
                    float(row.get('high', row.get('最高', 0))),
                    float(row.get('low', row.get('最低', 0))),
                    float(row.get('close', row.get('收盘', 0))),
                    int(row.get('volume', row.get('成交量', 0))),
                    float(row.get('amount', row.get('成交额', 0))),
                    float(row.get('amplitude', row.get('振幅', 0))),
                    float(row.get('pct_change', row.get('涨跌幅', 0))),
                    float(row.get('change', row.get('涨跌额', row.get('change_amount', 0)))),
                    float(row.get('turnover', row.get('换手率', 0)))
                ))

            # 批量插入（冲突时更新）
            insert_query = """
                INSERT INTO stock_daily
                (code, date, open, high, low, close, volume, amount,
                 amplitude, pct_change, change, turnover)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code, date)
                DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    amount = EXCLUDED.amount,
                    amplitude = EXCLUDED.amplitude,
                    pct_change = EXCLUDED.pct_change,
                    change = EXCLUDED.change,
                    turnover = EXCLUDED.turnover;
            """

            extras.execute_batch(cursor, insert_query, records, page_size=1000)
            conn.commit()

            count = len(records)
            logger.info(f"✓ 保存 {stock_code} 日线数据: {count} 条记录")
            return count

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ 保存 {stock_code} 日线数据失败: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self.release_connection(conn)

    def save_realtime_quote_single(self, quote: dict, data_source: str = 'akshare') -> int:
        """
        保存单条实时行情数据到数据库（用于增量保存）

        Args:
            quote: 包含实时行情数据的字典
            data_source: 数据源名称

        Returns:
            插入/更新的记录数（1或0）
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 辅助函数：安全地转换值，处理 NaN 和 None
            def safe_float(val, default=0.0):
                """安全转换为 float，处理 NaN"""
                if pd.isna(val) or val is None:
                    return default
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default

            def safe_int(val, default=0):
                """安全转换为 int，处理 NaN"""
                if pd.isna(val) or val is None:
                    return default
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return default

            # 准备数据
            record = (
                quote.get('code'),
                quote.get('name', ''),
                safe_float(quote.get('latest_price')),
                safe_float(quote.get('open')),
                safe_float(quote.get('high')),
                safe_float(quote.get('low')),
                safe_float(quote.get('pre_close')),
                safe_int(quote.get('volume')),
                safe_float(quote.get('amount')),
                safe_float(quote.get('pct_change')),
                safe_float(quote.get('change_amount')),
                safe_float(quote.get('turnover')),
                safe_float(quote.get('amplitude')),
                data_source
            )

            # 插入或更新单条记录
            insert_query = """
                INSERT INTO stock_realtime
                (code, name, latest_price, open, high, low, pre_close, volume, amount,
                 pct_change, change_amount, turnover, amplitude, data_source, trade_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (code)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    latest_price = EXCLUDED.latest_price,
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    pre_close = EXCLUDED.pre_close,
                    volume = EXCLUDED.volume,
                    amount = EXCLUDED.amount,
                    pct_change = EXCLUDED.pct_change,
                    change_amount = EXCLUDED.change_amount,
                    turnover = EXCLUDED.turnover,
                    amplitude = EXCLUDED.amplitude,
                    data_source = EXCLUDED.data_source,
                    trade_time = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP;
            """

            cursor.execute(insert_query, record)
            conn.commit()

            return 1

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ 保存单条实时行情数据失败 {quote.get('code', 'Unknown')}: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self.release_connection(conn)

    def save_realtime_quotes(self, df: pd.DataFrame, data_source: str = 'akshare') -> int:
        """
        保存实时行情数据到数据库

        Args:
            df: 包含实时行情数据的DataFrame
            data_source: 数据源名称

        Returns:
            插入/更新的记录数
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 辅助函数：安全地转换值，处理 NaN 和 None
            def safe_float(val, default=0.0):
                """安全转换为 float，处理 NaN"""
                if pd.isna(val) or val is None:
                    return default
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default

            def safe_int(val, default=0):
                """安全转换为 int，处理 NaN"""
                if pd.isna(val) or val is None:
                    return default
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return default

            # 准备数据
            records = []
            for idx, row in df.iterrows():
                records.append((
                    row.get('code', row.get('代码')),
                    row.get('name', row.get('名称')),
                    safe_float(row.get('latest_price', row.get('最新价', row.get('现价')))),
                    safe_float(row.get('open', row.get('今开'))),
                    safe_float(row.get('high', row.get('最高'))),
                    safe_float(row.get('low', row.get('最低'))),
                    safe_float(row.get('pre_close', row.get('昨收'))),
                    safe_int(row.get('volume', row.get('成交量'))),
                    safe_float(row.get('amount', row.get('成交额'))),
                    safe_float(row.get('pct_change', row.get('涨跌幅'))),
                    safe_float(row.get('change_amount', row.get('涨跌额'))),
                    safe_float(row.get('turnover', row.get('换手率'))),
                    safe_float(row.get('amplitude', row.get('振幅'))),
                    data_source
                ))

            # 批量插入（冲突时更新）
            insert_query = """
                INSERT INTO stock_realtime
                (code, name, latest_price, open, high, low, pre_close, volume, amount,
                 pct_change, change_amount, turnover, amplitude, data_source, trade_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (code)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    latest_price = EXCLUDED.latest_price,
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    pre_close = EXCLUDED.pre_close,
                    volume = EXCLUDED.volume,
                    amount = EXCLUDED.amount,
                    pct_change = EXCLUDED.pct_change,
                    change_amount = EXCLUDED.change_amount,
                    turnover = EXCLUDED.turnover,
                    amplitude = EXCLUDED.amplitude,
                    data_source = EXCLUDED.data_source,
                    trade_time = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP;
            """

            extras.execute_batch(cursor, insert_query, records, page_size=1000)
            conn.commit()

            count = len(records)
            logger.info(f"✓ 保存实时行情数据: {count} 条记录")
            return count

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ 保存实时行情数据失败: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self.release_connection(conn)

    def get_oldest_realtime_stocks(self, limit: int = 100) -> List[str]:
        """
        获取更新时间最早的N只股票代码（用于渐进式更新实时行情）

        Args:
            limit: 返回的股票数量

        Returns:
            股票代码列表
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 查询updated_at最早的股票
            query = """
                SELECT s.code
                FROM stock_basic s
                LEFT JOIN stock_realtime r ON s.code = r.code
                WHERE s.status = '正常'
                ORDER BY r.updated_at NULLS FIRST
                LIMIT %s
            """

            cursor.execute(query, (limit,))
            codes = [row[0] for row in cursor.fetchall()]

            logger.info(f"✓ 获取 {len(codes)} 只最早更新的股票代码")
            return codes

        except Exception as e:
            logger.error(f"❌ 获取最旧实时行情股票失败: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self.release_connection(conn)

    def load_daily_data(self, stock_code: str,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        从数据库加载股票日线数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            包含日线数据的DataFrame
        """
        conn = None
        try:
            conn = self.get_connection()

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

            df = pd.read_sql_query(query, conn, params=params, index_col='date', parse_dates=['date'])

            # 确保数值列是正确的类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount',
                              'amplitude', 'pct_change', 'change', 'turnover']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            logger.info(f"✓ 加载 {stock_code} 数据: {len(df)} 条记录")
            return df

        except Exception as e:
            logger.error(f"❌ 加载 {stock_code} 数据失败: {e}")
            raise
        finally:
            if conn:
                self.release_connection(conn)

    def get_stock_list(self, market: Optional[str] = None,
                      status: str = '正常') -> pd.DataFrame:
        """
        获取股票列表

        Args:
            market: 市场类型（可选）
            status: 股票状态（默认为正常）

        Returns:
            股票列表DataFrame
        """
        conn = None
        try:
            conn = self.get_connection()

            query = "SELECT * FROM stock_info WHERE status = %s"
            params = [status]

            if market:
                query += " AND market = %s"
                params.append(market)

            query += " ORDER BY code"

            df = pd.read_sql_query(query, conn, params=params)
            logger.info(f"✓ 获取股票列表: {len(df)} 只股票")
            return df

        except Exception as e:
            logger.error(f"❌ 获取股票列表失败: {e}")
            raise
        finally:
            if conn:
                self.release_connection(conn)

    def check_daily_data_completeness(self, code: str, start_date: str, end_date: str,
                                     min_expected_days: int = None) -> Dict[str, Any]:
        """
        检查股票的日线数据是否完整

        Args:
            code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            min_expected_days: 最小期望交易日数量（可选，如果不提供则不检查）

        Returns:
            Dict包含：
                - has_data: bool, 是否有数据
                - is_complete: bool, 数据是否完整（如果提供了min_expected_days）
                - record_count: int, 实际记录数
                - earliest_date: str, 最早日期
                - latest_date: str, 最新日期
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 转换日期格式 YYYYMMDD -> YYYY-MM-DD
            start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
            end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

            query = """
                SELECT
                    COUNT(*) as record_count,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM stock_daily
                WHERE code = %s
                    AND date >= %s
                    AND date <= %s
            """

            cursor.execute(query, (code, start_date_formatted, end_date_formatted))
            result = cursor.fetchone()

            record_count = result[0] if result else 0
            earliest_date = result[1] if result and result[1] else None
            latest_date = result[2] if result and result[2] else None

            has_data = record_count > 0

            # 如果提供了最小期望天数，检查是否完整
            is_complete = False
            if min_expected_days is not None:
                # 数据被认为是完整的，如果：
                # 1. 记录数达到最小期望的80%以上（考虑节假日等）
                # 2. 最新日期接近结束日期（在30天内）
                if has_data and record_count >= min_expected_days * 0.8:
                    if latest_date:
                        from datetime import datetime, timedelta
                        latest_dt = datetime.strptime(str(latest_date), '%Y-%m-%d')
                        end_dt = datetime.strptime(end_date_formatted, '%Y-%m-%d')
                        days_diff = (end_dt - latest_dt).days
                        is_complete = days_diff <= 30

            cursor.close()

            return {
                'has_data': has_data,
                'is_complete': is_complete,
                'record_count': record_count,
                'earliest_date': str(earliest_date) if earliest_date else None,
                'latest_date': str(latest_date) if latest_date else None
            }

        except Exception as e:
            logger.error(f"❌ 检查 {code} 数据完整性失败: {e}")
            return {
                'has_data': False,
                'is_complete': False,
                'record_count': 0,
                'earliest_date': None,
                'latest_date': None
            }
        finally:
            if conn:
                self.release_connection(conn)

    def save_minute_data(self, df: pd.DataFrame, code: str, period: str, trade_date: str) -> int:
        """
        保存分时数据到数据库

        Args:
            df: 包含分时数据的DataFrame
            code: 股票代码
            period: 分时周期 ('1', '5', '15', '30', '60')
            trade_date: 交易日期 (YYYY-MM-DD)

        Returns:
            插入的记录数
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 准备数据
            records = []
            for _, row in df.iterrows():
                records.append((
                    code,
                    row.get('trade_time'),
                    period,
                    float(row.get('open', 0)) if pd.notna(row.get('open')) else None,
                    float(row.get('high', 0)) if pd.notna(row.get('high')) else None,
                    float(row.get('low', 0)) if pd.notna(row.get('low')) else None,
                    float(row.get('close', 0)) if pd.notna(row.get('close')) else None,
                    int(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0,
                    float(row.get('amount', 0)) if pd.notna(row.get('amount')) else None,
                    float(row.get('pct_change', 0)) if pd.notna(row.get('pct_change')) else None,
                    float(row.get('change_amount', 0)) if pd.notna(row.get('change_amount')) else None,
                    'akshare'
                ))

            # 批量插入（冲突时更新）
            insert_query = """
                INSERT INTO stock_minute
                (code, trade_time, period, open, high, low, close, volume, amount,
                 pct_change, change_amount, data_source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code, trade_time, period)
                DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    amount = EXCLUDED.amount,
                    pct_change = EXCLUDED.pct_change,
                    change_amount = EXCLUDED.change_amount,
                    data_source = EXCLUDED.data_source,
                    updated_at = CURRENT_TIMESTAMP;
            """

            extras.execute_batch(cursor, insert_query, records, page_size=1000)

            # 更新元数据
            self._update_minute_meta(cursor, code, trade_date, period, len(records))

            conn.commit()

            logger.info(f"✓ 保存 {code} {period}分钟数据: {len(records)} 条记录")
            return len(records)

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ 保存分时数据失败: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self.release_connection(conn)

    def _update_minute_meta(self, cursor, code: str, trade_date: str, period: str, record_count: int):
        """更新分时数据元数据"""
        # 获取期望的记录数（根据周期计算）
        expected_count = self._get_expected_minute_count(period)
        is_complete = record_count >= expected_count * 0.95  # 允许5%的数据缺失

        # 获取时间范围
        cursor.execute("""
            SELECT MIN(trade_time), MAX(trade_time)
            FROM stock_minute
            WHERE code = %s AND DATE(trade_time) = %s AND period = %s
        """, (code, trade_date, period))

        result = cursor.fetchone()
        first_time, last_time = result if result else (None, None)

        # 插入或更新元数据
        cursor.execute("""
            INSERT INTO stock_minute_meta
            (code, trade_date, period, is_complete, record_count, expected_count,
             first_time, last_time, data_source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'akshare')
            ON CONFLICT (code, trade_date, period)
            DO UPDATE SET
                is_complete = EXCLUDED.is_complete,
                record_count = EXCLUDED.record_count,
                expected_count = EXCLUDED.expected_count,
                first_time = EXCLUDED.first_time,
                last_time = EXCLUDED.last_time,
                updated_at = CURRENT_TIMESTAMP;
        """, (code, trade_date, period, is_complete, record_count, expected_count,
              first_time, last_time))

    def _get_expected_minute_count(self, period: str) -> int:
        """获取期望的分时记录数"""
        # A股交易时间：9:30-11:30 (120分钟) + 13:00-15:00 (120分钟) = 240分钟
        total_minutes = 240
        period_map = {
            '1': total_minutes,      # 240条
            '5': total_minutes // 5,  # 48条
            '15': total_minutes // 15,  # 16条
            '30': total_minutes // 30,  # 8条
            '60': total_minutes // 60   # 4条
        }
        return period_map.get(period, 48)

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
        conn = None
        try:
            conn = self.get_connection()

            query = """
                SELECT trade_time, open, high, low, close, volume, amount,
                       pct_change, change_amount
                FROM stock_minute
                WHERE code = %s AND period = %s AND DATE(trade_time) = %s
                ORDER BY trade_time ASC
            """

            df = pd.read_sql_query(query, conn, params=(code, period, trade_date))
            logger.info(f"✓ 加载 {code} {period}分钟数据: {len(df)} 条记录")
            return df

        except Exception as e:
            logger.error(f"❌ 加载分时数据失败: {e}")
            raise
        finally:
            if conn:
                self.release_connection(conn)

    def check_minute_data_complete(self, code: str, period: str, trade_date: str) -> dict:
        """
        检查分时数据是否完整

        Returns:
            {
                'is_complete': bool,
                'record_count': int,
                'expected_count': int,
                'completeness': float  # 完整度百分比
            }
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 查询元数据
            cursor.execute("""
                SELECT is_complete, record_count, expected_count
                FROM stock_minute_meta
                WHERE code = %s AND trade_date = %s AND period = %s
            """, (code, trade_date, period))

            result = cursor.fetchone()

            if result:
                is_complete, record_count, expected_count = result
                completeness = (record_count / expected_count * 100) if expected_count > 0 else 0
            else:
                # 如果元数据不存在，直接查询数据表
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM stock_minute
                    WHERE code = %s AND DATE(trade_time) = %s AND period = %s
                """, (code, trade_date, period))

                record_count = cursor.fetchone()[0]
                expected_count = self._get_expected_minute_count(period)
                is_complete = record_count >= expected_count * 0.95
                completeness = (record_count / expected_count * 100) if expected_count > 0 else 0

            return {
                'is_complete': is_complete,
                'record_count': record_count,
                'expected_count': expected_count,
                'completeness': round(completeness, 2)
            }

        except Exception as e:
            logger.error(f"❌ 检查数据完整性失败: {e}")
            return {
                'is_complete': False,
                'record_count': 0,
                'expected_count': 0,
                'completeness': 0
            }
        finally:
            if conn:
                cursor.close()
                self.release_connection(conn)

    def is_trading_day(self, trade_date: str) -> bool:
        """检查是否为交易日"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT is_trading_day
                FROM trading_calendar
                WHERE trade_date = %s
            """, (trade_date,))

            result = cursor.fetchone()

            if result:
                return result[0]
            else:
                # 如果日历表中没有数据，简单判断：周一到周五为交易日
                from datetime import datetime
                date_obj = datetime.strptime(trade_date, '%Y-%m-%d')
                return date_obj.weekday() < 5  # 0-4 为周一到周五

        except Exception as e:
            logger.warning(f"检查交易日失败: {e}")
            return True  # 默认为交易日
        finally:
            if conn:
                cursor.close()
                self.release_connection(conn)

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
                if hasattr(cls._instance, 'connection_pool') and cls._instance.connection_pool:
                    try:
                        cls._instance.connection_pool.closeall()
                    except Exception as e:
                        logger.warning(f"关闭连接池时出错: {e}")

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
    print("测试数据库管理模块（单例模式）")
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

        print("\n2. 测试数据库连接...")
        print("   ✓ 数据库连接成功")

        print("\n3. 初始化数据库表结构...")
        db1.init_database()
        print("   ✓ 表结构初始化成功")

        print("\n✅ 数据库管理模块测试通过")
        print("   - 单例模式正常工作")
        print("   - 全局只有一个连接池实例")
        print("   - 避免了连接资源浪费")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
