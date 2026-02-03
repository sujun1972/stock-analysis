"""
回测数据加载器
负责加载和准备回测所需的数据
"""

from typing import Dict, List, Optional
import pandas as pd
from loguru import logger
import asyncio

from src.database.db_manager import DatabaseManager
from app.core.exceptions import DataQueryError, DataNotFoundError


class BacktestDataLoader:
    """
    回测数据加载器

    职责：
    - 加载股票价格数据
    - 加载基准数据（沪深300）
    - 数据标准化和清洗
    - 股票代码规范化
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化数据加载器

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        self.db = db or DatabaseManager()

    def normalize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码,去除交易所后缀
        数据库中存储的是不带后缀的代码

        Args:
            symbol: 股票代码（可能带后缀 .SH .SZ .BJ）

        Returns:
            标准化后的股票代码
        """
        if '.' in symbol:
            return symbol.split('.')[0]
        return symbol

    async def load_single_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        加载单只股票的日线数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            价格数据DataFrame（已标准化）

        Raises:
            ValueError: 股票无数据
        """
        # 标准化股票代码
        normalized_symbol = self.normalize_symbol(symbol)

        # 加载数据
        df = await asyncio.to_thread(
            self.db.load_daily_data,
            normalized_symbol,
            start_date=start_date,
            end_date=end_date
        )

        if df is None or len(df) == 0:
            raise ValueError(f"股票 {symbol} 无数据")

        # 标准化DataFrame
        return self._standardize_dataframe(df)

    async def load_multi_stock_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """
        加载多只股票的日线数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            股票代码 -> DataFrame 的字典

        Raises:
            ValueError: 所有股票均无有效数据
        """
        prices_dict = {}

        for symbol in symbols:
            normalized_symbol = self.normalize_symbol(symbol)
            try:
                df = await asyncio.to_thread(
                    self.db.load_daily_data,
                    normalized_symbol,
                    start_date=start_date,
                    end_date=end_date
                )

                if df is not None and len(df) > 0:
                    prices_dict[symbol] = self._standardize_dataframe(df)
                else:
                    logger.warning(f"股票 {symbol} 无数据,跳过")

            except DataQueryError:
                # 数据查询错误向上传播
                raise
            except Exception as e:
                logger.error(f"获取股票 {symbol} 数据失败: {e}")
                # 对于多股回测，单个股票失败不影响整体，所以记录错误但不抛出
                # 如果需要严格模式，可以改为 raise

        if len(prices_dict) == 0:
            raise ValueError("所有股票均无有效数据")

        return prices_dict

    async def load_benchmark_data(
        self,
        start_date: str,
        end_date: str,
        benchmark_code: str = '000300'
    ) -> Optional[pd.DataFrame]:
        """
        加载基准数据（默认沪深300）

        Args:
            start_date: 开始日期
            end_date: 结束日期
            benchmark_code: 基准代码（默认 000300 沪深300）

        Returns:
            基准数据DataFrame（包含收益率和归一化净值）
        """
        try:
            df = await asyncio.to_thread(
                self.db.load_daily_data,
                benchmark_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) == 0:
                logger.warning("无法获取基准数据")
                return None

            # 标准化DataFrame
            df = self._standardize_dataframe(df)

            # 计算收益率
            df['returns'] = df['close'].pct_change()

            # 归一化为净值曲线(初始值=1)
            df['total'] = (1 + df['returns']).cumprod()

            return df

        except DataQueryError:
            # 数据查询错误记录日志，但返回None（基准数据不是必需的）
            logger.warning(f"获取基准数据失败: 数据查询错误")
            return None
        except Exception as e:
            logger.error(f"获取基准数据失败: {e}")
            # 基准数据不是必需的，返回None而不抛出异常
            return None

    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化DataFrame
        - 确保索引是datetime类型
        - 按日期排序

        Args:
            df: 原始DataFrame

        Returns:
            标准化后的DataFrame
        """
        result = df.copy()

        # 确保索引是datetime类型
        if not isinstance(result.index, pd.DatetimeIndex):
            result.index = pd.to_datetime(result.index)

        # 确保按日期排序
        result = result.sort_index()

        return result
