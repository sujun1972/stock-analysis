"""
停复牌信息同步服务
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from loguru import logger
import pandas as pd

from app.repositories.suspend_repository import SuspendRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class SuspendService:
    """停复牌信息同步服务"""

    def __init__(self):
        self.suspend_repo = SuspendRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取 Tushare Provider"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_suspend(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        suspend_type: Optional[str] = None
    ) -> Dict:
        """
        同步停复牌信息

        Args:
            ts_code: 股票代码（可输入多值，逗号分隔）
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            suspend_type: 停复牌类型，S-停牌，R-复牌

        Returns:
            同步结果

        Examples:
            >>> service = SuspendService()
            >>> result = await service.sync_suspend(trade_date='20240315', suspend_type='S')
        """
        try:
            logger.info(f"开始同步停复牌信息: ts_code={ts_code}, trade_date={trade_date}, "
                       f"start_date={start_date}, end_date={end_date}, suspend_type={suspend_type}")

            # 获取 Tushare Provider
            provider = self._get_provider()

            # 如果没有指定任何参数，同步最近30天的数据
            if not any([ts_code, trade_date, start_date, end_date]):
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                logger.info(f"未指定参数，默认同步最近30天: {start_date} ~ {end_date}")

            # 从 Tushare 获取数据
            df = await asyncio.to_thread(
                provider.get_suspend_d,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                suspend_type=suspend_type
            )

            if df is None or df.empty:
                logger.warning("未获取到停复牌数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从 Tushare 获取到 {len(df)} 条停复牌记录")

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.suspend_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条停复牌记录")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条记录"
            }

        except Exception as e:
            logger.error(f"同步停复牌信息失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "error": str(e),
                "message": f"同步失败: {str(e)}"
            }

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        # 确保必需字段存在
        required_fields = ['ts_code', 'trade_date', 'suspend_type']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 删除必需字段为空的行
        df = df.dropna(subset=required_fields)

        # 确保日期格式正确（YYYYMMDD）
        df['trade_date'] = df['trade_date'].astype(str).str.replace('-', '')

        # 确保 suspend_type 只有 S 或 R
        df = df[df['suspend_type'].isin(['S', 'R'])]

        # suspend_timing 可以为空
        if 'suspend_timing' not in df.columns:
            df['suspend_timing'] = None

        logger.info(f"数据验证完成，有效记录数: {len(df)}")

        return df

    async def get_suspend_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        suspend_type: Optional[str] = None,
        limit: int = 100,
        page: int = 1
    ) -> Dict:
        """
        查询停复牌数据（支持分页）

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            ts_code: 股票代码
            suspend_type: 停复牌类型，S-停牌，R-复牌
            limit: 每页记录数
            page: 页码（从1开始）

        Returns:
            停复牌数据（包含分页信息）
        """
        try:
            # 如果没有指定日期，默认查询最近30天
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            # 计算 offset
            offset = (page - 1) * limit

            # 查询总数
            total = await asyncio.to_thread(
                self.suspend_repo.count_by_date_range,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                suspend_type=suspend_type
            )

            # 查询数据
            items = await asyncio.to_thread(
                self.suspend_repo.get_by_date_range,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                suspend_type=suspend_type,
                limit=limit,
                offset=offset
            )

            # 日期格式转换：YYYYMMDD → YYYY-MM-DD
            for item in items:
                if item.get('trade_date'):
                    date_str = item['trade_date']
                    item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": limit,
                "total_pages": (total + limit - 1) // limit if limit > 0 else 0
            }

        except Exception as e:
            logger.error(f"查询停复牌数据失败: {str(e)}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取停复牌统计信息

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            统计信息
        """
        try:
            # 如果没有指定日期，默认查询最近30天
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            stats = await asyncio.to_thread(
                self.suspend_repo.get_statistics,
                start_date=start_date,
                end_date=end_date
            )

            return stats

        except Exception as e:
            logger.error(f"获取停复牌统计信息失败: {str(e)}")
            raise

    async def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新的交易日期

        Returns:
            最新交易日期（YYYY-MM-DD格式）
        """
        try:
            latest = await asyncio.to_thread(
                self.suspend_repo.get_latest_trade_date
            )

            if latest:
                # 转换为 YYYY-MM-DD 格式
                return f"{latest[:4]}-{latest[4:6]}-{latest[6:]}"

            return None

        except Exception as e:
            logger.error(f"获取最新交易日期失败: {str(e)}")
            raise
