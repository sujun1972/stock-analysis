"""
股东人数数据服务

提供股东人数数据的业务逻辑处理
"""

import asyncio
from typing import Optional, Dict, Any
from loguru import logger
import pandas as pd

from app.repositories.stk_holdernumber_repository import StkHolderNumberRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class StkHolderNumberService:
    """股东人数数据服务"""

    def __init__(self):
        self.stk_holdernumber_repo = StkHolderNumberRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_stk_holdernumber(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步股东人数数据

        Args:
            ts_code: 股票代码（可选）
            ann_date: 公告日期，格式：YYYYMMDD（可选）
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            同步结果字典
        """
        try:
            logger.info(
                f"开始同步股东人数数据: ts_code={ts_code}, ann_date={ann_date}, "
                f"start_date={start_date}, end_date={end_date}"
            )

            # 1. 获取 Tushare 数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_stk_holdernumber,
                ts_code=ts_code,
                ann_date=ann_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到股东人数数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从Tushare获取到 {len(df)} 条股东人数数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            if df.empty:
                logger.warning("数据验证后为空")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "数据验证后为空"
                }

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.stk_holdernumber_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条股东人数数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步股东人数数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    async def get_stk_holdernumber_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        获取股东人数数据

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期，格式：YYYY-MM-DD（可选）
            end_date: 结束日期，格式：YYYY-MM-DD（可选）
            limit: 返回记录数限制

        Returns:
            数据字典
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 获取数据
            items = await asyncio.to_thread(
                self.stk_holdernumber_repo.get_by_code_and_date_range,
                ts_code=ts_code,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                limit=limit
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD（用于前端显示）
            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('end_date'):
                    item['end_date'] = self._format_date(item['end_date'])

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取股东人数数据失败: {e}")
            raise

    async def get_statistics(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取股东人数统计信息

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期，格式：YYYY-MM-DD（可选）
            end_date: 结束日期，格式：YYYY-MM-DD（可选）

        Returns:
            统计信息字典
        """
        try:
            # 日期格式转换
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 获取统计信息
            stats = await asyncio.to_thread(
                self.stk_holdernumber_repo.get_statistics,
                ts_code=ts_code,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    async def get_latest_by_code(
        self,
        ts_code: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        获取指定股票的最新股东人数数据

        Args:
            ts_code: 股票代码
            limit: 返回记录数限制

        Returns:
            数据字典
        """
        try:
            # 获取数据
            items = await asyncio.to_thread(
                self.stk_holdernumber_repo.get_latest_by_code,
                ts_code=ts_code,
                limit=limit
            )

            # 日期格式转换
            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('end_date'):
                    item['end_date'] = self._format_date(item['end_date'])

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            raise

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据DataFrame

        Returns:
            清洗后的DataFrame
        """
        if df is None or df.empty:
            return pd.DataFrame()

        # 必需字段
        required_fields = ['ts_code', 'ann_date', 'end_date']

        # 检查必需字段
        for field in required_fields:
            if field not in df.columns:
                logger.error(f"缺少必需字段: {field}")
                return pd.DataFrame()

        # 删除必需字段为空的行
        df = df.dropna(subset=required_fields)

        # 确保 holder_num 是数值类型
        if 'holder_num' in df.columns:
            df['holder_num'] = pd.to_numeric(df['holder_num'], errors='coerce')

        # 删除所有字段都为空的行
        df = df.dropna(how='all')

        logger.info(f"数据验证完成，剩余 {len(df)} 条有效数据")

        return df

    def _format_date(self, date_str: str) -> str:
        """
        格式化日期：YYYYMMDD -> YYYY-MM-DD

        Args:
            date_str: 日期字符串 YYYYMMDD

        Returns:
            格式化后的日期字符串 YYYY-MM-DD
        """
        if not date_str or len(date_str) != 8:
            return date_str

        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
