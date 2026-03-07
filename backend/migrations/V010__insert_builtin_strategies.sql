-- ============================================================
-- V009: 插入系统内置策略（完全数据库驱动）
-- 创建时间: 2026-03-07
-- 说明: 将所有入场策略和离场策略从本地文件迁移到数据库
-- ============================================================

-- 1. 清理旧的占位符数据（如果存在）
DELETE FROM strategies
WHERE source_type = 'builtin'
AND code LIKE '%pass%'
AND (code_hash = encode(sha256('%pass%'::bytea), 'hex') OR LENGTH(code) < 200);

-- ============================================================
-- 2. 插入入场策略（3个）
-- ============================================================

-- 动量入场策略
INSERT INTO strategies (
    user_id, name, display_name, class_name, code, code_hash,
    source_type, strategy_type, description, category, tags,
    default_params, validation_status, risk_level, is_enabled, created_by, version
) VALUES (
    NULL,
    'momentum_entry',
    '动量入场策略',
    'MomentumStrategy',
    'from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base_strategy import BaseStrategy
from src.strategies.signal_generator import SignalGenerator


class MomentumStrategy(BaseStrategy):
    """
    动量策略

    核心逻辑：
    - 计算过去N日的收益率作为动量指标
    - 每期选择动量最高的top_n只股票买入
    - 持有holding_period天后卖出

    参数：
        lookback_period: 动量计算回看期（默认20天）
        top_n: 每期选择前N只股票（默认50只）
        holding_period: 持仓期（默认5天）
        use_log_return: 是否使用对数收益率（默认False）
        filter_negative: 是否过滤负动量股票（默认True）

    适用场景：
        - 趋势性行情
        - 市场整体上涨
        - 中短期交易

    风险提示：
        - 震荡市场可能频繁止损
        - 追高风险
        - 转势时可能出现较大回撤
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化动量策略

        Args:
            name: 策略名称
            config: 策略配置
        """
        # 设置默认参数
        default_config = {
            ''lookback_period'': 20,
            ''top_n'': 50,
            ''holding_period'': 5,
            ''use_log_return'': False,
            ''filter_negative'': True,
        }
        default_config.update(config)

        super().__init__(name, default_config)

        # 提取策略特有参数
        self.lookback_period = self.config.custom_params.get(''lookback_period'', 20)
        self.use_log_return = self.config.custom_params.get(''use_log_return'', False)
        self.filter_negative = self.config.custom_params.get(''filter_negative'', True)

        logger.info(f"动量策略参数: 回看期={self.lookback_period}, "
                   f"选股数={self.config.top_n}, "
                   f"持仓期={self.config.holding_period}")

    def calculate_momentum(
        self,
        prices: pd.DataFrame,
        lookback: Optional[int] = None
    ) -> pd.DataFrame:
        """
        计算动量指标

        Args:
            prices: 价格DataFrame
            lookback: 回看期（None则使用默认）

        Returns:
            momentum: 动量DataFrame
        """
        if lookback is None:
            lookback = self.lookback_period

        if self.use_log_return:
            # 对数收益率（适合长期）
            momentum = np.log(prices / prices.shift(lookback)) * 100
        else:
            # 简单收益率（适合短期）
            momentum = prices.pct_change(lookback) * 100

        return momentum

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """
        计算股票评分（实现基类抽象方法）

        评分 = 动量值（过去N日收益率）

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame（本策略不使用）
            date: 指定日期

        Returns:
            scores: 股票评分Series
        """
        # 计算动量
        momentum = self.calculate_momentum(prices)

        # 获取指定日期的评分
        if date is None:
            date = momentum.index[-1]

        scores = momentum.loc[date]

        # 过滤负动量（可选）
        if self.filter_negative:
            scores[scores < 0] = np.nan

        return scores

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        生成交易信号（实现基类抽象方法）

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame（可选）
            volumes: 成交量DataFrame（可选）
            **kwargs: 其他参数

        Returns:
            signals: 信号DataFrame
        """
        logger.info(f"\n生成动量策略信号...")

        # 1. 计算动量
        momentum = self.calculate_momentum(prices)

        # 2. 过滤负动量（如果开启）
        if self.filter_negative:
            momentum[momentum < 0] = np.nan

        # 3. 使用信号生成器生成排名信号（返回Response对象）
        signals_response = SignalGenerator.generate_rank_signals(
            scores=momentum,
            top_n=self.config.top_n
        )

        # 检查信号生成结果并提取数据
        if not signals_response.is_success():
            raise ValueError(f"信号生成失败: {signals_response.error}")
        signals = signals_response.data

        # 4. 过滤股票（价格、成交量等）
        if volumes is not None:
            for date in signals.index:
                try:
                    valid_stocks = self.filter_stocks(prices, volumes, date)
                    # 将不符合条件的股票信号设为0
                    invalid_stocks = [s for s in signals.columns if s not in valid_stocks]
                    signals.loc[date, invalid_stocks] = 0
                except:
                    pass

        # 5. 验证信号
        signals = self.validate_signals(signals)

        logger.info(f"信号生成完成，总买入信号数: {(signals == 1).sum().sum()}")

        return signals

    def get_top_stocks(
        self,
        prices: pd.DataFrame,
        date: pd.Timestamp,
        n: Optional[int] = None
    ) -> pd.Series:
        """
        获取指定日期的top N股票

        Args:
            prices: 价格DataFrame
            date: 指定日期
            n: 选择前N只（None则使用默认）

        Returns:
            top_stocks: 股票代码和动量值的Series
        """
        if n is None:
            n = self.config.top_n

        scores = self.calculate_scores(prices, date=date)
        top_stocks = scores.nlargest(n)

        return top_stocks

',
    '469816481464d78b',
    'builtin',
    'entry',
    '基于价格动量选股：买入近期强势股，持有一段时间后卖出',
    'momentum',
    ARRAY['动量', '趋势', '入场'],
    '{"lookback_period": 20, "top_n": 50, "holding_period": 5, "use_log_return": false, "filter_negative": true}'::jsonb,
    'passed',
    'medium',
    TRUE,
    'system',
    1
) ON CONFLICT (user_id, name) DO UPDATE SET
    code = EXCLUDED.code,
    code_hash = EXCLUDED.code_hash,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    default_params = EXCLUDED.default_params,
    updated_at = NOW();


-- 均值回归入场策略
INSERT INTO strategies (
    user_id, name, display_name, class_name, code, code_hash,
    source_type, strategy_type, description, category, tags,
    default_params, validation_status, risk_level, is_enabled, created_by, version
) VALUES (
    NULL,
    'mean_reversion_entry',
    '均值回归入场策略',
    'MeanReversionStrategy',
    'from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base_strategy import BaseStrategy
from src.strategies.signal_generator import SignalGenerator


class MeanReversionStrategy(BaseStrategy):
    """
    均值回归策略

    核心逻辑：
    - 计算股价相对于移动平均线的偏离度（Z-score）
    - 选择偏离度最大（超跌）的股票买入
    - 等待价格回归均线后卖出

    参数：
        lookback_period: 均线计算周期（默认20天）
        z_score_threshold: Z-score阈值（默认-2.0，即低于均线2个标准差）
        top_n: 每期选择前N只股票
        holding_period: 持仓期

    适用场景：
        - 震荡市场
        - 个股短期超买超卖
        - 均值回归明显的股票

    风险提示：
        - 趋势市场可能持续下跌
        - 价值陷阱（基本面恶化导致的下跌）
        - 需要设置严格止损
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化均值回归策略

        Args:
            name: 策略名称
            config: 策略配置
        """
        default_config = {
            ''lookback_period'': 20,
            ''z_score_threshold'': -2.0,
            ''top_n'': 30,
            ''holding_period'': 5,
            ''use_bollinger'': False,  # 是否使用布林带
            ''bollinger_window'': 20,
            ''bollinger_std'': 2.0,
        }
        default_config.update(config)

        super().__init__(name, default_config)

        self.lookback_period = self.config.custom_params.get(''lookback_period'', 20)
        self.z_score_threshold = self.config.custom_params.get(''z_score_threshold'', -2.0)
        self.use_bollinger = self.config.custom_params.get(''use_bollinger'', False)
        self.bollinger_window = self.config.custom_params.get(''bollinger_window'', 20)
        self.bollinger_std = self.config.custom_params.get(''bollinger_std'', 2.0)

        logger.info(f"均值回归策略参数: 回看期={self.lookback_period}, "
                   f"Z-score阈值={self.z_score_threshold}")

    def calculate_z_score(
        self,
        prices: pd.DataFrame,
        lookback: Optional[int] = None
    ) -> pd.DataFrame:
        """
        计算Z-score（标准化偏离度）

        Z-score = (当前价 - 移动平均) / 标准差

        Args:
            prices: 价格DataFrame
            lookback: 回看期

        Returns:
            z_scores: Z-score DataFrame
        """
        if lookback is None:
            lookback = self.lookback_period

        # 计算移动平均
        ma = prices.rolling(window=lookback).mean()

        # 计算标准差
        std = prices.rolling(window=lookback).std()

        # 计算Z-score
        z_scores = (prices - ma) / (std + 1e-8)  # 加小值防止除零

        return z_scores

    def calculate_bollinger_position(
        self,
        prices: pd.DataFrame
    ) -> pd.DataFrame:
        """
        计算价格在布林带中的位置

        Position = (当前价 - 下轨) / (上轨 - 下轨)
        - 接近0：触及下轨（超卖）
        - 接近1：触及上轨（超买）

        Args:
            prices: 价格DataFrame

        Returns:
            positions: 位置DataFrame（0-1之间）
        """
        # 中轨（移动平均）
        ma = prices.rolling(window=self.bollinger_window).mean()

        # 标准差
        std = prices.rolling(window=self.bollinger_window).std()

        # 上下轨
        upper = ma + self.bollinger_std * std
        lower = ma - self.bollinger_std * std

        # 计算位置
        positions = (prices - lower) / (upper - lower + 1e-8)

        return positions

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """
        计算股票评分

        评分 = -Z-score（Z-score越低，超跌越严重，评分越高）
        或
        评分 = 1 - Bollinger Position（越接近下轨，评分越高）

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame
            date: 指定日期

        Returns:
            scores: 股票评分Series
        """
        if self.use_bollinger:
            # 使用布林带
            positions = self.calculate_bollinger_position(prices)
            # 反转：越接近下轨（0）评分越高
            raw_scores = 1 - positions
        else:
            # 使用Z-score
            z_scores = self.calculate_z_score(prices)
            # 反转：Z-score越低（越超跌）评分越高
            raw_scores = -z_scores

        if date is None:
            date = raw_scores.index[-1]

        scores = raw_scores.loc[date]

        # 只保留超卖的股票（Z-score < threshold 或 Position < 0.2）
        if self.use_bollinger:
            scores[scores < 0.8] = np.nan  # Position > 0.2 的过滤掉
        else:
            # 原始Z-score，只保留低于阈值的
            original_z = -scores
            scores[original_z > self.z_score_threshold] = np.nan

        return scores

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        生成交易信号

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame
            volumes: 成交量DataFrame
            **kwargs: 其他参数

        Returns:
            signals: 信号DataFrame
        """
        logger.info(f"\n生成均值回归策略信号...")

        # 1. 计算评分
        if self.use_bollinger:
            positions = self.calculate_bollinger_position(prices)
            scores = 1 - positions
        else:
            z_scores = self.calculate_z_score(prices)
            scores = -z_scores

        # 2. 使用信号生成器生成排名信号（返回Response对象）
        signals_response = SignalGenerator.generate_rank_signals(
            scores=scores,
            top_n=self.config.top_n
        )

        # 检查信号生成结果并提取数据
        if not signals_response.is_success():
            raise ValueError(f"信号生成失败: {signals_response.error}")
        signals = signals_response.data

        # 3. 过滤
        if volumes is not None:
            for date in signals.index:
                try:
                    valid_stocks = self.filter_stocks(prices, volumes, date)
                    invalid_stocks = [s for s in signals.columns if s not in valid_stocks]
                    signals.loc[date, invalid_stocks] = 0
                except:
                    pass

        # 4. 验证
        signals = self.validate_signals(signals)

        logger.info(f"信号生成完成，总买入信号数: {(signals == 1).sum().sum()}")

        return signals

',
    '40564b35d5cfe4e4',
    'builtin',
    'entry',
    '基于均值回归效应：买入短期超跌股票，等待反弹后卖出',
    'mean_reversion',
    ARRAY['均值回归', '反转', '入场'],
    '{"lookback_period": 20, "z_score_threshold": -2.0, "top_n": 30, "holding_period": 5, "use_bollinger": false}'::jsonb,
    'passed',
    'medium',
    TRUE,
    'system',
    1
) ON CONFLICT (user_id, name) DO UPDATE SET
    code = EXCLUDED.code,
    code_hash = EXCLUDED.code_hash,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    default_params = EXCLUDED.default_params,
    updated_at = NOW();


