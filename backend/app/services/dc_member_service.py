"""
东方财富板块成分数据服务

处理东方财富板块成分数据的业务逻辑
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.dc_member_repository import DcMemberRepository
from app.repositories.dc_index_repository import DcIndexRepository
from core.src.providers import DataProviderFactory


class DcMemberService:
    """东方财富板块成分数据服务"""

    def __init__(self):
        self.dc_member_repo = DcMemberRepository()
        self.dc_index_repo = DcIndexRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ DcMemberService initialized")

    def _get_provider(self):
        """获取 Tushare 数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def resolve_default_trade_date(self) -> Optional[str]:
        """
        解析默认交易日期：优先今天，否则回退到表中最新交易日

        Returns:
            YYYY-MM-DD 格式的日期字符串，无数据时返回 None
        """
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(self.dc_member_repo.exists_by_date, today)
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        latest = await asyncio.to_thread(self.dc_member_repo.get_latest_trade_date)
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def sync_dc_member(
        self,
        ts_code: Optional[str] = None,
        con_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步东方财富板块成分数据

        Args:
            ts_code: 板块指数代码（如 BK1184.DC）
            con_code: 成分股票代码（如 002117.SZ）
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步东方财富板块成分数据: ts_code={ts_code}, con_code={con_code}, "
                       f"trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 1. 从 Tushare 获取数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_dc_member,
                ts_code=ts_code,
                con_code=con_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning(f"未获取到东方财富板块成分数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从 Tushare 获取到 {len(df)} 条东方财富板块成分数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库（使用 Repository）
            records = await asyncio.to_thread(
                self.dc_member_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条东方财富板块成分数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步东方财富板块成分数据失败: {e}")
            import traceback
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
            # 确保必需字段存在
            required_fields = ['ts_code', 'con_code', 'trade_date']
            for field in required_fields:
                if field not in df.columns:
                    raise ValueError(f"缺少必需字段: {field}")

            # 删除缺少必需字段的行
            df = df.dropna(subset=required_fields)

            # 确保日期字段为字符串格式
            if 'trade_date' in df.columns:
                df['trade_date'] = df['trade_date'].astype(str)

            # 确保代码字段为字符串格式
            if 'ts_code' in df.columns:
                df['ts_code'] = df['ts_code'].astype(str)
            if 'con_code' in df.columns:
                df['con_code'] = df['con_code'].astype(str)

            # 处理名称字段
            if 'name' in df.columns:
                df['name'] = df['name'].fillna('')

            logger.debug(f"数据验证完成，有效数据: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise

    async def get_dc_member_data(
        self,
        ts_code: Optional[str] = None,
        con_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc'
    ) -> Dict:
        """
        获取东方财富板块成分数据（分页 + 后端排序）

        Args:
            ts_code: 板块代码
            con_code: 成分股票代码
            trade_date: 单日查询（YYYY-MM-DD）
            start_date: 开始日期（YYYY-MM-DD 或 YYYYMMDD）
            end_date: 结束日期（YYYY-MM-DD 或 YYYYMMDD）
            page: 页码，从 1 开始
            page_size: 每页记录数
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            包含数据列表、总数和回填日期的字典
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            trade_date_fmt = trade_date.replace('-', '') if trade_date and '-' in trade_date else trade_date
            start_date_fmt = start_date.replace('-', '') if start_date and '-' in start_date else start_date
            end_date_fmt = end_date.replace('-', '') if end_date and '-' in end_date else end_date

            # 未传 trade_date 时，解析最近有数据的交易日
            resolved_date: Optional[str] = None
            if not trade_date_fmt and not start_date_fmt and not end_date_fmt:
                resolved_date = await self.resolve_default_trade_date()
                if resolved_date:
                    trade_date_fmt = resolved_date.replace('-', '')

            # 并发查数据 + 总数 + 板块名称映射
            items, total, board_name_map = await asyncio.gather(
                asyncio.to_thread(
                    self.dc_member_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    con_code=con_code,
                    trade_date=trade_date_fmt,
                    page=page,
                    page_size=page_size,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.dc_member_repo.get_total_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    con_code=con_code,
                    trade_date=trade_date_fmt
                ),
                asyncio.to_thread(self.dc_index_repo.get_board_name_map)
            )

            # 注入板块名称
            for item in items:
                item['board_name'] = board_name_map.get(item['ts_code'], '')

            result = {
                "items": items,
                "total": total
            }

            # 回传解析后的交易日期（前端用于回填日期选择器）
            if resolved_date and not trade_date:
                result['trade_date'] = resolved_date

            return result

        except Exception as e:
            logger.error(f"获取东方财富板块成分数据失败: {e}")
            raise

    async def get_statistics(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        trade_date: Optional[str] = None
    ) -> Dict:
        """
        获取板块成分统计信息

        Args:
            ts_code: 板块代码
            start_date: 开始日期（YYYY-MM-DD 或 YYYYMMDD）
            end_date: 结束日期（YYYY-MM-DD 或 YYYYMMDD）
            trade_date: 单日查询（YYYY-MM-DD 或 YYYYMMDD）

        Returns:
            统计信息字典
        """
        try:
            trade_date_fmt = trade_date.replace('-', '') if trade_date and '-' in trade_date else trade_date
            start_date_fmt = start_date.replace('-', '') if start_date and '-' in start_date else start_date
            end_date_fmt = end_date.replace('-', '') if end_date and '-' in end_date else end_date

            stats = await asyncio.to_thread(
                self.dc_member_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                trade_date=trade_date_fmt
            )

            return stats

        except Exception as e:
            logger.error(f"获取板块成分统计信息失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """
        获取最新的板块成分数据

        Returns:
            最新数据
        """
        try:
            latest_date = await asyncio.to_thread(
                self.dc_member_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "trade_date": None,
                    "data": []
                }

            items = await asyncio.to_thread(
                self.dc_member_repo.get_by_date_range,
                trade_date=latest_date,
                page=1,
                page_size=100
            )

            return {
                "trade_date": latest_date,
                "data": items
            }

        except Exception as e:
            logger.error(f"获取最新板块成分数据失败: {e}")
            raise
