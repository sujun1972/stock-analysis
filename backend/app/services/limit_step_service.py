"""
连板天梯服务层

负责连板天梯数据的业务逻辑处理
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from loguru import logger

from app.repositories import LimitStepRepository
from core.src.providers import DataProviderFactory


class LimitStepService:
    """连板天梯服务类"""

    def __init__(self):
        """初始化连板天梯服务"""
        self.limit_step_repo = LimitStepRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ LimitStepService initialized")

    def _get_provider(self):
        """获取Tushare数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_limit_step(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        nums: Optional[str] = None
    ) -> Dict:
        """
        同步连板天梯数据

        Args:
            trade_date: 单个交易日期，格式：YYYYMMDD
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            nums: 连板次数（可选，支持多个，如 "2,3"）

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步连板天梯数据: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, nums={nums}")

            # 1. 获取Tushare数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_limit_step,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                nums=nums
            )

            if df is None or df.empty:
                logger.warning("未获取到连板天梯数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从Tushare获取到 {len(df)} 条连板天梯数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.limit_step_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条连板天梯数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步连板天梯数据失败: {str(e)}")
            return {
                "status": "error",
                "records": 0,
                "error": str(e),
                "message": "同步失败"
            }

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: pandas DataFrame

        Returns:
            清洗后的 DataFrame
        """
        # 确保必需字段存在
        required_fields = ['trade_date', 'ts_code']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 移除空值记录
        df = df.dropna(subset=['trade_date', 'ts_code'])

        # 数据类型转换
        if 'trade_date' in df.columns:
            df['trade_date'] = df['trade_date'].astype(str)

        if 'ts_code' in df.columns:
            df['ts_code'] = df['ts_code'].astype(str)

        if 'nums' in df.columns:
            df['nums'] = df['nums'].astype(str)

        # 移除重复记录
        df = df.drop_duplicates(subset=['trade_date', 'ts_code'], keep='last')

        logger.debug(f"数据清洗完成，剩余 {len(df)} 条记录")
        return df

    async def resolve_default_trade_date(self) -> Optional[str]:
        """
        解析默认交易日期：今天有数据则返回今天，否则返回最近有数据的交易日（YYYY-MM-DD格式）
        """
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(
            self.limit_step_repo.exists_by_date, today
        )
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"

        latest = await asyncio.to_thread(
            self.limit_step_repo.get_latest_trade_date
        )
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_limit_step_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        nums: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc'
    ) -> Dict:
        """
        获取连板天梯数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            nums: 连板次数（可选，支持多个，如 "2,3"）
            limit: 每页记录数
            offset: 偏移量（分页）
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            包含数据和统计信息的字典
        """
        try:
            # 并发获取数据和统计
            items_coro = asyncio.to_thread(
                self.limit_step_repo.get_by_date_range,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                nums=nums,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order
            )
            total_coro = asyncio.to_thread(
                self.limit_step_repo.get_total_count,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                nums=nums
            )
            statistics_coro = asyncio.to_thread(
                self.limit_step_repo.get_statistics,
                start_date=start_date,
                end_date=end_date
            )

            items, total, statistics = await asyncio.gather(
                items_coro, total_coro, statistics_coro
            )

            return {
                "items": items,
                "statistics": statistics,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取连板天梯数据失败: {str(e)}")
            raise

    async def get_latest_data(self, limit: int = 50) -> Dict:
        """
        获取最新的连板天梯数据

        Args:
            limit: 返回记录数限制

        Returns:
            包含最新数据的字典
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(
                self.limit_step_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "items": [],
                    "statistics": {},
                    "latest_date": None,
                    "total": 0
                }

            # 获取最新日期的数据
            items = await asyncio.to_thread(
                self.limit_step_repo.get_by_trade_date,
                trade_date=latest_date
            )

            # 获取统计信息
            statistics = await asyncio.to_thread(
                self.limit_step_repo.get_statistics,
                start_date=latest_date,
                end_date=latest_date
            )

            return {
                "items": items[:limit],
                "statistics": statistics,
                "latest_date": latest_date,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新连板天梯数据失败: {str(e)}")
            raise

    async def get_top_by_nums(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20,
        ascending: bool = False
    ) -> List[Dict]:
        """
        按连板次数排名获取数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD（可选）
            limit: 返回记录数
            ascending: 是否升序（False=降序，True=升序）

        Returns:
            排名数据列表
        """
        try:
            items = await asyncio.to_thread(
                self.limit_step_repo.get_top_by_nums,
                trade_date=trade_date,
                limit=limit,
                ascending=ascending
            )

            return items

        except Exception as e:
            logger.error(f"按连板次数排名查询失败: {str(e)}")
            raise
