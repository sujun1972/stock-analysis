"""
机构调研表服务

负责机构调研数据的同步和查询业务逻辑
"""

import asyncio
import traceback
from datetime import datetime
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.stk_surv_repository import StkSurvRepository
from core.src.providers import DataProviderFactory


class StkSurvService:
    """机构调研表服务"""

    def __init__(self):
        self.stk_surv_repo = StkSurvRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ StkSurvService initialized")

    async def sync_stk_surv(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步机构调研数据

        Args:
            ts_code: 股票代码
            trade_date: 调研日期 YYYYMMDD
            start_date: 调研开始日期 YYYYMMDD
            end_date: 调研结束日期 YYYYMMDD

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步机构调研数据: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 1. 获取Tushare数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_stk_surv,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从Tushare获取到 {len(df)} 条记录")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.stk_surv_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条机构调研记录")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条记录"
            }

        except Exception as e:
            logger.error(f"同步机构调研数据失败: {e}\n{traceback.format_exc()}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"同步失败: {str(e)}"
            }

    async def get_stk_surv_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        org_type: Optional[str] = None,
        rece_mode: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        获取机构调研数据

        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            ts_code: 股票代码（可选）
            org_type: 接待公司类型（可选）
            rece_mode: 接待方式（可选）
            limit: 返回记录数限制
            offset: 偏移量

        Returns:
            数据字典，包含items、total和statistics
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 并发查询数据和统计
            items, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.stk_surv_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    org_type=org_type,
                    rece_mode=rece_mode,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.stk_surv_repo.get_statistics,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt
                )
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD（用于前端显示）
            for item in items:
                if item['surv_date']:
                    item['surv_date'] = self._format_date_for_display(item['surv_date'])

            return {
                "items": items,
                "statistics": statistics,
                "total": statistics.get('total_records', len(items))
            }

        except Exception as e:
            logger.error(f"获取机构调研数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）

        Returns:
            统计信息字典
        """
        try:
            # 日期格式转换
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            stats = await asyncio.to_thread(
                self.stk_surv_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    async def get_latest_data(self, limit: int = 20) -> Dict:
        """
        获取最新的机构调研数据

        Args:
            limit: 返回记录数限制

        Returns:
            数据字典
        """
        try:
            # 获取最新调研日期
            latest_date = await asyncio.to_thread(
                self.stk_surv_repo.get_latest_date
            )

            if not latest_date:
                return {"items": [], "total": 0}

            # 获取该日期的数据
            items = await asyncio.to_thread(
                self.stk_surv_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                limit=limit
            )

            # 日期格式转换
            for item in items:
                if item['surv_date']:
                    item['surv_date'] = self._format_date_for_display(item['surv_date'])

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            raise

    def _get_provider(self):
        """获取Tushare数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: 原始DataFrame

        Returns:
            清洗后的DataFrame
        """
        # 确保必需列存在
        required_columns = ['ts_code', 'surv_date']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需列: {col}")

        # 确保日期格式为 YYYYMMDD（8位）
        if 'surv_date' in df.columns:
            df['surv_date'] = df['surv_date'].astype(str).str.replace('-', '')
            # 验证日期格式
            invalid_dates = df[df['surv_date'].str.len() != 8]
            if not invalid_dates.empty:
                logger.warning(f"发现 {len(invalid_dates)} 条无效surv_date记录，将被过滤")
                df = df[df['surv_date'].str.len() == 8]

        # 删除重复记录（基于ts_code, surv_date, fund_visitors）
        df = df.drop_duplicates(subset=['ts_code', 'surv_date', 'fund_visitors'], keep='last')

        # 处理空值
        df = df.fillna({
            'name': '',
            'fund_visitors': '',
            'rece_place': '',
            'rece_mode': '',
            'rece_org': '',
            'org_type': '',
            'comp_rece': '',
            'content': ''
        })

        return df

    def _format_date_for_display(self, date_str: str) -> str:
        """
        格式化日期用于前端显示

        Args:
            date_str: YYYYMMDD格式的日期字符串

        Returns:
            YYYY-MM-DD格式的日期字符串
        """
        if not date_str or len(date_str) != 8:
            return date_str

        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        except Exception:
            return date_str
