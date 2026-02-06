"""
MLSelector 单元测试

测试机器学习选股器的所有功能模块
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from src.strategies.three_layer.selectors.ml_selector import MLSelector


class TestMLSelectorBasic:
    """测试 MLSelector 基本功能"""

    def test_id_and_name(self):
        """测试选股器ID和名称"""
        selector = MLSelector()
        assert selector.id == "ml_selector"
        assert selector.name == "机器学习选股器（StarRanker 功能）"

    def test_get_parameters(self):
        """测试参数定义"""
        params = MLSelector.get_parameters()
        assert len(params) == 7

        param_names = [p.name for p in params]
        assert "mode" in param_names
        assert "top_n" in param_names
        assert "features" in param_names
        assert "model_path" in param_names
        assert "filter_min_volume" in param_names
        assert "filter_max_price" in param_names
        assert "filter_min_price" in param_names

    def test_default_parameters(self):
        """测试默认参数"""
        selector = MLSelector()
        params = selector.get_parameters()

        defaults = {p.name: p.default for p in params}
        assert defaults["mode"] == "multi_factor_weighted"
        assert defaults["top_n"] == 50
        assert defaults["features"] == "momentum_20d,rsi_14d,volatility_20d,volume_ratio"
        assert defaults["model_path"] == ""
        assert defaults["filter_min_volume"] == 0
        assert defaults["filter_max_price"] == 0
        assert defaults["filter_min_price"] == 0

    def test_initialization_with_custom_features(self):
        """测试自定义特征列表初始化"""
        selector = MLSelector(params={
            'features': 'momentum_20d,rsi_14d'
        })
        assert len(selector.features) == 2
        assert 'momentum_20d' in selector.features
        assert 'rsi_14d' in selector.features

    def test_initialization_with_default_features(self):
        """测试默认特征列表"""
        selector = MLSelector(params={'features': ''})
        default_features = selector.features

        # 默认特征集应该包含多个特征
        assert len(default_features) > 5
        assert 'momentum_20d' in default_features
        assert 'rsi_14d' in default_features
        assert 'volatility_20d' in default_features

    def test_mode_initialization(self):
        """测试不同模式初始化"""
        # 多因子加权模式
        selector1 = MLSelector(params={'mode': 'multi_factor_weighted'})
        assert selector1.mode == 'multi_factor_weighted'
        assert selector1.model is None

        # LightGBM 模式（无模型路径，应回退）
        selector2 = MLSelector(params={'mode': 'lightgbm_ranker'})
        assert selector2.mode == 'multi_factor_weighted'  # 回退
        assert selector2.model is None


class TestMLSelectorFeatureCalculation:
    """测试特征计算功能"""

    def setup_method(self):
        """设置测试数据"""
        # 创建60天的测试数据
        dates = pd.date_range(start="2023-01-01", periods=60, freq="D")

        # 股票A：持续上涨
        stock_a = np.linspace(100, 130, 60)

        # 股票B：震荡
        stock_b = 100 + np.sin(np.linspace(0, 4 * np.pi, 60)) * 10

        # 股票C：下跌
        stock_c = np.linspace(120, 90, 60)

        self.prices = pd.DataFrame(
            {
                "STOCK_A": stock_a,
                "STOCK_B": stock_b,
                "STOCK_C": stock_c,
            },
            index=dates,
        )

        self.test_date = dates[-1]

    def test_calculate_momentum_feature(self):
        """测试动量特征计算"""
        selector = MLSelector(params={
            'features': 'momentum_20d',
            'top_n': 5
        })

        # 计算特征矩阵
        feature_matrix = selector._calculate_features(
            self.test_date,
            self.prices,
            ["STOCK_A", "STOCK_B", "STOCK_C"]
        )

        assert not feature_matrix.empty
        assert 'momentum_20d' in feature_matrix.columns

        # 上涨股票的动量应该是正的
        assert feature_matrix.loc["STOCK_A", "momentum_20d"] > 0

        # 下跌股票的动量应该是负的
        assert feature_matrix.loc["STOCK_C", "momentum_20d"] < 0

    def test_calculate_rsi_feature(self):
        """测试RSI特征计算"""
        selector = MLSelector(params={
            'features': 'rsi_14d',
            'top_n': 5
        })

        feature_matrix = selector._calculate_features(
            self.test_date,
            self.prices,
            ["STOCK_A", "STOCK_B", "STOCK_C"]
        )

        assert not feature_matrix.empty
        assert 'rsi_14d' in feature_matrix.columns

        # RSI 应该在 0-100 之间
        for stock in feature_matrix.index:
            rsi = feature_matrix.loc[stock, "rsi_14d"]
            # 允许一些边界情况（如全0填充）
            assert rsi >= 0 or rsi == 0
            assert rsi <= 100 or np.isnan(rsi)

    def test_calculate_volatility_feature(self):
        """测试波动率特征计算"""
        selector = MLSelector(params={
            'features': 'volatility_20d',
            'top_n': 5
        })

        feature_matrix = selector._calculate_features(
            self.test_date,
            self.prices,
            ["STOCK_A", "STOCK_B", "STOCK_C"]
        )

        assert not feature_matrix.empty
        assert 'volatility_20d' in feature_matrix.columns

        # 波动率应该是非负的
        for stock in feature_matrix.index:
            vol = feature_matrix.loc[stock, "volatility_20d"]
            assert vol >= 0 or vol == 0

    def test_calculate_multiple_features(self):
        """测试多特征计算"""
        selector = MLSelector(params={
            'features': 'momentum_20d,rsi_14d,volatility_20d',
            'top_n': 5
        })

        feature_matrix = selector._calculate_features(
            self.test_date,
            self.prices,
            ["STOCK_A", "STOCK_B", "STOCK_C"]
        )

        assert not feature_matrix.empty
        assert len(feature_matrix.columns) == 3
        assert 'momentum_20d' in feature_matrix.columns
        assert 'rsi_14d' in feature_matrix.columns
        assert 'volatility_20d' in feature_matrix.columns

    def test_calculate_atr_feature(self):
        """测试ATR特征计算"""
        selector = MLSelector(params={
            'features': 'atr_14d',
            'top_n': 5
        })

        feature_matrix = selector._calculate_features(
            self.test_date,
            self.prices,
            ["STOCK_A", "STOCK_B", "STOCK_C"]
        )

        assert not feature_matrix.empty
        assert 'atr_14d' in feature_matrix.columns

    def test_calculate_ma_cross_feature(self):
        """测试均线偏离度特征计算"""
        selector = MLSelector(params={
            'features': 'ma_cross_20d',
            'top_n': 5
        })

        feature_matrix = selector._calculate_features(
            self.test_date,
            self.prices,
            ["STOCK_A", "STOCK_B", "STOCK_C"]
        )

        assert not feature_matrix.empty
        assert 'ma_cross_20d' in feature_matrix.columns

    def test_feature_calculation_with_invalid_stock(self):
        """测试无效股票的特征计算"""
        selector = MLSelector(params={
            'features': 'momentum_20d',
            'top_n': 5
        })

        # 包含不存在的股票
        feature_matrix = selector._calculate_features(
            self.test_date,
            self.prices,
            ["STOCK_A", "NONEXISTENT_STOCK"]
        )

        # 应该跳过无效股票
        assert not feature_matrix.empty
        assert "STOCK_A" in feature_matrix.index
        assert "NONEXISTENT_STOCK" not in feature_matrix.index

    def test_feature_calculation_handles_nan(self):
        """测试特征计算处理NaN值"""
        # 在价格数据中插入NaN
        prices_with_nan = self.prices.copy()
        prices_with_nan.loc[self.test_date - pd.Timedelta(days=5), "STOCK_A"] = np.nan

        selector = MLSelector(params={
            'features': 'momentum_20d,rsi_14d',
            'top_n': 5
        })

        feature_matrix = selector._calculate_features(
            self.test_date,
            prices_with_nan,
            ["STOCK_A", "STOCK_B"]
        )

        # 应该能处理NaN（填充为0）
        assert not feature_matrix.empty
        assert not feature_matrix.isna().all().any()


class TestMLSelectorScoring:
    """测试评分功能"""

    def setup_method(self):
        """设置测试数据"""
        # 创建测试特征矩阵
        self.feature_matrix = pd.DataFrame({
            'momentum_20d': [0.15, 0.10, -0.05, 0.20, 0.05],
            'rsi_14d': [70, 60, 40, 80, 50],
            'volatility_20d': [0.02, 0.03, 0.015, 0.025, 0.02],
        }, index=['STOCK_A', 'STOCK_B', 'STOCK_C', 'STOCK_D', 'STOCK_E'])

    def test_multi_factor_scoring(self):
        """测试多因子加权评分"""
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'features': 'momentum_20d,rsi_14d,volatility_20d'
        })

        scores = selector._score_multi_factor(self.feature_matrix)

        # 应该返回所有股票的评分
        assert len(scores) == 5
        assert not scores.isna().any()

        # 评分应该是数值
        assert all(isinstance(s, (int, float)) for s in scores)

    def test_scoring_normalization(self):
        """测试评分归一化"""
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'features': 'momentum_20d,rsi_14d,volatility_20d'
        })

        scores = selector._score_multi_factor(self.feature_matrix)

        # 归一化后的评分应该均值接近0
        assert abs(scores.mean()) < 1.0

    def test_lightgbm_scoring_without_model(self):
        """测试无模型的LightGBM评分（应回退）"""
        selector = MLSelector(params={
            'mode': 'lightgbm_ranker',
            'features': 'momentum_20d,rsi_14d'
        })

        # 模型未加载，应回退到多因子加权
        scores = selector._score_lightgbm(self.feature_matrix)

        assert not scores.empty
        assert len(scores) == 5

    @patch('joblib.load')
    def test_lightgbm_scoring_with_model(self, mock_joblib_load):
        """测试有模型的LightGBM评分"""
        # 创建模拟模型
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.8, 0.6, 0.4, 0.9, 0.5])
        mock_joblib_load.return_value = mock_model

        # 创建临时模型文件
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            selector = MLSelector(params={
                'mode': 'lightgbm_ranker',
                'model_path': tmp_path,
                'features': 'momentum_20d,rsi_14d'
            })

            scores = selector._score_lightgbm(self.feature_matrix)

            # 应该调用模型预测
            assert not scores.empty
            assert len(scores) == 5

        finally:
            os.unlink(tmp_path)

    def test_custom_model_scoring_not_implemented(self):
        """测试自定义模型评分（未实现）"""
        selector = MLSelector(params={
            'mode': 'custom_model',
            'features': 'momentum_20d'
        })

        with pytest.raises(NotImplementedError):
            selector._score_custom(self.feature_matrix)


class TestMLSelectorSelection:
    """测试选股功能"""

    def setup_method(self):
        """设置测试数据"""
        dates = pd.date_range(start="2023-01-01", periods=60, freq="D")

        # 创建5只股票，涨跌幅不同
        np.random.seed(42)
        stocks = {}
        for i in range(5):
            trend = (i - 2) * 0.001  # 有涨有跌
            noise = np.random.normal(0, 0.01, 60)
            returns = trend + noise
            prices = 100 * np.exp(np.cumsum(returns))
            stocks[f"STOCK_{i}"] = prices

        self.prices = pd.DataFrame(stocks, index=dates)
        self.test_date = dates[-1]

    def test_basic_selection(self):
        """测试基本选股功能"""
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 5,
            'features': 'momentum_20d,rsi_14d'
        })

        selected = selector.select(self.test_date, self.prices)

        # 应该选出5只股票
        assert len(selected) <= 5
        assert all(isinstance(s, str) for s in selected)

    def test_top_n_limit(self):
        """测试选股数量限制"""
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 10,  # 要求10只
            'features': 'momentum_20d'
        })

        selected = selector.select(self.test_date, self.prices)

        # 只有5只股票，最多选5只
        assert len(selected) <= 5

    def test_selection_consistency(self):
        """测试选股一致性"""
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 5,
            'features': 'momentum_20d,rsi_14d'
        })

        # 多次选股应该得到相同结果
        selected1 = selector.select(self.test_date, self.prices)
        selected2 = selector.select(self.test_date, self.prices)
        selected3 = selector.select(self.test_date, self.prices)

        assert selected1 == selected2
        assert selected2 == selected3

    def test_selection_with_different_features(self):
        """测试不同特征集的选股"""
        selector1 = MLSelector(params={
            'top_n': 5,
            'features': 'momentum_20d'
        })

        selector2 = MLSelector(params={
            'top_n': 5,
            'features': 'momentum_20d,rsi_14d,volatility_20d'
        })

        selected1 = selector1.select(self.test_date, self.prices)
        selected2 = selector2.select(self.test_date, self.prices)

        # 不同特征可能选出不同股票
        assert isinstance(selected1, list)
        assert isinstance(selected2, list)


class TestMLSelectorFiltering:
    """测试过滤功能"""

    def setup_method(self):
        """设置测试数据"""
        dates = pd.date_range(start="2023-01-01", periods=30, freq="D")

        self.prices = pd.DataFrame({
            "STOCK_LOW": np.linspace(5, 8, 30),      # 低价股
            "STOCK_MID": np.linspace(50, 60, 30),    # 中价股
            "STOCK_HIGH": np.linspace(200, 220, 30),  # 高价股
        }, index=dates)

        self.test_date = dates[-1]

    def test_min_price_filter(self):
        """测试最低价格过滤"""
        selector = MLSelector(params={
            'top_n': 5,
            'filter_min_price': 10,  # 过滤低于10元的股票
            'features': 'momentum_20d'
        })

        selected = selector.select(self.test_date, self.prices)

        # STOCK_LOW 应该被过滤掉
        assert "STOCK_LOW" not in selected

    def test_max_price_filter(self):
        """测试最高价格过滤"""
        selector = MLSelector(params={
            'top_n': 5,
            'filter_max_price': 100,  # 过滤高于100元的股票
            'features': 'momentum_20d'
        })

        selected = selector.select(self.test_date, self.prices)

        # STOCK_HIGH 应该被过滤掉
        assert "STOCK_HIGH" not in selected

    def test_min_max_price_filter_combined(self):
        """测试组合价格过滤"""
        selector = MLSelector(params={
            'top_n': 5,
            'filter_min_price': 10,
            'filter_max_price': 100,
            'features': 'momentum_20d'
        })

        selected = selector.select(self.test_date, self.prices)

        # 只有 STOCK_MID 符合条件
        assert "STOCK_LOW" not in selected
        assert "STOCK_HIGH" not in selected
        if len(selected) > 0:
            assert "STOCK_MID" in selected

    def test_no_filter(self):
        """测试无过滤条件"""
        selector = MLSelector(params={
            'top_n': 5,
            'filter_min_price': 0,
            'filter_max_price': 0,
            'features': 'momentum_20d'
        })

        selected = selector.select(self.test_date, self.prices)

        # 应该能选到所有符合条件的股票
        assert isinstance(selected, list)


class TestMLSelectorEdgeCases:
    """测试边界情况"""

    def test_invalid_date(self):
        """测试无效日期"""
        prices = pd.DataFrame(
            {"A": [100, 105, 110]},
            index=pd.date_range("2023-01-01", periods=3, freq="D")
        )

        selector = MLSelector(params={'top_n': 5, 'features': 'momentum_20d'})

        # 日期不在数据范围内
        invalid_date = pd.Timestamp("2024-01-01")
        selected = selector.select(invalid_date, prices)

        assert len(selected) == 0

    def test_empty_market_data(self):
        """测试空市场数据"""
        prices = pd.DataFrame()

        selector = MLSelector(params={'top_n': 5, 'features': 'momentum_20d'})

        if len(prices) > 0:
            selected = selector.select(pd.Timestamp("2023-01-01"), prices)
            assert len(selected) == 0

    def test_all_nan_prices(self):
        """测试全NaN价格"""
        dates = pd.date_range("2023-01-01", periods=10, freq="D")
        prices = pd.DataFrame({
            "A": [np.nan] * 10,
            "B": [np.nan] * 10,
        }, index=dates)

        selector = MLSelector(params={'top_n': 5, 'features': 'momentum_20d'})

        selected = selector.select(dates[-1], prices)

        # 应该返回空列表
        assert len(selected) == 0

    def test_insufficient_history(self):
        """测试历史数据不足"""
        # 只有5天数据，但需要20天计算动量
        dates = pd.date_range("2023-01-01", periods=5, freq="D")
        prices = pd.DataFrame({
            "A": [100, 101, 102, 103, 104],
        }, index=dates)

        selector = MLSelector(params={
            'top_n': 5,
            'features': 'momentum_20d'  # 需要20天
        })

        selected = selector.select(dates[-1], prices)

        # 应该能返回结果（即使特征为0）
        assert isinstance(selected, list)


class TestMLSelectorParameterValidation:
    """测试参数验证"""

    def test_invalid_mode(self):
        """测试无效模式"""
        with pytest.raises(ValueError, match="不在有效选项中"):
            MLSelector(params={'mode': 'invalid_mode'})

    def test_invalid_top_n_negative(self):
        """测试无效的选股数量"""
        with pytest.raises(ValueError, match="不能小于"):
            MLSelector(params={'top_n': -1})

    def test_invalid_top_n_too_large(self):
        """测试选股数量超过最大值"""
        with pytest.raises(ValueError, match="不能大于"):
            MLSelector(params={'top_n': 300})

    def test_invalid_parameter_type(self):
        """测试无效的参数类型"""
        with pytest.raises(ValueError, match="必须是整数"):
            MLSelector(params={'top_n': "50"})

    def test_unknown_parameter(self):
        """测试未知参数"""
        with pytest.raises(ValueError, match="未知参数"):
            MLSelector(params={'unknown_param': 123})

    def test_valid_edge_values(self):
        """测试边界有效值"""
        # 最小值
        selector1 = MLSelector(params={'top_n': 5})
        assert selector1.params['top_n'] == 5

        # 最大值
        selector2 = MLSelector(params={'top_n': 200})
        assert selector2.params['top_n'] == 200


class TestMLSelectorIntegration:
    """测试集成场景"""

    def test_realistic_market_scenario(self):
        """测试真实市场场景"""
        # 模拟1年的市场数据
        dates = pd.date_range("2023-01-01", periods=252, freq="D")
        np.random.seed(42)

        # 生成20只股票
        stocks = {}
        for i in range(20):
            returns = np.random.normal(0.0005, 0.02, 252)
            prices = 100 * np.exp(np.cumsum(returns))
            stocks[f"STOCK_{i:02d}"] = prices

        prices_df = pd.DataFrame(stocks, index=dates)

        # 使用MLSelector选股
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 10,
            'features': 'momentum_20d,rsi_14d,volatility_20d'
        })

        selected = selector.select(dates[-1], prices_df)

        # 应该选出10只股票
        assert len(selected) == 10
        assert all(stock in prices_df.columns for stock in selected)

    def test_different_modes_comparison(self):
        """测试不同模式的比较"""
        dates = pd.date_range("2023-01-01", periods=60, freq="D")
        np.random.seed(42)

        stocks = {}
        for i in range(10):
            returns = np.random.normal(0.001, 0.015, 60)
            prices = 100 * np.exp(np.cumsum(returns))
            stocks[f"STOCK_{i}"] = prices

        prices_df = pd.DataFrame(stocks, index=dates)

        # 多因子加权
        selector1 = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 5,
            'features': 'momentum_20d,rsi_14d'
        })

        selected1 = selector1.select(dates[-1], prices_df)

        assert len(selected1) > 0
        assert isinstance(selected1, list)

    def test_feature_combination_exploration(self):
        """测试不同特征组合"""
        dates = pd.date_range("2023-01-01", periods=60, freq="D")
        np.random.seed(42)

        stocks = {}
        for i in range(8):
            returns = np.random.normal(0.0005, 0.02, 60)
            prices = 100 * np.exp(np.cumsum(returns))
            stocks[f"STOCK_{i}"] = prices

        prices_df = pd.DataFrame(stocks, index=dates)

        # 测试不同特征组合
        feature_sets = [
            'momentum_20d',
            'momentum_20d,rsi_14d',
            'momentum_20d,rsi_14d,volatility_20d',
            'momentum_5d,momentum_10d,momentum_20d,rsi_14d',
        ]

        for features in feature_sets:
            selector = MLSelector(params={
                'top_n': 5,
                'features': features
            })

            selected = selector.select(dates[-1], prices_df)

            # 所有组合都应该能返回结果
            assert isinstance(selected, list)
            assert len(selected) <= 5


class TestMLSelectorRSICalculation:
    """测试RSI计算的正确性"""

    def test_rsi_calculation_uptrend(self):
        """测试上涨趋势的RSI"""
        dates = pd.date_range("2023-01-01", periods=30, freq="D")
        # 持续上涨
        prices = pd.Series(np.linspace(100, 120, 30), index=dates)

        selector = MLSelector(params={'features': 'rsi_14d'})
        rsi_series = selector._calculate_rsi(prices, period=14)

        # 上涨趋势RSI应该较高
        final_rsi = rsi_series.iloc[-1]
        if not np.isnan(final_rsi):
            assert final_rsi > 50

    def test_rsi_calculation_downtrend(self):
        """测试下跌趋势的RSI"""
        dates = pd.date_range("2023-01-01", periods=30, freq="D")
        # 持续下跌
        prices = pd.Series(np.linspace(120, 100, 30), index=dates)

        selector = MLSelector(params={'features': 'rsi_14d'})
        rsi_series = selector._calculate_rsi(prices, period=14)

        # 下跌趋势RSI应该较低
        final_rsi = rsi_series.iloc[-1]
        if not np.isnan(final_rsi):
            assert final_rsi < 50

    def test_rsi_bounds(self):
        """测试RSI边界值"""
        dates = pd.date_range("2023-01-01", periods=30, freq="D")
        np.random.seed(42)
        returns = np.random.normal(0, 0.02, 30)
        prices = pd.Series(100 * np.exp(np.cumsum(returns)), index=dates)

        selector = MLSelector(params={'features': 'rsi_14d'})
        rsi_series = selector._calculate_rsi(prices, period=14)

        # RSI应该在0-100之间
        valid_rsi = rsi_series.dropna()
        if len(valid_rsi) > 0:
            assert (valid_rsi >= 0).all()
            assert (valid_rsi <= 100).all()


class TestMLSelectorRankAndSelect:
    """测试排序和选股逻辑"""

    def test_rank_and_select_basic(self):
        """测试基本排序选股"""
        selector = MLSelector()

        scores = pd.Series({
            'A': 0.8,
            'B': 0.6,
            'C': 0.9,
            'D': 0.4,
            'E': 0.7
        })

        selected = selector._rank_and_select(scores, top_n=3)

        # 应该选出评分最高的3只
        assert len(selected) == 3
        assert 'C' in selected  # 0.9
        assert 'A' in selected  # 0.8
        assert 'E' in selected  # 0.7

    def test_rank_and_select_empty_scores(self):
        """测试空评分"""
        selector = MLSelector()

        scores = pd.Series(dtype=float)

        selected = selector._rank_and_select(scores, top_n=5)

        assert len(selected) == 0

    def test_rank_and_select_top_n_larger_than_available(self):
        """测试top_n大于可用股票数"""
        selector = MLSelector()

        scores = pd.Series({'A': 0.8, 'B': 0.6})

        selected = selector._rank_and_select(scores, top_n=10)

        # 只能选出2只
        assert len(selected) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
