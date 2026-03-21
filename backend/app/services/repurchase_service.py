"""
股票回购数据Service

管理股票回购数据的业务逻辑
"""

import asyncio
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.repurchase_repository import RepurchaseRepository
from core.src.providers import DataProviderFactory


class RepurchaseService:
    """股票回购数据服务"""

    def __init__(self):
        self.repurchase_repo = RepurchaseRepository()
        self.provider_factory = DataProviderFactory()

    async def get_repurchase_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        proc: Optional[str] = None,
        limit: int = 30
    ) -> Dict:
        """
        查询回购数据

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            ts_code: 股票代码
            proc: 回购进度
            limit: 限制返回记录数

        Returns:
            包含数据列表和总数的字典
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 查询数据
            items = await asyncio.to_thread(
                self.repurchase_repo.get_by_date_range,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                proc=proc,
                limit=limit
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('end_date'):
                    item['end_date'] = self._format_date(item['end_date'])
                if item.get('exp_date'):
                    item['exp_date'] = self._format_date(item['exp_date'])

                # 金额单位转换：元 -> 万元
                if item.get('amount') is not None:
                    item['amount'] = round(item['amount'] / 10000, 2)

            return {
                'items': items,
                'total': len(items)
            }

        except Exception as e:
            logger.error(f"查询回购数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            ts_code: 股票代码

        Returns:
            统计信息字典
        """
        try:
            # 日期格式转换
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 获取统计
            statistics = await asyncio.to_thread(
                self.repurchase_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code
            )

            # 金额单位转换：元 -> 万元
            statistics['total_amount'] = round(statistics['total_amount'] / 10000, 2)
            statistics['avg_amount'] = round(statistics['avg_amount'] / 10000, 2)
            statistics['max_amount'] = round(statistics['max_amount'] / 10000, 2)
            statistics['min_amount'] = round(statistics['min_amount'] / 10000, 2)

            # 数量单位转换：股 -> 万股
            statistics['total_vol'] = round(statistics['total_vol'] / 10000, 2)

            return statistics

        except Exception as e:
            logger.error(f"获取回购统计信息失败: {e}")
            raise

    async def get_latest_data(self, ts_code: Optional[str] = None) -> Optional[Dict]:
        """
        获取最新回购数据

        Args:
            ts_code: 股票代码

        Returns:
            最新回购记录
        """
        try:
            latest_date = await asyncio.to_thread(
                self.repurchase_repo.get_latest_ann_date,
                ts_code=ts_code
            )

            if not latest_date:
                return None

            items = await asyncio.to_thread(
                self.repurchase_repo.get_by_date_range,
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
                if item.get('exp_date'):
                    item['exp_date'] = self._format_date(item['exp_date'])

                # 金额单位转换
                if item.get('amount') is not None:
                    item['amount'] = round(item['amount'] / 10000, 2)

                return item

            return None

        except Exception as e:
            logger.error(f"获取最新回购数据失败: {e}")
            raise

    async def sync_repurchase(
        self,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步回购数据

        Args:
            ann_date: 公告日期，格式：YYYYMMDD
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步回购数据: ann_date={ann_date}, start_date={start_date}, end_date={end_date}")

            # 1. 获取Tushare数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_repurchase,
                ann_date=ann_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到回购数据")
                return {
                    "status": "success",
                    "message": "未获取到数据",
                    "records": 0
                }

            logger.info(f"获取到 {len(df)} 条回购数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.repurchase_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条回购记录")

            return {
                "status": "success",
                "message": f"成功同步 {records} 条记录",
                "records": records
            }

        except Exception as e:
            logger.error(f"同步回购数据失败: {e}")
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
        required_fields = ['ts_code', 'ann_date']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 移除空的ts_code或ann_date
        df = df.dropna(subset=['ts_code', 'ann_date'])

        # 确保日期格式正确（YYYYMMDD）
        df['ann_date'] = df['ann_date'].astype(str)

        # 处理可选的日期字段
        for date_field in ['end_date', 'exp_date']:
            if date_field in df.columns:
                df[date_field] = df[date_field].astype(str).replace('nan', None)
                df[date_field] = df[date_field].replace('None', None)

        # 处理字符串字段
        if 'proc' in df.columns:
            df['proc'] = df['proc'].astype(str).replace('nan', None)
            df['proc'] = df['proc'].replace('None', None)

        logger.info(f"数据清洗完成，剩余 {len(df)} 条记录")
        return df

    def _format_date(self, date_str: str) -> str:
        """格式化日期：YYYYMMDD -> YYYY-MM-DD"""
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
