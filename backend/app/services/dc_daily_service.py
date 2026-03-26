"""
东方财富概念板块行情服务

处理东方财富概念板块行情数据的业务逻辑
"""

import asyncio
import traceback
from datetime import datetime
from typing import Optional, Dict
from loguru import logger

from app.repositories.dc_daily_repository import DcDailyRepository
from core.src.providers import DataProviderFactory


class DcDailyService:
    """东方财富概念板块行情服务"""

    def __init__(self):
        self.dc_daily_repo = DcDailyRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ DcDailyService initialized")

    def _get_provider(self):
        """获取 Tushare 数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_dc_daily(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        idx_type: Optional[str] = None
    ) -> Dict:
        """
        同步东方财富概念板块行情数据

        Args:
            ts_code: 板块代码
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            idx_type: 板块类型（概念板块/行业板块/地域板块，可选）

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步东方财富概念板块行情数据: ts_code={ts_code}, "
                       f"trade_date={trade_date}, start_date={start_date}, end_date={end_date}, idx_type={idx_type}")

            # 1. 从 Tushare 获取数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_dc_daily,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                idx_type=idx_type
            )

            if df is None or df.empty:
                logger.warning(f"未获取到东方财富概念板块行情数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从 Tushare 获取到 {len(df)} 条东方财富概念板块行情数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库（使用 Repository）
            records = await asyncio.to_thread(
                self.dc_daily_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条东方财富概念板块行情数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步东方财富概念板块行情数据失败: {e}")
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: 原始数据 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        try:
            required_fields = ['ts_code', 'trade_date']
            for field in required_fields:
                if field not in df.columns:
                    raise ValueError(f"缺少必需字段: {field}")

            df = df.dropna(subset=required_fields)

            if 'trade_date' in df.columns:
                df['trade_date'] = df['trade_date'].astype(str)

            if 'ts_code' in df.columns:
                df['ts_code'] = df['ts_code'].astype(str)

            logger.debug(f"数据验证完成，有效数据: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise

    @staticmethod
    def _format_date(date_str: Optional[str]) -> Optional[str]:
        """将 YYYYMMDD 格式转换为 YYYY-MM-DD"""
        if date_str and len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str

    async def resolve_default_trade_date(self) -> Optional[str]:
        """
        未指定日期时解析默认交易日：先查今天是否有数据，无则回退到最近有数据的交易日。

        Returns:
            日期字符串，格式：YYYY-MM-DD；若无任何数据返回 None
        """
        today = datetime.now().strftime('%Y%m%d')
        count = await asyncio.to_thread(
            self.dc_daily_repo.get_record_count,
            start_date=today,
            end_date=today
        )
        if count > 0:
            return self._format_date(today)
        latest = await asyncio.to_thread(self.dc_daily_repo.get_latest_trade_date)
        return self._format_date(latest) if latest else None

    async def get_dc_daily_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc'
    ) -> Dict:
        """
        获取东方财富概念板块行情数据

        Args:
            ts_code: 板块代码
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            page: 页码
            page_size: 每页记录数
            sort_by: 排序字段
            sort_order: 排序方向 asc/desc

        Returns:
            包含数据列表和总数的字典
        """
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'
            offset = (page - 1) * page_size

            items, total = await asyncio.gather(
                asyncio.to_thread(
                    self.dc_daily_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    limit=page_size,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.dc_daily_repo.get_record_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code
                )
            )

            # 格式化日期字段
            for item in items:
                if item.get('trade_date'):
                    item['trade_date'] = self._format_date(item['trade_date'])

            return {
                "items": items,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取东方财富概念板块行情数据失败: {e}")
            raise

    async def get_statistics(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取板块行情数据统计信息

        Args:
            ts_code: 板块代码
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）

        Returns:
            统计信息字典
        """
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            stats = await asyncio.to_thread(
                self.dc_daily_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code
            )

            return stats

        except Exception as e:
            logger.error(f"获取板块行情统计信息失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """
        获取最新的板块行情数据

        Returns:
            最新数据
        """
        try:
            latest_date = await asyncio.to_thread(
                self.dc_daily_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "trade_date": None,
                    "data": []
                }

            items = await asyncio.to_thread(
                self.dc_daily_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                limit=100
            )

            return {
                "trade_date": latest_date,
                "data": items
            }

        except Exception as e:
            logger.error(f"获取最新板块行情数据失败: {e}")
            raise
