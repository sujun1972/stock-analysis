"""
股票收盘集合竞价服务

提供股票收盘集合竞价数据的同步和查询功能
数据来源：Tushare Pro stk_auction_c 接口
积分消耗：需要开通股票分钟权限
说明：每天盘后更新,单次请求最大返回10000行数据
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from core.src.providers import DataProviderFactory
from app.core.config import settings
from app.repositories import StkAuctionCRepository


class StkAuctionCService:
    """股票收盘集合竞价服务"""

    def __init__(self):
        self.stk_auction_c_repo = StkAuctionCRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_stk_auction_c(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步股票收盘集合竞价数据

        Args:
            ts_code: 股票代码
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步收盘集合竞价: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 如果没有指定任何参数,默认同步最近1个交易日
            if not ts_code and not trade_date and not start_date and not end_date:
                # 获取最近的交易日(假设最近3天内有交易日)
                trade_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                logger.info(f"未指定参数,默认同步最近交易日: {trade_date}")

            # 获取数据提供者
            provider = self._get_provider()

            # 从Tushare获取数据
            df = await asyncio.to_thread(
                provider.get_stk_auction_c,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) == 0:
                logger.warning("未获取到收盘集合竞价数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 插入数据库
            records = await self._insert_stk_auction_c_data(df)

            logger.info(f"成功同步收盘集合竞价数据 {records} 条")
            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条收盘集合竞价数据"
            }

        except Exception as e:
            logger.error("同步收盘集合竞价失败: {}", str(e), exc_info=True)
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据

        Returns:
            清洗后的数据
        """
        # 移除空行
        df = df.dropna(subset=['trade_date', 'ts_code'])

        # 确保必需字段存在
        required_columns = ['trade_date', 'ts_code']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        # 数值字段转换
        numeric_columns = ['close', 'open', 'high', 'low', 'vol', 'amount', 'vwap']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        logger.info(f"数据清洗完成,有效数据 {len(df)} 条")
        return df

    async def _insert_stk_auction_c_data(self, df: pd.DataFrame) -> int:
        """
        插入收盘集合竞价数据到数据库

        Args:
            df: 数据DataFrame

        Returns:
            插入的记录数
        """
        if len(df) == 0:
            return 0

        # 使用Repository的批量插入方法
        return await asyncio.to_thread(
            self.stk_auction_c_repo.bulk_upsert,
            df
        )

    async def get_stk_auction_c_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        查询收盘集合竞价数据

        Args:
            ts_code: 股票代码(可选)
            start_date: 开始日期 YYYYMMDD(可选)
            end_date: 结束日期 YYYYMMDD(可选)
            limit: 返回记录数
            offset: 偏移量

        Returns:
            查询结果字典
        """
        try:
            # 查询数据
            items = await asyncio.to_thread(
                self.stk_auction_c_repo.get_by_date_range,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                limit=limit,
                offset=offset
            )

            # 查询总记录数
            total = await asyncio.to_thread(
                self.stk_auction_c_repo.get_record_count,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code
            )

            # 查询统计信息
            statistics = await asyncio.to_thread(
                self.stk_auction_c_repo.get_statistics,
                start_date=start_date,
                end_date=end_date
            )

            return {
                "items": items,
                "statistics": statistics,
                "total": total
            }

        except Exception as e:
            logger.error(f"查询收盘集合竞价数据失败: {e}")
            raise

    async def get_latest_data(self) -> Dict[str, Any]:
        """
        获取最新的收盘集合竞价数据

        Returns:
            最新数据字典
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(
                self.stk_auction_c_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "latest_date": None,
                    "items": [],
                    "total": 0
                }

            # 获取该日期的数据
            items = await asyncio.to_thread(
                self.stk_auction_c_repo.get_by_trade_date,
                trade_date=latest_date,
                limit=100
            )

            return {
                "latest_date": latest_date,
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新收盘集合竞价数据失败: {e}")
            raise

    async def get_top_by_vol(
        self,
        trade_date: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        按成交量排名查询收盘集合竞价数据

        Args:
            trade_date: 交易日期 YYYYMMDD
            limit: 返回记录数

        Returns:
            成交量排名列表
        """
        try:
            return await asyncio.to_thread(
                self.stk_auction_c_repo.get_top_by_vol,
                trade_date=trade_date,
                limit=limit
            )
        except Exception as e:
            logger.error(f"查询成交量排名失败: {e}")
            raise
