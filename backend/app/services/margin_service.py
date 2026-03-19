"""
融资融券交易汇总服务

提供融资融券交易汇总数据的同步和查询功能
数据来源：Tushare Pro margin 接口
积分消耗：2000分/次
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from src.database.db_manager import DatabaseManager
from core.src.providers import DataProviderFactory
from app.core.config import settings


class MarginService:
    """融资融券交易汇总服务"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_margin(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步融资融券交易汇总数据

        Args:
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            exchange_id: 交易所代码（SSE上交所/SZSE深交所/BSE北交所）

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步融资融券交易汇总: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, exchange_id={exchange_id}")

            # 如果没有指定任何日期，默认同步最近30天
            if not trade_date and not start_date and not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                logger.info(f"未指定日期，默认同步最近30天: {start_date} ~ {end_date}")

            # 获取数据提供者
            provider = self._get_provider()

            # 从Tushare获取数据
            df = await asyncio.to_thread(
                provider.get_margin,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                exchange_id=exchange_id
            )

            if df is None or len(df) == 0:
                logger.warning("未获取到融资融券交易汇总数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 插入数据库
            records = await self._insert_margin_data(df)

            logger.info(f"成功同步融资融券交易汇总数据 {records} 条")
            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条融资融券交易汇总数据"
            }

        except Exception as e:
            logger.error(f"同步融资融券交易汇总失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据

        Returns:
            清洗后的数据
        """
        # 移除空行
        df = df.dropna(subset=['trade_date', 'exchange_id'])

        # 确保必需字段存在
        required_columns = ['trade_date', 'exchange_id']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        # 数值字段转换
        numeric_columns = ['rzye', 'rzmre', 'rzche', 'rqye', 'rqmcl', 'rzrqye', 'rqyl']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 移除所有数值字段都为空的行
        df = df.dropna(subset=numeric_columns, how='all')

        logger.info(f"数据清洗完成，有效数据 {len(df)} 条")
        return df

    async def _insert_margin_data(self, df: pd.DataFrame) -> int:
        """
        插入融资融券交易汇总数据到数据库

        Args:
            df: 数据DataFrame

        Returns:
            插入的记录数
        """
        if len(df) == 0:
            return 0

        # 构建SQL语句（使用标准SQL占位符）
        insert_query = """
            INSERT INTO margin (
                trade_date, exchange_id, rzye, rzmre, rzche, rqye, rqmcl, rzrqye, rqyl, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (trade_date, exchange_id)
            DO UPDATE SET
                rzye = EXCLUDED.rzye,
                rzmre = EXCLUDED.rzmre,
                rzche = EXCLUDED.rzche,
                rqye = EXCLUDED.rqye,
                rqmcl = EXCLUDED.rqmcl,
                rzrqye = EXCLUDED.rzrqye,
                rqyl = EXCLUDED.rqyl,
                updated_at = CURRENT_TIMESTAMP
        """

        # 准备数据
        values = []
        for _, row in df.iterrows():
            values.append((
                str(row['trade_date']),
                str(row['exchange_id']),
                float(row['rzye']) if pd.notna(row['rzye']) else None,
                float(row['rzmre']) if pd.notna(row['rzmre']) else None,
                float(row['rzche']) if pd.notna(row['rzche']) else None,
                float(row['rqye']) if pd.notna(row['rqye']) else None,
                float(row['rqmcl']) if pd.notna(row['rqmcl']) else None,
                float(row['rzrqye']) if pd.notna(row['rzrqye']) else None,
                float(row['rqyl']) if pd.notna(row['rqyl']) else None,
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
                logger.info(f"成功批量插入 {len(values)} 条融资融券数据")
            except Exception as e:
                conn.rollback()
                logger.error(f"批量插入失败: {e}")
                raise
            finally:
                self.db_manager.release_connection(conn)

        await asyncio.to_thread(_batch_insert)

        return len(values)

    async def get_margin_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 30
    ) -> Dict[str, Any]:
        """
        查询融资融券交易汇总数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            exchange_id: 交易所代码
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
                conditions.append("trade_date >= %s")
                params.append(start_date.replace('-', ''))

            if end_date:
                conditions.append("trade_date <= %s")
                params.append(end_date.replace('-', ''))

            if exchange_id:
                conditions.append("exchange_id = %s")
                params.append(exchange_id)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 查询总数
            count_query = f"SELECT COUNT(*) FROM margin WHERE {where_clause}"
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
                    exchange_id,
                    rzye,
                    rzmre,
                    rzche,
                    rqye,
                    rqmcl,
                    rzrqye,
                    rqyl,
                    created_at,
                    updated_at
                FROM margin
                WHERE {where_clause}
                ORDER BY trade_date DESC, exchange_id
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
                data.append({
                    'trade_date': row[0],
                    'exchange_id': row[1],
                    'rzye': float(row[2]) if row[2] is not None else None,
                    'rzmre': float(row[3]) if row[3] is not None else None,
                    'rzche': float(row[4]) if row[4] is not None else None,
                    'rqye': float(row[5]) if row[5] is not None else None,
                    'rqmcl': float(row[6]) if row[6] is not None else None,
                    'rzrqye': float(row[7]) if row[7] is not None else None,
                    'rqyl': float(row[8]) if row[8] is not None else None,
                    'created_at': row[9].isoformat() if row[9] else None,
                    'updated_at': row[10].isoformat() if row[10] else None
                })

            return {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size
            }

        except Exception as e:
            logger.error(f"查询融资融券交易汇总数据失败: {str(e)}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取融资融券交易汇总统计数据

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
                conditions.append("trade_date >= %s")
                params.append(start_date.replace('-', ''))

            if end_date:
                conditions.append("trade_date <= %s")
                params.append(end_date.replace('-', ''))

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 统计查询
            stats_query = f"""
                SELECT
                    AVG(rzrqye) as avg_rzrqye,
                    SUM(rzrqye) as total_rzrqye,
                    MAX(rzye) as max_rzye,
                    MAX(rqye) as max_rqye
                FROM margin
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
                    "max_rzye": float(row[2]) if row[2] is not None else 0,
                    "max_rqye": float(row[3]) if row[3] is not None else 0
                }
            else:
                return {
                    "avg_rzrqye": 0,
                    "total_rzrqye": 0,
                    "max_rzye": 0,
                    "max_rqye": 0
                }

        except Exception as e:
            logger.error(f"获取融资融券统计数据失败: {str(e)}")
            raise
