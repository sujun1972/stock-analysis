"""
卖方盈利预测数据服务

处理卖方盈利预测数据的业务逻辑
"""

import asyncio
from typing import Optional, Dict, List

from loguru import logger

from app.repositories.report_rc_repository import ReportRcRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class ReportRcService:
    """卖方盈利预测数据服务"""

    def __init__(self):
        self.report_rc_repo = ReportRcRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ ReportRcService initialized")

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def sync_report_rc(
        self,
        ts_code: Optional[str] = None,
        report_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步卖方盈利预测数据

        Args:
            ts_code: 股票代码
            report_date: 研报日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步卖方盈利预测数据: ts_code={ts_code}, report_date={report_date}, start_date={start_date}, end_date={end_date}")

            # 1. 从 Tushare 获取数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.api_client.query,
                'report_rc',
                ts_code=ts_code,
                report_date=report_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning(f"未获取到卖方盈利预测数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从 Tushare 获取到 {len(df)} 条卖方盈利预测数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库（使用 Repository）
            records = await asyncio.to_thread(
                self.report_rc_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条卖方盈利预测数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步卖方盈利预测数据失败: {e}")
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
            required_fields = ['ts_code', 'report_date', 'org_name', 'quarter']
            for field in required_fields:
                if field not in df.columns:
                    raise ValueError(f"缺少必需字段: {field}")

            # 删除缺少必需字段的行
            df = df.dropna(subset=required_fields)

            # 确保日期字段为字符串格式
            if 'report_date' in df.columns:
                df['report_date'] = df['report_date'].astype(str)

            # 处理数值字段的空值
            numeric_fields = [
                'op_rt', 'op_pr', 'tp', 'np',
                'eps', 'pe', 'rd', 'roe', 'ev_ebitda',
                'max_price', 'min_price'
            ]
            for field in numeric_fields:
                if field in df.columns:
                    df[field] = df[field].apply(lambda x: None if str(x).strip() == '' or str(x) == 'nan' else x)

            logger.debug(f"数据验证完成，有效数据: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise

    async def resolve_default_report_date(self) -> Optional[str]:
        """
        返回最近有数据的研报日期（YYYY-MM-DD 格式），用于前端日期选择器回填。

        Returns:
            最近研报日期字符串（如 '2024-01-15'），无数据时返回 None
        """
        latest = await asyncio.to_thread(self.report_rc_repo.get_latest_report_date)
        if latest and len(latest) == 8:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_report_rc_data(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        org_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict:
        """
        查询卖方盈利预测数据

        Args:
            ts_code: 股票代码（可选）
            trade_date: 单日精确查询 YYYY-MM-DD（可选，优先于 start_date/end_date）
            start_date: 开始日期 YYYY-MM-DD（可选）
            end_date: 结束日期 YYYY-MM-DD（可选）
            org_name: 机构名称（可选）
            page: 页码（从1开始）
            page_size: 每页记录数
            sort_by: 排序字段
            sort_order: 排序方向（asc/desc）

        Returns:
            查询结果字典（items, statistics, total）
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 并发获取数据 + 总数 + 统计
            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.report_rc_repo.get_by_date_range,
                    trade_date=trade_date_fmt,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    org_name=org_name,
                    page=page,
                    page_size=page_size,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.report_rc_repo.get_total_count,
                    trade_date=trade_date_fmt,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    org_name=org_name
                ),
                asyncio.to_thread(
                    self.report_rc_repo.get_statistics,
                    start_date=trade_date_fmt or start_date_fmt,
                    end_date=trade_date_fmt or end_date_fmt,
                    ts_code=ts_code
                )
            )

            return {
                "items": items,
                "statistics": statistics,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取卖方盈利预测数据失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """
        获取最新的卖方盈利预测数据

        Returns:
            最新数据
        """
        try:
            # 获取最新研报日期
            latest_date = await asyncio.to_thread(
                self.report_rc_repo.get_latest_report_date
            )

            if not latest_date:
                return {
                    "latest_date": None,
                    "data": []
                }

            # 获取该日期的数据
            items = await asyncio.to_thread(
                self.report_rc_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                page_size=100
            )

            return {
                "latest_date": latest_date,
                "data": items
            }

        except Exception as e:
            logger.error(f"获取最新卖方盈利预测数据失败: {e}")
            raise

    async def get_top_rated_stocks(
        self,
        report_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取高评级股票

        Args:
            report_date: 研报日期 YYYY-MM-DD（可选，默认最新）
            limit: 返回记录数

        Returns:
            高评级股票列表
        """
        try:
            # 如果未指定日期，使用最新日期
            if not report_date:
                latest_date = await asyncio.to_thread(
                    self.report_rc_repo.get_latest_report_date
                )
                if not latest_date:
                    return []
                report_date_fmt = latest_date
            else:
                # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
                report_date_fmt = report_date.replace('-', '')

            # 获取高评级股票
            items = await asyncio.to_thread(
                self.report_rc_repo.get_top_rated_stocks,
                report_date=report_date_fmt,
                limit=limit
            )

            return items

        except Exception as e:
            logger.error(f"获取高评级股票失败: {e}")
            raise
