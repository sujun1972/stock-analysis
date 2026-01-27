#!/usr/bin/env python3
"""
数据库表结构管理器

负责创建和管理数据库表结构、索引等。
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg2.extensions import cursor as Cursor
    from .connection_pool_manager import ConnectionPoolManager

logger = logging.getLogger(__name__)


class TableManager:
    """
    数据库表结构管理器

    职责：
    - 创建和管理所有数据库表
    - 创建索引
    - TimescaleDB优化（可选）
    """

    def __init__(self, pool_manager: 'ConnectionPoolManager'):
        """
        初始化表管理器

        Args:
            pool_manager: 连接池管理器实例
        """
        self.pool_manager = pool_manager

    def init_all_tables(self) -> None:
        """初始化所有数据库表结构"""
        conn = None
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 1. 创建股票基本信息表
            self._create_stock_info_table(cursor)

            # 2. 创建股票日线数据表
            self._create_stock_daily_table(cursor)

            # 3. TimescaleDB优化（可选）
            self._optimize_with_timescaledb(cursor, 'stock_daily', 'date')

            # 4. 创建股票特征表
            self._create_stock_features_table(cursor)

            # 5. 创建模型预测表
            self._create_stock_predictions_table(cursor)

            # 6. 创建回测结果表
            self._create_backtest_results_table(cursor)

            # 7. 创建分时数据表
            self._create_stock_minute_table(cursor)

            # 8. 创建分时数据元数据表
            self._create_stock_minute_meta_table(cursor)

            # 9. 创建交易日历表
            self._create_trading_calendar_table(cursor)

            # 10. 创建实时行情表
            self._create_stock_realtime_table(cursor)

            # 11. 创建所有索引
            self._create_all_indexes(cursor)

            # 12. TimescaleDB优化分时数据表（可选）
            self._optimize_minute_data_with_timescaledb(cursor)

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
                self.pool_manager.release_connection(conn)

    def _create_stock_info_table(self, cursor: 'Cursor') -> None:
        """创建股票基本信息表"""
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

    def _create_stock_daily_table(self, cursor: 'Cursor') -> None:
        """创建股票日线数据表"""
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

    def _create_stock_features_table(self, cursor: 'Cursor') -> None:
        """创建股票特征表"""
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

    def _create_stock_predictions_table(self, cursor: 'Cursor') -> None:
        """创建模型预测表"""
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

    def _create_backtest_results_table(self, cursor: 'Cursor') -> None:
        """创建回测结果表"""
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

    def _create_stock_minute_table(self, cursor: 'Cursor') -> None:
        """创建分时数据表"""
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

    def _create_stock_minute_meta_table(self, cursor: 'Cursor') -> None:
        """创建分时数据元数据表"""
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

    def _create_trading_calendar_table(self, cursor: 'Cursor') -> None:
        """创建交易日历表"""
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

    def _create_stock_realtime_table(self, cursor: 'Cursor') -> None:
        """创建实时行情表"""
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

    def _create_all_indexes(self, cursor: 'Cursor') -> None:
        """创建所有索引"""
        # 日线数据索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_daily_code ON stock_daily(code);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_daily_date ON stock_daily(date);")

        # 特征表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_features_code_date ON stock_features(code, date);")

        # 预测表索引
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

    def _optimize_with_timescaledb(self, cursor: 'Cursor', table_name: str, time_column: str) -> None:
        """使用TimescaleDB优化时序表"""
        try:
            # 检查是否支持TimescaleDB
            cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'timescaledb';")
            if cursor.fetchone():
                # 将表转换为时序表
                cursor.execute(f"""
                    SELECT create_hypertable('{table_name}', '{time_column}',
                        if_not_exists => TRUE,
                        migrate_data => TRUE
                    );
                """)
                logger.info(f"✓ {table_name} TimescaleDB时序表优化完成")
        except Exception as e:
            logger.warning(f"TimescaleDB优化跳过 ({table_name}): {e}")

    def _optimize_minute_data_with_timescaledb(self, cursor: 'Cursor') -> None:
        """TimescaleDB优化分时数据表"""
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