-- 多因子入场策略
INSERT INTO strategies (
    user_id, name, display_name, class_name, code, code_hash,
    source_type, strategy_type, description, category, tags,
    default_params, validation_status, risk_level, is_enabled, created_by, version
) VALUES (
    NULL,
    'multi_factor_entry',
    '多因子入场策略',
    'MultiFactorStrategy',
    'from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base_strategy import BaseStrategy
from src.strategies.signal_generator import SignalGenerator


class MultiFactorStrategy(BaseStrategy):
    """
    多因子策略

    核心逻辑：
    - 选择多个有效的Alpha因子
    - 对因子进行标准化处理
    - 加权组合得到综合评分
    - 选择评分最高的股票

    参数：
        factors: 因子列表 [''MOM20'', ''REV5'', ''VOLATILITY20'']
        weights: 因子权重 [0.4, 0.3, 0.3]
        normalize_method: 标准化方法 (''rank''/''zscore''/''minmax'')
        neutralize: 是否行业中性化（默认False）

    适用场景：
        - 所有市场环境
        - 分散单因子风险
        - 提高稳定性

    优势：
        - 因子分散，风险降低
        - 可以capture多种市场特征
        - 可调整因子权重适应不同市场
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化多因子策略

        Args:
            name: 策略名称
            config: 策略配置
        """
        default_config = {
            ''factors'': [''MOM20'', ''REV5'', ''VOLATILITY20''],
            ''weights'': None,  # None表示等权重
            ''normalize_method'': ''rank'',
            ''top_n'': 50,
            ''holding_period'': 5,
            ''neutralize'': False,
            ''min_factor_coverage'': 0.8,  # 最少需要80%因子有效
        }
        default_config.update(config)

        super().__init__(name, default_config)

        self.factors = self.config.custom_params.get(''factors'', [])
        self.weights = self.config.custom_params.get(''weights'')
        self.normalize_method = self.config.custom_params.get(''normalize_method'', ''rank'')
        self.neutralize = self.config.custom_params.get(''neutralize'', False)
        self.min_factor_coverage = self.config.custom_params.get(''min_factor_coverage'', 0.8)

        # 如果没有指定权重，使用等权重
        if self.weights is None:
            self.weights = [1.0 / len(self.factors)] * len(self.factors)

        if len(self.weights) != len(self.factors):
            raise ValueError("因子权重数量必须与因子数量一致")

        logger.info(f"多因子策略: {len(self.factors)}个因子")
        for factor, weight in zip(self.factors, self.weights):
            logger.info(f"  {factor}: {weight:.2%}")

    def normalize_factor(
        self,
        factor: pd.Series,
        method: Optional[str] = None
    ) -> pd.Series:
        """
        标准化因子

        Args:
            factor: 因子Series
            method: 标准化方法

        Returns:
            normalized: 标准化后的因子
        """
        if method is None:
            method = self.normalize_method

        if method == ''rank'':
            # 排名百分位（0-1）
            normalized = factor.rank(pct=True)

        elif method == ''zscore'':
            # Z-score标准化
            mean = factor.mean()
            std = factor.std()
            normalized = (factor - mean) / (std + 1e-8)

        elif method == ''minmax'':
            # Min-Max归一化（0-1）
            min_val = factor.min()
            max_val = factor.max()
            normalized = (factor - min_val) / (max_val - min_val + 1e-8)

        else:
            raise ValueError(f"不支持的标准化方法: {method}")

        return normalized

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """
        计算综合评分

        评分 = Σ(权重i × 标准化因子i)

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame（必需）
            date: 指定日期

        Returns:
            scores: 综合评分Series
        """
        if features is None:
            raise ValueError("多因子策略需要特征DataFrame")

        if date is None:
            date = features.index[-1]

        # 检查日期是否存在
        if date not in features.index:
            logger.warning(f"日期 {date} 不在特征DataFrame中")
            return pd.Series(dtype=float)

        # 提取各因子值
        factor_values = {}
        for factor in self.factors:
            # 支持MultiIndex列 (factor, stock)
            if isinstance(features.columns, pd.MultiIndex):
                # MultiIndex: 选择该因子的所有股票
                if factor in features.columns.get_level_values(0):
                    factor_values[factor] = features.loc[date, factor]
                else:
                    logger.warning(f"因子 {factor} 不在特征DataFrame中")
                    continue
            else:
                # 简单列索引
                if factor not in features.columns:
                    logger.warning(f"因子 {factor} 不在特征DataFrame中")
                    continue
                factor_values[factor] = features.loc[date, factor]

        if not factor_values:
            logger.error("没有可用的因子")
            return pd.Series(dtype=float)

        # 标准化
        normalized_factors = {}
        for factor_name, factor_series in factor_values.items():
            try:
                normalized = self.normalize_factor(factor_series.dropna())
                normalized_factors[factor_name] = normalized
            except Exception as e:
                logger.warning(f"标准化因子 {factor_name} 失败: {e}")
                continue

        if not normalized_factors:
            logger.error("没有成功标准化的因子")
            return pd.Series(dtype=float)

        # 加权组合
        # 确定股票列表（从第一个有效因子中获取）
        if normalized_factors:
            first_factor = list(normalized_factors.values())[0]
            stock_index = first_factor.index
        else:
            # 从features中提取股票列表
            if isinstance(features.columns, pd.MultiIndex):
                stock_index = features.columns.get_level_values(1).unique()
            else:
                stock_index = features.columns

        composite_score = pd.Series(0.0, index=stock_index)
        total_weight = 0.0

        for i, factor_name in enumerate(self.factors):
            if factor_name in normalized_factors:
                weight = self.weights[i]
                composite_score += normalized_factors[factor_name] * weight
                total_weight += weight

        # 归一化权重
        if total_weight > 0:
            composite_score = composite_score / total_weight

        # 过滤缺失值过多的股票
        factor_count = pd.DataFrame(normalized_factors).notna().sum(axis=1)
        min_factors = int(len(self.factors) * self.min_factor_coverage)
        valid_stocks = factor_count[factor_count >= min_factors].index
        composite_score[~composite_score.index.isin(valid_stocks)] = np.nan

        return composite_score

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        生成交易信号

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame（必需）
            volumes: 成交量DataFrame
            **kwargs: 其他参数

        Returns:
            signals: 信号DataFrame
        """
        logger.info(f"\n生成多因子策略信号...")

        if features is None:
            raise ValueError("多因子策略需要特征DataFrame")

        # 1. 计算每日综合评分
        scores_dict = {}
        for date in features.index:
            try:
                scores = self.calculate_scores(prices, features, date)
                scores_dict[date] = scores
            except Exception as e:
                logger.warning(f"计算日期 {date} 评分失败: {e}")
                continue

        if not scores_dict:
            logger.error("没有成功计算的评分")
            return pd.DataFrame(0, index=prices.index, columns=prices.columns)

        # 转换为DataFrame
        scores_df = pd.DataFrame(scores_dict).T

        # 2. 生成排名信号（返回Response对象）
        signals_response = SignalGenerator.generate_rank_signals(
            scores=scores_df,
            top_n=self.config.top_n
        )

        # 检查信号生成结果并提取数据
        if not signals_response.is_success():
            raise ValueError(f"信号生成失败: {signals_response.error}")
        signals = signals_response.data

        # 3. 对齐到价格DataFrame的索引
        signals = signals.reindex(prices.index, fill_value=0)

        # 4. 过滤
        if volumes is not None:
            for date in signals.index:
                try:
                    valid_stocks = self.filter_stocks(prices, volumes, date)
                    invalid_stocks = [s for s in signals.columns if s not in valid_stocks]
                    signals.loc[date, invalid_stocks] = 0
                except:
                    pass

        # 5. 验证
        signals = self.validate_signals(signals)

        logger.info(f"信号生成完成，总买入信号数: {(signals == 1).sum().sum()}")

        return signals

    def get_factor_weights(self) -> Dict[str, float]:
        """
        获取因子权重

        Returns:
            {factor_name: weight} 字典
        """
        return dict(zip(self.factors, self.weights))

    def update_weights(self, new_weights: List[float]):
        """
        更新因子权重

        Args:
            new_weights: 新权重列表
        """
        if len(new_weights) != len(self.factors):
            raise ValueError("权重数量必须与因子数量一致")

        self.weights = new_weights
        logger.info(f"更新因子权重:")
        for factor, weight in zip(self.factors, self.weights):
            logger.info(f"  {factor}: {weight:.2%}")

',
    'efbd49364b9bfbbb',
    'builtin',
    'entry',
    '结合多个Alpha因子进行选股，提高稳定性',
    'multi_factor',
    ARRAY['多因子', 'Alpha', '入场'],
    '{"factors": ["MOM20", "REV5", "VOLATILITY20"], "weights": null, "normalize_method": "rank", "top_n": 50, "holding_period": 5}'::jsonb,
    'passed',
    'low',
    TRUE,
    'system',
    1
) ON CONFLICT (user_id, name) DO UPDATE SET
    code = EXCLUDED.code,
    code_hash = EXCLUDED.code_hash,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    default_params = EXCLUDED.default_params,
    updated_at = NOW();

-- ============================================================
-- 3. 插入离场策���（5个）
-- ============================================================

-- 止损离场策略
INSERT INTO strategies (
    user_id, name, display_name, class_name, code, code_hash,
    source_type, strategy_type, description, category, tags,
    default_params, validation_status, risk_level, is_enabled, created_by, version
) VALUES (
    NULL,
    'stop_loss_exit',
    '止损离场策略',
    'StopLossExitStrategy',
    'from typing import Optional, Dict
from datetime import datetime
import pandas as pd
import numpy as np
from loguru import logger
from src.ml.exit_strategy import BaseExitStrategy, ExitSignal



@dataclass
class ExitSignal:
    """
    离场信号数据类

    属性:
        stock_code: 股票代码
        reason: 离场原因 (''strategy'', ''reverse_entry'', ''risk_control'')
        trigger: 具体触发条件 (如 ''stop_loss'', ''take_profit'', ''holding_period'')
        priority: 优先级 (1-10, 数字越大优先级越高)
        metadata: 附加元数据
    """
    stock_code: str
    reason: str  # ''strategy'', ''reverse_entry'', ''risk_control''
    trigger: str
    priority: int = 5
    metadata: Optional[Dict] = None

    def __repr__(self) -> str:
        return (
            f"ExitSignal({self.stock_code}, "
            f"reason={self.reason}, trigger={self.trigger}, "
            f"priority={self.priority})"
        )


class BaseExitStrategy(ABC):
    """
    离场策略基类

    所有离场策略必须继承此类并实现 should_exit() 方法
    """

    def __init__(self, name: str, priority: int = 5):
        """
        初始化离场策略

        Args:
            name: 策略名称
            priority: 优先级 (1-10)
        """
        self.name = name
        self.priority = priority

    @abstractmethod
    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """
        判断是否应该离场

        Args:
            position: 持仓信息
                {
                    ''stock_code'': str,
                    ''shares'': int,
                    ''entry_price'': float,
                    ''entry_date'': datetime,
                    ''current_price'': float,
                    ''unrealized_pnl_pct'': float
                }
            current_price: 当前价格
            current_date: 当前日期
            market_data: 市场数据（可选）

        Returns:
            ExitSignal if should exit, None otherwise
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name=''{self.name}'', priority={self.priority})"


