"""
股东增减持Service

处理股东增减持数据的业务逻辑
"""

import asyncio
from typing import Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories import StkHoldertradeRepository
from core.src.providers import DataProviderFactory


class StkHoldertradeService:
    """股东增减持服务"""

    def __init__(self):
        self.repo = StkHoldertradeRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_stk_holdertrade(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        trade_type: Optional[str] = None,
        holder_type: Optional[str] = None
    ) -> Dict:
        """
        同步股东增减持数据

        Args:
            ts_code: 股票代码
            ann_date: 公告日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            trade_type: 交易类型 IN=增持 DE=减持
            holder_type: 股东类型 G=高管 P=个人 C=公司

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步股东增减持数据: ts_code={ts_code}, ann_date={ann_date}, "
                       f"start_date={start_date}, end_date={end_date}, "
                       f"trade_type={trade_type}, holder_type={holder_type}")

            # 1. 获取Tushare数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_stk_holdertrade,
                ts_code=ts_code,
                ann_date=ann_date,
                start_date=start_date,
                end_date=end_date,
                trade_type=trade_type,
                holder_type=holder_type
            )

            if df is None or df.empty:
                logger.warning("未获取到股东增减持数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"获取到 {len(df)} 条股东增减持数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(self.repo.bulk_upsert, df)

            logger.info(f"成功同步 {records} 条股东增减持数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步{records}条记录"
            }

        except Exception as e:
            logger.error(f"同步股东增减持数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "error": str(e),
                "message": "同步失败"
            }

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据

        Returns:
            清洗后的数据
        """
        try:
            # 确保必需字段存在
            required_fields = [
                'ts_code', 'ann_date', 'holder_name', 'in_de'
            ]

            for field in required_fields:
                if field not in df.columns:
                    raise ValueError(f"缺少必需字段: {field}")

            # 移除重复记录（基于主键）
            df = df.drop_duplicates(
                subset=['ts_code', 'ann_date', 'holder_name', 'in_de'],
                keep='last'
            )

            # 填充缺失值
            if 'holder_type' not in df.columns:
                df['holder_type'] = None

            if 'begin_date' not in df.columns:
                df['begin_date'] = None

            if 'close_date' not in df.columns:
                df['close_date'] = None

            # 数值字段填充
            numeric_fields = [
                'change_vol', 'change_ratio', 'after_share',
                'after_ratio', 'avg_price', 'total_share'
            ]

            for field in numeric_fields:
                if field not in df.columns:
                    df[field] = None

            return df

        except Exception as e:
            logger.error(f"数据验证清洗失败: {e}")
            raise

    async def get_stk_holdertrade_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        holder_type: Optional[str] = None,
        trade_type: Optional[str] = None,
        limit: int = 100
    ) -> Dict:
        """
        获取股东增减持数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            ts_code: 股票代码
            holder_type: 股东类型
            trade_type: 交易类型
            limit: 限制数量

        Returns:
            数据字典
        """
        try:
            # 日期格式转换 YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 查询数据
            items = await asyncio.to_thread(
                self.repo.get_by_date_range,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                holder_type=holder_type,
                trade_type=trade_type,
                limit=limit
            )

            # 日期格式转换 YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('begin_date'):
                    item['begin_date'] = self._format_date(item['begin_date'])
                if item.get('close_date'):
                    item['close_date'] = self._format_date(item['close_date'])

            # 查询统计信息
            statistics = await asyncio.to_thread(
                self.repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code
            )

            return {
                "items": items,
                "statistics": statistics,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取股东增减持数据失败: {e}")
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
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            ts_code: 股票代码

        Returns:
            统计信息
        """
        try:
            # 日期格式转换
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            statistics = await asyncio.to_thread(
                self.repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code
            )

            return statistics

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """
        获取最新数据

        Returns:
            最新数据信息
        """
        try:
            latest_date = await asyncio.to_thread(self.repo.get_latest_ann_date)

            if not latest_date:
                return {
                    "latest_date": None,
                    "record_count": 0
                }

            # 格式化日期
            latest_date_formatted = self._format_date(latest_date)

            # 获取该日期的记录数
            record_count = await asyncio.to_thread(
                self.repo.get_record_count,
                start_date=latest_date,
                end_date=latest_date
            )

            return {
                "latest_date": latest_date_formatted,
                "record_count": record_count
            }

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            raise

    @staticmethod
    def _format_date(date_str: str) -> str:
        """
        格式化日期 YYYYMMDD -> YYYY-MM-DD

        Args:
            date_str: YYYYMMDD格式的日期

        Returns:
            YYYY-MM-DD格式的日期
        """
        if not date_str or len(date_str) != 8:
            return date_str

        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
