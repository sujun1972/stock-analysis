"""
特征工程引擎 - 统一接口
对齐文档: core/docs/ml/README.md (阶段1)

FeatureEngine提供统一的特征计算接口，封装了:
- AlphaFactors: 125+ Alpha因子
- TechnicalIndicators: 60+ 技术指标
- FeatureTransformer: 特征预处理

作者: Stock Analysis Team
创建时间: 2026-02-08
版本: v1.0.0
"""
from typing import List, Dict, Optional, Set
import pandas as pd
import numpy as np
from loguru import logger

from src.features.alpha_factors import AlphaFactors
from src.features.technical_indicators import TechnicalIndicators
from src.features.feature_transformer import FeatureTransformer


class FeatureEngine:
    """
    特征工程引擎

    职责:
    - 计算125+ Alpha因子
    - 计算60+ 技术指标
    - 特征转换与预处理

    使用示例:
        >>> engine = FeatureEngine(
        ...     feature_groups=['alpha', 'technical'],
        ...     lookback_window=60
        ... )
        >>> features = engine.calculate_features(
        ...     stock_codes=['600000.SH', '000001.SZ'],
        ...     market_data=data,
        ...     date='2024-01-15'
        ... )
    """

    def __init__(
        self,
        feature_groups: Optional[List[str]] = None,
        lookback_window: int = 60,
        cache_enabled: bool = True,
        fill_method: str = 'forward'
    ):
        """
        初始化特征引擎

        Args:
            feature_groups: 特征组列表
                - 'alpha': Alpha因子
                - 'technical': 技术指标
                - 'volume': 成交量特征
                - 'all': 所有特征
            lookback_window: 回溯窗口(天数)
            cache_enabled: 是否启用缓存
            fill_method: 缺失值填充方法 ('forward', 'zero', 'mean')
        """
        self.feature_groups = feature_groups or ['all']
        self.lookback_window = lookback_window
        self.cache_enabled = cache_enabled
        self.fill_method = fill_method

        # 缓存
        self._cache: Dict[str, pd.DataFrame] = {} if cache_enabled else {}

        # 特征列名缓存（用于对齐）
        self._feature_columns: Optional[List[str]] = None

        logger.debug(
            f"FeatureEngine初始化: groups={feature_groups}, "
            f"lookback={lookback_window}, cache={cache_enabled}"
        )

    def calculate_features(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str,
        return_type: str = 'dataframe'
    ) -> pd.DataFrame:
        """
        计算特征矩阵

        Args:
            stock_codes: 股票代码列表
            market_data: 市场数据 (包含OHLCV)
                必需列: date, stock_code, close
                可选列: open, high, low, volume
            date: 计算日期
            return_type: 返回类型 ('dataframe' or 'dict')

        Returns:
            pd.DataFrame: 特征矩阵
                - index: stock_codes
                - columns: feature_names (125+)
        """
        # 1. 检查缓存
        cache_key = self._generate_cache_key(stock_codes, date)
        if self.cache_enabled and cache_key in self._cache:
            logger.debug(f"从缓存返回特征: {cache_key}")
            return self._cache[cache_key].copy()

        # 2. 准备数据切片
        data_slice = self._prepare_data_slice(
            stock_codes, market_data, date
        )

        # 3. 计算特征
        features_df = self._calculate_all_features(
            stock_codes, data_slice, date
        )

        # 4. 特征后处理
        features_df = self._postprocess_features(features_df)

        # 5. 缓存
        if self.cache_enabled:
            self._cache[cache_key] = features_df.copy()

        return features_df

    def calculate_batch(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> pd.DataFrame:
        """
        批量计算特征（与calculate_features相同，提供兼容性）

        Args:
            stock_codes: 股票代码列表
            market_data: 市场数据
            date: 计算日期

        Returns:
            pd.DataFrame: 特征矩阵
        """
        return self.calculate_features(stock_codes, market_data, date)

    def get_feature_names(self) -> List[str]:
        """
        获取特征列名

        Returns:
            特征列名列表
        """
        if self._feature_columns is None:
            # 如果还没有计算过，返回空列表
            return []
        return self._feature_columns.copy()

    def clear_cache(self):
        """清空缓存"""
        if self.cache_enabled:
            self._cache.clear()
            logger.debug("缓存已清空")

    # ==================== 私有方法 ====================

    def _generate_cache_key(self, stock_codes: List[str], date: str) -> str:
        """生成缓存键"""
        stock_hash = hash(tuple(sorted(stock_codes)))
        return f"{date}_{stock_hash}"

    def _prepare_data_slice(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> pd.DataFrame:
        """
        准备数据切片

        Args:
            stock_codes: 股票代码列表
            market_data: 完整市场数据
            date: 目标日期

        Returns:
            数据切片
        """
        # 确保date列是datetime类型
        if 'date' not in market_data.columns:
            raise ValueError("market_data必须包含'date'列")

        if not pd.api.types.is_datetime64_any_dtype(market_data['date']):
            market_data = market_data.copy()
            market_data['date'] = pd.to_datetime(market_data['date'])

        # 计算日期范围
        end_date = pd.to_datetime(date)
        # 额外多取一些天数以确保有足够的数据计算指标
        start_date = end_date - pd.Timedelta(days=self.lookback_window + 100)

        # 过滤数据
        mask = (
            (market_data['date'] >= start_date) &
            (market_data['date'] <= end_date) &
            (market_data['stock_code'].isin(stock_codes))
        )
        data_slice = market_data[mask].copy()

        if len(data_slice) == 0:
            raise ValueError(
                f"No data found for date {date} and {len(stock_codes)} stocks"
            )

        logger.debug(
            f"数据切片: {len(data_slice)} 行, "
            f"{data_slice['date'].min()} 到 {data_slice['date'].max()}"
        )

        return data_slice

    def _calculate_all_features(
        self,
        stock_codes: List[str],
        data_slice: pd.DataFrame,
        date: str
    ) -> pd.DataFrame:
        """
        计算所有特征

        Args:
            stock_codes: 股票代码列表
            data_slice: 数据切片
            date: 目标日期

        Returns:
            特征DataFrame
        """
        features = pd.DataFrame(index=stock_codes)

        # 获取目标日期
        target_date = pd.to_datetime(date)

        # 按股票分组计算
        for stock in stock_codes:
            stock_data = data_slice[
                data_slice['stock_code'] == stock
            ].sort_values('date').copy()

            if len(stock_data) < 20:
                logger.warning(f"{stock}: 数据不足 ({len(stock_data)}天)")
                continue

            # 确保包含目标日期
            if target_date not in stock_data['date'].values:
                logger.warning(f"{stock}: 缺少目标日期 {date}")
                continue

            # 计算Alpha因子
            if self._should_include('alpha'):
                alpha_features = self._calculate_alpha_features(stock, stock_data)
                for col, val in alpha_features.items():
                    features.loc[stock, col] = val

            # 计算技术指标
            if self._should_include('technical'):
                tech_features = self._calculate_technical_features(stock, stock_data)
                for col, val in tech_features.items():
                    features.loc[stock, col] = val

            # 计算成交量特征
            if self._should_include('volume'):
                volume_features = self._calculate_volume_features(stock, stock_data, target_date)
                for col, val in volume_features.items():
                    features.loc[stock, col] = val

        # 记录特征列名
        self._feature_columns = features.columns.tolist()

        logger.debug(f"计算完成: {len(features)} 股票 × {len(features.columns)} 特征")

        return features

    def _should_include(self, group: str) -> bool:
        """判断是否包含特征组"""
        return 'all' in self.feature_groups or group in self.feature_groups

    def _calculate_alpha_features(
        self,
        stock_code: str,
        stock_data: pd.DataFrame
    ) -> Dict[str, float]:
        """
        计算Alpha因子

        Args:
            stock_code: 股票代码
            stock_data: 股票历史数据

        Returns:
            特征字典
        """
        try:
            # 准备数据格式 - AlphaFactors需要特定格式
            df = stock_data.copy()

            # 确保有必需的列
            if 'close' not in df.columns:
                logger.warning(f"{stock_code}: 缺少close列")
                return {}

            # 设置索引为日期
            if 'date' in df.columns:
                df = df.set_index('date')

            # 计算Alpha因子
            alpha_calculator = AlphaFactors(df, inplace=False)
            result = alpha_calculator.add_all_alpha_factors()

            if not result.success:
                logger.warning(f"{stock_code}: Alpha因子计算失败 - {result.message}")
                return {}

            # 提取最后一行的特征值
            result_df = result.data
            if len(result_df) == 0:
                return {}

            last_row = result_df.iloc[-1]

            # 过滤出alpha因子列
            alpha_cols = [col for col in last_row.index if col not in
                         ['open', 'high', 'low', 'close', 'volume', 'vol']]

            features = {}
            for col in alpha_cols:
                val = last_row[col]
                # 转换为float以避免isinf的类型问题
                try:
                    val_float = float(val)
                    if pd.notna(val_float) and not np.isinf(val_float):
                        features[col] = val_float
                except (ValueError, TypeError):
                    # 如果无法转换为float，跳过
                    pass

            return features

        except Exception as e:
            logger.warning(f"{stock_code}: Alpha因子计算异常 - {str(e)}")
            return {}

    def _calculate_technical_features(
        self,
        stock_code: str,
        stock_data: pd.DataFrame
    ) -> Dict[str, float]:
        """
        计算技术指标

        Args:
            stock_code: 股票代码
            stock_data: 股票历史数据

        Returns:
            特征字典
        """
        try:
            # 准备数据
            df = stock_data.copy()

            # 确保有OHLCV列
            required_cols = ['close']
            if not all(col in df.columns for col in required_cols):
                logger.warning(f"{stock_code}: 缺少必需列")
                return {}

            # 设置索引
            if 'date' in df.columns:
                df = df.set_index('date')

            # 计算技术指标
            tech_calculator = TechnicalIndicators(df)
            result_df = tech_calculator.add_all_indicators()

            if len(result_df) == 0:
                return {}

            # 提取最后一行
            last_row = result_df.iloc[-1]

            # 过滤技术指标列
            tech_cols = [col for col in last_row.index if col not in
                        ['open', 'high', 'low', 'close', 'volume', 'vol']]

            features = {}
            for col in tech_cols:
                val = last_row[col]
                # 转换为float以避免isinf的类型问题
                try:
                    val_float = float(val)
                    if pd.notna(val_float) and not np.isinf(val_float):
                        features[col] = val_float
                except (ValueError, TypeError):
                    # 如果无法转换为float，跳过
                    pass

            return features

        except Exception as e:
            logger.warning(f"{stock_code}: 技术指标计算异常 - {str(e)}")
            return {}

    def _calculate_volume_features(
        self,
        stock_code: str,
        stock_data: pd.DataFrame,
        target_date: pd.Timestamp
    ) -> Dict[str, float]:
        """
        计算成交量特征

        Args:
            stock_code: 股票代码
            stock_data: 股票历史数据
            target_date: 目标日期

        Returns:
            特征字典
        """
        features = {}

        try:
            # 确保有volume列
            volume_col = None
            if 'volume' in stock_data.columns:
                volume_col = 'volume'
            elif 'vol' in stock_data.columns:
                volume_col = 'vol'

            if volume_col is None:
                return features

            # 排序并获取到目标日期为止的数据
            df = stock_data.sort_values('date')
            df = df[df['date'] <= target_date]

            if len(df) < 20:
                return features

            # 计算成交量比率
            windows = [5, 10, 20]
            for window in windows:
                if len(df) >= window + 1:
                    recent_volume = df.iloc[-1][volume_col]
                    avg_volume = df.iloc[-window-1:-1][volume_col].mean()

                    if avg_volume > 0 and pd.notna(recent_volume):
                        ratio = recent_volume / avg_volume
                        if not np.isinf(ratio):
                            features[f'volume_ratio_{window}d'] = float(ratio)

            # 成交量标准差
            if len(df) >= 20:
                vol_std = df.iloc[-20:][volume_col].std()
                vol_mean = df.iloc[-20:][volume_col].mean()
                if vol_mean > 0:
                    features['volume_volatility'] = float(vol_std / vol_mean)

        except Exception as e:
            logger.warning(f"{stock_code}: 成交量特征计算异常 - {str(e)}")

        return features

    def _postprocess_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        特征后处理

        Args:
            features: 原始特征DataFrame

        Returns:
            处理后的特征DataFrame
        """
        # 处理缺失值
        if self.fill_method == 'zero':
            features = features.fillna(0)
        elif self.fill_method == 'mean':
            features = features.fillna(features.mean())
        elif self.fill_method == 'forward':
            # 新版pandas使用ffill()替代fillna(method='ffill')
            features = features.ffill().fillna(0)

        # 处理无穷值
        features = features.replace([np.inf, -np.inf], 0)

        # 使用FeatureTransformer进行标准化（可选）
        # 这里先保持简单，后续可以增强

        return features

    def __repr__(self) -> str:
        return (
            f"FeatureEngine("
            f"groups={self.feature_groups}, "
            f"lookback={self.lookback_window}, "
            f"cache={self.cache_enabled}, "
            f"n_features={len(self._feature_columns) if self._feature_columns else 0})"
        )