class StopLossExitStrategy(BaseExitStrategy):
    """
    止损离场策略

    当亏损超过阈值时触发离场
    """

    def __init__(self, stop_loss_pct: float = 0.10, priority: int = 10):
        """
        初始化

        Args:
            stop_loss_pct: 止损比例 (默认10%)
            priority: 优先级 (止损优先级最高，默认10)
        """
        super().__init__(name=''StopLoss'', priority=priority)
        self.stop_loss_pct = stop_loss_pct

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """止损检查"""
        pnl_pct = position.get(''unrealized_pnl_pct'', 0.0)

        if pnl_pct < -self.stop_loss_pct:
            return ExitSignal(
                stock_code=position[''stock_code''],
                reason=''risk_control'',
                trigger=''stop_loss'',
                priority=self.priority,
                metadata={
                    ''stop_loss_pct'': self.stop_loss_pct,
                    ''actual_loss_pct'': pnl_pct,
                    ''entry_price'': position[''entry_price''],
                    ''current_price'': current_price
                }
            )

        return None

',
    '5fab15c690e06046',
    'builtin',
    'exit',
    '当亏损超过指定比例时触发离场，用于风险控制',
    'stop_loss',
    ARRAY['风控', '止损', '离场'],
    '{"stop_loss_pct": 0.1, "priority": 10}'::jsonb,
    'passed',
    'safe',
    TRUE,
    'system',
    1
) ON CONFLICT (user_id, name) DO UPDATE SET
    code = EXCLUDED.code,
    code_hash = EXCLUDED.code_hash,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    default_params = EXCLUDED.default_params,
    updated_at = NOW();


