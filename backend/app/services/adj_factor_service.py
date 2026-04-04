"""
复权因子数据服务

负责复权因子数据的业务逻辑处理
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime
import pandas as pd
from loguru import logger

from app.repositories.adj_factor_repository import AdjFactorRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class AdjFactorService:
    """复权因子数据服务"""

    def __init__(self):
        self.adj_factor_repo = AdjFactorRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取 Tushare Provider"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def get_adj_factor_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        page: int = 1
    ) -> Dict:
        """
        获取复权因子数据

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期，格式：YYYY-MM-DD（可选）
            end_date: 结束日期，格式：YYYY-MM-DD（可选）
            limit: 每页记录数
            page: 页码（从1开始）

        Returns:
            包含数据列表和总数的字典
        """
        # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        offset = (page - 1) * limit

        # 并发查询数据和总数
        items, total = await asyncio.gather(
            asyncio.to_thread(
                self.adj_factor_repo.get_by_code_and_date_range,
                ts_code=ts_code,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                limit=limit,
                offset=offset
            ),
            asyncio.to_thread(
                self.adj_factor_repo.get_total_count,
                ts_code=ts_code,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )
        )

        # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
        for item in items:
            if item.get('trade_date'):
                date_str = item['trade_date']
                item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        return {
            "items": items,
            "total": total
        }

    async def get_statistics(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取复权因子统计信息

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期，格式：YYYY-MM-DD（可选）
            end_date: 结束日期，格式：YYYY-MM-DD（可选）

        Returns:
            统计信息字典
        """
        # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        stats = await asyncio.to_thread(
            self.adj_factor_repo.get_statistics,
            ts_code=ts_code,
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
        if stats.get('latest_date'):
            date_str = stats['latest_date']
            stats['latest_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        return stats

    async def get_latest_data(self, ts_code: Optional[str] = None) -> Dict:
        """
        获取最新复权因子数据

        Args:
            ts_code: 股票代码（可选，如果不指定则返回最新日期的所有数据）

        Returns:
            最新数据字典
        """
        if ts_code:
            # 查询指定股票的最新数据
            latest = await asyncio.to_thread(
                self.adj_factor_repo.get_latest_by_code,
                ts_code
            )
            if latest and latest.get('trade_date'):
                date_str = latest['trade_date']
                latest['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            return latest or {}
        else:
            # 查询所有股票的最新数据
            stats = await asyncio.to_thread(
                self.adj_factor_repo.get_statistics
            )
            if stats.get('latest_date'):
                latest_date = stats['latest_date']
                items = await asyncio.to_thread(
                    self.adj_factor_repo.get_by_code_and_date_range,
                    start_date=latest_date,
                    end_date=latest_date
                )
                # 日期格式转换
                for item in items:
                    if item.get('trade_date'):
                        date_str = item['trade_date']
                        item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                return {
                    "latest_date": f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8]}",
                    "items": items,
                    "total": len(items)
                }
            return {}

    async def sync_adj_factor(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步复权因子数据

        Args:
            ts_code: 股票代码（可选）
            trade_date: 单个交易日期，格式：YYYYMMDD（可选）
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步复权因子数据: ts_code={ts_code}, trade_date={trade_date}, "
                       f"start_date={start_date}, end_date={end_date}")

            # 1. 获取 Tushare 数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_adj_factor,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到复权因子数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从 Tushare 获取到 {len(df)} 条复权因子数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.adj_factor_repo.bulk_upsert,
                df
            )

            logger.info(f"✓ 成功同步 {records} 条复权因子数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步复权因子数据失败: {e}")
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
            df: 原始数据 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        # 检查必需列
        required_columns = ['ts_code', 'trade_date', 'adj_factor']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"缺少必需列: {missing_columns}")

        # 去除重复记录（按 ts_code + trade_date）
        original_count = len(df)
        df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
        if len(df) < original_count:
            logger.warning(f"去除 {original_count - len(df)} 条重复记录")

        # 移除空值记录
        df = df.dropna(subset=['ts_code', 'trade_date'])

        # 确保日期格式正确（8位字符串）
        df['trade_date'] = df['trade_date'].astype(str).str.replace('-', '')

        # 确保复权因子为数值类型
        df['adj_factor'] = pd.to_numeric(df['adj_factor'], errors='coerce')

        # 移除复权因子为空或非正数的记录
        df = df[df['adj_factor'].notna()]
        df = df[df['adj_factor'] > 0]

        logger.info(f"数据清洗完成，保留 {len(df)} 条有效记录")

        return df
