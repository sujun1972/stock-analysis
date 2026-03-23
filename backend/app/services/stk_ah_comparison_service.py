"""
AH股比价数据同步服务

负责从 Tushare 获取 AH股比价数据并同步到数据库
"""

import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta
from loguru import logger

from app.repositories import StkAhComparisonRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class StkAhComparisonService:
    """AH股比价数据同步服务"""

    def __init__(self):
        self.stk_ah_comparison_repo = StkAhComparisonRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取 Tushare Provider"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_stk_ah_comparison(
        self,
        hk_code: Optional[str] = None,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步AH股比价数据

        Args:
            hk_code: 港股代码，格式：xxxxx.HK
            ts_code: A股代码，格式：xxxxxx.SH/SZ/BJ
            trade_date: 交易日期，格式：YYYYMMDD
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            同步结果字典

        Examples:
            >>> service = StkAhComparisonService()
            >>> result = await service.sync_stk_ah_comparison(trade_date='20250812')
        """
        try:
            logger.info(f"开始同步AH股比价数据: hk_code={hk_code}, ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 如果没有指定任何日期，默认同步最近30天
            if not trade_date and not start_date and not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                logger.info(f"未指定日期，默认同步最近30天: {start_date} ~ {end_date}")

            # 获取 Tushare Provider
            provider = self._get_provider()

            # 调用 Provider 方法获取数据
            df = await asyncio.to_thread(
                provider.get_stk_ah_comparison,
                hk_code=hk_code,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            # 检查数据
            if df is None or df.empty:
                logger.warning("未获取到AH股比价数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从Tushare获取到 {len(df)} 条AH股比价数据")

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.stk_ah_comparison_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条AH股比价数据到数据库")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            error_msg = f"同步AH股比价数据失败: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "records": 0,
                "error": error_msg
            }

    def _validate_and_clean_data(self, df):
        """
        数据验证和清洗

        Args:
            df: 原始DataFrame

        Returns:
            清洗后的DataFrame
        """
        # 检查必需字段
        required_fields = ['hk_code', 'ts_code', 'trade_date']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 删除trade_date为空的记录
        df = df.dropna(subset=['trade_date'])

        # 确保数值字段为数值类型
        numeric_fields = [
            'hk_pct_chg', 'hk_close', 'close',
            'pct_chg', 'ah_comparison', 'ah_premium'
        ]
        for field in numeric_fields:
            if field in df.columns:
                df[field] = df[field].astype(float, errors='ignore')

        logger.info(f"数据验证和清洗完成，剩余 {len(df)} 条记录")
        return df

    async def get_stk_ah_comparison_data(
        self,
        hk_code: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30
    ) -> Dict:
        """
        查询AH股比价数据

        Args:
            hk_code: 港股代码
            ts_code: A股代码
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            limit: 返回记录数

        Returns:
            包含数据列表和统计信息的字典

        Examples:
            >>> service = StkAhComparisonService()
            >>> result = await service.get_stk_ah_comparison_data(limit=50)
        """
        # 查询数据
        items = await asyncio.to_thread(
            self.stk_ah_comparison_repo.get_by_date_range,
            start_date=start_date,
            end_date=end_date,
            hk_code=hk_code,
            ts_code=ts_code,
            limit=limit
        )

        # 查询统计信息
        statistics = await asyncio.to_thread(
            self.stk_ah_comparison_repo.get_statistics,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "items": items,
            "statistics": statistics,
            "total": len(items)
        }

    async def get_top_premium(self, trade_date: Optional[str] = None, limit: int = 20) -> Dict:
        """
        获取溢价率最高的股票

        Args:
            trade_date: 交易日期，格式：YYYYMMDD，默认最新交易日
            limit: 返回记录数

        Returns:
            包含数据列表的字典

        Examples:
            >>> service = StkAhComparisonService()
            >>> result = await service.get_top_premium(limit=20)
        """
        items = await asyncio.to_thread(
            self.stk_ah_comparison_repo.get_top_premium,
            trade_date=trade_date,
            limit=limit
        )

        return {
            "items": items,
            "total": len(items)
        }

    async def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新交易日期

        Returns:
            最新交易日期（YYYYMMDD格式）

        Examples:
            >>> service = StkAhComparisonService()
            >>> latest_date = await service.get_latest_trade_date()
        """
        latest_date = await asyncio.to_thread(
            self.stk_ah_comparison_repo.get_latest_trade_date
        )

        return latest_date
