"""
融资融券交易明细服务

提供融资融券交易明细数据的同步和查询功能
数据来源：Tushare Pro margin_detail 接口
积分消耗：2000分/次
单次限制：最大6000行
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from src.database.db_manager import DatabaseManager
from core.src.providers import DataProviderFactory
from app.core.config import settings


class MarginDetailService:
    """融资融券交易明细服务"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_margin_detail(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步融资融券交易明细数据

        Args:
            trade_date: 交易日期 YYYYMMDD
            ts_code: TS股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步融资融券交易明细: trade_date={trade_date}, ts_code={ts_code}, start_date={start_date}, end_date={end_date}")

            # 如果没有指定任何日期，默认同步最近一个交易日
            if not trade_date and not start_date and not end_date:
                # 获取最近一个交易日
                trade_date = await self._get_latest_trade_date()
                logger.info(f"未指定日期，默认同步最近交易日: {trade_date}")

            # 获取数据提供者
            provider = self._get_provider()

            # 从Tushare获取数据
            df = await asyncio.to_thread(
                provider.get_margin_detail,
                trade_date=trade_date,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) == 0:
                logger.warning("未获取到融资融券交易明细数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 插入数据库
            records = await self._insert_margin_detail_data(df)

            logger.info(f"成功同步融资融券交易明细数据 {records} 条")
            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条融资融券交易明细数据"
            }

        except Exception as e:
            logger.error(f"同步融资融券交易明细失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    async def _get_latest_trade_date(self) -> str:
        """
        获取最近一个交易日

        Returns:
            交易日期 YYYYMMDD
        """
        try:
            # 从数据库获取最近一个有数据的交易日
            query = """
                SELECT DISTINCT trade_date
                FROM stock_daily
                ORDER BY trade_date DESC
                LIMIT 1
            """
            result = await asyncio.to_thread(
                self.db_manager._execute_query,
                query,
                ()
            )

            if result and result[0]:
                return result[0][0]
            else:
                # 如果没有数据，返回前一天
                return (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

        except Exception as e:
            logger.error(f"获取最近交易日失败: {e}")
            # 返回前一天作为默认值
            return (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据

        Returns:
            清洗后的数据
        """
        # 移除空行
        df = df.dropna(subset=['trade_date', 'ts_code'])

        # 确保必需字段存在
        required_columns = ['trade_date', 'ts_code']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        # 数值字段转换
        numeric_columns = ['rzye', 'rqye', 'rzmre', 'rqyl', 'rzche', 'rqchl', 'rqmcl', 'rzrqye']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 移除所有数值字段都为空的行
        df = df.dropna(subset=numeric_columns, how='all')

        logger.info(f"数据清洗完成，有效数据 {len(df)} 条")
        return df

    async def _insert_margin_detail_data(self, df: pd.DataFrame) -> int:
        """
        插入融资融券交易明细数据到数据库

        Args:
            df: 数据DataFrame

        Returns:
            插入的记录数
        """
        if len(df) == 0:
            return 0

        # 构建SQL语句（使用标准SQL占位符）
        insert_query = """
            INSERT INTO margin_detail (
                trade_date, ts_code, name, rzye, rqye, rzmre, rqyl,
                rzche, rqchl, rqmcl, rzrqye, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (trade_date, ts_code)
            DO UPDATE SET
                name = EXCLUDED.name,
                rzye = EXCLUDED.rzye,
                rqye = EXCLUDED.rqye,
                rzmre = EXCLUDED.rzmre,
                rqyl = EXCLUDED.rqyl,
                rzche = EXCLUDED.rzche,
                rqchl = EXCLUDED.rqchl,
                rqmcl = EXCLUDED.rqmcl,
                rzrqye = EXCLUDED.rzrqye,
                updated_at = CURRENT_TIMESTAMP
        """

        # 准备数据
        values = []
        for _, row in df.iterrows():
            values.append((
                str(row['trade_date']),
                str(row['ts_code']),
                str(row['name']) if pd.notna(row.get('name')) else None,
                float(row['rzye']) if pd.notna(row['rzye']) else None,
                float(row['rqye']) if pd.notna(row['rqye']) else None,
                float(row['rzmre']) if pd.notna(row['rzmre']) else None,
                float(row['rqyl']) if pd.notna(row['rqyl']) else None,
                float(row['rzche']) if pd.notna(row['rzche']) else None,
                float(row['rqchl']) if pd.notna(row['rqchl']) else None,
                float(row['rqmcl']) if pd.notna(row['rqmcl']) else None,
                float(row['rzrqye']) if pd.notna(row['rzrqye']) else None,
                datetime.now()
            ))

        # 执行批量插入（使用 get_connection + executemany 模式）
        def _batch_insert():
            conn = self.db_manager.get_connection()
            try:
                cursor = conn.cursor()
                cursor.executemany(insert_query, values)
                conn.commit()
                cursor.close()
                logger.info(f"成功批量插入 {len(values)} 条融资融券明细数据")
            except Exception as e:
                conn.rollback()
                logger.error(f"批量插入失败: {e}")
                raise
            finally:
                self.db_manager.release_connection(conn)

        await asyncio.to_thread(_batch_insert)

        return len(values)

    async def get_margin_detail_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        page: int = 1,
        page_size: int = 30
    ) -> Dict[str, Any]:
        """
        查询融资融券交易明细数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            ts_code: 股票代码
            page: 页码
            page_size: 每页数量

        Returns:
            包含数据和统计信息的字典
        """
        try:
            # 构建查询条件
            conditions = []
            params = []

            if start_date:
                # 兼容 date 类型和 varchar 类型
                conditions.append("(trade_date >= %s::date OR trade_date::text >= %s)")
                params.append(start_date)
                params.append(start_date.replace('-', ''))

            if end_date:
                # 兼容 date 类型和 varchar 类型
                conditions.append("(trade_date <= %s::date OR trade_date::text <= %s)")
                params.append(end_date)
                params.append(end_date.replace('-', ''))

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 查询总数
            count_query = f"SELECT COUNT(*) FROM margin_detail WHERE {where_clause}"
            total = await asyncio.to_thread(
                self.db_manager._execute_query,
                count_query,
                tuple(params)
            )
            total = total[0][0] if total else 0

            # 查询数据
            offset = (page - 1) * page_size
            data_query = f"""
                SELECT
                    trade_date,
                    ts_code,
                    name,
                    rzye,
                    rqye,
                    rzmre,
                    rqyl,
                    rzche,
                    rqchl,
                    rqmcl,
                    rzrqye,
                    created_at,
                    updated_at
                FROM margin_detail
                WHERE {where_clause}
                ORDER BY trade_date DESC, rzrqye DESC NULLS LAST
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])

            rows = await asyncio.to_thread(
                self.db_manager._execute_query,
                data_query,
                tuple(params)
            )

            # 转换为字典列表
            data = []
            for row in rows:
                # 处理 trade_date：可能是 date 对象或字符串
                trade_date_value = row[0]
                if hasattr(trade_date_value, 'strftime'):
                    trade_date_str = trade_date_value.strftime('%Y%m%d')
                else:
                    trade_date_str = str(trade_date_value)

                data.append({
                    'trade_date': trade_date_str,
                    'ts_code': row[1],
                    'name': row[2],
                    'rzye': float(row[3]) if row[3] is not None else None,
                    'rqye': float(row[4]) if row[4] is not None else None,
                    'rzmre': float(row[5]) if row[5] is not None else None,
                    'rqyl': float(row[6]) if row[6] is not None else None,
                    'rzche': float(row[7]) if row[7] is not None else None,
                    'rqchl': float(row[8]) if row[8] is not None else None,
                    'rqmcl': float(row[9]) if row[9] is not None else None,
                    'rzrqye': float(row[10]) if row[10] is not None else None,
                    'created_at': row[11].isoformat() if row[11] else None,
                    'updated_at': row[12].isoformat() if row[12] else None
                })

            return {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size
            }

        except Exception as e:
            logger.error(f"查询融资融券交易明细数据失败: {str(e)}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取融资融券交易明细统计数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD

        Returns:
            统计数据字典
        """
        try:
            # 构建查询条件
            conditions = []
            params = []

            if start_date:
                # 兼容 date 类型和 varchar 类型
                conditions.append("(trade_date >= %s::date OR trade_date::text >= %s)")
                params.append(start_date)
                params.append(start_date.replace('-', ''))

            if end_date:
                # 兼容 date 类型和 varchar 类型
                conditions.append("(trade_date <= %s::date OR trade_date::text <= %s)")
                params.append(end_date)
                params.append(end_date.replace('-', ''))

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 统计查询
            stats_query = f"""
                SELECT
                    AVG(rzrqye) as avg_rzrqye,
                    SUM(rzrqye) as total_rzrqye,
                    MAX(rzrqye) as max_rzrqye,
                    COUNT(DISTINCT ts_code) as stock_count
                FROM margin_detail
                WHERE {where_clause}
            """

            result = await asyncio.to_thread(
                self.db_manager._execute_query,
                stats_query,
                tuple(params)
            )

            if result and result[0]:
                row = result[0]
                return {
                    "avg_rzrqye": float(row[0]) if row[0] is not None else 0,
                    "total_rzrqye": float(row[1]) if row[1] is not None else 0,
                    "max_rzrqye": float(row[2]) if row[2] is not None else 0,
                    "stock_count": int(row[3]) if row[3] is not None else 0
                }
            else:
                return {
                    "avg_rzrqye": 0,
                    "total_rzrqye": 0,
                    "max_rzrqye": 0,
                    "stock_count": 0
                }

        except Exception as e:
            logger.error(f"获取融资融券明细统计数据失败: {str(e)}")
            raise

    async def get_top_stocks(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取融资融券余额TOP股票

        Args:
            trade_date: 交易日期 YYYY-MM-DD
            limit: 返回数量

        Returns:
            TOP股票列表
        """
        try:
            # 如果未指定日期，获取最新交易日
            if not trade_date:
                latest_query = """
                    SELECT DISTINCT trade_date
                    FROM margin_detail
                    ORDER BY trade_date DESC
                    LIMIT 1
                """
                result = await asyncio.to_thread(
                    self.db_manager._execute_query,
                    latest_query,
                    ()
                )
                trade_date = result[0][0] if result and result[0] else None

            if not trade_date:
                return []

            # 格式化日期（处理字符串和日期对象）
            if isinstance(trade_date, str):
                trade_date_formatted = trade_date.replace('-', '')
            else:
                # 如果是日期对象，转换为YYYYMMDD格式
                trade_date_formatted = trade_date.strftime('%Y%m%d') if hasattr(trade_date, 'strftime') else str(trade_date)

            # 查询TOP股票
            # 注意：trade_date 列类型可能是 date 或 varchar，需要兼容处理
            query = """
                SELECT
                    ts_code,
                    name,
                    rzrqye,
                    rzye,
                    rqye
                FROM margin_detail
                WHERE trade_date::text = %s OR trade_date = %s::date
                ORDER BY rzrqye DESC NULLS LAST
                LIMIT %s
            """

            rows = await asyncio.to_thread(
                self.db_manager._execute_query,
                query,
                (trade_date_formatted, trade_date_formatted, limit)
            )

            # 转换为字典列表
            top_stocks = []
            for row in rows:
                top_stocks.append({
                    'ts_code': row[0],
                    'name': row[1],
                    'rzrqye': float(row[2]) if row[2] is not None else 0,
                    'rzye': float(row[3]) if row[3] is not None else 0,
                    'rqye': float(row[4]) if row[4] is not None else 0
                })

            return top_stocks

        except Exception as e:
            logger.error(f"获取TOP股票失败: {str(e)}")
            raise
