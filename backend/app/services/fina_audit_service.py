"""
财务审计意见数据服务

Author: Claude
Date: 2026-03-22
"""

import asyncio
from typing import Optional, Dict, List
from loguru import logger
import pandas as pd

from app.repositories.fina_audit_repository import FinaAuditRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class FinaAuditService:
    """财务审计意见数据服务"""

    def __init__(self):
        self.fina_audit_repo = FinaAuditRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取 Tushare Provider"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def get_fina_audit_data(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 30
    ) -> Dict:
        """
        获取财务审计意见数据

        Args:
            ts_code: 股票代码
            ann_date: 公告日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            period: 报告期 YYYYMMDD
            limit: 限制返回记录数

        Returns:
            包含数据列表和统计信息的字典
        """
        try:
            # 如果提供了ts_code，使用按股票代码查询
            if ts_code:
                items = await asyncio.to_thread(
                    self.fina_audit_repo.get_by_ts_code,
                    ts_code=ts_code,
                    start_date=start_date or ann_date,
                    end_date=end_date,
                    limit=limit
                )
            else:
                # 否则使用按日期范围查询
                items = await asyncio.to_thread(
                    self.fina_audit_repo.get_by_date_range,
                    start_date=start_date or ann_date,
                    end_date=end_date,
                    limit=limit
                )

            # 获取统计信息
            statistics = await asyncio.to_thread(
                self.fina_audit_repo.get_statistics,
                start_date=start_date or ann_date,
                end_date=end_date
            )

            return {
                "items": items,
                "total": len(items),
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"获取财务审计意见数据失败: {e}")
            raise

    async def sync_fina_audit(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None
    ) -> Dict:
        """
        同步财务审计意见数据

        Args:
            ts_code: 股票代码
            ann_date: 公告日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            period: 报告期 YYYYMMDD

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步财务审计意见数据: ts_code={ts_code}, ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}")

            # 获取 Tushare Provider
            provider = self._get_provider()

            # 从 Tushare 获取数据
            df = await asyncio.to_thread(
                provider.get_fina_audit,
                ts_code=ts_code,
                ann_date=ann_date,
                start_date=start_date,
                end_date=end_date,
                period=period
            )

            if df is None or df.empty:
                logger.warning("未获取到财务审计意见数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.fina_audit_repo.bulk_upsert,
                df
            )

            logger.info(f"✓ 财务审计意见数据同步成功: {records} 条记录")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条记录"
            }

        except Exception as e:
            logger.error(f"同步财务审计意见数据失败: {e}")
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        # 确保必需字段存在
        required_fields = ['ts_code', 'ann_date', 'end_date']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 移除完全重复的行
        df = df.drop_duplicates(subset=['ts_code', 'ann_date', 'end_date'], keep='first')

        # 确保日期格式正确（移除任何非数字字符）
        if 'ann_date' in df.columns:
            df['ann_date'] = df['ann_date'].astype(str).str.replace(r'\D', '', regex=True)

        if 'end_date' in df.columns:
            df['end_date'] = df['end_date'].astype(str).str.replace(r'\D', '', regex=True)

        # 处理数值字段
        if 'audit_fees' in df.columns:
            df['audit_fees'] = pd.to_numeric(df['audit_fees'], errors='coerce')

        logger.debug(f"数据清洗完成，剩余 {len(df)} 条记录")
        return df

    async def get_latest_audit(self, ts_code: str) -> Optional[Dict]:
        """
        获取指定股票的最新审计意见

        Args:
            ts_code: 股票代码

        Returns:
            最新审计意见，如果不存在则返回 None
        """
        try:
            result = await asyncio.to_thread(
                self.fina_audit_repo.get_latest_by_ts_code,
                ts_code
            )
            return result
        except Exception as e:
            logger.error(f"获取最新审计意见失败: {e}")
            raise
