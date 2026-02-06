"""
MomentumSelector 单元测试
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.three_layer.selectors import MomentumSelector


class TestMomentumSelectorBasic:
    """测试 MomentumSelector 基本功能"""

    def test_id_and_name(self):
        """测试选股器ID和名称"""
        selector = MomentumSelector()
        assert selector.id == "momentum"
        assert selector.name == "动量选股器"

    def test_get_parameters(self):
        """测试参数定义"""
        params = MomentumSelector.get_parameters()
        assert len(params) == 4

        param_names = [p.name for p in params]
        assert "lookback_period" in param_names
        assert "top_n" in param_names
        assert "use_log_return" in param_names
        assert "filter_negative" in param_names

    def test_default_parameters(self):
        """测试默认参数"""
        selector = MomentumSelector()
        params = selector.get_parameters()

        defaults = {p.name: p.default for p in params}
        assert defaults["lookback_period"] == 20
        assert defaults["top_n"] == 50
        assert defaults["use_log_return"] is False
        assert defaults["filter_negative"] is True


class TestMomentumSelectorSelection:
    """测试 MomentumSelector 选股逻辑"""

    def setup_method(self):
        """设置测试数据"""
        # 创建测试价格数据（30天）
        dates = pd.date_range(start="2023-01-01", periods=30, freq="D")

        # 股票A：持续上涨（涨幅20%）
        stock_a = np.linspace(100, 120, 30)

        # 股票B：适度上涨（涨幅10%）
        stock_b = np.linspace(100, 110, 30)

        # 股票C：下跌（跌幅10%）
        stock_c = np.linspace(100, 90, 30)

        # 股票D：震荡（基本不涨）
        stock_d = 100 + np.sin(np.linspace(0, 2 * np.pi, 30)) * 2

        # 股票E：大幅上涨（涨幅30%）
        stock_e = np.linspace(100, 130, 30)

        self.prices = pd.DataFrame(
            {
                "A": stock_a,
                "B": stock_b,
                "C": stock_c,
                "D": stock_d,
                "E": stock_e,
            },
            index=dates,
        )

        self.test_date = dates[-1]

    def test_basic_selection(self):
        """测试基本选股功能"""
        selector = MomentumSelector(params={"lookback_period": 20, "top_n": 5})

        selected = selector.select(self.test_date, self.prices)

        # 应该选出5只股票（或更少，取决于可用股票数量）
        assert len(selected) <= 5

        # 涨幅最大的E应该被选中
        assert "E" in selected

        # 涨幅第二的A应该被选中
        assert "A" in selected

        # 涨幅第三的B应该被选中
        assert "B" in selected

    def test_filter_negative_momentum(self):
        """测试过滤负动量功能"""
        selector = MomentumSelector(
            params={"lookback_period": 20, "top_n": 10, "filter_negative": True}
        )

        selected = selector.select(self.test_date, self.prices)

        # 下跌的股票C不应该被选中
        assert "C" not in selected

        # 上涨的股票应该被选中
        assert "E" in selected
        assert "A" in selected

    def test_no_filter_negative(self):
        """测试不过滤负动量"""
        selector = MomentumSelector(
            params={"lookback_period": 20, "top_n": 5, "filter_negative": False}
        )

        selected = selector.select(self.test_date, self.prices)

        # 应该选出所有5只股票（不过滤下跌股票）
        assert len(selected) == 5

    def test_log_return(self):
        """测试对数收益率模式"""
        selector_simple = MomentumSelector(
            params={"lookback_period": 20, "top_n": 5, "use_log_return": False}
        )
        selector_log = MomentumSelector(
            params={"lookback_period": 20, "top_n": 5, "use_log_return": True}
        )

        selected_simple = selector_simple.select(self.test_date, self.prices)
        selected_log = selector_log.select(self.test_date, self.prices)

        # 对于涨跌幅度较小的情况，两种方法结果应该相似
        # 但不一定完全相同
        assert len(selected_simple) == len(selected_log)
        assert "E" in selected_simple
        assert "E" in selected_log

    def test_top_n_limit(self):
        """测试选股数量限制"""
        # 要求选10只，但只有5只股票
        selector = MomentumSelector(params={"lookback_period": 20, "top_n": 10})

        selected = selector.select(self.test_date, self.prices)

        # 最多只能选出5只（总共只有5只股票）
        assert len(selected) <= 5

    def test_short_lookback_period(self):
        """测试短回溯期"""
        selector = MomentumSelector(params={"lookback_period": 5, "top_n": 5})

        selected = selector.select(self.test_date, self.prices)

        # 应该能正常选出股票
        assert len(selected) > 0
        assert "E" in selected  # 最强势股票应该被选中


class TestMomentumSelectorEdgeCases:
    """测试 MomentumSelector 边界情况"""

    def test_invalid_date(self):
        """测试无效日期"""
        prices = pd.DataFrame(
            {"A": [100, 105, 110], "B": [100, 102, 104]},
            index=pd.date_range("2023-01-01", periods=3, freq="D"),
        )

        selector = MomentumSelector(params={"lookback_period": 5, "top_n": 5})

        # 日期不在数据范围内
        invalid_date = pd.Timestamp("2024-01-01")
        selected = selector.select(invalid_date, prices)

        assert len(selected) == 0

    def test_insufficient_data(self):
        """测试数据不足"""
        # 只有10天数据，但回溯期要20天
        prices = pd.DataFrame(
            {"A": range(100, 110), "B": range(100, 110)},
            index=pd.date_range("2023-01-01", periods=10, freq="D"),
        )

        selector = MomentumSelector(params={"lookback_period": 20, "top_n": 5})

        test_date = prices.index[-1]
        selected = selector.select(test_date, prices)

        # 由于数据不足，可能返回空列表或部分结果
        # 具体取决于实现细节
        assert isinstance(selected, list)

    def test_all_negative_momentum_with_filter(self):
        """测试所有股票都下跌且开启过滤"""
        # 所有股票都下跌
        dates = pd.date_range("2023-01-01", periods=25, freq="D")
        prices = pd.DataFrame(
            {"A": np.linspace(100, 90, 25), "B": np.linspace(100, 85, 25)}, index=dates
        )

        selector = MomentumSelector(
            params={"lookback_period": 20, "top_n": 5, "filter_negative": True}
        )

        selected = selector.select(dates[-1], prices)

        # 所有股票都是负动量，过滤后应该返回空列表
        assert len(selected) == 0

    def test_nan_values_in_prices(self):
        """测试价格数据中包含NaN值"""
        dates = pd.date_range("2023-01-01", periods=25, freq="D")
        prices = pd.DataFrame(
            {
                "A": [100 + i for i in range(25)],
                "B": [100 + i * 0.5 for i in range(25)],
            },
            index=dates,
        )

        # 在某些位置插入NaN
        prices.loc[dates[10], "A"] = np.nan
        prices.loc[dates[15], "B"] = np.nan

        selector = MomentumSelector(params={"lookback_period": 20, "top_n": 5})

        selected = selector.select(dates[-1], prices)

        # 应该能处理NaN值，返回有效结果
        assert isinstance(selected, list)


class TestMomentumSelectorParameterValidation:
    """测试 MomentumSelector 参数验证"""

    def test_invalid_lookback_period_negative(self):
        """测试无效的回溯期（负数）"""
        with pytest.raises(ValueError, match="不能小于"):
            MomentumSelector(params={"lookback_period": -1})

    def test_invalid_lookback_period_too_large(self):
        """测试无效的回溯期（超过最大值）"""
        with pytest.raises(ValueError, match="不能大于"):
            MomentumSelector(params={"lookback_period": 300})

    def test_invalid_top_n_negative(self):
        """测试无效的选股数量（负数）"""
        with pytest.raises(ValueError, match="不能小于"):
            MomentumSelector(params={"top_n": -1})

    def test_invalid_top_n_zero(self):
        """测试无效的选股数量（零）"""
        with pytest.raises(ValueError, match="不能小于"):
            MomentumSelector(params={"top_n": 0})

    def test_invalid_parameter_type(self):
        """测试无效的参数类型"""
        with pytest.raises(ValueError, match="必须是整数"):
            MomentumSelector(params={"lookback_period": "20"})

    def test_unknown_parameter(self):
        """测试未知参数"""
        with pytest.raises(ValueError, match="未知参数"):
            MomentumSelector(params={"unknown_param": 123})

    def test_valid_edge_values(self):
        """测试边界有效值"""
        # 最小值
        selector1 = MomentumSelector(
            params={"lookback_period": 5, "top_n": 5}
        )
        assert selector1.params["lookback_period"] == 5
        assert selector1.params["top_n"] == 5

        # 最大值
        selector2 = MomentumSelector(
            params={"lookback_period": 200, "top_n": 200}
        )
        assert selector2.params["lookback_period"] == 200
        assert selector2.params["top_n"] == 200


class TestMomentumSelectorIntegration:
    """测试 MomentumSelector 集成场景"""

    def test_realistic_market_data(self):
        """测试真实市场数据场景"""
        # 模拟1年的市场数据
        dates = pd.date_range("2023-01-01", periods=252, freq="D")
        np.random.seed(42)

        # 生成10只股票的价格数据
        stocks = {}
        for i in range(10):
            # 随机游走模拟股价
            returns = np.random.normal(0.001, 0.02, 252)
            prices = 100 * np.exp(np.cumsum(returns))
            stocks[f"STOCK_{i}"] = prices

        prices_df = pd.DataFrame(stocks, index=dates)

        # 使用不同参数测试
        selector1 = MomentumSelector(params={"lookback_period": 20, "top_n": 5})
        selector2 = MomentumSelector(params={"lookback_period": 60, "top_n": 5})

        test_date = dates[-1]
        selected1 = selector1.select(test_date, prices_df)
        selected2 = selector2.select(test_date, prices_df)

        # 两个选股器应该都能返回结果
        assert len(selected1) > 0
        assert len(selected2) > 0

        # 不同回溯期可能选出不同的股票
        # 但也可能有重叠
        assert isinstance(selected1, list)
        assert isinstance(selected2, list)

    def test_multiple_calls_consistency(self):
        """测试多次调用的一致性"""
        dates = pd.date_range("2023-01-01", periods=30, freq="D")
        prices = pd.DataFrame(
            {
                "A": np.linspace(100, 120, 30),
                "B": np.linspace(100, 110, 30),
                "C": np.linspace(100, 90, 30),
            },
            index=dates,
        )

        selector = MomentumSelector(params={"lookback_period": 20, "top_n": 5})

        # 多次调用同一日期
        test_date = dates[-1]
        selected1 = selector.select(test_date, prices)
        selected2 = selector.select(test_date, prices)
        selected3 = selector.select(test_date, prices)

        # 结果应该完全一致
        assert selected1 == selected2
        assert selected2 == selected3
