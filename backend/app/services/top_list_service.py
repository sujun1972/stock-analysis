"""
龙虎榜每日明细 Service
"""
import asyncio
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger

from app.repositories import TopListRepository
from app.repositories.trading_calendar_repository import TradingCalendarRepository
from core.src.providers import DataProviderFactory


class TopListService:
    """龙虎榜每日明细业务逻辑层"""

    def __init__(self):
        self.top_list_repo = TopListRepository()
        self.calendar_repo = TradingCalendarRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ TopListService initialized")

    async def get_top_list_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        page: int = 1,
        page_size: int = 30
    ) -> Dict:
        """
        获取龙虎榜数据

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            ts_code: 股票代码
            page: 页码（从1开始）
            page_size: 每页记录数

        Returns:
            数据字典，包含 items、total、page、page_size
        """
        # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
        start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
        end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

        offset = (page - 1) * page_size

        # 并发查询数据和总条数
        items, total = await asyncio.gather(
            asyncio.to_thread(
                self.top_list_repo.get_by_date_range,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                limit=page_size,
                offset=offset
            ),
            asyncio.to_thread(
                self.top_list_repo.get_record_count,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code
            )
        )

        # 日期格式转换（YYYYMMDD -> YYYY-MM-DD）
        for item in items:
            if item['trade_date']:
                item['trade_date'] = self._format_date(item['trade_date'])

        # 金额单位换算（元 -> 万元）
        for item in items:
            if item['amount'] is not None:
                item['amount'] = item['amount'] / 10000
            if item['l_sell'] is not None:
                item['l_sell'] = item['l_sell'] / 10000
            if item['l_buy'] is not None:
                item['l_buy'] = item['l_buy'] / 10000
            if item['l_amount'] is not None:
                item['l_amount'] = item['l_amount'] / 10000
            if item['net_amount'] is not None:
                item['net_amount'] = item['net_amount'] / 10000
            if item['float_values'] is not None:
                item['float_values'] = item['float_values'] / 10000

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取龙虎榜统计信息

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD

        Returns:
            统计信息字典
        """
        # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        # 获取统计信息
        statistics = await asyncio.to_thread(
            self.top_list_repo.get_statistics,
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        # 金额单位换算（元 -> 万元）
        statistics['avg_net_amount'] = statistics['avg_net_amount'] / 10000
        statistics['total_net_amount'] = statistics['total_net_amount'] / 10000
        statistics['max_net_amount'] = statistics['max_net_amount'] / 10000
        statistics['min_net_amount'] = statistics['min_net_amount'] / 10000
        statistics['avg_amount'] = statistics['avg_amount'] / 10000

        return statistics

    async def get_latest_data(self) -> Dict:
        """
        获取最新交易日的龙虎榜数据

        Returns:
            最新数据字典
        """
        # 获取最新交易日期
        latest_date = await asyncio.to_thread(
            self.top_list_repo.get_latest_trade_date
        )

        if not latest_date:
            return {
                "latest_date": None,
                "items": [],
                "total": 0
            }

        # 获取最新数据
        items = await asyncio.to_thread(
            self.top_list_repo.get_by_trade_date,
            trade_date=latest_date
        )

        # 日期格式转换
        for item in items:
            if item['trade_date']:
                item['trade_date'] = self._format_date(item['trade_date'])

        # 金额单位换算（元 -> 万元）
        for item in items:
            if item['amount'] is not None:
                item['amount'] = item['amount'] / 10000
            if item['l_sell'] is not None:
                item['l_sell'] = item['l_sell'] / 10000
            if item['l_buy'] is not None:
                item['l_buy'] = item['l_buy'] / 10000
            if item['l_amount'] is not None:
                item['l_amount'] = item['l_amount'] / 10000
            if item['net_amount'] is not None:
                item['net_amount'] = item['net_amount'] / 10000
            if item['float_values'] is not None:
                item['float_values'] = item['float_values'] / 10000

        return {
            "latest_date": self._format_date(latest_date),
            "items": items,
            "total": len(items)
        }

    async def sync_top_list(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        从 Tushare 同步龙虎榜数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD（可选，默认为前一个交易日）
            ts_code: 股票代码（可选）

        Returns:
            同步结果字典
        """
        # 如果没有指定日期，从 trading_calendar 表取最新交易日
        # 注意：top_list 接口的 trade_date 是必需参数，传 None 不会返回最新日期
        if not trade_date:
            trade_date = await asyncio.to_thread(
                self.calendar_repo.get_latest_trading_day
            )
            logger.info(f"未指定日期，使用最新交易日: {trade_date}")

        logger.info(f"开始同步龙虎榜数据: trade_date={trade_date}, ts_code={ts_code}")

        try:
            # 1. 从 Tushare 获取数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_top_list,
                trade_date=trade_date,
                ts_code=ts_code
            )

            if df.empty:
                logger.warning(f"未获取到龙虎榜数据: trade_date={trade_date}")
                return {
                    "status": "success",
                    "message": "未获取到数据",
                    "records": 0
                }

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.top_list_repo.bulk_upsert,
                df
            )

            logger.info(f"✓ 龙虎榜数据同步完成: {records} 条记录")
            return {
                "status": "success",
                "message": f"成功同步 {records} 条龙虎榜记录",
                "records": records,
                "trade_date": trade_date
            }

        except Exception as e:
            logger.error(f"同步龙虎榜数据失败: {e}")
            return {
                "status": "error",
                "message": f"同步失败: {str(e)}",
                "records": 0
            }

    async def get_top_by_net_amount(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取净买入额排名TOP数据

        Args:
            trade_date: 交易日期，格式：YYYY-MM-DD
            limit: 返回记录数

        Returns:
            排名数据列表
        """
        # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
        trade_date_fmt = trade_date.replace('-', '') if trade_date else None

        # 获取排名数据
        items = await asyncio.to_thread(
            self.top_list_repo.get_top_by_net_amount,
            trade_date=trade_date_fmt,
            limit=limit
        )

        # 日期格式转换
        for item in items:
            if item['trade_date']:
                item['trade_date'] = self._format_date(item['trade_date'])

        # 金额单位换算（元 -> 万元）
        for item in items:
            if item['amount'] is not None:
                item['amount'] = item['amount'] / 10000
            if item['l_sell'] is not None:
                item['l_sell'] = item['l_sell'] / 10000
            if item['l_buy'] is not None:
                item['l_buy'] = item['l_buy'] / 10000
            if item['l_amount'] is not None:
                item['l_amount'] = item['l_amount'] / 10000
            if item['net_amount'] is not None:
                item['net_amount'] = item['net_amount'] / 10000
            if item['float_values'] is not None:
                item['float_values'] = item['float_values'] / 10000

        return items

    def _get_provider(self):
        """获取Tushare数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        数据验证和清洗

        Args:
            df: 原始数据

        Returns:
            清洗后的数据
        """
        # 删除重复数据
        df = df.drop_duplicates(subset=['trade_date', 'ts_code'], keep='last')

        # 处理缺失值
        numeric_columns = [
            'close', 'pct_change', 'turnover_rate', 'amount',
            'l_sell', 'l_buy', 'l_amount', 'net_amount',
            'net_rate', 'amount_rate', 'float_values'
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 确保必需列存在
        required_columns = ['trade_date', 'ts_code']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需列: {col}")

        # 删除 trade_date 或 ts_code 为空的记录
        df = df.dropna(subset=['trade_date', 'ts_code'])

        logger.info(f"数据清洗完成，保留 {len(df)} 条有效记录")
        return df

    def _format_date(self, date_str: str) -> str:
        """
        格式化日期字符串（YYYYMMDD -> YYYY-MM-DD）

        Args:
            date_str: 日期字符串，格式：YYYYMMDD

        Returns:
            格式化后的日期字符串，格式：YYYY-MM-DD
        """
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
