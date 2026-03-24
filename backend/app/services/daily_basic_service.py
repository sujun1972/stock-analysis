"""
每日指标服务

提供每日指标数据（换手率、市盈率、市净率等）的同步和查询功能
数据来源：Tushare Pro daily_basic 接口
积分消耗：2000分/次
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from core.src.providers import DataProviderFactory
from app.core.config import settings
from app.repositories import DailyBasicRepository


class DailyBasicService:
    """每日指标服务"""

    def __init__(self):
        self.daily_basic_repo = DailyBasicRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_daily_basic(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步每日指标数据

        Args:
            trade_date: 交易日期 YYYYMMDD
            ts_code: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步每日指标: trade_date={trade_date}, ts_code={ts_code}, start_date={start_date}, end_date={end_date}")

            # 如果没有指定任何日期，默认同步最近30天
            if not trade_date and not start_date and not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                logger.info(f"未指定日期，默认同步最近30天: {start_date} ~ {end_date}")

            # 获取数据提供者
            provider = self._get_provider()

            # 从Tushare获取数据
            df = await asyncio.to_thread(
                provider.get_daily_basic,
                trade_date=trade_date,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) == 0:
                logger.warning("未获取到每日指标数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 插入数据库
            records = await self._insert_daily_basic_data(df)

            logger.info(f"成功同步每日指标数据 {records} 条")
            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条每日指标数据"
            }

        except Exception as e:
            logger.error(f"同步每日指标失败: {str(e)}", exc_info=True)
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

        # 数值字段转换
        numeric_columns = [
            'close', 'turnover_rate', 'turnover_rate_f', 'volume_ratio',
            'pe', 'pe_ttm', 'pb', 'ps', 'ps_ttm',
            'dv_ratio', 'dv_ttm', 'total_share', 'float_share',
            'free_share', 'total_mv', 'circ_mv'
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        logger.info(f"数据清洗完成，有效数据 {len(df)} 条")
        return df

    async def _insert_daily_basic_data(self, df: pd.DataFrame) -> int:
        """
        插入每日指标数据到数据库

        Args:
            df: 数据DataFrame

        Returns:
            插入的记录数
        """
        if len(df) == 0:
            return 0

        # 使用 Repository 批量插入
        records = await asyncio.to_thread(self.daily_basic_repo.bulk_upsert, df)
        return records

    async def get_daily_basic_data(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        查询每日指标数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            limit: 返回记录数

        Returns:
            包含数据的字典
        """
        try:
            # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 使用 Repository 查询数据
            items = await asyncio.to_thread(
                self.daily_basic_repo.get_by_code_and_date_range,
                ts_code=ts_code,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                limit=limit
            )

            return {
                "items": items,
                "count": len(items)
            }

        except Exception as e:
            logger.error(f"查询每日指标数据失败: {str(e)}")
            raise

    async def get_daily_basic_list(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 30
    ) -> Dict[str, Any]:
        """
        查询每日指标数据列表（支持分页）

        Args:
            trade_date: 交易日期 YYYYMMDD
            ts_code: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            page: 页码
            page_size: 每页数量

        Returns:
            包含数据和分页信息的字典
        """
        try:
            # 计算偏移量
            offset = (page - 1) * page_size

            # 如果指定了 trade_date，使用单日查询
            if trade_date:
                items = await asyncio.to_thread(
                    self.daily_basic_repo.get_by_date_range,
                    start_date=trade_date,
                    end_date=trade_date,
                    ts_code=ts_code,
                    limit=page_size,
                    offset=offset
                )
                total = await asyncio.to_thread(
                    self.daily_basic_repo.get_record_count,
                    start_date=trade_date,
                    end_date=trade_date
                )
            else:
                # 使用日期范围查询
                if not start_date:
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                if not end_date:
                    end_date = datetime.now().strftime('%Y%m%d')

                items = await asyncio.to_thread(
                    self.daily_basic_repo.get_by_date_range,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code,
                    limit=page_size,
                    offset=offset
                )
                total = await asyncio.to_thread(
                    self.daily_basic_repo.get_record_count,
                    start_date=start_date,
                    end_date=end_date
                )

            # 转换日期格式 YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if 'trade_date' in item and item['trade_date']:
                    date_obj = item['trade_date']
                    if hasattr(date_obj, 'strftime'):
                        item['trade_date'] = date_obj.strftime('%Y-%m-%d')
                    else:
                        # 已经是字符串格式（YYYYMMDD）
                        item['trade_date'] = f"{str(date_obj)[:4]}-{str(date_obj)[4:6]}-{str(date_obj)[6:8]}"

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size
            }

        except Exception as e:
            logger.error(f"查询每日指标数据列表失败: {str(e)}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取每日指标统计数据

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            统计数据字典
        """
        try:
            # 使用 Repository 获取统计数据
            stats = await asyncio.to_thread(
                self.daily_basic_repo.get_statistics,
                start_date=start_date,
                end_date=end_date
            )

            # 转换日期格式：YYYYMMDD -> YYYY-MM-DD
            if stats.get('date_range'):
                earliest = stats['date_range'].get('earliest_date', '')
                latest = stats['date_range'].get('latest_date', '')

                if earliest and len(earliest) == 8 and earliest.isdigit():
                    stats['date_range']['earliest_date'] = f"{earliest[:4]}-{earliest[4:6]}-{earliest[6:8]}"
                if latest and len(latest) == 8 and latest.isdigit():
                    stats['date_range']['latest_date'] = f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"

            # 处理null值
            if stats.get('avg_pe_ttm') is None:
                stats['avg_pe_ttm'] = 0.0

            return stats

        except Exception as e:
            logger.error(f"获取每日指标统计数据失败: {str(e)}")
            raise

    async def get_latest_data(self) -> Dict[str, Any]:
        """
        获取最新交易日的每日指标数据

        Returns:
            最新数据字典
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(
                self.daily_basic_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "items": [],
                    "trade_date": None
                }

            # 查询该交易日的数据
            items = await asyncio.to_thread(
                self.daily_basic_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                limit=100
            )

            # 转换日期格式：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if 'trade_date' in item and item['trade_date']:
                    date_str = item['trade_date']
                    # 如果是日期对象，转换为字符串
                    if hasattr(date_str, 'strftime'):
                        date_str = date_str.strftime('%Y%m%d')
                    # 如果是YYYYMMDD格式，转换为YYYY-MM-DD
                    if isinstance(date_str, str) and len(date_str) == 8 and date_str.isdigit():
                        item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            return {
                "items": items,
                "trade_date": latest_date,
                "count": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新每日指标数据失败: {str(e)}")
            raise
