"""
每日筹码分布数据同步服务

处理筹码分布数据的获取和存储
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, date
from loguru import logger
import pandas as pd

from app.repositories.cyq_chips_repository import CyqChipsRepository
from app.repositories.trading_calendar_repository import TradingCalendarRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class CyqChipsService:
    """每日筹码分布数据同步服务"""

    def __init__(self):
        self.cyq_chips_repo = CyqChipsRepository()
        self.calendar_repo = TradingCalendarRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def sync_cyq_chips(
        self,
        ts_code: str,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步筹码分布数据

        Args:
            ts_code: 股票代码（必填），如 '600000.SH'
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步筹码分布数据: ts_code={ts_code}, trade_date={trade_date}, "
                       f"start_date={start_date}, end_date={end_date}")

            # 获取 Tushare Provider
            provider = self._get_provider()

            # 从 Tushare 获取数据
            df = await asyncio.to_thread(
                provider.get_cyq_chips,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning(f"未获取到筹码分布数据: ts_code={ts_code}")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库（使用 UPSERT）
            records = await asyncio.to_thread(
                self.cyq_chips_repo.bulk_upsert,
                df
            )

            logger.info(f"筹码分布数据同步成功: {records} 条")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条筹码分布数据"
            }

        except Exception as e:
            logger.error(f"同步筹码分布数据失败: {e}")
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        # 1. 确保必需列存在
        required_cols = ['ts_code', 'trade_date', 'price', 'percent']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"缺少必需列: {missing_cols}")

        # 2. 删除缺失关键字段的行
        df = df.dropna(subset=['ts_code', 'trade_date', 'price'])

        # 3. 数据类型转换
        df['ts_code'] = df['ts_code'].astype(str)
        df['trade_date'] = df['trade_date'].astype(str)

        # 4. 去除重复数据（保留最后一条）
        df = df.drop_duplicates(subset=['ts_code', 'trade_date', 'price'], keep='last')

        logger.debug(f"数据验证完成，有效记录数: {len(df)}")
        return df

    async def resolve_default_trade_date(self) -> Optional[str]:
        """返回最近有数据的交易日期（YYYY-MM-DD），用于前端日期选择器回填。"""
        latest = await asyncio.to_thread(self.cyq_chips_repo.get_latest_trade_date)
        if latest and len(latest) == 8:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    def _is_data_stale(self, ts_code: str) -> bool:
        """
        判断指定股票的筹码数据是否过时：
        - 无数据：视为过时
        - 最新数据日期早于最近交易日：视为过时
        """
        latest_in_db = self.cyq_chips_repo.get_latest_trade_date(ts_code)
        if not latest_in_db:
            return True
        latest_trading_day = self.calendar_repo.get_latest_trading_day()
        if not latest_trading_day:
            return False
        # latest_trading_day 可能是 date 对象或 YYYYMMDD 字符串
        if hasattr(latest_trading_day, 'strftime'):
            latest_trading_day = latest_trading_day.strftime('%Y%m%d')
        return latest_in_db < latest_trading_day

    async def get_cyq_chips_with_auto_sync(self, ts_code: str) -> list:
        """
        获取指定股票的最新筹码分布数据，若数据过时则先同步再返回。

        Returns:
            筹码分布数据列表 [{price, percent}, ...]
        """
        stale = await asyncio.to_thread(self._is_data_stale, ts_code)
        if stale:
            logger.info(f"筹码数据不存在或过时，自动同步: {ts_code}")
            await self.sync_cyq_chips(ts_code=ts_code)

        latest_date = await asyncio.to_thread(
            self.cyq_chips_repo.get_latest_trade_date, ts_code
        )
        if not latest_date:
            return []

        items = await asyncio.to_thread(
            self.cyq_chips_repo.get_by_code_and_date_range,
            ts_code=ts_code,
            start_date=latest_date,
            end_date=latest_date,
            limit=2000
        )
        return items

    async def get_cyq_chips_data(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查询筹码分布数据

        Args:
            ts_code: 股票代码（可选）
            trade_date: 单日交易日期 YYYY-MM-DD（可选）
            start_date: 开始日期 YYYY-MM-DD（可选）
            end_date: 结束日期 YYYY-MM-DD（可选）
            page: 页码
            page_size: 每页记录数
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            查询结果字典（items, statistics, total）
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 单日查询：将 trade_date 映射为 start_date/end_date
            if trade_date_fmt and not start_date_fmt and not end_date_fmt:
                start_date_fmt = trade_date_fmt
                end_date_fmt = trade_date_fmt

            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.cyq_chips_repo.get_by_date_range,
                    ts_code=ts_code,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    page=page,
                    page_size=page_size,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.cyq_chips_repo.get_total_count,
                    ts_code=ts_code,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt
                ),
                asyncio.to_thread(
                    self.cyq_chips_repo.get_statistics,
                    ts_code=ts_code,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt
                )
            )

            return {
                "items": items,
                "statistics": statistics,
                "total": total
            }

        except Exception as e:
            logger.error(f"查询筹码分布数据失败: {e}")
            raise

    async def get_statistics(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取筹码分布统计信息

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            统计信息字典
        """
        try:
            stats = await asyncio.to_thread(
                self.cyq_chips_repo.get_statistics,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            return stats

        except Exception as e:
            logger.error(f"获取筹码分布统计信息失败: {e}")
            raise

    async def get_latest_data(self, ts_code: Optional[str] = None) -> Dict[str, Any]:
        """
        获取最新筹码分布数据

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新数据字典
        """
        try:
            latest_date = await asyncio.to_thread(
                self.cyq_chips_repo.get_latest_trade_date,
                ts_code=ts_code
            )

            if not latest_date:
                return {
                    "latest_date": None,
                    "items": []
                }

            if ts_code:
                items = await asyncio.to_thread(
                    self.cyq_chips_repo.get_by_code_and_date_range,
                    ts_code=ts_code,
                    start_date=latest_date,
                    end_date=latest_date,
                    limit=1000
                )
            else:
                items = await asyncio.to_thread(
                    self.cyq_chips_repo.get_by_trade_date,
                    trade_date=latest_date,
                    ts_code=None,
                    limit=1000
                )

            return {
                "latest_date": latest_date,
                "items": items
            }

        except Exception as e:
            logger.error(f"获取最新筹码分布数据失败: {e}")
            raise
