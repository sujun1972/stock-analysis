"""
中央结算系统持股明细数据服务

处理中央结算系统持股明细数据的业务逻辑
"""

import asyncio
from typing import Optional, Dict, List
from loguru import logger
import pandas as pd

from app.repositories.ccass_hold_detail_repository import CcassHoldDetailRepository
from core.src.providers import DataProviderFactory


class CcassHoldDetailService:
    """中央结算系统持股明细数据服务"""

    def __init__(self):
        self.ccass_hold_detail_repo = CcassHoldDetailRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ CcassHoldDetailService initialized")

    def _get_provider(self):
        """获取 Tushare 数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_ccass_hold_detail(
        self,
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步中央结算系统持股明细数据

        Args:
            ts_code: 股票代码（如 00960.HK）
            hk_code: 港交所代码（如 95009）
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步中央结算系统持股明细数据: ts_code={ts_code}, hk_code={hk_code}, "
                       f"trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 1. 从 Tushare 获取数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_ccass_hold_detail,
                ts_code=ts_code,
                hk_code=hk_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning(f"未获取到中央结算系统持股明细数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从 Tushare 获取到 {len(df)} 条中央结算系统持股明细数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库（使用 Repository）
            records = await asyncio.to_thread(
                self.ccass_hold_detail_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条中央结算系统持股明细数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步中央结算系统持股明细数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
        if df is None or df.empty:
            return df

        # 确保必要字段存在
        required_columns = ['trade_date', 'ts_code', 'col_participant_id']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必要字段: {col}")

        # 移除完全重复的行
        original_count = len(df)
        df = df.drop_duplicates(subset=['trade_date', 'ts_code', 'col_participant_id'])
        if len(df) < original_count:
            logger.warning(f"移除了 {original_count - len(df)} 条重复数据")

        # 处理空值（将空字符串替换为None）
        df = df.replace('', None)

        # 数值字段处理
        if 'col_shareholding' in df.columns:
            df['col_shareholding'] = pd.to_numeric(df['col_shareholding'], errors='coerce')

        if 'col_shareholding_percent' in df.columns:
            df['col_shareholding_percent'] = pd.to_numeric(df['col_shareholding_percent'], errors='coerce')

        logger.info(f"数据验证和清洗完成，保留 {len(df)} 条有效数据")
        return df

    async def get_ccass_hold_detail_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        col_participant_id: Optional[str] = None,
        limit: int = 30
    ) -> Dict:
        """
        获取中央结算系统持股明细数据（从数据库）

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            ts_code: 股票代码
            col_participant_id: 参与者编号
            limit: 返回记录数限制

        Returns:
            数据和统计信息
        """
        try:
            # 查询数据
            items = await asyncio.to_thread(
                self.ccass_hold_detail_repo.get_by_date_range,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                col_participant_id=col_participant_id,
                limit=limit
            )

            # 查询统计信息
            statistics = await asyncio.to_thread(
                self.ccass_hold_detail_repo.get_statistics,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code
            )

            return {
                "items": items,
                "statistics": statistics,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取中央结算系统持股明细数据失败: {e}")
            raise

    async def get_latest_data(self, ts_code: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        获取最新的中央结算系统持股明细数据

        Args:
            ts_code: 股票代码（可选）
            limit: 返回记录数限制

        Returns:
            最新数据列表
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(
                self.ccass_hold_detail_repo.get_latest_trade_date,
                ts_code=ts_code
            )

            if not latest_date:
                return []

            # 获取该日期的数据
            items = await asyncio.to_thread(
                self.ccass_hold_detail_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                ts_code=ts_code,
                limit=limit
            )

            return items

        except Exception as e:
            logger.error(f"获取最新中央结算系统持股明细数据失败: {e}")
            raise

    async def get_top_participants(
        self,
        trade_date: str,
        ts_code: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取指定日期的TOP持股机构

        Args:
            trade_date: 交易日期 YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 返回TOP N

        Returns:
            TOP持股机构列表
        """
        try:
            participants = await asyncio.to_thread(
                self.ccass_hold_detail_repo.get_top_participants,
                trade_date=trade_date,
                ts_code=ts_code,
                limit=limit
            )

            return participants

        except Exception as e:
            logger.error(f"获取TOP持股机构失败: {e}")
            raise
