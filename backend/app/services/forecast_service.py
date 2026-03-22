"""
业绩预告数据Service

管理业绩预告数据的业务逻辑
"""

import asyncio
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.forecast_repository import ForecastRepository
from core.src.providers import DataProviderFactory


class ForecastService:
    """业绩预告数据服务"""

    def __init__(self):
        self.forecast_repo = ForecastRepository()
        self.provider_factory = DataProviderFactory()

    async def get_forecast_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        period: Optional[str] = None,
        type_: Optional[str] = None,
        limit: int = 30
    ) -> Dict:
        """
        查询业绩预告数据

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            ts_code: 股票代码
            period: 报告期
            type_: 预告类型
            limit: 限制返回记录数

        Returns:
            包含数据列表和总数的字典
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'
            period_fmt = period.replace('-', '') if period else None

            # 查询数据
            items = await asyncio.to_thread(
                self.forecast_repo.get_by_date_range,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                period=period_fmt,
                type_=type_,
                limit=limit
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('end_date'):
                    item['end_date'] = self._format_date(item['end_date'])
                if item.get('first_ann_date'):
                    item['first_ann_date'] = self._format_date(item['first_ann_date'])

            return {
                'items': items,
                'total': len(items)
            }

        except Exception as e:
            logger.error(f"查询业绩预告数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        type_: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            ts_code: 股票代码
            type_: 预告类型

        Returns:
            统计信息字典
        """
        try:
            # 日期格式转换
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 获取统计
            statistics = await asyncio.to_thread(
                self.forecast_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                type_=type_
            )

            return statistics

        except Exception as e:
            logger.error(f"获取业绩预告统计信息失败: {e}")
            raise

    async def get_latest_data(self, ts_code: Optional[str] = None) -> Optional[Dict]:
        """
        获取最新业绩预告数据

        Args:
            ts_code: 股票代码

        Returns:
            最新业绩预告记录
        """
        try:
            latest_date = await asyncio.to_thread(
                self.forecast_repo.get_latest_ann_date,
                ts_code=ts_code
            )

            if not latest_date:
                return None

            items = await asyncio.to_thread(
                self.forecast_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                ts_code=ts_code,
                limit=1
            )

            if items:
                item = items[0]
                # 日期格式转换
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('end_date'):
                    item['end_date'] = self._format_date(item['end_date'])
                if item.get('first_ann_date'):
                    item['first_ann_date'] = self._format_date(item['first_ann_date'])

                return item

            return None

        except Exception as e:
            logger.error(f"获取最新业绩预告数据失败: {e}")
            raise

    async def sync_forecast(
        self,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        type_: Optional[str] = None
    ) -> Dict:
        """
        同步业绩预告数据

        Args:
            ann_date: 公告日期，格式：YYYYMMDD
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            period: 报告期，格式：YYYYMMDD
            type_: 预告类型

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步业绩预告数据: ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}, type={type_}")

            # 1. 获取Tushare数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_forecast,
                ann_date=ann_date,
                start_date=start_date,
                end_date=end_date,
                period=period,
                type_=type_
            )

            if df is None or df.empty:
                logger.warning("未获取到业绩预告数据")
                return {
                    "status": "success",
                    "message": "未获取到数据",
                    "records": 0
                }

            logger.info(f"获取到 {len(df)} 条业绩预告数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.forecast_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条业绩预告记录")

            return {
                "status": "success",
                "message": f"成功同步 {records} 条记录",
                "records": records
            }

        except Exception as e:
            logger.error(f"同步业绩预告数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "message": str(e),
                "error": str(e),
                "records": 0
            }

    def _get_provider(self):
        """获取Tushare数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    def _validate_and_clean_data(self, df):
        """验证和清洗数据"""
        # 确保必需字段存在
        required_fields = ['ts_code', 'ann_date', 'end_date']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 移除空的必需字段
        df = df.dropna(subset=['ts_code', 'ann_date', 'end_date'])

        # 确保日期格式正确（YYYYMMDD）
        df['ann_date'] = df['ann_date'].astype(str)
        df['end_date'] = df['end_date'].astype(str)

        # 处理可选的日期字段
        if 'first_ann_date' in df.columns:
            df['first_ann_date'] = df['first_ann_date'].astype(str).replace('nan', None)
            df['first_ann_date'] = df['first_ann_date'].replace('None', None)

        # 处理字符串字段
        for str_field in ['type', 'summary', 'change_reason']:
            if str_field in df.columns:
                df[str_field] = df[str_field].astype(str).replace('nan', None)
                df[str_field] = df[str_field].replace('None', None)

        logger.info(f"数据清洗完成，剩余 {len(df)} 条记录")
        return df

    def _format_date(self, date_str: str) -> str:
        """格式化日期：YYYYMMDD -> YYYY-MM-DD"""
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
