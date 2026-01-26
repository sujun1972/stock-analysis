#!/usr/bin/env python3
"""
数据插入管理器

负责所有数据的批量插入操作。
"""

import pandas as pd
import numpy as np
from psycopg2 import extras
import logging
from typing import TYPE_CHECKING, Dict, Any

# 导入类型转换工具
from utils.type_utils import (
    safe_float,
    safe_int,
    safe_float_series,
    safe_int_series,
    safe_float_or_none,
    safe_float_or_zero,
    safe_int_or_zero
)

if TYPE_CHECKING:
    from .connection_pool_manager import ConnectionPoolManager

logger = logging.getLogger(__name__)


class DataInsertManager:
    """
    数据插入管理器

    职责：
    - 处理所有数据的批量插入
    - 数据类型转换和验证
    - 处理冲突更新逻辑
    """

    def __init__(self, pool_manager: 'ConnectionPoolManager'):
        """
        初始化数据插入管理器

        Args:
            pool_manager: 连接池管理器实例
        """
        self.pool_manager = pool_manager

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
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 准备数据（向量化优化 - 避免 iterrows）
            # 统一列名处理
            code_col = 'code' if 'code' in df.columns else '股票代码'
            name_col = 'name' if 'name' in df.columns else '股票名称'
            market_col = 'market' if 'market' in df.columns else '市场类型'
            industry_col = 'industry' if 'industry' in df.columns else '行业'
            area_col = 'area' if 'area' in df.columns else '地域'
            list_date_col = 'list_date' if 'list_date' in df.columns else '上市日期'
            delist_date_col = 'delist_date' if 'delist_date' in df.columns else '退市日期'
            status_col = 'status' if 'status' in df.columns else None

            # 向量化构建记录
            records = list(zip(
                df[code_col].fillna('').values,
                df[name_col].fillna('').values,
                df[market_col].fillna('').values if market_col in df.columns else [''] * len(df),
                df[industry_col].fillna('').values if industry_col in df.columns else [''] * len(df),
                df[area_col].fillna('').values if area_col in df.columns else [''] * len(df),
                df[list_date_col].fillna(None).values if list_date_col in df.columns else [None] * len(df),
                df[delist_date_col].fillna(None).values if delist_date_col in df.columns else [None] * len(df),
                df[status_col].fillna('正常').values if status_col in df.columns else ['正常'] * len(df),
                [data_source] * len(df)
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
                self.pool_manager.release_connection(conn)

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
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 准备数据（向量化优化 - 避免 iterrows）
            # 处理日期列
            if 'trade_date' in df.columns:
                dates = pd.to_datetime(df['trade_date']).dt.date
            else:
                # 使用索引作为日期
                dates = pd.to_datetime(df.index).date if isinstance(df.index, pd.DatetimeIndex) else df.index

            # 统一列名处理
            open_col = 'open' if 'open' in df.columns else '开盘'
            high_col = 'high' if 'high' in df.columns else '最高'
            low_col = 'low' if 'low' in df.columns else '最低'
            close_col = 'close' if 'close' in df.columns else '收盘'
            volume_col = 'volume' if 'volume' in df.columns else '成交量'
            amount_col = 'amount' if 'amount' in df.columns else '成交额'
            amplitude_col = 'amplitude' if 'amplitude' in df.columns else '振幅'
            pct_change_col = 'pct_change' if 'pct_change' in df.columns else '涨跌幅'
            change_col = 'change' if 'change' in df.columns else ('涨跌额' if '涨跌额' in df.columns else 'change_amount')
            turnover_col = 'turnover' if 'turnover' in df.columns else '换手率'

            # 向量化构建记录
            records = list(zip(
                [stock_code] * len(df),
                dates,
                df[open_col].fillna(0).astype(float).values,
                df[high_col].fillna(0).astype(float).values,
                df[low_col].fillna(0).astype(float).values,
                df[close_col].fillna(0).astype(float).values,
                df[volume_col].fillna(0).astype(int).values,
                df[amount_col].fillna(0).astype(float).values,
                df[amplitude_col].fillna(0).astype(float).values if amplitude_col in df.columns else [0.0] * len(df),
                df[pct_change_col].fillna(0).astype(float).values if pct_change_col in df.columns else [0.0] * len(df),
                df[change_col].fillna(0).astype(float).values if change_col in df.columns else [0.0] * len(df),
                df[turnover_col].fillna(0).astype(float).values if turnover_col in df.columns else [0.0] * len(df)
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
                self.pool_manager.release_connection(conn)

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
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 准备数据（使用 type_utils 中的转换函数）
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
                self.pool_manager.release_connection(conn)

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
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 准备数据（向量化优化 - 避免 iterrows）
            # 统一列名处理
            code_col = 'code' if 'code' in df.columns else '代码'
            name_col = 'name' if 'name' in df.columns else '名称'
            latest_price_col = 'latest_price' if 'latest_price' in df.columns else ('最新价' if '最新价' in df.columns else '现价')
            open_col = 'open' if 'open' in df.columns else '今开'
            high_col = 'high' if 'high' in df.columns else '最高'
            low_col = 'low' if 'low' in df.columns else '最低'
            pre_close_col = 'pre_close' if 'pre_close' in df.columns else '昨收'
            volume_col = 'volume' if 'volume' in df.columns else '成交量'
            amount_col = 'amount' if 'amount' in df.columns else '成交额'
            pct_change_col = 'pct_change' if 'pct_change' in df.columns else '涨跌幅'
            change_amount_col = 'change_amount' if 'change_amount' in df.columns else '涨跌额'
            turnover_col = 'turnover' if 'turnover' in df.columns else '换手率'
            amplitude_col = 'amplitude' if 'amplitude' in df.columns else '振幅'

            # 向量化构建记录（使用 type_utils 中的转换函数）
            records = list(zip(
                df[code_col].fillna('').values,
                df[name_col].fillna('').values,
                safe_float_series(df[latest_price_col]) if latest_price_col in df.columns else [0.0] * len(df),
                safe_float_series(df[open_col]) if open_col in df.columns else [0.0] * len(df),
                safe_float_series(df[high_col]) if high_col in df.columns else [0.0] * len(df),
                safe_float_series(df[low_col]) if low_col in df.columns else [0.0] * len(df),
                safe_float_series(df[pre_close_col]) if pre_close_col in df.columns else [0.0] * len(df),
                safe_int_series(df[volume_col]) if volume_col in df.columns else [0] * len(df),
                safe_float_series(df[amount_col]) if amount_col in df.columns else [0.0] * len(df),
                safe_float_series(df[pct_change_col]) if pct_change_col in df.columns else [0.0] * len(df),
                safe_float_series(df[change_amount_col]) if change_amount_col in df.columns else [0.0] * len(df),
                safe_float_series(df[turnover_col]) if turnover_col in df.columns else [0.0] * len(df),
                safe_float_series(df[amplitude_col]) if amplitude_col in df.columns else [0.0] * len(df),
                [data_source] * len(df)
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
                self.pool_manager.release_connection(conn)

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
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 准备数据（向量化优化 - 避免 iterrows）
            # 使用 type_utils 中的转换函数
            records = list(zip(
                [code] * len(df),
                df['trade_time'].values,
                [period] * len(df),
                safe_float_or_none(df['open']) if 'open' in df.columns else [None] * len(df),
                safe_float_or_none(df['high']) if 'high' in df.columns else [None] * len(df),
                safe_float_or_none(df['low']) if 'low' in df.columns else [None] * len(df),
                safe_float_or_none(df['close']) if 'close' in df.columns else [None] * len(df),
                safe_int_or_zero(df['volume']) if 'volume' in df.columns else [0] * len(df),
                safe_float_or_none(df['amount']) if 'amount' in df.columns else [None] * len(df),
                safe_float_or_none(df['pct_change']) if 'pct_change' in df.columns else [None] * len(df),
                safe_float_or_none(df['change_amount']) if 'change_amount' in df.columns else [None] * len(df),
                ['akshare'] * len(df)
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
                self.pool_manager.release_connection(conn)

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

    @staticmethod
    def _get_expected_minute_count(period: str) -> int:
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
