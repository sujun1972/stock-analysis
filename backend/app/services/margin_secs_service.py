"""
融资融券标的 Service

业务逻辑层，处理融资融券标的数据的同步、查询和统计
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime
from loguru import logger
import pandas as pd

from core.src.providers import DataProviderFactory
from app.core.config import settings
from app.repositories import MarginSecsRepository


class MarginSecsService:
    """融资融券标的服务"""

    def __init__(self):
        """初始化服务"""
        self.margin_secs_repo = MarginSecsRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ MarginSecsService initialized")

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def sync_margin_secs(
        self,
        trade_date: Optional[str] = None,
        exchange: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步融资融券标的数据

        Args:
            trade_date: 交易日期（YYYYMMDD）
            exchange: 交易所代码（SSE/SZSE/BSE）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            同步结果

        Examples:
            >>> service = MarginSecsService()
            >>> result = await service.sync_margin_secs(trade_date='20240417')
        """
        try:
            logger.info(f"开始同步融资融券标的: trade_date={trade_date}, exchange={exchange}")

            # 1. 从 Tushare 获取数据
            df = await self._fetch_from_tushare(
                trade_date=trade_date,
                exchange=exchange,
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                logger.warning("未获取到数据")
                return {
                    "status": "success",
                    "message": "未获取到数据",
                    "records": 0
                }

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 保存到数据库
            records = await asyncio.to_thread(
                self.margin_secs_repo.bulk_upsert, df
            )

            logger.info(f"成功同步 {records} 条融资融券标的记录")

            return {
                "status": "success",
                "message": f"成功同步 {records} 条记录",
                "records": records,
                "date_range": {
                    "start": df['trade_date'].min(),
                    "end": df['trade_date'].max()
                }
            }

        except Exception as e:
            logger.error(f"同步融资融券标的失败: {e}")
            return {
                "status": "error",
                "message": f"同步失败: {str(e)}",
                "records": 0
            }

    async def resolve_default_trade_date(self) -> Optional[str]:
        """
        解析默认交易日期：优先今天，否则回退到表中最新交易日

        Returns:
            YYYY-MM-DD 格式的日期，或 None
        """
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(self.margin_secs_repo.exists_by_date, today)
        if has_today:
            return self._format_date_for_display(today)
        latest = await asyncio.to_thread(self.margin_secs_repo.get_latest_trade_date)
        if latest:
            return self._format_date_for_display(latest)
        return None

    async def get_margin_secs_data(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        exchange: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> Dict:
        """
        获取融资融券标的数据（单日筛选 + 分页）

        Args:
            trade_date: 交易日期（YYYY-MM-DD 或 YYYYMMDD），为空时自动解析最近有数据的交易日
            ts_code: 标的代码
            exchange: 交易所代码
            page: 页码（从1开始）
            page_size: 每页记录数

        Returns:
            数据、统计信息、总数、回填的交易日期
        """
        try:
            # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None

            # 未指定日期时自动解析最近有数据的交易日
            resolved_date: Optional[str] = None
            if not trade_date_fmt:
                resolved_date = await self.resolve_default_trade_date()
                if resolved_date:
                    trade_date_fmt = resolved_date.replace('-', '')
            else:
                resolved_date = self._format_date_for_display(trade_date_fmt)

            if not trade_date_fmt:
                return {
                    "items": [],
                    "statistics": {},
                    "total": 0,
                    "trade_date": None
                }

            offset = (page - 1) * page_size

            # 并发获取数据、总数、统计
            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.margin_secs_repo.get_by_trade_date_paged,
                    trade_date=trade_date_fmt,
                    ts_code=ts_code,
                    exchange=exchange,
                    limit=page_size,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.margin_secs_repo.get_total_count,
                    trade_date=trade_date_fmt,
                    ts_code=ts_code,
                    exchange=exchange
                ),
                asyncio.to_thread(
                    self.margin_secs_repo.get_statistics,
                    start_date=trade_date_fmt,
                    end_date=trade_date_fmt,
                    exchange=exchange
                )
            )

            # 日期格式转换用于显示（YYYYMMDD -> YYYY-MM-DD）
            for item in items:
                if item.get('trade_date'):
                    item['trade_date'] = self._format_date_for_display(item['trade_date'])

            return {
                "items": items,
                "statistics": statistics,
                "total": total,
                "trade_date": resolved_date
            }

        except Exception as e:
            logger.error(f"获取融资融券标的数据失败: {e}")
            raise

    async def get_latest_data(self, exchange: Optional[str] = None) -> Dict:
        """
        获取最新交易日的数据

        Args:
            exchange: 交易所代码（可选）

        Returns:
            最新数据
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(
                self.margin_secs_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "items": [],
                    "statistics": {},
                    "trade_date": None
                }

            # 获取该日期的数据
            items = await asyncio.to_thread(
                self.margin_secs_repo.get_by_trade_date,
                trade_date=latest_date,
                exchange=exchange
            )

            # 获取交易所分布
            distribution = await asyncio.to_thread(
                self.margin_secs_repo.get_exchange_distribution,
                trade_date=latest_date
            )

            # 日期格式转换
            for item in items:
                if item.get('trade_date'):
                    item['trade_date'] = self._format_date_for_display(item['trade_date'])

            return {
                "items": items,
                "statistics": {
                    "total_count": len(items),
                    "trade_date": self._format_date_for_display(latest_date),
                    "exchange_distribution": distribution
                },
                "trade_date": self._format_date_for_display(latest_date)
            }

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            raise

    async def _fetch_from_tushare(
        self,
        trade_date: Optional[str] = None,
        exchange: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        从 Tushare 获取数据

        Args:
            trade_date: 交易日期
            exchange: 交易所代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame
        """
        try:
            # 准备参数
            params = {}
            if trade_date:
                params['trade_date'] = trade_date
            if exchange:
                params['exchange'] = exchange
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            logger.info(f"从 Tushare 获取融资融券标的数据，参数: {params}")

            # 获取数据提供者
            provider = self._get_provider()

            # 调用 Tushare API（通过 api_client.pro）
            df = await asyncio.to_thread(
                provider.api_client.pro.margin_secs,
                **params
            )

            logger.info(f"从 Tushare 获取到 {len(df)} 条记录")
            return df

        except Exception as e:
            logger.error(f"从 Tushare 获取数据失败: {e}")
            raise

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        try:
            # 检查必需列
            required_columns = ['trade_date', 'ts_code', 'name', 'exchange']
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                raise ValueError(f"缺少必需列: {missing_columns}")

            # 删除重复记录
            before_count = len(df)
            df = df.drop_duplicates(subset=['trade_date', 'ts_code'])
            after_count = len(df)
            if before_count != after_count:
                logger.warning(f"删除了 {before_count - after_count} 条重复记录")

            # 删除空值记录
            df = df.dropna(subset=['trade_date', 'ts_code'])

            # 数据类型转换
            df['trade_date'] = df['trade_date'].astype(str)
            df['ts_code'] = df['ts_code'].astype(str)
            df['name'] = df['name'].astype(str)
            df['exchange'] = df['exchange'].astype(str)

            logger.info(f"数据验证完成，有效记录数: {len(df)}")
            return df

        except Exception as e:
            logger.error(f"数据验证和清洗失败: {e}")
            raise

    def _format_date_for_display(self, date_str: str) -> str:
        """
        格式化日期用于显示（YYYYMMDD -> YYYY-MM-DD）

        Args:
            date_str: YYYYMMDD 格式的日期

        Returns:
            YYYY-MM-DD 格式的日期
        """
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
