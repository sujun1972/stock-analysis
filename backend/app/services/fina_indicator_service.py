"""
财务指标数据同步服务

提供财务指标数据的同步、查询等功能
"""

import asyncio
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.fina_indicator_repository import FinaIndicatorRepository
from core.src.providers import DataProviderFactory


class FinaIndicatorService:
    """财务指标数据同步服务"""

    def __init__(self):
        self.fina_indicator_repo = FinaIndicatorRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ FinaIndicatorService initialized")

    def _get_provider(self):
        """获取 Tushare Provider"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_fina_indicator(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None
    ) -> Dict:
        """
        同步财务指标数据

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
            logger.info(f"开始同步财务指标数据: ts_code={ts_code}, ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}")

            # 获取 Tushare 数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_fina_indicator,
                ts_code=ts_code,
                ann_date=ann_date,
                start_date=start_date,
                end_date=end_date,
                period=period
            )

            if df is None or df.empty:
                logger.warning("未获取到财务指标数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"获取到 {len(df)} 条财务指标数据")

            # 数据验证和清洗：过滤掉缺少必需字段的记录
            required_fields = ['ts_code', 'ann_date', 'end_date']
            before_count = len(df)
            df = df.dropna(subset=required_fields)
            after_count = len(df)

            if before_count > after_count:
                logger.warning(f"过滤掉 {before_count - after_count} 条缺少必需字段的记录")

            if df.empty:
                logger.warning("过滤后无有效数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "过滤后无有效数据"
                }

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.fina_indicator_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条财务指标数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            error_msg = f"同步财务指标数据失败: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "records": 0,
                "error": error_msg
            }

    async def get_fina_indicator_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 30
    ) -> Dict:
        """
        获取财务指标数据

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
                    self.fina_indicator_repo.get_by_period,
                    period=period,
                    limit=limit
                )
            # 如果指定了股票代码，按代码查询
            elif ts_code:
                items = await asyncio.to_thread(
                    self.fina_indicator_repo.get_by_code,
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
                    self.fina_indicator_repo.get_by_date_range,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )

            # 获取统计信息
            statistics = await asyncio.to_thread(
                self.fina_indicator_repo.get_statistics,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code
            )

            return {
                "items": items,
                "total": len(items),
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"获取财务指标数据失败: {str(e)}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取财务指标统计信息

        Args:
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            ts_code: 股票代码（可选）

        Returns:
            统计信息
        """
        try:
            statistics = await asyncio.to_thread(
                self.fina_indicator_repo.get_statistics,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code
            )
            return statistics
        except Exception as e:
            logger.error(f"获取财务指标统计信息失败: {str(e)}")
            raise