-- 止盈离场策略
INSERT INTO strategies (
    user_id, name, display_name, class_name, code, code_hash,
    source_type, strategy_type, description, category, tags,
    default_params, validation_status, risk_level, is_enabled, created_by, version
) VALUES (
    NULL,
    'take_profit_exit',
    '止盈离场策略',
    'TakeProfitExitStrategy',
    'from typing import Optional, Dict
from datetime import datetime
import pandas as pd
import numpy as np
from loguru import logger
from src.ml.exit_strategy import BaseExitStrategy, ExitSignal



@dataclass
class ExitSignal:
    """
    离场信号数据类

    属性:
        stock_code: 股票代码
        reason: 离场原因 (''strategy'', ''reverse_entry'', ''risk_control'')
        trigger: 具体触发条件 (如 ''stop_loss'', ''take_profit'', ''holding_period'')
        priority: 优先级 (1-10, 数字越大优先级越高)
        metadata: 附加元数据
    """
    stock_code: str
    reason: str  # ''strategy'', ''reverse_entry'', ''risk_control''
    trigger: str
    priority: int = 5
    metadata: Optional[Dict] = None

    def __repr__(self) -> str:
        return (
            f"ExitSignal({self.stock_code}, "
            f"reason={self.reason}, trigger={self.trigger}, "
            f"priority={self.priority})"
        )


class BaseExitStrategy(ABC):
    """
    离场策略基类

    所有离场策略必须继承此类并实现 should_exit() 方法
    """

    def __init__(self, name: str, priority: int = 5):
        """
        初始化离场策略

        Args:
            name: 策略名称
            priority: 优先级 (1-10)
        """
        self.name = name
        self.priority = priority

    @abstractmethod
    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """
        判断是否应该离场

        Args:
            position: 持仓信息
                {
                    ''stock_code'': str,
                    ''shares'': int,
                    ''entry_price'': float,
                    ''entry_date'': datetime,
                    ''current_price'': float,
                    ''unrealized_pnl_pct'': float
                }
            current_price: 当前价格
            current_date: 当前日期
            market_data: 市场数据（可选）

        Returns:
            ExitSignal if should exit, None otherwise
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name=''{self.name}'', priority={self.priority})"


class StopLossExitStrategy(BaseExitStrategy):
    """
    止损离场策略

    当亏损超过阈值时触发离场
    """

    def __init__(self, stop_loss_pct: float = 0.10, priority: int = 10):
        """
        初始化

        Args:
            stop_loss_pct: 止损比例 (默认10%)
            priority: 优先级 (止损优先级最高，默认10)
        """
        super().__init__(name=''StopLoss'', priority=priority)
        self.stop_loss_pct = stop_loss_pct

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """止损检查"""
        pnl_pct = position.get(''unrealized_pnl_pct'', 0.0)

        if pnl_pct < -self.stop_loss_pct:
            return ExitSignal(
                stock_code=position[''stock_code''],
                reason=''risk_control'',
                trigger=''stop_loss'',
                priority=self.priority,
                metadata={
                    ''stop_loss_pct'': self.stop_loss_pct,
                    ''actual_loss_pct'': pnl_pct,
                    ''entry_price'': position[''entry_price''],
                    ''current_price'': current_price
                }
            )

        return None


class TakeProfitExitStrategy(BaseExitStrategy):
    """
    止盈离场策略

    当盈利达到目标时触发离场
    """

    def __init__(self, take_profit_pct: float = 0.20, priority: int = 8):
        """
        初始化

        Args:
            take_profit_pct: 止盈比例 (默认20%)
            priority: 优先级
        """
        super().__init__(name=''TakeProfit'', priority=priority)
        self.take_profit_pct = take_profit_pct

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """止盈检查"""
        pnl_pct = position.get(''unrealized_pnl_pct'', 0.0)

        if pnl_pct > self.take_profit_pct:
            return ExitSignal(
                stock_code=position[''stock_code''],
                reason=''strategy'',
                trigger=''take_profit'',
                priority=self.priority,
                metadata={
                    ''take_profit_pct'': self.take_profit_pct,
                    ''actual_profit_pct'': pnl_pct,
                    ''entry_price'': position[''entry_price''],
                    ''current_price'': current_price
                }
            )

        return None

',
    '68167766d68979d5',
    'builtin',
    'exit',
    '当盈利达到目标时触发离场，锁定利润',
    'take_profit',
    ARRAY['止盈', '离场'],
    '{"take_profit_pct": 0.2, "priority": 8}'::jsonb,
    'passed',
    'safe',
    TRUE,
    'system',
    1
) ON CONFLICT (user_id, name) DO UPDATE SET
    code = EXCLUDED.code,
    code_hash = EXCLUDED.code_hash,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    default_params = EXCLUDED.default_params,
    updated_at = NOW();


-- 持仓时长离场策略
INSERT INTO strategies (
    user_id, name, display_name, class_name, code, code_hash,
    source_type, strategy_type, description, category, tags,
    default_params, validation_status, risk_level, is_enabled, created_by, version
) VALUES (
    NULL,
    'holding_period_exit',
    '持仓时长离场策略',
    'HoldingPeriodExitStrategy',
    'from typing import Optional, Dict
from datetime import datetime
import pandas as pd
import numpy as np
from loguru import logger
from src.ml.exit_strategy import BaseExitStrategy, ExitSignal



@dataclass
class ExitSignal:
    """
    离场信号数据类

    属性:
        stock_code: 股票代码
        reason: 离场原因 (''strategy'', ''reverse_entry'', ''risk_control'')
        trigger: 具体触发条件 (如 ''stop_loss'', ''take_profit'', ''holding_period'')
        priority: 优先级 (1-10, 数字越大优先级越高)
        metadata: 附加元数据
    """
    stock_code: str
    reason: str  # ''strategy'', ''reverse_entry'', ''risk_control''
    trigger: str
    priority: int = 5
    metadata: Optional[Dict] = None

    def __repr__(self) -> str:
        return (
            f"ExitSignal({self.stock_code}, "
            f"reason={self.reason}, trigger={self.trigger}, "
            f"priority={self.priority})"
        )


class BaseExitStrategy(ABC):
    """
    离场策略基类

    所有离场策略必须继承此类并实现 should_exit() 方法
    """

    def __init__(self, name: str, priority: int = 5):
        """
        初始化离场策略

        Args:
            name: 策略名称
            priority: 优先级 (1-10)
        """
        self.name = name
        self.priority = priority

    @abstractmethod
    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """
        判断是否应该离场

        Args:
            position: 持仓信息
                {
                    ''stock_code'': str,
                    ''shares'': int,
                    ''entry_price'': float,
                    ''entry_date'': datetime,
                    ''current_price'': float,
                    ''unrealized_pnl_pct'': float
                }
            current_price: 当前价格
            current_date: 当前日期
            market_data: 市场数据（可选）

        Returns:
            ExitSignal if should exit, None otherwise
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name=''{self.name}'', priority={self.priority})"


