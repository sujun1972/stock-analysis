"""
日线数据管理服务

职责：
- 下载单只股票数据
- 数据格式标准化
- 数据增量更新
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd
from loguru import logger

from app.core.exceptions import DataSyncError, ExternalAPIError
from app.repositories.stock_data_repository import StockDataRepository
from app.services.data_provider_service import DataProviderService
from app.utils.data_transformer import DataTransformer


class DailyDataService:
    """
    日线数据管理服务

    职责：
    - 从数据提供者下载日线数据
    - 统一数据格式转换（使用工具类）
    - 保存到数据库（使用 Repository）
    - 提供查询接口（带缓存）

    重构说明：
    - 从 DataDownloadService 提取日线数据相关功能
    - 移除 akshare 直接调用，统一使用 Provider
    - 移除 DatabaseManager 依赖，使用 Repository
    - 使用 DataTransformer 处理格式转换
    """

    def __init__(
        self,
        stock_repo: Optional[StockDataRepository] = None,
        provider_service: Optional[DataProviderService] = None
    ):
        """
        初始化日线数据服务

        Args:
            stock_repo: 股票数据 Repository（可选，用于依赖注入）
            provider_service: 数据提供者服务（可选，用于依赖注入）
        """
        self.stock_repo = stock_repo or StockDataRepository()
        self.provider_service = provider_service or DataProviderService()
        logger.debug("✓ DailyDataService initialized")

    # ==================== 下载和保存 ====================

    async def download_and_save(
        self,
        code: str,
        years: int = 5,
        module: str = "main",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[int]:
        """
        下载单只股票日线数据并保存到数据库

        处理流程：
        1. 计算日期范围
        2. 从数据提供者获取数据
        3. 数据格式转换（使用工具类）
        4. 保存到数据库并清除缓存

        Args:
            code: 股票代码
            years: 下载年数（当 start_date 为 None 时使用）
            module: 使用的数据源模块（默认 'main'）
            start_date: 起始日期（可选，格式：YYYYMMDD）
            end_date: 结束日期（可选，格式：YYYYMMDD）

        Returns:
            保存的记录数，如果无数据则返回 None

        Raises:
            ExternalAPIError: 数据获取失败
            DataSyncError: 同步失败

        Examples:
            >>> service = DailyDataService()
            >>> # 下载最近5年数据
            >>> count = await service.download_and_save('000001', years=5)
            >>> # 下载指定日期范围
            >>> count = await service.download_and_save('000001', start_date='20240101', end_date='20241231')
        """
        try:
            # 1. 计算日期范围
            if start_date is None or end_date is None:
                start_date, end_date = self._calculate_date_range(years)

            logger.info(f"下载 {code} 日线数据 ({start_date} - {end_date})")

            # 2. 获取数据提供者
            provider = await self.provider_service.get_provider(module)

            # 3. 获取日线数据（统一使用 Provider）
            response = await asyncio.to_thread(
                provider.get_daily_data,
                code=code,
                start_date=start_date,
                end_date=end_date
            )

            if not response.is_success():
                raise ValueError(response.error_message or "获取日线数据失败")

            df = response.data

            if df is None or df.empty:
                logger.warning(f"  {code}: 无数据")
                return None

            # 4. 数据转换（使用工具类）
            df = DataTransformer.transform_daily_data(df, set_date_index=True)

            # 5. 保存到数据库（使用 Repository）
            count = await self.stock_repo.save_daily_data_and_clear_cache(df, code)

            logger.info(f"  ✓ {code}: {count} 条记录")
            return count

        except (ConnectionError, TimeoutError) as e:
            # 网络相关错误
            logger.error(f"  ✗ {code}: 数据获取超时或网络错误")
            raise ExternalAPIError(
                f"股票 {code} 数据获取失败",
                error_code="DATA_FETCH_TIMEOUT",
                stock_code=code,
                reason=str(e)
            )
        except ValueError as e:
            # 数据为空或提供者错误
            logger.warning(f"  {code}: {e}")
            return None
        except Exception as e:
            # 其他未预期错误
            logger.error(f"  ✗ {code}: {e}")
            raise DataSyncError(
                f"股票 {code} 数据同步失败",
                error_code="DAILY_DATA_SYNC_FAILED",
                stock_code=code,
                reason=str(e)
            )

    async def update_latest_data(
        self,
        code: str,
        module: str = "main",
        days: int = 30
    ) -> Optional[int]:
        """
        增量更新最新数据

        只下载最近 N 天的数据，用于日常更新

        Args:
            code: 股票代码
            module: 数据源模块
            days: 更新最近N天（默认30天）

        Returns:
            新增的记录数

        Examples:
            >>> service = DailyDataService()
            >>> count = await service.update_latest_data('000001', days=30)
        """
        try:
            # 计算日期范围（最近N天）
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

            logger.info(f"增量更新 {code} ({start_date} - {end_date})")

            return await self.download_and_save(
                code=code,
                module=module,
                start_date=start_date,
                end_date=end_date
            )

        except Exception as e:
            logger.error(f"增量更新失败 ({code}): {e}")
            raise

    # ==================== 查询接口 ====================

    async def get_daily_data(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        获取日线数据

        Args:
            code: 股票代码
            start_date: 起始日期（格式：YYYY-MM-DD，可选）
            end_date: 结束日期（格式：YYYY-MM-DD，可选）
            limit: 最大记录数（可选）
            use_cache: 是否使用缓存（默认 True）

        Returns:
            日线数据 DataFrame

        Examples:
            >>> service = DailyDataService()
            >>> # 获取最近100条数据
            >>> df = await service.get_daily_data('000001', limit=100)
            >>> # 获取指定日期范围数据
            >>> df = await service.get_daily_data('000001', '2024-01-01', '2024-12-31')
        """
        if use_cache:
            return await self.stock_repo.get_daily_data_cached(
                code, start_date, end_date, limit
            )
        else:
            return await asyncio.to_thread(
                self.stock_repo.get_daily_data,
                code, start_date, end_date, limit
            )

    async def get_latest_date(self, code: str) -> Optional[datetime]:
        """
        获取股票最新数据日期

        Args:
            code: 股票代码

        Returns:
            最新日期，如果没有数据则返回 None

        Examples:
            >>> service = DailyDataService()
            >>> latest = await service.get_latest_date('000001')
            >>> if latest:
            ...     print(f"最新数据: {latest.strftime('%Y-%m-%d')}")
        """
        return await asyncio.to_thread(self.stock_repo.get_latest_date, code)

    async def get_data_range(self, code: str) -> Optional[tuple[datetime, datetime]]:
        """
        获取股票数据日期范围

        Args:
            code: 股票代码

        Returns:
            (最早日期, 最晚日期) 元组，如果没有数据则返回 None

        Examples:
            >>> service = DailyDataService()
            >>> date_range = await service.get_data_range('000001')
            >>> if date_range:
            ...     start, end = date_range
            ...     print(f"数据范围: {start} - {end}")
        """
        return await asyncio.to_thread(self.stock_repo.get_data_range, code)

    # ==================== 数据管理 ====================

    async def delete_data(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        删除日线数据

        Args:
            code: 股票代码
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            删除的记录数

        Examples:
            >>> service = DailyDataService()
            >>> # 删除所有数据
            >>> count = await service.delete_data('000001')
            >>> # 删除指定日期范围数据
            >>> count = await service.delete_data('000001', '2024-01-01', '2024-12-31')
        """
        return await asyncio.to_thread(
            self.stock_repo.delete_daily_data,
            code, start_date, end_date
        )

    async def has_data(self, code: str) -> bool:
        """
        检查股票是否有日线数据

        Args:
            code: 股票代码

        Returns:
            是否有数据

        Examples:
            >>> service = DailyDataService()
            >>> has_data = await service.has_data('000001')
        """
        latest = await self.get_latest_date(code)
        return latest is not None

    async def get_data_coverage(self, code: str) -> Dict:
        """
        获取数据覆盖情况

        Args:
            code: 股票代码

        Returns:
            覆盖情况字典 {
                has_data: bool,
                latest_date: Optional[datetime],
                date_range: Optional[tuple],
                record_count: int
            }

        Examples:
            >>> service = DailyDataService()
            >>> coverage = await service.get_data_coverage('000001')
            >>> print(f"记录数: {coverage['record_count']}")
        """
        date_range = await self.get_data_range(code)

        if date_range:
            df = await self.get_daily_data(code, use_cache=False)
            record_count = len(df)
            latest_date = date_range[1]
        else:
            record_count = 0
            latest_date = None

        return {
            "has_data": date_range is not None,
            "latest_date": latest_date,
            "date_range": date_range,
            "record_count": record_count
        }

    # ==================== 辅助方法 ====================

    def _calculate_date_range(self, years: int) -> tuple[str, str]:
        """
        计算日期范围

        Args:
            years: 年数

        Returns:
            (起始日期, 结束日期) 元组，格式：YYYYMMDD

        Examples:
            >>> service = DailyDataService()
            >>> start, end = service._calculate_date_range(5)
        """
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y%m%d")
        return start_date, end_date

    @staticmethod
    def format_date(date_str: str, input_format: str = "%Y%m%d", output_format: str = "%Y-%m-%d") -> str:
        """
        格式化日期字符串

        Args:
            date_str: 输入日期字符串
            input_format: 输入格式
            output_format: 输出格式

        Returns:
            格式化后的日期字符串

        Examples:
            >>> DailyDataService.format_date('20240101')
            '2024-01-01'
        """
        return DataTransformer.parse_date_string(date_str, input_format, output_format)
