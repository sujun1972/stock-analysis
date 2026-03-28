"""
券商每月荐股服务

负责券商荐股数据的同步和查询业务逻辑
"""

import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta
from loguru import logger

from app.repositories.broker_recommend_repository import BrokerRecommendRepository
from core.src.providers import DataProviderFactory


class BrokerRecommendService:
    """券商每月荐股服务"""

    def __init__(self):
        self.broker_repo = BrokerRecommendRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者"""
        try:
            provider = self.provider_factory.get_provider('tushare')
            logger.debug("✓ 已获取Tushare数据提供者")
            return provider
        except Exception as e:
            logger.error(f"获取数据提供者失败: {e}")
            raise

    async def sync_broker_recommend(
        self,
        month: Optional[str] = None
    ) -> Dict:
        """
        同步券商荐股数据

        Args:
            month: 月度,格式：YYYYMM（可选,不传则同步当前月）

        Returns:
            同步结果字典

        Examples:
            >>> service = BrokerRecommendService()
            >>> result = await service.sync_broker_recommend('202106')
        """
        try:
            # 如果没有指定月度,使用当前月度
            if not month:
                month = datetime.now().strftime('%Y%m')
                logger.info(f"未指定月度,默认同步当前月: {month}")

            logger.info(f"开始同步券商荐股数据: month={month}")

            # 获取Tushare数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.pro.broker_recommend,
                month=month
            )

            if df is None or df.empty:
                logger.warning(f"未获取到券商荐股数据: month={month}")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "无可用数据"
                }

            logger.info(f"从Tushare获取到 {len(df)} 条券商荐股数据")

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.broker_repo.bulk_upsert,
                df
            )

            logger.info(f"券商荐股数据同步成功: {records} 条")

            return {
                "status": "success",
                "records": records,
                "month": month
            }

        except Exception as e:
            logger.error(f"同步券商荐股数据失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "records": 0
            }

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: 原始DataFrame

        Returns:
            清洗后的DataFrame
        """
        try:
            # 确保必需列存在
            required_columns = ['month', 'broker', 'ts_code']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"缺少必需列: {col}")

            # 删除必需字段为空的行
            df = df.dropna(subset=required_columns)

            # name字段可以为空,但确保存在
            if 'name' not in df.columns:
                df['name'] = None

            # 去重（按month, broker, ts_code）
            df = df.drop_duplicates(subset=['month', 'broker', 'ts_code'])

            logger.debug(f"数据验证和清洗完成,剩余 {len(df)} 条有效数据")

            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise

    async def get_broker_recommend_data(
        self,
        month: Optional[str] = None,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
        broker: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        查询券商荐股数据

        Args:
            month: 单个月度,格式：YYYYMM
            start_month: 开始月度,格式：YYYYMM
            end_month: 结束月度,格式：YYYYMM
            broker: 券商名称（可选）
            ts_code: 股票代码（可选）
            limit: 限制返回数量
            offset: 偏移量

        Returns:
            数据字典，包含items、statistics和total

        Examples:
            >>> service = BrokerRecommendService()
            >>> result = await service.get_broker_recommend_data(month='202106')
        """
        try:
            # 确定月度范围
            effective_start = start_month
            effective_end = end_month
            if not month and not start_month and not end_month:
                effective_end = datetime.now().strftime('%Y%m')
                effective_start = (datetime.now() - timedelta(days=90)).strftime('%Y%m')
                logger.info(f"未指定日期,默认查询最近3个月: {effective_start} ~ {effective_end}")
            elif not start_month:
                effective_start = '190001'
            elif not end_month:
                effective_end = '299912'

            # 并发查询数据和统计
            if month:
                items_coro = asyncio.to_thread(
                    self.broker_repo.get_by_month, month, broker, limit
                )
                stats_coro = asyncio.to_thread(
                    self.broker_repo.get_statistics, month, month
                )
            else:
                items_coro = asyncio.to_thread(
                    self.broker_repo.get_by_month_range,
                    effective_start, effective_end, broker, ts_code, limit, offset
                )
                stats_coro = asyncio.to_thread(
                    self.broker_repo.get_statistics, effective_start, effective_end
                )

            items, statistics = await asyncio.gather(items_coro, stats_coro)

            return {
                "items": items,
                "statistics": statistics,
                "total": statistics.get('total_records', len(items))
            }

        except Exception as e:
            logger.error(f"查询券商荐股数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_month: 开始月度（可选）
            end_month: 结束月度（可选）

        Returns:
            统计信息字典

        Examples:
            >>> service = BrokerRecommendService()
            >>> stats = await service.get_statistics()
        """
        try:
            stats = await asyncio.to_thread(
                self.broker_repo.get_statistics,
                start_month,
                end_month
            )
            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    async def get_latest_month(self) -> Optional[str]:
        """
        获取最新月度

        Returns:
            最新月度字符串

        Examples:
            >>> service = BrokerRecommendService()
            >>> latest = await service.get_latest_month()
        """
        try:
            latest = await asyncio.to_thread(
                self.broker_repo.get_latest_month
            )
            return latest

        except Exception as e:
            logger.error(f"获取最新月度失败: {e}")
            raise

    async def get_broker_list(
        self,
        month: Optional[str] = None
    ) -> list:
        """
        获取券商列表

        Args:
            month: 月度（可选）

        Returns:
            券商名称列表

        Examples:
            >>> service = BrokerRecommendService()
            >>> brokers = await service.get_broker_list('202106')
        """
        try:
            brokers = await asyncio.to_thread(
                self.broker_repo.get_broker_list,
                month
            )
            return brokers

        except Exception as e:
            logger.error(f"获取券商列表失败: {e}")
            raise

    async def get_top_stocks(
        self,
        month: str,
        limit: int = 20
    ) -> list:
        """
        获取某月被推荐次数最多的股票

        Args:
            month: 月度
            limit: 返回数量

        Returns:
            股票列表

        Examples:
            >>> service = BrokerRecommendService()
            >>> top_stocks = await service.get_top_stocks('202106', 10)
        """
        try:
            stocks = await asyncio.to_thread(
                self.broker_repo.get_top_stocks,
                month,
                limit
            )
            return stocks

        except Exception as e:
            logger.error(f"获取热门股票失败: {e}")
            raise