class StopLossExitStrategy(BaseExitStrategy):
    """
    止损离场策略

    当亏损超过阈值时触发离场
    """

    def __init__(self, stop_loss_pct: float = 0.10, priority: int = 10):
        """
        初始化

        Args:
            stop_loss_pct: 止损比例 (默认10%)
            priority: 优先级 (止损优先级最高，默认10)
        """
        super().__init__(name=''StopLoss'', priority=priority)
        self.stop_loss_pct = stop_loss_pct

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """止损检查"""
        pnl_pct = position.get(''unrealized_pnl_pct'', 0.0)

        if pnl_pct < -self.stop_loss_pct:
            return ExitSignal(
                stock_code=position[''stock_code''],
                reason=''risk_control'',
                trigger=''stop_loss'',
                priority=self.priority,
                metadata={
                    ''stop_loss_pct'': self.stop_loss_pct,
                    ''actual_loss_pct'': pnl_pct,
                    ''entry_price'': position[''entry_price''],
                    ''current_price'': current_price
                }
            )

        return None


class TakeProfitExitStrategy(BaseExitStrategy):
    """
    止盈离场策略

    当盈利达到目标时触发离场
    """

    def __init__(self, take_profit_pct: float = 0.20, priority: int = 8):
        """
        初始化

        Args:
            take_profit_pct: 止盈比例 (默认20%)
            priority: 优先级
        """
        super().__init__(name=''TakeProfit'', priority=priority)
        self.take_profit_pct = take_profit_pct

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """止盈检查"""
        pnl_pct = position.get(''unrealized_pnl_pct'', 0.0)

        if pnl_pct > self.take_profit_pct:
            return ExitSignal(
                stock_code=position[''stock_code''],
                reason=''strategy'',
                trigger=''take_profit'',
                priority=self.priority,
                metadata={
                    ''take_profit_pct'': self.take_profit_pct,
                    ''actual_profit_pct'': pnl_pct,
                    ''entry_price'': position[''entry_price''],
                    ''current_price'': current_price
                }
            )

        return None


