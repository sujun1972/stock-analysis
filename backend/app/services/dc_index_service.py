"""
东方财富板块数据服务

处理东方财富板块（概念/行业/地域）数据的业务逻辑
"""

import asyncio
import traceback
from datetime import datetime
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.dc_index_repository import DcIndexRepository
from core.src.providers import DataProviderFactory


class DcIndexService:
    """东方财富板块数据服务"""

    def __init__(self):
        self.dc_index_repo = DcIndexRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ DcIndexService initialized")

    def _get_provider(self):
        """获取 Tushare 数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_dc_index(
        self,
        ts_code: Optional[str] = None,
        name: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        idx_type: str = '概念板块'
    ) -> Dict:
        """
        同步东方财富板块数据

        Args:
            ts_code: 指数代码
            name: 板块名称
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            idx_type: 板块类型（必填）

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步东方财富板块数据: ts_code={ts_code}, name={name}, "
                       f"trade_date={trade_date}, start_date={start_date}, end_date={end_date}, idx_type={idx_type}")

            # 1. 从 Tushare 获取数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_dc_index,
                ts_code=ts_code,
                name=name,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                idx_type=idx_type
            )

            if df is None or df.empty:
                logger.warning(f"未获取到东方财富板块数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从 Tushare 获取到 {len(df)} 条东方财富板块数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库（使用 Repository）
            records = await asyncio.to_thread(
                self.dc_index_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条东方财富板块数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步东方财富板块数据失败: {e}")
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: 原始数据 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        try:
            required_fields = ['ts_code', 'trade_date']
            for field in required_fields:
                if field not in df.columns:
                    raise ValueError(f"缺少必需字段: {field}")

            df = df.dropna(subset=required_fields)

            if 'trade_date' in df.columns:
                df['trade_date'] = df['trade_date'].astype(str)

            if 'ts_code' in df.columns:
                df['ts_code'] = df['ts_code'].astype(str)

            # Rename 'leading' to 'leading_stock' (leading is a reserved word in PostgreSQL)
            if 'leading' in df.columns:
                df = df.rename(columns={'leading': 'leading_stock'})

            logger.debug(f"数据验证完成，有效数据: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise

    async def resolve_default_trade_date(self) -> Optional[str]:
        """
        解析默认交易日期：优先今天，否则回退到表中最新交易日

        Returns:
            YYYY-MM-DD 格式的日期字符串，或 None
        """
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(self.dc_index_repo.exists_by_date, today)
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        latest = await asyncio.to_thread(self.dc_index_repo.get_latest_trade_date)
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_dc_index_data(
        self,
        trade_date: Optional[str] = None,
        idx_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Dict:
        """
        获取东方财富板块数据（单日分页模式）

        trade_date 为空时自动解析最近有数据的交易日，并回传给前端用于回填日期选择器。

        Args:
            trade_date: 交易日期（YYYY-MM-DD）
            idx_type: 板块类型（概念板块/行业板块/地域板块）
            page: 页码
            page_size: 每页记录数
            sort_by: 排序字段（见 DcIndexRepository.SORTABLE_COLUMNS）
            sort_order: 排序方向（asc/desc）

        Returns:
            包含 items、total、trade_date（YYYY-MM-DD）的字典
        """
        try:
            resolved_date = trade_date or await self.resolve_default_trade_date()

            if not resolved_date:
                return {"items": [], "total": 0, "trade_date": None}

            trade_date_yyyymmdd = resolved_date.replace('-', '')

            result = await asyncio.to_thread(
                self.dc_index_repo.get_by_trade_date,
                trade_date=trade_date_yyyymmdd,
                idx_type=idx_type,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order
            )

            result['trade_date'] = resolved_date
            return result

        except Exception as e:
            logger.error(f"获取东方财富板块数据失败: {e}")
            raise

    async def get_statistics(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        idx_type: Optional[str] = None
    ) -> Dict:
        """
        获取板块数据统计信息

        Args:
            ts_code: 板块代码
            start_date: 开始日期（YYYY-MM-DD 或 YYYYMMDD）
            end_date: 结束日期（YYYY-MM-DD 或 YYYYMMDD）
            idx_type: 板块类型

        Returns:
            统计信息字典
        """
        try:
            start_date_fmt = start_date.replace('-', '') if start_date and '-' in start_date else start_date
            end_date_fmt = end_date.replace('-', '') if end_date and '-' in end_date else end_date

            stats = await asyncio.to_thread(
                self.dc_index_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                idx_type=idx_type
            )

            return stats

        except Exception as e:
            logger.error(f"获取板块数据统计信息失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """
        获取最新的板块数据

        Returns:
            最新数据
        """
        try:
            latest_date = await asyncio.to_thread(
                self.dc_index_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "trade_date": None,
                    "data": []
                }

            items = await asyncio.to_thread(
                self.dc_index_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                limit=100
            )

            return {
                "trade_date": latest_date,
                "data": items
            }

        except Exception as e:
            logger.error(f"获取最新板块数据失败: {e}")
            raise
