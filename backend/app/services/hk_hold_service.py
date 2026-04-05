"""
北向资金持股服务

提供北向资金持股数据（沪股通、深股通）的同步和查询功能
数据来源：Tushare Pro hk_hold 接口
积分消耗：2000分/次
注意：该接口仅支持到2025年，2026年及以后请使用 moneyflow_hsgt 接口
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from core.src.providers import DataProviderFactory
from app.core.config import settings
from app.repositories import HkHoldRepository


class HkHoldService:
    """北向资金持股服务"""

    def __init__(self):
        self.hk_hold_repo = HkHoldRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def sync_hk_hold(
        self,
        code: Optional[str] = None,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步北向资金持股数据

        Args:
            code: 原始代码（如 90000）
            ts_code: 股票代码（如 600000.SH）
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            exchange: 交易所代码（SH上交所/SZ深交所/HK港股通）

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步北向资金持股: code={code}, ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}, exchange={exchange}")

            # 如果没有指定任何日期，默认同步最近30天
            if not trade_date and not start_date and not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                logger.info(f"未指定日期，默认同步最近30天: {start_date} ~ {end_date}")

            # 获取数据提供者
            provider = self._get_provider()

            # 从Tushare获取数据
            df = await asyncio.to_thread(
                provider.get_hk_hold,
                code=code,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                exchange=exchange
            )

            if df is None or len(df) == 0:
                logger.warning("未获取到北向资金持股数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(self.hk_hold_repo.bulk_upsert, df)

            logger.info(f"成功同步北向资金持股数据 {records} 条")
            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条北向资金持股数据"
            }

        except Exception as e:
            logger.error("同步北向资金持股失败: {}", str(e), exc_info=True)
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

        # 数值字段转换（exchange 是字符串字段，不做转换）
        numeric_columns = ['vol', 'ratio', 'amount']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        logger.info(f"数据清洗完成，有效数据 {len(df)} 条")
        return df

    async def resolve_default_trade_date(self) -> Optional[str]:
        """
        解析默认查询日期：优先今天，否则回退到表中最新交易日

        Returns:
            日期字符串 YYYY-MM-DD 格式，无数据则返回 None
        """
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(self.hk_hold_repo.exists_by_date, today)
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        latest = await asyncio.to_thread(self.hk_hold_repo.get_latest_trade_date)
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_hk_hold_data(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        code: Optional[str] = None,
        exchange: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc',
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        查询北向资金持股数据（支持分页和排序）

        Args:
            trade_date: 交易日期 YYYY-MM-DD
            ts_code: A股代码
            code: 港股代码
            exchange: 交易所代码（SH/SZ）
            sort_by: 排序字段
            sort_order: 排序方向（asc/desc）
            page: 页码（从1开始）
            page_size: 每页记录数

        Returns:
            包含数据、分页信息、统计信息的字典
        """
        try:
            # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None

            # 并发查询数据、总数和统计
            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.hk_hold_repo.get_paged,
                    trade_date=trade_date_fmt,
                    ts_code=ts_code,
                    code=code,
                    exchange=exchange,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    page=page,
                    page_size=page_size
                ),
                asyncio.to_thread(
                    self.hk_hold_repo.get_total_count,
                    trade_date=trade_date_fmt,
                    ts_code=ts_code,
                    code=code,
                    exchange=exchange
                ),
                asyncio.to_thread(
                    self.hk_hold_repo.get_statistics_by_date,
                    trade_date=trade_date_fmt,
                    ts_code=ts_code,
                    code=code,
                    exchange=exchange
                )
            )

            return {
                "items": items,
                "total": total,
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"查询北向资金持股数据失败: {str(e)}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取北向资金持股统计数据

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
                self.hk_hold_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            return stats

        except Exception as e:
            logger.error(f"获取北向资金持股统计数据失败: {str(e)}")
            raise
