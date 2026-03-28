"""
中央结算系统持股汇总数据服务

处理中央结算系统持股汇总数据的业务逻辑
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.ccass_hold_repository import CcassHoldRepository
from core.src.providers import DataProviderFactory


class CcassHoldService:
    """中央结算系统持股汇总数据服务"""

    def __init__(self):
        self.ccass_hold_repo = CcassHoldRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ CcassHoldService initialized")

    def _get_provider(self):
        """获取 Tushare 数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_ccass_hold(
        self,
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步中央结算系统持股汇总数据

        Args:
            ts_code: 股票代码（如 605009.SH）
            hk_code: 港交所代码（如 95009）
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步中央结算系统持股汇总数据: ts_code={ts_code}, hk_code={hk_code}, "
                       f"trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 1. 从 Tushare 获取数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_ccass_hold,
                ts_code=ts_code,
                hk_code=hk_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning(f"未获取到中央结算系统持股汇总数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从 Tushare 获取到 {len(df)} 条中央结算系统持股汇总数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库（使用 Repository）
            records = await asyncio.to_thread(
                self.ccass_hold_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条中央结算系统持股汇总数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步中央结算系统持股汇总数据失败: {e}")
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
            required_fields = ['ts_code', 'trade_date']
            for field in required_fields:
                if field not in df.columns:
                    raise ValueError(f"缺少必需字段: {field}")

            # 删除缺少必需字段的行
            df = df.dropna(subset=required_fields)

            # 确保日期字段为字符串格式
            if 'trade_date' in df.columns:
                df['trade_date'] = df['trade_date'].astype(str)

            # 处理数值字段的空值
            numeric_fields = ['shareholding', 'hold_nums', 'hold_ratio']
            for field in numeric_fields:
                if field in df.columns:
                    df[field] = df[field].apply(lambda x: None if str(x).strip() == '' or str(x) == 'nan' else x)

            logger.debug(f"数据验证完成，有效数据: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise

    async def resolve_default_trade_date(self) -> Optional[str]:
        """
        解析默认交易日期：优先今天，否则回退到表中最新交易日
        Returns: YYYY-MM-DD 格式，无数据时返回 None
        """
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(self.ccass_hold_repo.exists_by_date, today)
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        latest = await asyncio.to_thread(self.ccass_hold_repo.get_latest_trade_date)
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_ccass_hold_data(
        self,
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict:
        """
        获取中央结算系统持股汇总数据

        Args:
            ts_code: 股票代码
            hk_code: 港交所代码
            trade_date: 单日交易日期（YYYY-MM-DD格式）
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            page: 页码
            page_size: 每页记录数
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            数据字典，包含 items、statistics 和 total
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 单日查询：将 trade_date 映射为 start_date/end_date
            if trade_date_fmt and not start_date_fmt and not end_date_fmt:
                start_date_fmt = trade_date_fmt
                end_date_fmt = trade_date_fmt

            # 并发获取数据、总数和统计
            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.ccass_hold_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    hk_code=hk_code,
                    page=page,
                    page_size=page_size,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.ccass_hold_repo.get_total_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    hk_code=hk_code
                ),
                asyncio.to_thread(
                    self.ccass_hold_repo.get_statistics,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code
                )
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item['trade_date']:
                    date_str = item['trade_date']
                    if len(date_str) == 8:
                        item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            return {
                "items": items,
                "statistics": statistics,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取中央结算系统持股汇总数据失败: {e}")
            raise

    async def get_latest_data(
        self,
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        limit: int = 10
    ) -> Dict:
        """
        获取最新的中央结算系统持股汇总数据

        Args:
            ts_code: 股票代码
            hk_code: 港交所代码
            limit: 返回记录数限制

        Returns:
            最新数据列表
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(
                self.ccass_hold_repo.get_latest_trade_date,
                ts_code=ts_code
            )

            if not latest_date:
                return {
                    "latest_date": None,
                    "items": [],
                    "total": 0
                }

            # 获取最新日期的数据
            items = await asyncio.to_thread(
                self.ccass_hold_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                ts_code=ts_code,
                hk_code=hk_code,
                limit=limit
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item['trade_date']:
                    date_str = item['trade_date']
                    if len(date_str) == 8:
                        item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            # 格式化最新日期
            formatted_date = None
            if latest_date and len(latest_date) == 8:
                formatted_date = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8]}"

            return {
                "latest_date": formatted_date,
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新中央结算系统持股汇总数据失败: {e}")
            raise

    async def get_top_shareholding(
        self,
        trade_date: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取持股量排名前N的股票

        Args:
            trade_date: 交易日期（YYYY-MM-DD格式）
            limit: 返回记录数限制

        Returns:
            排名数据列表
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            trade_date_fmt = trade_date.replace('-', '')

            # 获取排名数据
            items = await asyncio.to_thread(
                self.ccass_hold_repo.get_top_by_shareholding,
                trade_date=trade_date_fmt,
                limit=limit
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item['trade_date']:
                    date_str = item['trade_date']
                    if len(date_str) == 8:
                        item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            return items

        except Exception as e:
            logger.error(f"获取持股量排名失败: {e}")
            raise
