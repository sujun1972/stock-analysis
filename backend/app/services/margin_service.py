"""
融资融券交易汇总服务

提供融资融券交易汇总数据的同步和查询功能
数据来源：Tushare Pro margin 接口
积分消耗：2000分/次
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from core.src.providers import DataProviderFactory
from app.core.config import settings
from app.repositories import MarginRepository


class MarginService:
    """融资融券交易汇总服务"""

    def __init__(self):
        self.margin_repo = MarginRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

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

        # 使用 Repository 批量插入
        records = await asyncio.to_thread(self.margin_repo.bulk_upsert, df)
        return records

    async def resolve_default_date_range(self) -> Dict[str, Optional[str]]:
        """
        解析默认日期范围：返回表中最新交易日（YYYY-MM-DD），用于前端回填

        Returns:
            {'latest_date': 'YYYY-MM-DD' or None}
        """
        try:
            latest = await asyncio.to_thread(self.margin_repo.get_latest_trade_date)
            if latest:
                d = str(latest)
                return {'latest_date': f"{d[:4]}-{d[4:6]}-{d[6:8]}"}
            return {'latest_date': None}
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            return {'latest_date': None}

    async def get_margin_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查询融资融券交易汇总数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            exchange_id: 交易所代码
            page: 页码
            page_size: 每页数量
            sort_by: 排序字段
            sort_order: 排序方向 asc/desc

        Returns:
            包含数据、总数、统计信息的字典
        """
        try:
            # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 计算分页参数
            offset = (page - 1) * page_size

            # 并发查数据、总数、统计
            data, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.margin_repo.get_by_date_range,
                    start_date_fmt,
                    end_date_fmt,
                    exchange_id=exchange_id,
                    limit=page_size,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.margin_repo.get_record_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    exchange_id=exchange_id
                ),
                asyncio.to_thread(
                    self.margin_repo.get_statistics,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    exchange_id=exchange_id
                )
            )

            return {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "statistics": statistics
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
            # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 使用 Repository 获取统计数据
            stats = await asyncio.to_thread(
                self.margin_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            return stats

        except Exception as e:
            logger.error(f"获取融资融券统计数据失败: {str(e)}")
            raise
