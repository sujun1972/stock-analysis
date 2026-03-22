"""
业绩快报数据同步服务

提供业绩快报数据的同步、查询等功能
"""

import asyncio
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.express_repository import ExpressRepository
from core.src.providers import DataProviderFactory


class ExpressService:
    """业绩快报数据同步服务"""

    def __init__(self):
        self.express_repo = ExpressRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ ExpressService initialized")

    def _get_provider(self):
        """获取 Tushare Provider"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_express(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None
    ) -> Dict:
        """
        同步业绩快报数据

        Args:
            ts_code: 股票代码（可选）
            ann_date: 公告日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            period: 报告期 YYYYMMDD（可选）

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步业绩快报数据: ts_code={ts_code}, ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}")

            # 获取 Tushare 数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_express,
                ts_code=ts_code,
                ann_date=ann_date,
                start_date=start_date,
                end_date=end_date,
                period=period
            )

            if df is None or df.empty:
                logger.warning("未获取到业绩快报数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"获取到 {len(df)} 条业绩快报数据")

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.express_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条业绩快报数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            error_msg = f"同步业绩快报数据失败: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "records": 0,
                "error": error_msg
            }

    async def get_express_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 30
    ) -> Dict:
        """
        获取业绩快报数据

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            period: 报告期 YYYYMMDD（可选）
            limit: 限制返回数量

        Returns:
            数据列表
        """
        try:
            # 如果指定了报告期，按报告期查询
            if period:
                items = await asyncio.to_thread(
                    self.express_repo.get_by_period,
                    period=period,
                    limit=limit
                )
            # 如果指定了股票代码，按代码查询
            elif ts_code:
                items = await asyncio.to_thread(
                    self.express_repo.get_by_code,
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )
            # 否则按日期范围查询
            else:
                # 提供默认日期范围
                start_date = start_date or '19900101'
                end_date = end_date or '29991231'

                items = await asyncio.to_thread(
                    self.express_repo.get_by_date_range,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )

            # 转换单位（元 -> 亿元）
            for item in items:
                if item.get('revenue') is not None:
                    item['revenue'] = item['revenue'] / 100000000
                if item.get('operate_profit') is not None:
                    item['operate_profit'] = item['operate_profit'] / 100000000
                if item.get('total_profit') is not None:
                    item['total_profit'] = item['total_profit'] / 100000000
                if item.get('n_income') is not None:
                    item['n_income'] = item['n_income'] / 100000000
                if item.get('total_assets') is not None:
                    item['total_assets'] = item['total_assets'] / 100000000
                if item.get('total_hldr_eqy_exc_min_int') is not None:
                    item['total_hldr_eqy_exc_min_int'] = item['total_hldr_eqy_exc_min_int'] / 100000000

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取业绩快报数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取业绩快报统计信息

        Args:
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            ts_code: 股票代码（可选）

        Returns:
            统计信息
        """
        try:
            stats = await asyncio.to_thread(
                self.express_repo.get_statistics,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code
            )

            # 转换单位（元 -> 亿元）
            if stats.get('avg_revenue'):
                stats['avg_revenue'] = stats['avg_revenue'] / 100000000
            if stats.get('max_revenue'):
                stats['max_revenue'] = stats['max_revenue'] / 100000000
            if stats.get('min_revenue'):
                stats['min_revenue'] = stats['min_revenue'] / 100000000
            if stats.get('avg_n_income'):
                stats['avg_n_income'] = stats['avg_n_income'] / 100000000

            return stats

        except Exception as e:
            logger.error(f"获取业绩快报统计信息失败: {e}")
            raise