class HoldingPeriodExitStrategy(BaseExitStrategy):
    """
    持仓时长离场策略

    当持仓天数达到上限时触发离场
    """

    def __init__(self, max_holding_days: int = 30, priority: int = 3):
        """
        初始化

        Args:
            max_holding_days: 最大持仓天数
            priority: 优先级
        """
        super().__init__(name=''HoldingPeriod'', priority=priority)
        self.max_holding_days = max_holding_days

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """持仓时长检查"""
        entry_date = position.get(''entry_date'')

        if entry_date is None:
            return None

        # 计算持仓天数
        if isinstance(entry_date, str):
            entry_date = pd.to_datetime(entry_date)
        if isinstance(current_date, str):
            current_date = pd.to_datetime(current_date)

        holding_days = (current_date - entry_date).days

        if holding_days >= self.max_holding_days:
            return ExitSignal(
                stock_code=position[''stock_code''],
                reason=''strategy'',
                trigger=''max_holding_period'',
                priority=self.priority,
                metadata={
                    ''max_holding_days'': self.max_holding_days,
                    ''actual_holding_days'': holding_days,
                    ''entry_date'': entry_date,
                    ''current_date'': current_date
                }
            )

        return None

',
    'b3865f946f321098',
    'builtin',
    'exit',
    '当持仓天数达到上限时触发离场',
    'holding_period',
    ARRAY['持仓时长', '离场'],
    '{"max_holding_days": 30, "priority": 3}'::jsonb,
    'passed',
    'low',
    TRUE,
    'system',
    1
) ON CONFLICT (user_id, name) DO UPDATE SET
    code = EXCLUDED.code,
    code_hash = EXCLUDED.code_hash,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    default_params = EXCLUDED.default_params,
    updated_at = NOW();


