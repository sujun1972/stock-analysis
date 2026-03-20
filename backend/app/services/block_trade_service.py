"""
大宗交易服务

提供大宗交易数据的同步和查询功能
数据来源：Tushare Pro block_trade 接口
积分消耗：2000分/次
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from core.src.providers import DataProviderFactory
from app.core.config import settings
from app.repositories import BlockTradeRepository


class BlockTradeService:
    """大宗交易服务"""

    def __init__(self):
        self.block_trade_repo = BlockTradeRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_block_trade(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步大宗交易数据

        Args:
            trade_date: 交易日期 YYYYMMDD
            ts_code: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步大宗交易: trade_date={trade_date}, ts_code={ts_code}, start_date={start_date}, end_date={end_date}")

            # 如果没有指定任何日期，默认同步最近30天
            if not trade_date and not start_date and not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                logger.info(f"未指定日期，默认同步最近30天: {start_date} ~ {end_date}")

            # 获取数据提供者
            provider = self._get_provider()

            # 从Tushare获取数据
            df = await asyncio.to_thread(
                provider.get_block_trade,
                trade_date=trade_date,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) == 0:
                logger.warning("未获取到大宗交易数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 插入数据库
            records = await self._insert_block_trade_data(df)

            logger.info(f"成功同步大宗交易数据 {records} 条")
            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条大宗交易数据"
            }

        except Exception as e:
            logger.error(f"同步大宗交易失败: {str(e)}", exc_info=True)
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
        numeric_columns = ['price', 'vol', 'amount']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        logger.info(f"数据清洗完成，有效数据 {len(df)} 条")
        return df

    async def _insert_block_trade_data(self, df: pd.DataFrame) -> int:
        """
        插入大宗交易数据到数据库

        Args:
            df: 数据DataFrame

        Returns:
            插入的记录数
        """
        if len(df) == 0:
            return 0

        # 使用 Repository 批量插入
        records = await asyncio.to_thread(self.block_trade_repo.bulk_upsert, df)
        return records

    async def get_block_trade_data(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        查询大宗交易数据

        Args:
            trade_date: 交易日期 YYYY-MM-DD
            ts_code: 股票代码
            limit: 返回记录数

        Returns:
            包含数据的字典
        """
        try:
            # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None

            # 使用 Repository 查询数据
            items = await asyncio.to_thread(
                self.block_trade_repo.get_by_date,
                trade_date=trade_date_fmt,
                ts_code=ts_code,
                limit=limit
            )

            return {
                "items": items,
                "count": len(items)
            }

        except Exception as e:
            logger.error(f"查询大宗交易数据失败: {str(e)}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取大宗交易统计数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD

        Returns:
            统计数据字典
        """
        try:
            # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 使用 Repository 获取统计数据
            stats = await asyncio.to_thread(
                self.block_trade_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            return stats

        except Exception as e:
            logger.error(f"获取大宗交易统计数据失败: {str(e)}")
            raise
