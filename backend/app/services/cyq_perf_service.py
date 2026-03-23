"""
每日筹码及胜率数据服务

处理筹码及胜率数据的业务逻辑
"""

import asyncio
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.cyq_perf_repository import CyqPerfRepository
from core.src.providers import DataProviderFactory


class CyqPerfService:
    """每日筹码及胜率数据服务"""

    def __init__(self):
        self.cyq_perf_repo = CyqPerfRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ CyqPerfService initialized")

    def _get_provider(self):
        """获取 Tushare 数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_cyq_perf(
        self,
        ts_code: str,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步筹码及胜率数据

        Args:
            ts_code: 股票代码（必填）
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步筹码及胜率数据: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 1. 从 Tushare 获取数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_cyq_perf,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning(f"未获取到筹码及胜率数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从 Tushare 获取到 {len(df)} 条筹码及胜率数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库（使用 Repository）
            records = await asyncio.to_thread(
                self.cyq_perf_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条筹码及胜率数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步筹码及胜率数据失败: {e}")
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
            numeric_fields = [
                'his_low', 'his_high',
                'cost_5pct', 'cost_15pct', 'cost_50pct', 'cost_85pct', 'cost_95pct',
                'weight_avg', 'winner_rate'
            ]
            for field in numeric_fields:
                if field in df.columns:
                    df[field] = df[field].apply(lambda x: None if str(x).strip() == '' or str(x) == 'nan' else x)

            logger.debug(f"数据验证完成，有效数据: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise

    async def get_cyq_perf_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30
    ) -> Dict:
        """
        获取筹码及胜率数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            limit: 返回记录数

        Returns:
            数据和统计信息
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 获取数据
            items = await asyncio.to_thread(
                self.cyq_perf_repo.get_by_date_range,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                limit=limit
            )

            # 获取统计信息
            statistics = await asyncio.to_thread(
                self.cyq_perf_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code
            )

            return {
                "items": items,
                "statistics": statistics,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取筹码及胜率数据失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """
        获取最新的筹码及胜率数据

        Returns:
            最新数据
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(
                self.cyq_perf_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "latest_date": None,
                    "data": []
                }

            # 获取该日期的数据
            items = await asyncio.to_thread(
                self.cyq_perf_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                limit=100
            )

            return {
                "latest_date": latest_date,
                "data": items
            }

        except Exception as e:
            logger.error(f"获取最新筹码及胜率数据失败: {e}")
            raise

    async def get_top_winner_stocks(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取高胜率股票

        Args:
            trade_date: 交易日期 YYYY-MM-DD（可选，默认最新）
            limit: 返回记录数

        Returns:
            高胜率股票列表
        """
        try:
            # 如果未指定日期，使用最新日期
            if not trade_date:
                latest_date = await asyncio.to_thread(
                    self.cyq_perf_repo.get_latest_trade_date
                )
                if not latest_date:
                    return []
                trade_date_fmt = latest_date
            else:
                # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
                trade_date_fmt = trade_date.replace('-', '')

            # 获取高胜率股票
            items = await asyncio.to_thread(
                self.cyq_perf_repo.get_top_winner_stocks,
                trade_date=trade_date_fmt,
                limit=limit
            )

            return items

        except Exception as e:
            logger.error(f"获取高胜率股票失败: {e}")
            raise
