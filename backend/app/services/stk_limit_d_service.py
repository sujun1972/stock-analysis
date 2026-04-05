"""
每日涨跌停价格服务

管理每日涨跌停价格数据的同步和查询
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from app.repositories.stk_limit_d_repository import StkLimitDRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class StkLimitDService:
    """每日涨跌停价格服务"""

    def __init__(self):
        self.stk_limit_d_repo = StkLimitDRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ StkLimitDService initialized")

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def sync_stk_limit_d(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步每日涨跌停价格数据

        Args:
            ts_code: 股票代码（可选）
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            同步结果
        """
        try:
            logger.info(
                f"开始同步每日涨跌停价格: ts_code={ts_code}, trade_date={trade_date}, "
                f"start_date={start_date}, end_date={end_date}"
            )

            # 获取 Tushare Provider
            provider = self._get_provider()

            # 调用 Provider 获取数据
            df = await asyncio.to_thread(
                provider.get_stk_limit_d,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到每日涨跌停价格数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.stk_limit_d_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条每日涨跌停价格记录")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条记录"
            }

        except Exception as e:
            logger.error(f"同步每日涨跌停价格失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _validate_and_clean_data(self, df):
        """
        数据验证和清洗

        Args:
            df: 原始 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        # 确保必需字段存在
        required_columns = ['trade_date', 'ts_code']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        # 删除trade_date或ts_code为空的行
        df = df.dropna(subset=['trade_date', 'ts_code'])

        # 转换日期格式（如果需要）
        if 'trade_date' in df.columns:
            df['trade_date'] = df['trade_date'].astype(str).str.replace('-', '')

        logger.info(f"数据验证完成，有效记录数: {len(df)}")
        return df

    async def get_stk_limit_d_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 30
    ) -> Dict[str, Any]:
        """
        获取每日涨跌停价格数据（支持分页）

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            page: 页码（从1开始）
            page_size: 每页记录数

        Returns:
            数据、统计信息和总记录数
        """
        try:
            # 如果没有指定日期范围，默认查询最近30天
            if not start_date and not end_date:
                end_date_dt = datetime.now()
                start_date_dt = end_date_dt - timedelta(days=30)
                start_date = start_date_dt.strftime('%Y%m%d')
                end_date = end_date_dt.strftime('%Y%m%d')

            effective_start = start_date or '19900101'
            effective_end = end_date or '29991231'
            offset = (page - 1) * page_size

            # 并发查询数据、总数、统计信息
            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.stk_limit_d_repo.get_by_date_range,
                    start_date=effective_start,
                    end_date=effective_end,
                    ts_code=ts_code,
                    limit=page_size,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.stk_limit_d_repo.get_total_count,
                    start_date=effective_start,
                    end_date=effective_end,
                    ts_code=ts_code
                ),
                asyncio.to_thread(
                    self.stk_limit_d_repo.get_statistics,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code
                )
            )

            return {
                "items": items,
                "statistics": statistics,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取每日涨跌停价格数据失败: {e}")
            raise

    async def get_latest_data(self, limit: int = 100) -> Dict[str, Any]:
        """
        获取最新的每日涨跌停价格数据

        Args:
            limit: 返回记录数限制

        Returns:
            最新数据
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(
                self.stk_limit_d_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "items": [],
                    "latest_date": None,
                    "total": 0
                }

            # 查询该日期的数据
            items = await asyncio.to_thread(
                self.stk_limit_d_repo.get_by_trade_date,
                trade_date=latest_date
            )

            # 限制返回数量
            items = items[:limit] if items else []

            return {
                "items": items,
                "latest_date": latest_date,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新每日涨跌停价格数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取统计信息

        Args:
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            ts_code: 股票代码（可选）

        Returns:
            统计信息
        """
        try:
            statistics = await asyncio.to_thread(
                self.stk_limit_d_repo.get_statistics,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code
            )

            return statistics

        except Exception as e:
            logger.error(f"获取每日涨跌停价格统计信息失败: {e}")
            raise
