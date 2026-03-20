"""
股票列表管理服务

职责：
- 下载和更新股票列表
- 市场分类标准化
- 股票信息查询
"""

import asyncio
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from app.core.exceptions import DataSyncError, ExternalAPIError
from app.repositories.stock_data_repository import StockDataRepository
from app.services.data_provider_service import DataProviderService
from app.utils.data_transformer import DataTransformer
from app.utils.market_classifier import MarketClassifier


class StockListService:
    """
    股票列表管理服务

    职责：
    - 从数据提供者下载股票列表
    - 自动进行市场分类
    - 保存到数据库（使用 Repository）
    - 提供查询接口（带缓存）

    重构说明：
    - 从 DataDownloadService 提取股票列表相关功能
    - 移除 DatabaseManager 依赖，使用 Repository
    - 使用工具类处理市场分类和数据转换
    """

    def __init__(
        self,
        stock_repo: Optional[StockDataRepository] = None,
        provider_service: Optional[DataProviderService] = None
    ):
        """
        初始化股票列表服务

        Args:
            stock_repo: 股票数据 Repository（可选，用于依赖注入）
            provider_service: 数据提供者服务（可选，用于依赖注入）
        """
        self.stock_repo = stock_repo or StockDataRepository()
        self.provider_service = provider_service or DataProviderService()
        logger.debug("✓ StockListService initialized")

    # ==================== 下载和保存 ====================

    async def download_and_save(self, module: str = "main") -> Dict:
        """
        下载股票列表并保存到数据库

        处理流程：
        1. 从数据提供者获取股票列表
        2. 数据转换和验证
        3. 市场分类
        4. 保存到数据库并清除缓存

        Args:
            module: 使用的数据源模块（默认 'main'）

        Returns:
            {count: int, message: str, markets: Dict[str, int]}

        Raises:
            ExternalAPIError: 数据获取失败
            DataSyncError: 同步失败

        Examples:
            >>> service = StockListService()
            >>> result = await service.download_and_save()
            >>> print(f"成功下载 {result['count']} 只股票")
        """
        try:
            logger.info(f"开始下载股票列表 (module={module})...")

            # 1. 获取数据提供者
            provider = await self.provider_service.get_provider(module)

            # 2. 获取股票列表
            response = await asyncio.to_thread(provider.get_stock_list)

            if not response.is_success():
                raise ValueError(response.error_message or "获取股票列表失败")

            stock_df = response.data

            if stock_df is None or stock_df.empty:
                raise ValueError("获取股票列表失败，返回数据为空")

            logger.info(f"从 {module} 获取到 {len(stock_df)} 只股票")

            # 3. 数据转换（使用工具类）
            stock_df = DataTransformer.transform_stock_list(stock_df)

            # 4. 市场分类（使用工具类）
            stock_df = MarketClassifier.classify(stock_df)

            # 5. 获取市场分布统计
            market_summary = MarketClassifier.get_market_summary(stock_df)

            # 6. 保存到数据库（使用 Repository）
            count = await self.stock_repo.save_stock_list_and_clear_cache(stock_df)

            logger.info(f"✓ 股票列表下载完成: {count} 只")
            logger.info(f"  市场分布: {market_summary}")

            return {
                "count": count,
                "message": f"成功下载 {count} 只股票信息",
                "markets": market_summary
            }

        except ValueError as e:
            # 数据为空或格式错误
            raise ExternalAPIError(
                "股票列表数据获取失败",
                error_code="STOCK_LIST_EMPTY",
                reason=str(e)
            )
        except Exception as e:
            # 其他未预期错误
            logger.error(f"下载股票列表失败: {e}")
            raise DataSyncError(
                "股票列表同步失败",
                error_code="STOCK_LIST_SYNC_FAILED",
                reason=str(e)
            )

    # ==================== 查询接口 ====================

    async def get_stock_list(
        self,
        market: Optional[str] = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        获取股票列表

        Args:
            market: 市场类型（可选，如 '上海主板'、'深圳主板' 等）
            use_cache: 是否使用缓存（默认 True）

        Returns:
            股票列表 DataFrame

        Examples:
            >>> service = StockListService()
            >>> # 获取所有股票
            >>> df = await service.get_stock_list()
            >>> # 获取上海主板股票
            >>> df_sh = await service.get_stock_list(market='上海主板')
        """
        if use_cache:
            return await self.stock_repo.get_stock_list_cached(market)
        else:
            return await asyncio.to_thread(self.stock_repo.get_stock_list, market)

    async def get_stock_by_code(self, code: str) -> Optional[Dict]:
        """
        根据股票代码获取股票信息

        Args:
            code: 股票代码

        Returns:
            股票信息字典，如果不存在则返回 None

        Examples:
            >>> service = StockListService()
            >>> stock = await service.get_stock_by_code('000001')
            >>> if stock:
            ...     print(f"{stock['name']} ({stock['code']})")
        """
        return await asyncio.to_thread(self.stock_repo.get_stock_by_code, code)

    async def stock_exists(self, code: str) -> bool:
        """
        检查股票是否存在

        Args:
            code: 股票代码

        Returns:
            是否存在

        Examples:
            >>> service = StockListService()
            >>> exists = await service.stock_exists('000001')
        """
        return await asyncio.to_thread(self.stock_repo.stock_exists, code)

    async def get_stock_count(self, market: Optional[str] = None) -> int:
        """
        获取股票数量

        Args:
            market: 市场类型（可选）

        Returns:
            股票数量

        Examples:
            >>> service = StockListService()
            >>> total = await service.get_stock_count()
            >>> sh_count = await service.get_stock_count(market='上海主板')
        """
        return await asyncio.to_thread(self.stock_repo.get_stock_count, market)

    # ==================== 市场分类相关 ====================

    async def get_market_summary(self) -> Dict[str, int]:
        """
        获取市场分布统计

        Returns:
            各市场股票数量 {'上海主板': 100, '深圳主板': 200, ...}

        Examples:
            >>> service = StockListService()
            >>> summary = await service.get_market_summary()
            >>> print(f"上海主板: {summary.get('上海主板', 0)} 只")
        """
        df = await self.get_stock_list(use_cache=True)
        return MarketClassifier.get_market_summary(df, code_column="code")

    async def get_stocks_by_market(self, market: str) -> List[Dict]:
        """
        获取指定市场的股票列表

        Args:
            market: 市场类型（如 '上海主板'）

        Returns:
            股票信息列表 [{'code': '000001', 'name': '平安银行', 'market': '深圳主板'}, ...]

        Examples:
            >>> service = StockListService()
            >>> stocks = await service.get_stocks_by_market('科创板')
        """
        df = await self.get_stock_list(market=market, use_cache=True)
        return df.to_dict('records')

    def classify_market(self, code: str) -> str:
        """
        根据股票代码判断市场类型（同步方法）

        Args:
            code: 股票代码

        Returns:
            市场类型

        Examples:
            >>> service = StockListService()
            >>> market = service.classify_market('000001')
            >>> print(market)  # '深圳主板'
        """
        return MarketClassifier.get_market(code)

    def validate_code(self, code: str) -> bool:
        """
        验证股票代码是否符合市场规则（同步方法）

        Args:
            code: 股票代码

        Returns:
            是否为有效的A股代码

        Examples:
            >>> service = StockListService()
            >>> is_valid = service.validate_code('000001')
        """
        return MarketClassifier.validate_code(code)

    # ==================== 批量操作 ====================

    async def get_codes_list(self, market: Optional[str] = None) -> List[str]:
        """
        获取股票代码列表

        Args:
            market: 市场类型（可选）

        Returns:
            股票代码列表

        Examples:
            >>> service = StockListService()
            >>> codes = await service.get_codes_list()
            >>> codes_sh = await service.get_codes_list(market='上海主板')
        """
        df = await self.get_stock_list(market=market, use_cache=True)
        return df["code"].tolist()

    async def filter_valid_codes(self, codes: List[str]) -> List[str]:
        """
        过滤有效的股票代码

        Args:
            codes: 股票代码列表

        Returns:
            有效的股票代码列表

        Examples:
            >>> service = StockListService()
            >>> codes = ['000001', '999999', '600000']
            >>> valid_codes = await service.filter_valid_codes(codes)
            >>> # 返回: ['000001', '600000']
        """
        # 从数据库获取所有代码
        all_codes = await self.get_codes_list()
        all_codes_set = set(all_codes)

        # 过滤
        valid_codes = [code for code in codes if code in all_codes_set]

        logger.debug(f"过滤股票代码: {len(valid_codes)}/{len(codes)} 有效")
        return valid_codes
