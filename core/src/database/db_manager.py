#!/usr/bin/env python3
"""
数据库管理模块
负责数据库连接、表创建和数据存储
"""

import psycopg2
from psycopg2 import pool, extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import logging

# 尝试加载配置
try:
    from ..config.config import DATABASE_CONFIG
except ImportError:
    from src.config.config import DATABASE_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据库管理器

        Args:
            config: 数据库配置字典，如果为None则使用默认配置
        """
        self.config = config or DATABASE_CONFIG
        self.connection_pool = None
        self._init_connection_pool()

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
            self.connection_pool.closeall()
            logger.info("所有数据库连接已关闭")

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

            # 7. 创建常用索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_daily_code ON stock_daily(code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_daily_date ON stock_daily(date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_features_code_date ON stock_features(code, date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_code_date ON stock_predictions(code, pred_date);")
            logger.info("✓ 索引创建完成")

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

            df = pd.read_sql_query(query, conn, params=params, index_col='date')
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

    def __del__(self):
        """析构函数，确保连接池关闭"""
        self.close_all_connections()


# 便捷函数
def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return DatabaseManager()


if __name__ == "__main__":
    # 测试数据库连接和初始化
    print("\n" + "="*60)
    print("测试数据库管理模块")
    print("="*60)

    try:
        db = DatabaseManager()
        print("\n✓ 数据库连接成功")

        print("\n初始化数据库表结构...")
        db.init_database()

        print("\n✅ 数据库管理模块测试通过")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
