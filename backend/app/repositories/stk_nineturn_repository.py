"""
神奇九转指标数据 Repository
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository


class StkNineturnRepository(BaseRepository):
    """神奇九转指标数据 Repository"""

    TABLE_NAME = "stk_nineturn"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ StkNineturnRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        freq: str = 'daily',
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询神奇九转数据

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            ts_code: 股票代码（可选）
            freq: 频率，默认daily
            limit: 返回记录数限制

        Returns:
            神奇九转数据列表

        Examples:
            >>> repo = StkNineturnRepository()
            >>> data = repo.get_by_date_range('2024-01-01', '2024-01-31', ts_code='000001.SZ')
        """
        try:
            # 构建查询条件
            conditions = ["freq = %s"]
            params = [freq]

            if start_date:
                conditions.append("trade_date >= %s::timestamp")
                params.append(start_date)
            if end_date:
                conditions.append("trade_date <= %s::timestamp")
                params.append(end_date)
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)

            # 构建查询语句
            query = f"""
                SELECT
                    ts_code,
                    trade_date,
                    freq,
                    open,
                    high,
                    low,
                    close,
                    vol,
                    amount,
                    up_count,
                    down_count,
                    nine_up_turn,
                    nine_down_turn
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC, ts_code
            """

            if limit:
                query += f" LIMIT {int(limit)}"

            result = self.execute_query(query, tuple(params))

            # 转换为字典列表
            data = []
            for row in result:
                data.append({
                    'ts_code': row[0],
                    'trade_date': row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else None,
                    'freq': row[2],
                    'open': float(row[3]) if row[3] is not None else None,
                    'high': float(row[4]) if row[4] is not None else None,
                    'low': float(row[5]) if row[5] is not None else None,
                    'close': float(row[6]) if row[6] is not None else None,
                    'vol': float(row[7]) if row[7] is not None else None,
                    'amount': float(row[8]) if row[8] is not None else None,
                    'up_count': float(row[9]) if row[9] is not None else None,
                    'down_count': float(row[10]) if row[10] is not None else None,
                    'nine_up_turn': row[11],
                    'nine_down_turn': row[12]
                })

            return data

        except Exception as e:
            logger.error(f"查询神奇九转数据失败: {e}")
            raise

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        freq: str = 'daily'
    ) -> Dict:
        """
        获取神奇九转统计信息

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            ts_code: 股票代码（可选）
            freq: 频率，默认daily

        Returns:
            统计信息字典

        Examples:
            >>> repo = StkNineturnRepository()
            >>> stats = repo.get_statistics('2024-01-01', '2024-01-31')
        """
        try:
            conditions = ["freq = %s"]
            params = [freq]

            if start_date:
                conditions.append("trade_date >= %s::timestamp")
                params.append(start_date)
            if end_date:
                conditions.append("trade_date <= %s::timestamp")
                params.append(end_date)
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT ts_code) as stock_count,
                    COUNT(CASE WHEN nine_up_turn = '+9' THEN 1 END) as up_turn_count,
                    COUNT(CASE WHEN nine_down_turn = '-9' THEN 1 END) as down_turn_count,
                    AVG(up_count) as avg_up_count,
                    AVG(down_count) as avg_down_count,
                    MAX(up_count) as max_up_count,
                    MAX(down_count) as max_down_count
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            if result and len(result) > 0:
                row = result[0]
                return {
                    'total_records': int(row[0]) if row[0] else 0,
                    'stock_count': int(row[1]) if row[1] else 0,
                    'up_turn_count': int(row[2]) if row[2] else 0,
                    'down_turn_count': int(row[3]) if row[3] else 0,
                    'avg_up_count': float(row[4]) if row[4] is not None else 0.0,
                    'avg_down_count': float(row[5]) if row[5] is not None else 0.0,
                    'max_up_count': float(row[6]) if row[6] is not None else 0.0,
                    'max_down_count': float(row[7]) if row[7] is not None else 0.0
                }

            return {
                'total_records': 0,
                'stock_count': 0,
                'up_turn_count': 0,
                'down_turn_count': 0,
                'avg_up_count': 0.0,
                'avg_down_count': 0.0,
                'max_up_count': 0.0,
                'max_down_count': 0.0
            }

        except Exception as e:
            logger.error(f"获取神奇九转统计信息失败: {e}")
            raise

    def get_latest_trade_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新交易日期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新交易日期字符串（YYYY-MM-DD），如果没有数据则返回None

        Examples:
            >>> repo = StkNineturnRepository()
            >>> latest_date = repo.get_latest_trade_date('000001.SZ')
        """
        try:
            if ts_code:
                query = f"""
                    SELECT MAX(trade_date)
                    FROM {self.TABLE_NAME}
                    WHERE ts_code = %s
                """
                params = (ts_code,)
            else:
                query = f"""
                    SELECT MAX(trade_date)
                    FROM {self.TABLE_NAME}
                """
                params = ()

            result = self.execute_query(query, params)

            if result and result[0][0]:
                return result[0][0].strftime('%Y-%m-%d')

            return None

        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            raise

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新神奇九转数据

        Args:
            df: 包含神奇九转数据的DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = StkNineturnRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过插入")
            return 0

        try:
            # 辅助函数：将pandas/numpy类型转换为Python原生类型
            def to_python_type(value):
                """将pandas/numpy类型转换为Python原生类型"""
                if pd.isna(value):
                    return None
                if isinstance(value, (pd.Int64Dtype, int)) or hasattr(value, 'item'):
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return None
                if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                    return float(value)
                return value

            # 准备插入数据
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('trade_date')),
                    to_python_type(row.get('freq', 'daily')),
                    to_python_type(row.get('open')),
                    to_python_type(row.get('high')),
                    to_python_type(row.get('low')),
                    to_python_type(row.get('close')),
                    to_python_type(row.get('vol')),
                    to_python_type(row.get('amount')),
                    to_python_type(row.get('up_count')),
                    to_python_type(row.get('down_count')),
                    to_python_type(row.get('nine_up_turn')),
                    to_python_type(row.get('nine_down_turn'))
                ))

            # UPSERT 查询
            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (ts_code, trade_date, freq, open, high, low, close, vol, amount,
                 up_count, down_count, nine_up_turn, nine_down_turn, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (ts_code, trade_date, freq)
                DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    vol = EXCLUDED.vol,
                    amount = EXCLUDED.amount,
                    up_count = EXCLUDED.up_count,
                    down_count = EXCLUDED.down_count,
                    nine_up_turn = EXCLUDED.nine_up_turn,
                    nine_down_turn = EXCLUDED.nine_down_turn,
                    updated_at = NOW()
            """

            # 批量执行
            count = self.execute_batch(query, values)

            logger.info(f"成功插入/更新 {count} 条神奇九转记录")
            return count

        except Exception as e:
            logger.error(f"批量插入神奇九转数据失败: {e}")
            raise

    def get_turn_signals(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        signal_type: str = 'all',  # 'up', 'down', 'all'
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        获取九转信号（+9或-9）

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            signal_type: 信号类型 ('up': 上九转, 'down': 下九转, 'all': 全部)
            limit: 返回记录数限制

        Returns:
            九转信号列表

        Examples:
            >>> repo = StkNineturnRepository()
            >>> signals = repo.get_turn_signals('2024-01-01', signal_type='up', limit=20)
        """
        try:
            conditions = []
            params = []

            # 日期条件
            if start_date:
                conditions.append("trade_date >= %s::timestamp")
                params.append(start_date)
            if end_date:
                conditions.append("trade_date <= %s::timestamp")
                params.append(end_date)

            # 信号类型条件
            if signal_type == 'up':
                conditions.append("nine_up_turn = '+9'")
            elif signal_type == 'down':
                conditions.append("nine_down_turn = '-9'")
            else:  # all
                conditions.append("(nine_up_turn = '+9' OR nine_down_turn = '-9')")

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    ts_code,
                    trade_date,
                    close,
                    up_count,
                    down_count,
                    nine_up_turn,
                    nine_down_turn
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC, ts_code
            """

            if limit:
                query += f" LIMIT {int(limit)}"

            result = self.execute_query(query, tuple(params))

            # 转换为字典列表
            data = []
            for row in result:
                data.append({
                    'ts_code': row[0],
                    'trade_date': row[1].strftime('%Y-%m-%d') if row[1] else None,
                    'close': float(row[2]) if row[2] is not None else None,
                    'up_count': float(row[3]) if row[3] is not None else None,
                    'down_count': float(row[4]) if row[4] is not None else None,
                    'nine_up_turn': row[5],
                    'nine_down_turn': row[6]
                })

            return data

        except Exception as e:
            logger.error(f"获取九转信号失败: {e}")
            raise
