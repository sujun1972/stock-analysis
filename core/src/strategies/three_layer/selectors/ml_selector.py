"""
MLSelector - 机器学习选股器

在 Core 内部实现 StarRanker 功能

本模块提供基于机器学习的股票选择器，支持多因子加权和 LightGBM 排序模型。

版本历史：
- v1.0: 基础实现（11个手工特征）
- v2.0: 集成 FeatureEngineer（125+ 因子库）
"""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from loguru import logger

from ..base.stock_selector import SelectorParameter, StockSelector

# 集成特征工程模块（ML-4）
try:
    from src.features.technical_indicators import TechnicalIndicators
    from src.features.alpha import AlphaFactors
    HAS_FEATURE_ENGINE = True
except ImportError as e:
    logger.warning(f"无法导入特征工程模块: {e}，将使用简化版特征计算")
    HAS_FEATURE_ENGINE = False


class MLSelector(StockSelector):
    """
    机器学习选股器 - Core 内部实现 StarRanker 功能

    核心功能：
    1. 自动计算多维度因子（技术、基本面、市场）
    2. 使用机器学习模型对股票评分
    3. 选出评分最高的 Top N 股票

    支持三种模式：
    - multi_factor_weighted: 多因子加权（基础版，默认）
    - lightgbm_ranker: LightGBM 排序模型（进阶版）
    - custom_model: 自定义模型（用户继承并实现）

    使用示例：
        # 基础版：多因子加权
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 50,
            'features': 'momentum_20d,rsi_14d,volume_ratio,volatility_20d'
        })

        # 进阶版：LightGBM 模型
        selector = MLSelector(params={
            'mode': 'lightgbm_ranker',
            'model_path': './models/stock_ranker.pkl',
            'top_n': 50
        })

        # 选股
        selected_stocks = selector.select(
            date=pd.Timestamp('2023-06-01'),
            market_data=prices_df
        )
    """

    @property
    def id(self) -> str:
        return "ml_selector"

    @property
    def name(self) -> str:
        return "机器学习选股器（StarRanker 功能）"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        """获取参数定义列表"""
        return [
            SelectorParameter(
                name="mode",
                label="选股模式",
                type="select",
                default="multi_factor_weighted",
                options=[
                    {"value": "multi_factor_weighted", "label": "多因子加权"},
                    {"value": "lightgbm_ranker", "label": "LightGBM排序模型"},
                    {"value": "custom_model", "label": "自定义模型"}
                ],
                description="选择评分模型类型"
            ),
            SelectorParameter(
                name="top_n",
                label="选股数量",
                type="integer",
                default=50,
                min_value=5,
                max_value=200,
                description="选出评分最高的前 N 只股票"
            ),
            SelectorParameter(
                name="features",
                label="特征列表",
                type="string",
                default="momentum_20d,rsi_14d,volatility_20d,volume_ratio",
                description="逗号分隔的特征名称（留空使用默认特征集；支持通配符：'alpha:*'表示所有Alpha因子，'tech:*'表示所有技术指标）"
            ),
            SelectorParameter(
                name="use_feature_engine",
                label="使用完整特征库",
                type="boolean",
                default=True,
                description="是否使用完整特征工程库（125+ 因子），False则使用快速简化版（11个特征）"
            ),
            SelectorParameter(
                name="model_path",
                label="模型路径",
                type="string",
                default="",
                description="训练好的模型文件路径（仅 lightgbm/custom 模式需要）"
            ),
            SelectorParameter(
                name="filter_min_volume",
                label="最小成交量过滤",
                type="float",
                default=0,
                min_value=0,
                description="过滤日均成交量小于此值的股票（0=不过滤）"
            ),
            SelectorParameter(
                name="filter_max_price",
                label="最高价格过滤",
                type="float",
                default=0,
                min_value=0,
                description="过滤价格高于此值的股票（0=不过滤）"
            ),
            SelectorParameter(
                name="filter_min_price",
                label="最低价格过滤",
                type="float",
                default=0,
                min_value=0,
                description="过滤价格低于此值的股票（0=不过滤）"
            ),
            SelectorParameter(
                name="factor_weights",
                label="因子权重",
                type="string",
                default="",
                description="因子权重配置（JSON格式），如：{\"momentum_20d\": 0.3, \"rsi_14d\": 0.2}"
            ),
            SelectorParameter(
                name="normalization_method",
                label="归一化方法",
                type="select",
                default="z_score",
                options=[
                    {"value": "z_score", "label": "Z-Score标准化"},
                    {"value": "min_max", "label": "Min-Max归一化"},
                    {"value": "rank", "label": "排名归一化"},
                    {"value": "none", "label": "不归一化"}
                ],
                description="特征归一化方法"
            ),
            SelectorParameter(
                name="factor_groups",
                label="因子分组",
                type="string",
                default="",
                description="因子分组配置（JSON格式），如：{\"momentum\": [\"momentum_5d\", \"momentum_20d\"], \"technical\": [\"rsi_14d\"]}"
            ),
            SelectorParameter(
                name="group_weights",
                label="分组权重",
                type="string",
                default="",
                description="分组权重配置（JSON格式），如：{\"momentum\": 0.4, \"technical\": 0.6}"
            )
        ]

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化 MLSelector

        Args:
            params: 参数字典
                - mode: 选股模式（'multi_factor_weighted', 'lightgbm_ranker', 'custom_model'）
                - top_n: 选股数量
                - features: 特征列表（逗号分隔）
                - use_feature_engine: 是否使用完整特征库（默认 True）
                - model_path: 模型文件路径
                - filter_*: 过滤条件
                - factor_weights: 因子权重配置（JSON）
                - normalization_method: 归一化方法
                - factor_groups: 因子分组配置（JSON）
                - group_weights: 分组权重配置（JSON）

        Raises:
            ValueError: 参数验证失败时抛出
        """
        super().__init__(params)

        # 加载模型
        self.mode = self.params.get('mode', 'multi_factor_weighted')
        self.model = self._load_model()

        # 是否使用完整特征库（ML-4 新增）
        self.use_feature_engine = self.params.get('use_feature_engine', True) and HAS_FEATURE_ENGINE
        if self.params.get('use_feature_engine', True) and not HAS_FEATURE_ENGINE:
            logger.warning("无法加载特征工程库，使用简化版特征计算")

        # 解析特征列表（支持通配符）
        features_str = self.params.get('features', '')
        if features_str:
            self.features = self._parse_features(features_str)
        else:
            # 使用默认特征集
            self.features = self._get_default_features()

        # 解析因子权重
        self.factor_weights = self._parse_factor_weights()

        # 解析因子分组
        self.factor_groups = self._parse_factor_groups()
        self.group_weights = self._parse_group_weights()

        # 特征缓存（优化性能）
        self._feature_cache: Dict[str, pd.DataFrame] = {}

        logger.info(
            f"MLSelector 初始化完成: mode={self.mode}, "
            f"features={len(self.features)}, top_n={self.params.get('top_n', 50)}, "
            f"use_feature_engine={self.use_feature_engine}, "
            f"normalization={self.params.get('normalization_method', 'z_score')}"
        )

    def select(
        self,
        date: pd.Timestamp,
        market_data: pd.DataFrame
    ) -> List[str]:
        """
        机器学习选股主流程

        步骤：
        1. 数据预处理和过滤
        2. 计算特征矩阵
        3. 模型评分
        4. 排序并选出 Top N

        Args:
            date: 选股日期
            market_data: 全市场价格数据
                        DataFrame(index=日期, columns=股票代码, values=收盘价)

        Returns:
            选出的股票代码列表

        注意:
            - 如果数据不足或无有效股票，返回空列表
            - 过滤规则按优先级应用：价格 -> 成交量 -> 其他
        """
        logger.debug(f"MLSelector 选股: date={date}")

        # 1. 数据预处理
        valid_stocks = self._preprocess(date, market_data)
        if not valid_stocks:
            logger.warning(f"日期 {date} 无有效股票")
            return []

        # 2. 计算特征
        feature_matrix = self._calculate_features(date, market_data, valid_stocks)
        if feature_matrix.empty:
            logger.warning(f"日期 {date} 特征计算失败")
            return []

        # 3. 模型评分
        scores = self._score_stocks(feature_matrix)
        if scores.empty or scores.isna().all():
            logger.warning(f"日期 {date} 评分失败")
            return []

        # 4. 排序选股
        top_n = self.params.get('top_n', 50)
        selected_stocks = self._rank_and_select(scores, top_n)

        logger.info(
            f"MLSelector 完成: 选出 {len(selected_stocks)} 只股票 "
            f"(候选: {len(valid_stocks)})"
        )
        return selected_stocks

    def _preprocess(
        self,
        date: pd.Timestamp,
        market_data: pd.DataFrame
    ) -> List[str]:
        """
        数据预处理：过滤不符合条件的股票

        Args:
            date: 选股日期
            market_data: 全市场价格数据

        Returns:
            通过过滤条件的股票代码列表

        过滤规则：
        1. 基础过滤：去除 NaN 价格
        2. 价格过滤：最低价格、最高价格
        3. 成交量过滤（如果有数据）
        """
        # 检查日期是否在数据范围内
        if date not in market_data.index:
            logger.warning(f"日期 {date} 不在数据范围内")
            return []

        try:
            current_prices = market_data.loc[date]
        except KeyError:
            logger.warning(f"日期 {date} 无法获取价格数据")
            return []

        # 基础过滤：去除 NaN
        valid_stocks = current_prices.dropna().index.tolist()
        logger.debug(f"基础过滤后: {len(valid_stocks)} 只股票")

        if not valid_stocks:
            return []

        # 价格过滤：最低价格
        min_price = self.params.get('filter_min_price', 0)
        if min_price > 0:
            valid_stocks = [
                stock for stock in valid_stocks
                if current_prices[stock] >= min_price
            ]
            logger.debug(
                f"最低价格过滤 (>={min_price}) 后: {len(valid_stocks)} 只股票"
            )

        # 价格过滤：最高价格
        max_price = self.params.get('filter_max_price', 0)
        if max_price > 0:
            valid_stocks = [
                stock for stock in valid_stocks
                if current_prices[stock] <= max_price
            ]
            logger.debug(
                f"最高价格过滤 (<={max_price}) 后: {len(valid_stocks)} 只股票"
            )

        # 成交量过滤（如果需要）
        min_volume = self.params.get('filter_min_volume', 0)
        if min_volume > 0:
            # TODO: 集成成交量数据
            logger.debug("成交量过滤暂未实现（需要成交量数据）")

        return valid_stocks

    def _calculate_features(
        self,
        date: pd.Timestamp,
        market_data: pd.DataFrame,
        stocks: List[str]
    ) -> pd.DataFrame:
        """
        计算特征矩阵（ML-4 增强版：支持完整特征库）

        Args:
            date: 选股日期
            market_data: 全市场价格数据
            stocks: 候选股票列表

        Returns:
            特征矩阵 DataFrame(index=股票代码, columns=特征名)

        特征计算规则：
        - v2.0: 支持特征库集成（125+ 因子）
        - v1.0: 每只股票独立计算特征（11个简化特征）
        - 遇到错误的股票跳过
        - 缺失值填充为 0
        """
        if self.use_feature_engine:
            # 使用完整特征库（ML-4 新增）
            return self._calculate_features_with_engine(date, market_data, stocks)
        else:
            # 使用简化版快速计算（向后兼容）
            return self._calculate_features_fast(date, market_data, stocks)

    def _calculate_features_with_engine(
        self,
        date: pd.Timestamp,
        market_data: pd.DataFrame,
        stocks: List[str]
    ) -> pd.DataFrame:
        """
        使用完整特征工程库计算特征（ML-4 核心方法）

        支持的特征类别：
        - 技术指标（TechnicalIndicators）：60+ 指标
        - Alpha因子（AlphaFactors）：50+ 因子
          - momentum: 动量因子
          - reversal: 反转因子
          - volatility: 波动率因子
          - volume: 成交量因子
          - trend: 趋势因子
          - liquidity: 流动性因子

        Args:
            date: 选股日期
            market_data: 全市场价格数据
            stocks: 候选股票列表

        Returns:
            特征矩阵 DataFrame(index=股票代码, columns=特征名)
        """
        feature_data = []

        for stock in stocks:
            try:
                # 获取股票历史数据
                stock_prices = market_data[stock].dropna()
                if len(stock_prices) < 60:  # 至少需要60天数据
                    logger.debug(f"{stock} 数据不足 ({len(stock_prices)} < 60)")
                    continue

                # 转换为OHLCV格式（如果market_data只有收盘价）
                if isinstance(stock_prices, pd.Series):
                    stock_df = pd.DataFrame({
                        'close': stock_prices,
                        'open': stock_prices,  # 简化：使用close代替
                        'high': stock_prices * 1.02,  # 简化：估算高点
                        'low': stock_prices * 0.98,   # 简化：估算低点
                        'volume': 1000000  # 简化：固定成交量
                    })
                else:
                    stock_df = stock_prices

                # 计算特征
                features = self._compute_features_for_stock(stock_df, date)
                if features:
                    features['stock_code'] = stock
                    feature_data.append(features)

            except Exception as e:
                logger.debug(f"计算 {stock} 特征失败: {e}")
                continue

        if not feature_data:
            logger.warning("没有成功计算特征的股票")
            return pd.DataFrame()

        df = pd.DataFrame(feature_data)
        df.set_index('stock_code', inplace=True)

        # 处理缺失值和无穷值
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.fillna(0, inplace=True)

        logger.debug(
            f"特征矩阵（完整库）: {len(df)} 只股票 × {len(df.columns)} 个特征"
        )

        return df

    def _calculate_features_fast(
        self,
        date: pd.Timestamp,
        market_data: pd.DataFrame,
        stocks: List[str]
    ) -> pd.DataFrame:
        """
        使用简化版快速特征计算（向后兼容）

        仅支持11个基础技术指标，计算速度快
        """
        feature_data = []

        for stock in stocks:
            try:
                stock_prices = market_data[stock]

                # 计算每个特征
                features = {}
                for feature_name in self.features:
                    feature_value = self._calculate_single_feature(
                        feature_name, stock_prices, date
                    )
                    features[feature_name] = feature_value

                features['stock_code'] = stock
                feature_data.append(features)

            except Exception as e:
                logger.debug(f"计算 {stock} 特征失败: {e}")
                continue

        if not feature_data:
            logger.warning("没有成功计算特征的股票")
            return pd.DataFrame()

        df = pd.DataFrame(feature_data)
        df.set_index('stock_code', inplace=True)

        # 处理缺失值和无穷值
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.fillna(0, inplace=True)

        logger.debug(
            f"特征矩阵（快速版）: {len(df)} 只股票 × {len(df.columns)} 个特征"
        )

        return df

    def _calculate_single_feature(
        self,
        feature_name: str,
        prices: pd.Series,
        date: pd.Timestamp
    ) -> float:
        """
        计算单个特征值

        支持的特征类型：
        - momentum_Nd: N日动量（收益率）
        - rsi_Nd: N日RSI指标
        - volatility_Nd: N日波动率
        - atr_Nd: N日ATR（平均真实波幅）
        - volume_ratio: 量比（需要成交量数据）
        - ma_cross_Nd: N日均线偏离度

        Args:
            feature_name: 特征名称
            prices: 股票价格序列
            date: 计算日期

        Returns:
            特征值（float）

        注意：
            - 如果计算失败或日期不存在，返回 0.0
            - 所有特征值应该是无量纲的相对指标
        """
        try:
            # 确保日期在价格序列中
            if date not in prices.index:
                return 0.0

            # 动量类特征: momentum_20d
            if feature_name.startswith('momentum_'):
                period = int(feature_name.split('_')[1].replace('d', ''))
                if len(prices) < period:
                    return 0.0
                momentum = prices.pct_change(period)
                return float(momentum.loc[date]) if not pd.isna(momentum.loc[date]) else 0.0

            # RSI 指标: rsi_14d
            elif feature_name.startswith('rsi_'):
                period = int(feature_name.split('_')[1].replace('d', ''))
                rsi = self._calculate_rsi(prices, period)
                return float(rsi.loc[date]) if not pd.isna(rsi.loc[date]) else 0.0

            # 波动率: volatility_20d
            elif feature_name.startswith('volatility_'):
                period = int(feature_name.split('_')[1].replace('d', ''))
                if len(prices) < period:
                    return 0.0
                volatility = prices.pct_change().rolling(period).std()
                return float(volatility.loc[date]) if not pd.isna(volatility.loc[date]) else 0.0

            # ATR 指标: atr_14d (简化版，仅用收盘价)
            elif feature_name.startswith('atr_'):
                period = int(feature_name.split('_')[1].replace('d', ''))
                if len(prices) < period:
                    return 0.0
                # 简化版：使用价格变化的绝对值作为 ATR 近似
                atr = prices.diff().abs().rolling(period).mean()
                atr_pct = atr / prices  # 归一化
                return float(atr_pct.loc[date]) if not pd.isna(atr_pct.loc[date]) else 0.0

            # 量比: volume_ratio (需要成交量数据，暂未实现)
            elif feature_name == 'volume_ratio':
                # TODO: 需要成交量数据
                logger.debug(f"特征 {feature_name} 暂未实现（需要成交量数据）")
                return 0.0

            # 均线偏离度: ma_cross_20d
            elif feature_name.startswith('ma_cross_'):
                period = int(feature_name.split('_')[2].replace('d', ''))
                if len(prices) < period:
                    return 0.0
                ma = prices.rolling(period).mean()
                # 计算价格相对均线的偏离度
                deviation = (prices - ma) / ma
                return float(deviation.loc[date]) if not pd.isna(deviation.loc[date]) else 0.0

            # 未知特征
            else:
                logger.warning(f"未知特征: {feature_name}")
                return 0.0

        except Exception as e:
            logger.debug(f"特征 {feature_name} 计算失败: {e}")
            return 0.0

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        计算 RSI 指标（相对强弱指数）

        Args:
            prices: 价格序列
            period: RSI 周期（默认14日）

        Returns:
            RSI 序列（0-100）

        公式:
            RSI = 100 - (100 / (1 + RS))
            RS = 平均涨幅 / 平均跌幅
        """
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()

        # 避免除以零
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _score_stocks(self, feature_matrix: pd.DataFrame) -> pd.Series:
        """
        对股票评分

        Args:
            feature_matrix: 特征矩阵 DataFrame(index=股票代码, columns=特征名)

        Returns:
            评分序列 pd.Series(index=股票代码, values=评分)

        评分策略：
        - multi_factor_weighted: 多因子加权（特征归一化后等权平均）
        - lightgbm_ranker: LightGBM 排序模型预测
        - custom_model: 自定义模型评分（需要子类实现）
        """
        if self.mode == 'multi_factor_weighted':
            return self._score_multi_factor(feature_matrix)
        elif self.mode == 'lightgbm_ranker':
            return self._score_lightgbm(feature_matrix)
        elif self.mode == 'custom_model':
            return self._score_custom(feature_matrix)
        else:
            raise ValueError(f"未知模式: {self.mode}")

    def _score_multi_factor(self, feature_matrix: pd.DataFrame) -> pd.Series:
        """
        多因子加权评分（增强版）

        策略：
        1. 特征归一化（支持多种方法：Z-score、Min-Max、Rank）
        2. 加权平均（支持因子权重、分组权重）
        3. 返回综合评分

        Args:
            feature_matrix: 特征矩阵

        Returns:
            评分序列

        支持的增强功能：
            - 多种归一化方法（z_score、min_max、rank、none）
            - 自定义因子权重
            - 因子分组加权
            - 分组内等权、组间加权
        """
        if feature_matrix.empty:
            return pd.Series(dtype=float)

        # 1. 归一化特征
        normalization_method = self.params.get('normalization_method', 'z_score')
        normalized = self._normalize_features(feature_matrix, normalization_method)

        # 2. 计算加权评分
        if self.factor_groups:
            # 使用因子分组加权
            scores = self._score_with_groups(normalized)
        elif self.factor_weights:
            # 使用因子权重加权
            scores = self._score_with_weights(normalized)
        else:
            # 等权平均（默认）
            scores = normalized.mean(axis=1)

        logger.debug(
            f"多因子评分完成: 范围=[{scores.min():.4f}, {scores.max():.4f}], "
            f"均值={scores.mean():.4f}, 方法={normalization_method}"
        )

        return scores

    def _normalize_features(
        self,
        feature_matrix: pd.DataFrame,
        method: str
    ) -> pd.DataFrame:
        """
        归一化特征矩阵

        Args:
            feature_matrix: 原始特征矩阵
            method: 归一化方法
                - z_score: Z-Score 标准化 (X - mean) / std
                - min_max: Min-Max 归一化 (X - min) / (max - min)
                - rank: 排名归一化（转换为百分位排名）
                - none: 不归一化

        Returns:
            归一化后的特征矩阵
        """
        if method == 'z_score':
            # Z-Score 标准化
            mean = feature_matrix.mean()
            std = feature_matrix.std()
            std = std.replace(0, 1)  # 避免除以零
            normalized = (feature_matrix - mean) / std

        elif method == 'min_max':
            # Min-Max 归一化到 [0, 1]
            min_val = feature_matrix.min()
            max_val = feature_matrix.max()
            range_val = max_val - min_val
            range_val = range_val.replace(0, 1)  # 避免除以零
            normalized = (feature_matrix - min_val) / range_val

        elif method == 'rank':
            # 排名归一化（百分位）
            normalized = feature_matrix.rank(pct=True)

        elif method == 'none':
            # 不归一化
            normalized = feature_matrix.copy()

        else:
            logger.warning(f"未知归一化方法: {method}，使用 z_score")
            mean = feature_matrix.mean()
            std = feature_matrix.std()
            std = std.replace(0, 1)
            normalized = (feature_matrix - mean) / std

        # 处理缺失值和无穷值
        normalized.replace([np.inf, -np.inf], np.nan, inplace=True)
        normalized.fillna(0, inplace=True)

        return normalized

    def _score_with_weights(self, feature_matrix: pd.DataFrame) -> pd.Series:
        """
        使用因子权重加权评分

        Args:
            feature_matrix: 归一化后的特征矩阵

        Returns:
            加权评分序列
        """
        # 确保所有特征都有权重
        weights = {}
        total_weight = 0.0

        for feature in feature_matrix.columns:
            weight = self.factor_weights.get(feature, 1.0)
            weights[feature] = weight
            total_weight += weight

        # 归一化权重（使权重和为1）
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        else:
            weights = {k: 1.0 / len(weights) for k in weights}

        # 加权求和
        scores = pd.Series(0.0, index=feature_matrix.index)
        for feature, weight in weights.items():
            if feature in feature_matrix.columns:
                scores += feature_matrix[feature] * weight

        logger.debug(f"因子权重加权: {len(weights)} 个因子")

        return scores

    def _score_with_groups(self, feature_matrix: pd.DataFrame) -> pd.Series:
        """
        使用因子分组加权评分

        策略：
        1. 组内因子等权平均
        2. 组间加权求和

        Args:
            feature_matrix: 归一化后的特征矩阵

        Returns:
            分组加权评分序列
        """
        group_scores = {}

        # 计算每个组的评分（组内等权平均）
        for group_name, feature_list in self.factor_groups.items():
            # 筛选出该组中存在的特征
            valid_features = [f for f in feature_list if f in feature_matrix.columns]

            if not valid_features:
                logger.warning(f"分组 {group_name} 中没有有效特征")
                continue

            # 组内等权平均
            group_score = feature_matrix[valid_features].mean(axis=1)
            group_scores[group_name] = group_score

        if not group_scores:
            logger.warning("没有有效的因子分组，使用等权平均")
            return feature_matrix.mean(axis=1)

        # 组间加权求和
        total_weight = 0.0
        final_scores = pd.Series(0.0, index=feature_matrix.index)

        for group_name, group_score in group_scores.items():
            weight = self.group_weights.get(group_name, 1.0)
            total_weight += weight
            final_scores += group_score * weight

        # 归一化
        if total_weight > 0:
            final_scores = final_scores / total_weight

        logger.debug(
            f"分组加权评分: {len(group_scores)} 个分组, "
            f"权重={list(self.group_weights.values())}"
        )

        return final_scores

    def _score_lightgbm(self, feature_matrix: pd.DataFrame) -> pd.Series:
        """
        LightGBM 排序模型评分

        Args:
            feature_matrix: 特征矩阵

        Returns:
            评分序列

        注意：
            - 需要预先训练好的模型文件
            - 特征顺序必须与训练时一致
            - 如果模型未加载，回退到多因子加权
        """
        if self.model is None:
            logger.warning("LightGBM 模型未加载，使用多因子加权评分")
            return self._score_multi_factor(feature_matrix)

        try:
            # 预测评分
            scores = self.model.predict(feature_matrix.values)
            result = pd.Series(index=feature_matrix.index, data=scores)

            logger.debug(
                f"LightGBM 评分范围: [{result.min():.4f}, {result.max():.4f}]"
            )

            return result

        except Exception as e:
            logger.error(f"LightGBM 评分失败: {e}，回退到多因子加权")
            return self._score_multi_factor(feature_matrix)

    def _score_custom(self, feature_matrix: pd.DataFrame) -> pd.Series:
        """
        自定义模型评分

        用户可以继承 MLSelector 并重写此方法实现自定义评分逻辑

        Args:
            feature_matrix: 特征矩阵

        Returns:
            评分序列

        Raises:
            NotImplementedError: 默认未实现，需要子类重写

        示例：
            class MyCustomSelector(MLSelector):
                def _score_custom(self, feature_matrix):
                    # 自定义评分逻辑
                    return my_scoring_function(feature_matrix)
        """
        raise NotImplementedError(
            "请继承 MLSelector 并实现 _score_custom() 方法"
        )

    def _rank_and_select(self, scores: pd.Series, top_n: int) -> List[str]:
        """
        排序并选出 Top N

        Args:
            scores: 评分序列
            top_n: 选股数量

        Returns:
            选出的股票代码列表

        排序规则：
        - 按评分降序排序
        - 选出前 top_n 只股票
        - 如果评分相同，按股票代码字典序排序
        """
        if scores.empty:
            return []

        # 降序排序
        ranked = scores.sort_values(ascending=False)

        # 选出前 top_n
        actual_top_n = min(top_n, len(ranked))
        selected = ranked.head(actual_top_n).index.tolist()

        # 打印 Top 5 评分
        if len(selected) > 0:
            top_5 = ranked.head(5)
            logger.debug(
                f"Top 5 评分: " +
                ", ".join([f"{stock}: {score:.4f}" for stock, score in top_5.items()])
            )

        return selected

    def _load_model(self):
        """
        加载机器学习模型

        Returns:
            加载的模型对象，如果不需要或加载失败则返回 None

        支持的模型格式：
        - joblib pickle (.pkl)
        - 其他格式可扩展

        注意：
            - 仅 lightgbm_ranker 和 custom_model 模式需要加载模型
            - 如果加载失败，自动回退到 multi_factor_weighted 模式
        """
        if self.mode == 'multi_factor_weighted':
            # 多因子加权不需要模型
            return None

        elif self.mode in ['lightgbm_ranker', 'custom_model']:
            model_path = self.params.get('model_path', '')
            if not model_path:
                logger.warning(
                    f"{self.mode} 模式未提供 model_path，"
                    f"回退到 multi_factor_weighted 模式"
                )
                self.mode = 'multi_factor_weighted'
                return None

            try:
                import joblib
                model = joblib.load(model_path)
                logger.info(f"模型加载成功: {model_path}")
                return model

            except ImportError:
                logger.error("joblib 未安装，无法加载模型，回退到 multi_factor_weighted")
                self.mode = 'multi_factor_weighted'
                return None

            except Exception as e:
                logger.error(f"模型加载失败: {e}，回退到 multi_factor_weighted")
                self.mode = 'multi_factor_weighted'
                return None

        return None

    def _get_default_features(self) -> List[str]:
        """
        获取默认特征集

        Returns:
            默认特征名称列表

        默认特征集：
        - 动量类: 5/10/20/60 日动量
        - 技术指标: RSI(14/28)
        - 波动率: 20/60 日波动率
        - 均线: 20/60 日均线偏离度
        - ATR: 14 日平均真实波幅
        """
        return [
            # 动量类（短期到长期）
            'momentum_5d',
            'momentum_10d',
            'momentum_20d',
            'momentum_60d',

            # 技术指标
            'rsi_14d',
            'rsi_28d',

            # 波动率
            'volatility_20d',
            'volatility_60d',

            # 均线偏离度
            'ma_cross_20d',
            'ma_cross_60d',

            # ATR（风险指标）
            'atr_14d',
        ]

    def _parse_factor_weights(self) -> Dict[str, float]:
        """
        解析因子权重配置

        Returns:
            因子权重字典 {feature_name: weight}

        示例配置：
            {"momentum_20d": 0.3, "rsi_14d": 0.2, "volatility_20d": 0.5}
        """
        weights_str = self.params.get('factor_weights', '')
        if not weights_str:
            return {}

        try:
            import json
            weights = json.loads(weights_str)

            # 验证权重格式
            if not isinstance(weights, dict):
                logger.warning("因子权重格式错误，应为字典")
                return {}

            # 转换为浮点数
            weights = {k: float(v) for k, v in weights.items()}

            logger.info(f"解析因子权重: {len(weights)} 个因子")
            return weights

        except Exception as e:
            logger.error(f"解析因子权重失败: {e}")
            return {}

    def _parse_factor_groups(self) -> Dict[str, List[str]]:
        """
        解析因子分组配置

        Returns:
            因子分组字典 {group_name: [feature1, feature2, ...]}

        示例配置：
            {
                "momentum": ["momentum_5d", "momentum_20d"],
                "technical": ["rsi_14d", "rsi_28d"],
                "volatility": ["volatility_20d", "atr_14d"]
            }
        """
        groups_str = self.params.get('factor_groups', '')
        if not groups_str:
            return {}

        try:
            import json
            groups = json.loads(groups_str)

            # 验证分组格式
            if not isinstance(groups, dict):
                logger.warning("因子分组格式错误，应为字典")
                return {}

            # 验证每个分组是列表
            for group_name, feature_list in groups.items():
                if not isinstance(feature_list, list):
                    logger.warning(f"分组 {group_name} 的特征列表格式错误")
                    return {}

            logger.info(f"解析因子分组: {len(groups)} 个分组")
            return groups

        except Exception as e:
            logger.error(f"解析因子分组失败: {e}")
            return {}

    def _parse_group_weights(self) -> Dict[str, float]:
        """
        解析分组权重配置

        Returns:
            分组权重字典 {group_name: weight}

        示例配置：
            {"momentum": 0.4, "technical": 0.3, "volatility": 0.3}
        """
        weights_str = self.params.get('group_weights', '')
        if not weights_str:
            # 如果没有配置，默认等权
            if self.factor_groups:
                num_groups = len(self.factor_groups)
                return {name: 1.0 / num_groups for name in self.factor_groups.keys()}
            return {}

        try:
            import json
            weights = json.loads(weights_str)

            # 验证权重格式
            if not isinstance(weights, dict):
                logger.warning("分组权重格式错误，应为字典")
                return {}

            # 转换为浮点数
            weights = {k: float(v) for k, v in weights.items()}

            logger.info(f"解析分组权重: {len(weights)} 个分组")
            return weights

        except Exception as e:
            logger.error(f"解析分组权重失败: {e}")
            return {}

    def _parse_features(self, features_str: str) -> List[str]:
        """
        解析特征列表（ML-4 新增：支持通配符）

        支持的格式：
        - 普通列表: "momentum_20d,rsi_14d,volatility_20d"
        - 通配符: "alpha:*" (所有Alpha因子)
        - 通配符: "tech:*" (所有技术指标)
        - 混合: "momentum_20d,alpha:momentum,tech:rsi"

        Args:
            features_str: 特征字符串

        Returns:
            特征名称列表
        """
        if not features_str:
            return self._get_default_features()

        features = []
        for item in features_str.split(','):
            item = item.strip()
            if not item:
                continue

            # 通配符：alpha:* 表示所有Alpha因子
            if item == 'alpha:*':
                features.extend(self._get_all_alpha_factors())
            # 通配符：tech:* 表示所有技术指标
            elif item == 'tech:*':
                features.extend(self._get_all_technical_indicators())
            # 通配符：alpha:momentum 表示某类Alpha因子
            elif item.startswith('alpha:'):
                category = item.split(':')[1]
                features.extend(self._get_alpha_factors_by_category(category))
            # 通配符：tech:rsi 表示某类技术指标
            elif item.startswith('tech:'):
                category = item.split(':')[1]
                features.extend(self._get_tech_indicators_by_category(category))
            # 普通特征名
            else:
                features.append(item)

        # 去重
        features = list(dict.fromkeys(features))

        logger.debug(f"解析特征列表: {len(features)} 个特征")
        return features

    def _compute_features_for_stock(
        self,
        stock_df: pd.DataFrame,
        date: pd.Timestamp
    ) -> Optional[Dict[str, float]]:
        """
        为单只股票计算所有特征（ML-4 核心方法）

        Args:
            stock_df: 股票OHLCV数据
            date: 计算日期

        Returns:
            特征字典 {feature_name: value}
        """
        if date not in stock_df.index:
            return None

        features = {}

        try:
            # 计算技术指标
            ti = TechnicalIndicators(stock_df)
            ti.add_all_indicators()
            ti_df = ti.get_dataframe()

            # 计算Alpha因子
            af = AlphaFactors(stock_df)
            af.add_all_alpha_factors()
            af_df = af.get_dataframe()

            # 提取指定日期的特征值
            for feature_name in self.features:
                try:
                    if feature_name in ti_df.columns:
                        value = ti_df.loc[date, feature_name]
                    elif feature_name in af_df.columns:
                        value = af_df.loc[date, feature_name]
                    else:
                        # 尝试使用简化版计算
                        value = self._calculate_single_feature(
                            feature_name, stock_df['close'], date
                        )

                    features[feature_name] = float(value) if not pd.isna(value) else 0.0

                except Exception as e:
                    logger.debug(f"特征 {feature_name} 计算失败: {e}")
                    features[feature_name] = 0.0

            return features

        except Exception as e:
            logger.debug(f"计算特征失败: {e}")
            return None

    def _get_all_alpha_factors(self) -> List[str]:
        """获取所有Alpha因子名称列表"""
        if not HAS_FEATURE_ENGINE:
            return []

        # 返回常用Alpha因子名称
        return [
            # 动量因子
            'momentum_5d', 'momentum_10d', 'momentum_20d', 'momentum_60d',
            # 反转因子
            'reversal_1d', 'reversal_3d', 'reversal_5d',
            # 波动率因子
            'volatility_5d', 'volatility_10d', 'volatility_20d',
            # 成交量因子
            'volume_ratio_5d', 'volume_ratio_10d', 'volume_ratio_20d',
            # 趋势因子
            'trend_strength_20d', 'trend_strength_60d',
        ]

    def _get_all_technical_indicators(self) -> List[str]:
        """获取所有技术指标名称列表"""
        if not HAS_FEATURE_ENGINE:
            return []

        # 返回常用技术指标名称
        return [
            # 均线
            'ma_5', 'ma_10', 'ma_20', 'ma_60',
            # EMA
            'ema_12', 'ema_26',
            # RSI
            'rsi_6', 'rsi_12', 'rsi_24',
            # MACD
            'macd', 'macd_signal', 'macd_hist',
            # 布林带
            'bb_upper', 'bb_middle', 'bb_lower',
            # ATR
            'atr_14', 'atr_28',
            # CCI
            'cci_14', 'cci_28',
        ]

    def _get_alpha_factors_by_category(self, category: str) -> List[str]:
        """
        根据类别获取Alpha因子

        Args:
            category: 因子类别 (momentum, reversal, volatility, volume, trend)

        Returns:
            因子名称列表
        """
        category_map = {
            'momentum': ['momentum_5d', 'momentum_10d', 'momentum_20d', 'momentum_60d'],
            'reversal': ['reversal_1d', 'reversal_3d', 'reversal_5d'],
            'volatility': ['volatility_5d', 'volatility_10d', 'volatility_20d'],
            'volume': ['volume_ratio_5d', 'volume_ratio_10d', 'volume_ratio_20d'],
            'trend': ['trend_strength_20d', 'trend_strength_60d'],
        }

        return category_map.get(category, [])

    def _get_tech_indicators_by_category(self, category: str) -> List[str]:
        """
        根据类别获取技术指标

        Args:
            category: 指标类别 (ma, ema, rsi, macd, bb, atr, cci)

        Returns:
            指标名称列表
        """
        category_map = {
            'ma': ['ma_5', 'ma_10', 'ma_20', 'ma_60'],
            'ema': ['ema_12', 'ema_26'],
            'rsi': ['rsi_6', 'rsi_12', 'rsi_24'],
            'macd': ['macd', 'macd_signal', 'macd_hist'],
            'bb': ['bb_upper', 'bb_middle', 'bb_lower'],
            'atr': ['atr_14', 'atr_28'],
            'cci': ['cci_14', 'cci_28'],
        }

        return category_map.get(category, [])
