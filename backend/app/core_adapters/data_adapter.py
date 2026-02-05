"""
数据访问适配器 (Data Adapter)

将 Core 的数据库访问模块包装为异步方法，供 FastAPI 使用。

核心功能:
- 异步获取股票列表
- 异步获取日线数据
- 异步获取分钟数据
- 异步插入数据
- 数据完整性检查

作者: Backend Team
创建日期: 2026-02-01
版本: 1.0.0
"""

import asyncio
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

# 添加 core 项目到 Python 路径
core_path = Path(__file__).parent.parent.parent.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

from src.data_pipeline.batch_download_coordinator import BatchDownloadCoordinator

# 导入 Core 模块
from src.database.connection_pool_manager import ConnectionPoolManager
from src.database.data_insert_manager import DataInsertManager
from src.database.data_query_manager import DataQueryManager

from app.core.config import settings
from app.core.exceptions import DataQueryError, ExternalAPIError

# 延迟导入 Provider 避免循环依赖
try:
    from src.providers.tushare_provider import TushareProvider as DataProvider
except ImportError:
    try:
        from src.providers.akshare_provider import AkshareProvider as DataProvider
    except ImportError:
        # 如果都不可用，使用 None，在使用时再报错
        DataProvider = None


class DataAdapter:
    """
    Core 数据模块的异步适配器

    包装 Core 的 DataQueryManager 和 DataInsertManager，
    将同步方法转换为异步方法。

    示例:
        >>> adapter = DataAdapter()
        >>> stocks = await adapter.get_stock_list(market="主板")
        >>> data = await adapter.get_daily_data("000001", start_date, end_date)
    """

    def __init__(self):
        """初始化数据适配器"""
        # 构建数据库配置字典
        db_config = {
            "host": settings.DATABASE_HOST,
            "port": settings.DATABASE_PORT,
            "database": settings.DATABASE_NAME,
            "user": settings.DATABASE_USER,
            "password": settings.DATABASE_PASSWORD,
        }

        # 延迟初始化：尝试创建连接池，如果失败则警告但不中断
        try:
            self.pool_manager = ConnectionPoolManager(config=db_config)
            self.query_manager = DataQueryManager(self.pool_manager)
            self.insert_manager = DataInsertManager(self.pool_manager)
        except Exception as e:
            logger.warning(f"数据库连接失败（将在实际使用时重试）: {e}")
            self.pool_manager = None
            self.query_manager = None
            self.insert_manager = None

        # 初始化 Provider（如果可用）
        self.provider = None
        if DataProvider is not None:
            try:
                self.provider = DataProvider()
            except (ImportError, ValueError, KeyError) as e:
                logger.warning(f"无法初始化数据提供者: {e}")

        # 初始化下载协调器（如果 Provider 可用）
        self.download_coordinator = None
        if self.provider is not None:
            try:
                self.download_coordinator = BatchDownloadCoordinator(
                    provider=self.provider, max_workers=3
                )
            except (ValueError, TypeError) as e:
                logger.warning(f"无法初始化下载协调器: {e}")

    def _ensure_connection(self):
        """确保数据库连接可用"""
        if self.query_manager is None:
            raise DataQueryError(
                "数据库连接不可用",
                error_code="DB_NOT_INITIALIZED",
                reason="数据库连接在初始化时失败，请检查数据库配置和连接",
            )

    async def get_stock_list(
        self, market: Optional[str] = None, status: str = "正常"
    ) -> List[Dict[str, Any]]:
        """
        异步获取股票列表

        Args:
            market: 市场类型 (主板/创业板/科创板/北交所)，None 表示所有市场
            status: 股票状态，默认 "正常"

        Returns:
            股票列表，每个元素为字典包含股票信息
            格式: [{'code': '000001', 'name': '平安银行', ...}, ...]

        Raises:
            DatabaseError: 数据库访问错误

        Note:
            Core的query_manager返回DataFrame，此方法转换为列表格式
            以便于JSON序列化和API响应
        """
        self._ensure_connection()
        df = await asyncio.to_thread(
            self.query_manager.get_stock_list, market=market, status=status
        )
        # 将 DataFrame 转换为列表格式 (orient='records')
        # 从 {'col': {'0': val1, '1': val2}} 转为 [{'col': val1}, {'col': val2}]
        return df.to_dict(orient="records")

    async def get_daily_data(
        self, code: str, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        异步获取股票日线数据

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            包含日线数据的 DataFrame

        Raises:
            DatabaseError: 数据库访问错误
        """
        self._ensure_connection()
        start_str = start_date.strftime("%Y-%m-%d") if start_date else None
        end_str = end_date.strftime("%Y-%m-%d") if end_date else None

        return await asyncio.to_thread(
            self.query_manager.load_daily_data,
            stock_code=code,
            start_date=start_str,
            end_date=end_str,
        )

    async def get_minute_data(
        self, code: str, period: str = "1min", trade_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        异步获取分钟数据

        Args:
            code: 股票代码
            period: 周期 (1min/5min/15min/30min/60min)
            trade_date: 交易日期

        Returns:
            包含分钟数据的 DataFrame

        Raises:
            DatabaseError: 数据库访问错误
        """
        self._ensure_connection()
        date_str = trade_date.strftime("%Y-%m-%d") if trade_date else None

        return await asyncio.to_thread(
            self.query_manager.load_minute_data, code=code, period=period, trade_date=date_str
        )

    async def insert_stock_list(self, df: pd.DataFrame) -> bool:
        """
        异步插入股票列表

        Args:
            df: 包含股票信息的 DataFrame

        Returns:
            是否插入成功

        Raises:
            DatabaseError: 数据库写入错误
        """
        self._ensure_connection()
        return await asyncio.to_thread(self.insert_manager.insert_stock_list, df=df)

    async def insert_daily_data(self, df: pd.DataFrame, code: str) -> bool:
        """
        异步插入日线数据

        Args:
            df: 包含日线数据的 DataFrame
            code: 股票代码

        Returns:
            是否插入成功

        Raises:
            DatabaseError: 数据库写入错误
        """
        self._ensure_connection()
        return await asyncio.to_thread(self.insert_manager.insert_daily_data, df=df, code=code)

    async def insert_minute_data(self, df: pd.DataFrame, code: str, period: str = "1min") -> bool:
        """
        异步插入分钟数据

        Args:
            df: 包含分钟数据的 DataFrame
            code: 股票代码
            period: 周期

        Returns:
            是否插入成功

        Raises:
            DatabaseError: 数据库写入错误
        """
        self._ensure_connection()
        return await asyncio.to_thread(
            self.insert_manager.insert_minute_data, df=df, code=code, period=period
        )

    async def check_data_completeness(
        self, code: str, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """
        异步检查数据完整性

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            包含完整性信息的字典
        """
        self._ensure_connection()
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        return await asyncio.to_thread(
            self.query_manager.check_daily_data_completeness,
            stock_code=code,
            start_date=start_str,
            end_date=end_str,
        )

    async def is_trading_day(self, trade_date: date) -> bool:
        """
        异步判断是否为交易日

        Args:
            trade_date: 日期

        Returns:
            是否为交易日
        """
        self._ensure_connection()
        date_str = trade_date.strftime("%Y-%m-%d")

        return await asyncio.to_thread(self.query_manager.is_trading_day, trade_date=date_str)

    async def get_stock_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        异步获取股票基本信息

        Args:
            code: 股票代码

        Returns:
            股票信息字典，不存在时返回 None
        """
        stocks = await self.get_stock_list()
        for stock in stocks:
            if stock.get("code") == code:
                return stock
        return None

    async def download_daily_data(
        self, code: str, start_date: date, end_date: date
    ) -> Optional[pd.DataFrame]:
        """
        异步下载单只股票日线数据

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            包含日线数据的 DataFrame，失败时返回 None
        """
        if self.provider is None:
            raise DataQueryError("数据提供者未初始化，无法下载数据")

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        try:
            # 使用 provider 下载数据
            df = await asyncio.to_thread(
                self.provider.fetch_daily_data, symbol=code, start_date=start_str, end_date=end_str
            )
            return df
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"数据源API连接失败: {code} - {e}")
            raise ExternalAPIError(
                "数据源API调用失败",
                error_code="API_CONNECTION_ERROR",
                api_name="data_provider",
                stock_code=code,
                reason=str(e),
            )
        except (ValueError, KeyError) as e:
            logger.error(f"数据源返回数据格式错误: {code} - {e}")
            raise DataQueryError(
                "数据下载失败", error_code="DATA_DOWNLOAD_FAILED", stock_code=code, reason=str(e)
            )

    async def check_data_integrity(
        self, code: str, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """
        异步检查数据完整性（别名方法）

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            包含完整性信息的字典
        """
        return await self.check_data_completeness(code, start_date, end_date)

    def __del__(self):
        """清理资源"""
        if hasattr(self, "pool_manager"):
            try:
                self.pool_manager.close_all()
            except (AttributeError, RuntimeError):
                # 忽略清理时的错误（对象可能已被销毁）
                pass