-- 移动止损离场策略
INSERT INTO strategies (
    user_id, name, display_name, class_name, code, code_hash,
    source_type, strategy_type, description, category, tags,
    default_params, validation_status, risk_level, is_enabled, created_by, version
) VALUES (
    NULL,
    'trailing_stop_exit',
    '移动止损离场策略',
    'TrailingStopExitStrategy',
    'from typing import Optional, Dict
from datetime import datetime
import pandas as pd
import numpy as np
from loguru import logger
from src.ml.exit_strategy import BaseExitStrategy, ExitSignal



@dataclass
class ExitSignal:
    """
    离场信号数据类

    属性:
        stock_code: 股票代码
        reason: 离场原因 (''strategy'', ''reverse_entry'', ''risk_control'')
        trigger: 具体触发条件 (如 ''stop_loss'', ''take_profit'', ''holding_period'')
        priority: 优先级 (1-10, 数字越大优先级越高)
        metadata: 附加元数据
    """
    stock_code: str
    reason: str  # ''strategy'', ''reverse_entry'', ''risk_control''
    trigger: str
    priority: int = 5
    metadata: Optional[Dict] = None

    def __repr__(self) -> str:
        return (
            f"ExitSignal({self.stock_code}, "
            f"reason={self.reason}, trigger={self.trigger}, "
            f"priority={self.priority})"
        )


class BaseExitStrategy(ABC):
    """
    离场策略基类

    所有离场策略必须继承此类并实现 should_exit() 方法
    """

    def __init__(self, name: str, priority: int = 5):
        """
        初始化离场策略

        Args:
            name: 策略名称
            priority: 优先级 (1-10)
        """
        self.name = name
        self.priority = priority

    @abstractmethod
    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """
        判断是否应该离场

        Args:
            position: 持仓信息
                {
                    ''stock_code'': str,
                    ''shares'': int,
                    ''entry_price'': float,
                    ''entry_date'': datetime,
                    ''current_price'': float,
                    ''unrealized_pnl_pct'': float
                }
            current_price: 当前价格
            current_date: 当前日期
            market_data: 市场数据（可选）

        Returns:
            ExitSignal if should exit, None otherwise
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name=''{self.name}'', priority={self.priority})"


class StopLossExitStrategy(BaseExitStrategy):
    """
    止损离场策略

    当亏损超过阈值时触发离场
    """

    def __init__(self, stop_loss_pct: float = 0.10, priority: int = 10):
        """
        初始化

        Args:
            stop_loss_pct: 止损比例 (默认10%)
            priority: 优先级 (止损优先级最高，默认10)
        """
        super().__init__(name=''StopLoss'', priority=priority)
        self.stop_loss_pct = stop_loss_pct

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """止损检查"""
        pnl_pct = position.get(''unrealized_pnl_pct'', 0.0)

        if pnl_pct < -self.stop_loss_pct:
            return ExitSignal(
                stock_code=position[''stock_code''],
                reason=''risk_control'',
                trigger=''stop_loss'',
                priority=self.priority,
                metadata={
                    ''stop_loss_pct'': self.stop_loss_pct,
                    ''actual_loss_pct'': pnl_pct,
                    ''entry_price'': position[''entry_price''],
                    ''current_price'': current_price
                }
            )

        return None


class TakeProfitExitStrategy(BaseExitStrategy):
    """
    止盈离场策略

    当盈利达到目标时触发离场
    """

    def __init__(self, take_profit_pct: float = 0.20, priority: int = 8):
        """
        初始化

        Args:
            take_profit_pct: 止盈比例 (默认20%)
            priority: 优先级
        """
        super().__init__(name=''TakeProfit'', priority=priority)
        self.take_profit_pct = take_profit_pct

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """止盈检查"""
        pnl_pct = position.get(''unrealized_pnl_pct'', 0.0)

        if pnl_pct > self.take_profit_pct:
            return ExitSignal(
                stock_code=position[''stock_code''],
                reason=''strategy'',
                trigger=''take_profit'',
                priority=self.priority,
                metadata={
                    ''take_profit_pct'': self.take_profit_pct,
                    ''actual_profit_pct'': pnl_pct,
                    ''entry_price'': position[''entry_price''],
                    ''current_price'': current_price
                }
            )

        return None


class HoldingPeriodExitStrategy(BaseExitStrategy):
    """
    持仓时长离场策略

    当持仓天数达到上限时触发离场
    """

    def __init__(self, max_holding_days: int = 30, priority: int = 3):
        """
        初始化

        Args:
            max_holding_days: 最大持仓天数
            priority: 优先级
        """
        super().__init__(name=''HoldingPeriod'', priority=priority)
        self.max_holding_days = max_holding_days

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """持仓时长检查"""
        entry_date = position.get(''entry_date'')

        if entry_date is None:
            return None

        # 计算持仓天数
        if isinstance(entry_date, str):
            entry_date = pd.to_datetime(entry_date)
        if isinstance(current_date, str):
            current_date = pd.to_datetime(current_date)

        holding_days = (current_date - entry_date).days

        if holding_days >= self.max_holding_days:
            return ExitSignal(
                stock_code=position[''stock_code''],
                reason=''strategy'',
                trigger=''max_holding_period'',
                priority=self.priority,
                metadata={
                    ''max_holding_days'': self.max_holding_days,
                    ''actual_holding_days'': holding_days,
                    ''entry_date'': entry_date,
                    ''current_date'': current_date
                }
            )

        return None


class TrailingStopExitStrategy(BaseExitStrategy):
    """
    移动止损离场策略

    跟踪最高价，当回撤超过阈值时触发离场
    """

    def __init__(self, trailing_stop_pct: float = 0.05, priority: int = 9):
        """
        初始化

        Args:
            trailing_stop_pct: 移动止损比例 (从最高点回撤，默认5%)
            priority: 优先级
        """
        super().__init__(name=''TrailingStop'', priority=priority)
        self.trailing_stop_pct = trailing_stop_pct

        # 记录每只股票的最高价
        self.peak_prices: Dict[str, float] = {}

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """移动止损检查"""
        stock_code = position[''stock_code'']
        entry_price = position[''entry_price'']

        # 更新最高价
        if stock_code not in self.peak_prices:
            self.peak_prices[stock_code] = max(entry_price, current_price)
        else:
            self.peak_prices[stock_code] = max(self.peak_prices[stock_code], current_price)

        peak_price = self.peak_prices[stock_code]

        # 计算从最高点的回撤
        drawdown_from_peak = (current_price - peak_price) / peak_price

        if drawdown_from_peak < -self.trailing_stop_pct:
            return ExitSignal(
                stock_code=stock_code,
                reason=''risk_control'',
                trigger=''trailing_stop'',
                priority=self.priority,
                metadata={
                    ''trailing_stop_pct'': self.trailing_stop_pct,
                    ''drawdown_from_peak'': drawdown_from_peak,
                    ''peak_price'': peak_price,
                    ''current_price'': current_price,
                    ''entry_price'': entry_price
                }
            )

        return None

    def reset_stock(self, stock_code: str):
        """重置某只股票的记录（离场后调用）"""
        if stock_code in self.peak_prices:
            del self.peak_prices[stock_code]

',
    '7aa14300a87437f2',
    'builtin',
    'exit',
    '跟踪最高价，当回撤超过阈值时触发离场',
    'trailing_stop',
    ARRAY['移动止损', '风控', '离场'],
    '{"trailing_stop_pct": 0.05, "priority": 9}'::jsonb,
    'passed',
    'safe',
    TRUE,
    'system',
    1
) ON CONFLICT (user_id, name) DO UPDATE SET
    code = EXCLUDED.code,
    code_hash = EXCLUDED.code_hash,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    default_params = EXCLUDED.default_params,
    updated_at = NOW();


-- 自适应离场策略
INSERT INTO strategies (
    user_id, name, display_name, class_name, code, code_hash,
    source_type, strategy_type, description, category, tags,
    default_params, validation_status, risk_level, is_enabled, created_by, version
) VALUES (
    NULL,
    'adaptive_exit',
    '自适应离场策略',
    'AdaptiveExitStrategy',
    'from typing import Optional, Dict
from datetime import datetime
import pandas as pd
import numpy as np
from loguru import logger
from src.ml.exit_strategy import BaseExitStrategy, ExitSignal



class AdaptiveExitStrategy(BaseExitStrategy):
    """
    自适应离场策略

    根据以下因素动态调整离场条件:
    1. 市场波动性（ATR/价格波动）
    2. 持仓盈亏情况
    3. 持仓时长

    使用场景:
    - 希望在不同市场环境下采用不同风控策略
    - 需要根据盈利情况调整止盈目标
    - 想要避免在震荡市场中被频繁止损
    """

    def __init__(
        self,
        base_stop_loss: float = 0.08,
        base_take_profit: float = 0.15,
        volatility_window: int = 20,
        priority: int = 9
    ):
        """
        初始化

        Args:
            base_stop_loss: 基准止损比例 (默认 8%)
            base_take_profit: 基准止盈比例 (默认 15%)
            volatility_window: 波动性计算窗口 (默认 20天)
            priority: 优先级 (默认 9)
        """
        super().__init__(name=''AdaptiveExit'', priority=priority)

        self.base_stop_loss = base_stop_loss
        self.base_take_profit = base_take_profit
        self.volatility_window = volatility_window

        # 缓存波动性数据
        self.volatility_cache: Dict[str, float] = {}

        logger.info(
            f"初始化自适应离场策略: "
            f"止损={base_stop_loss:.1%}, 止盈={base_take_profit:.1%}, "
            f"波动窗口={volatility_window}天"
        )

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """
        判断是否应该离场

        逻辑:
        1. 计算市场波动性
        2. 根据波动性调整止损/止盈参数
        3. 根据持仓时长微调参数
        4. 检查是否触发离场条件
        """
        stock_code = position[''stock_code'']
        entry_price = position[''entry_price'']
        entry_date = position.get(''entry_date'')
        pnl_pct = position.get(''unrealized_pnl_pct'', 0.0)

        # 1. 计算波动性
        volatility = self._calculate_volatility(
            stock_code, current_price, market_data
        )

        # 2. 计算持仓天数
        holding_days = 0
        if entry_date:
            if isinstance(entry_date, str):
                entry_date = pd.to_datetime(entry_date)
            if isinstance(current_date, str):
                current_date = pd.to_datetime(current_date)
            holding_days = (current_date - entry_date).days

        # 3. 动态调整参数
        adjusted_params = self._adjust_parameters(
            volatility, holding_days, pnl_pct
        )

        stop_loss = adjusted_params[''stop_loss'']
        take_profit = adjusted_params[''take_profit'']

        # 4. 检查止损
        if pnl_pct < -stop_loss:
            return ExitSignal(
                stock_code=stock_code,
                reason=''risk_control'',
                trigger=''adaptive_stop_loss'',
                priority=self.priority,
                metadata={
                    ''base_stop_loss'': self.base_stop_loss,
                    ''adjusted_stop_loss'': stop_loss,
                    ''actual_loss'': pnl_pct,
                    ''volatility'': volatility,
                    ''holding_days'': holding_days,
                    ''adjustment_reason'': adjusted_params[''reason'']
                }
            )

        # 5. 检查止盈
        if pnl_pct > take_profit:
            return ExitSignal(
                stock_code=stock_code,
                reason=''strategy'',
                trigger=''adaptive_take_profit'',
                priority=self.priority,
                metadata={
                    ''base_take_profit'': self.base_take_profit,
                    ''adjusted_take_profit'': take_profit,
                    ''actual_profit'': pnl_pct,
                    ''volatility'': volatility,
                    ''holding_days'': holding_days,
                    ''adjustment_reason'': adjusted_params[''reason'']
                }
            )

        return None

    def _calculate_volatility(
        self,
        stock_code: str,
        current_price: float,
        market_data: Optional[pd.DataFrame] = None
    ) -> float:
        """
        计算市场波动性

        方法:
        - 如果有市场数据，使用ATR（Average True Range）
        - 否则使用简化的价格波动率估算

        Returns:
            波动性系数 (0-1之间，0.5为中性)
        """
        # 检查缓存
        if stock_code in self.volatility_cache:
            return self.volatility_cache[stock_code]

        if market_data is None:
            # 简化估算：默认中等波动
            volatility = 0.5
        else:
            try:
                # 筛选当前股票的数据
                stock_data = market_data[
                    market_data[''stock_code''] == stock_code
                ].copy()

                if len(stock_data) < self.volatility_window:
                    volatility = 0.5
                else:
                    # 计算最近N天的收益率标准差
                    stock_data = stock_data.sort_values(''date'').tail(
                        self.volatility_window
                    )
                    returns = stock_data[''close''].pct_change().dropna()

                    if len(returns) > 0:
                        # 年化波动率
                        vol = returns.std() * np.sqrt(252)

                        # 归一化到 0-1 (假设年化波动率 0-50%)
                        volatility = min(vol / 0.5, 1.0)
                    else:
                        volatility = 0.5

            except Exception as e:
                logger.warning(f"计算波动性失败 {stock_code}: {e}")
                volatility = 0.5

        # 缓存结果
        self.volatility_cache[stock_code] = volatility

        return volatility

    def _adjust_parameters(
        self,
        volatility: float,
        holding_days: int,
        current_pnl_pct: float
    ) -> Dict:
        """
        根据市场条件动态调整参数

        规则:
        1. 低波动市场（< 0.3）：更严格止损，更快止盈
        2. 中等波动（0.3-0.7）：使用基准参数
        3. 高波动市场（> 0.7）：更宽松止损，更高止盈目标
        4. 持仓超过15天：逐步收紧止盈，放宽止损
        5. 盈利超过5%：将止损调整为保本或小盈

        Returns:
            {
                ''stop_loss'': 调整后的止损比例,
                ''take_profit'': 调整后的止盈比例,
                ''reason'': 调整原因
            }
        """
        stop_loss = self.base_stop_loss
        take_profit = self.base_take_profit
        reasons = []

        # 1. 根据波动性调整
        if volatility < 0.3:
            # 低波动：严格止损 (-20%), 快速止盈 (-30%)
            stop_loss *= 0.8
            take_profit *= 0.7
            reasons.append(''低波动环境'')
        elif volatility > 0.7:
            # 高波动：宽松止损 (+50%), 高目标止盈 (+50%)
            stop_loss *= 1.5
            take_profit *= 1.5
            reasons.append(''高波动环境'')
        else:
            reasons.append(''中等波动环境'')

        # 2. 根据持仓时长调整
        if holding_days > 15:
            # 持仓超过15天：收紧止盈 (-10% per 5 days)
            days_over = holding_days - 15
            take_profit_reduction = min(days_over // 5 * 0.1, 0.4)
            take_profit *= (1 - take_profit_reduction)

            # 放宽止损 (+5% per 5 days)
            stop_loss_increase = min(days_over // 5 * 0.05, 0.2)
            stop_loss *= (1 + stop_loss_increase)

            reasons.append(f''持仓{holding_days}天'')

        # 3. 盈利保护
        if current_pnl_pct > 0.05:
            # 盈利超过5%：将止损调整为保本或小盈
            protected_stop_loss = min(
                stop_loss,
                current_pnl_pct * 0.3  # 保护30%的利润
            )

            if protected_stop_loss < stop_loss:
                stop_loss = protected_stop_loss
                reasons.append(f''盈利保护({current_pnl_pct:.1%})'')

        # 4. 安全边界
        stop_loss = max(0.02, min(stop_loss, 0.25))  # 2%-25%
        take_profit = max(0.05, min(take_profit, 0.50))  # 5%-50%

        return {
            ''stop_loss'': stop_loss,
            ''take_profit'': take_profit,
            ''reason'': '', ''.join(reasons)
        }

    def reset_stock(self, stock_code: str):
        """清理缓存"""
        if stock_code in self.volatility_cache:
            del self.volatility_cache[stock_code]

    def __repr__(self) -> str:
        return (
            f"AdaptiveExitStrategy("
            f"stop_loss={self.base_stop_loss:.1%}, "
            f"take_profit={self.base_take_profit:.1%}, "
            f"vol_window={self.volatility_window})"
        )

',
    'a2a8fa7f5355a617',
    'builtin',
    'exit',
    '根据市场波动性和持仓盈亏动态调整止盈止损参数',
    'adaptive',
    ARRAY['自适应', '动态调整', '离场'],
    '{"base_stop_loss": 0.08, "base_take_profit": 0.15, "volatility_window": 20, "priority": 9}'::jsonb,
    'passed',
    'medium',
    TRUE,
    'system',
    1
) ON CONFLICT (user_id, name) DO UPDATE SET
    code = EXCLUDED.code,
    code_hash = EXCLUDED.code_hash,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    default_params = EXCLUDED.default_params,
    updated_at = NOW();

-- ============================================================
-- 4. 验证插入结果
-- ============================================================

DO $$
DECLARE
    entry_count INT;
    exit_count INT;
    rec RECORD;
BEGIN
    SELECT COUNT(*) INTO entry_count FROM strategies WHERE strategy_type = 'entry' AND source_type = 'builtin';
    SELECT COUNT(*) INTO exit_count FROM strategies WHERE strategy_type = 'exit' AND source_type = 'builtin';

    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '✅ 系统内置策略迁移完成！';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE '入场策略数量: %', entry_count;
    RAISE NOTICE '离场策略数量: %', exit_count;
    RAISE NOTICE '总计: % 个策略', entry_count + exit_count;
    RAISE NOTICE '';
    RAISE NOTICE '策略列表:';

    FOR rec IN SELECT id, name, display_name, strategy_type FROM strategies WHERE source_type = 'builtin' ORDER BY strategy_type, id
    LOOP
        RAISE NOTICE '  [%] % - % (%)', rec.id, rec.strategy_type, rec.display_name, rec.name;
    END LOOP;

    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
END $$;

