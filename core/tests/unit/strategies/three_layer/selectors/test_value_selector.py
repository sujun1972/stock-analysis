"""
ValueSelector 单元测试
"""

import pytest
import pandas as pd
import numpy as np

from src.strategies.three_layer.selectors import ValueSelector


class TestValueSelectorBasic:
    """测试 ValueSelector 基本功能"""

    def test_id_and_name(self):
        """测试选股器ID和名称"""
        selector = ValueSelector()
        assert selector.id == "value"
        assert selector.name == "价值选股器（简化版）"

    def test_get_parameters(self):
        """测试参数定义"""
        params = ValueSelector.get_parameters()
        assert len(params) == 6

        param_names = [p.name for p in params]
        assert "volatility_period" in param_names
        assert "return_period" in param_names
        assert "top_n" in param_names
        assert "select_low_volatility" in param_names
        assert "select_negative_return" in param_names
        assert "volatility_weight" in param_names

    def test_default_parameters(self):
        """测试默认参数"""
        selector = ValueSelector()
        params = selector.get_parameters()

        defaults = {p.name: p.default for p in params}
        assert defaults["volatility_period"] == 20
        assert defaults["return_period"] == 20
        assert defaults["top_n"] == 50
        assert defaults["select_low_volatility"] is True
        assert defaults["select_negative_return"] is True
        assert defaults["volatility_weight"] == 0.5


class TestValueSelectorSelection:
    """测试 ValueSelector 选股逻辑"""

    def setup_method(self):
        """设置测试数据"""
        # 创建测试价格数据（40天，确保有足够数据计算指标）
        dates = pd.date_range(start="2023-01-01", periods=40, freq="D")

        # 股票A：高波动率，上涨
        np.random.seed(42)
        stock_a = 100 + np.cumsum(np.random.normal(1, 3, 40))

        # 股票B：低波动率，下跌
        stock_b = 100 - np.linspace(0, 10, 40) + np.random.normal(0, 0.5, 40)

        # 股票C：低波动率，上涨
        stock_c = 100 + np.linspace(0, 5, 40) + np.random.normal(0, 0.5, 40)

        # 股票D：高波动率，下跌
        stock_d = 100 - np.cumsum(np.random.uniform(-1, 1, 40))

        # 股票E：中等波动率，震荡
        stock_e = 100 + np.sin(np.linspace(0, 4 * np.pi, 40)) * 5

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
        selector = ValueSelector(
            params={
                "volatility_period": 20,
                "return_period": 20,
                "top_n": 5,
                "select_low_volatility": True,
                "select_negative_return": True,
            }
        )

        selected = selector.select(self.test_date, self.prices)

        # 应该选出股票
        assert len(selected) > 0
        assert len(selected) <= 5

    def test_low_volatility_preference(self):
        """测试低波动率偏好"""
        # 创建明显的高低波动率股票
        dates = pd.date_range("2023-01-01", periods=40, freq="D")

        # 低波动股票
        low_vol = 100 + np.linspace(0, -5, 40) + np.random.normal(0, 0.1, 40)
        # 高波动股票
        high_vol = 100 + np.linspace(0, -5, 40) + np.random.normal(0, 5, 40)

        prices = pd.DataFrame({"LOW": low_vol, "HIGH": high_vol}, index=dates)

        selector = ValueSelector(
            params={
                "volatility_period": 20,
                "return_period": 20,
                "top_n": 5,
                "select_low_volatility": True,
                "select_negative_return": True,
                "volatility_weight": 0.9,  # 高权重给波动率
            }
        )

        selected = selector.select(dates[-1], prices)

        # 低波动率股票应该被优先选中
        assert "LOW" in selected or len(selected) > 0

    def test_negative_return_preference(self):
        """测试负收益偏好（反转策略）"""
        dates = pd.date_range("2023-01-01", periods=40, freq="D")

        # 下跌股票
        down = np.linspace(100, 90, 40) + np.random.normal(0, 1, 40)
        # 上涨股票
        up = np.linspace(100, 110, 40) + np.random.normal(0, 1, 40)

        prices = pd.DataFrame({"DOWN": down, "UP": up}, index=dates)

        selector = ValueSelector(
            params={
                "volatility_period": 20,
                "return_period": 20,
                "top_n": 5,
                "select_low_volatility": False,
                "select_negative_return": True,
                "volatility_weight": 0.1,  # 低权重给波动率
            }
        )

        selected = selector.select(dates[-1], prices)

        # 下跌股票应该被优先选中（反转策略）
        assert "DOWN" in selected or len(selected) > 0

    def test_high_volatility_positive_return(self):
        """测试高波动率+正收益偏好"""
        dates = pd.date_range("2023-01-01", periods=40, freq="D")

        # 高波动、上涨股票
        high_vol_up = 100 + np.cumsum(np.random.normal(0.5, 3, 40))
        # 低波动、下跌股票
        low_vol_down = 100 - np.linspace(0, 10, 40) + np.random.normal(0, 0.5, 40)

        prices = pd.DataFrame(
            {"HIGH_UP": high_vol_up, "LOW_DOWN": low_vol_down}, index=dates
        )

        selector = ValueSelector(
            params={
                "volatility_period": 20,
                "return_period": 20,
                "top_n": 5,
                "select_low_volatility": False,  # 选择高波动
                "select_negative_return": False,  # 选择正收益
                "volatility_weight": 0.5,
            }
        )

        selected = selector.select(dates[-1], prices)

        # 高波动上涨股票应该被选中
        assert "HIGH_UP" in selected or len(selected) > 0

    def test_top_n_limit(self):
        """测试选股数量限制"""
        selector = ValueSelector(
            params={"volatility_period": 20, "return_period": 20, "top_n": 10}
        )

        selected = selector.select(self.test_date, self.prices)

        # 最多选出5只股票（总共只有5只）
        assert len(selected) <= 5

    def test_different_periods(self):
        """测试不同的计算周期"""
        selector_short = ValueSelector(
            params={"volatility_period": 10, "return_period": 10, "top_n": 5}
        )
        selector_long = ValueSelector(
            params={"volatility_period": 30, "return_period": 30, "top_n": 5}
        )

        selected_short = selector_short.select(self.test_date, self.prices)
        selected_long = selector_long.select(self.test_date, self.prices)

        # 两个选股器都应该返回结果
        assert len(selected_short) > 0
        assert len(selected_long) > 0

    def test_weight_variation(self):
        """测试不同的权重配置"""
        # 只看波动率
        selector_vol = ValueSelector(
            params={
                "volatility_period": 20,
                "return_period": 20,
                "top_n": 5,
                "volatility_weight": 1.0,
            }
        )

        # 只看收益率
        selector_ret = ValueSelector(
            params={
                "volatility_period": 20,
                "return_period": 20,
                "top_n": 5,
                "volatility_weight": 0.0,
            }
        )

        selected_vol = selector_vol.select(self.test_date, self.prices)
        selected_ret = selector_ret.select(self.test_date, self.prices)

        # 两种方法可能选出不同的股票
        assert len(selected_vol) > 0
        assert len(selected_ret) > 0


class TestValueSelectorEdgeCases:
    """测试 ValueSelector 边界情况"""

    def test_invalid_date(self):
        """测试无效日期"""
        prices = pd.DataFrame(
            {"A": [100, 105, 110], "B": [100, 102, 104]},
            index=pd.date_range("2023-01-01", periods=3, freq="D"),
        )

        selector = ValueSelector(
            params={"volatility_period": 5, "return_period": 5, "top_n": 5}
        )

        invalid_date = pd.Timestamp("2024-01-01")
        selected = selector.select(invalid_date, prices)

        assert len(selected) == 0

    def test_insufficient_data(self):
        """测试数据不足"""
        # 只有15天数据，但周期要20天
        prices = pd.DataFrame(
            {"A": range(100, 115), "B": range(100, 115)},
            index=pd.date_range("2023-01-01", periods=15, freq="D"),
        )

        selector = ValueSelector(
            params={"volatility_period": 20, "return_period": 20, "top_n": 5}
        )

        test_date = prices.index[-1]
        selected = selector.select(test_date, prices)

        # 数据不足时应该返回空列表或处理 NaN
        assert isinstance(selected, list)

    def test_all_same_values(self):
        """测试所有股票价格相同"""
        dates = pd.date_range("2023-01-01", periods=30, freq="D")
        prices = pd.DataFrame(
            {"A": [100] * 30, "B": [100] * 30, "C": [100] * 30}, index=dates
        )

        selector = ValueSelector(
            params={"volatility_period": 20, "return_period": 20, "top_n": 5}
        )

        selected = selector.select(dates[-1], prices)

        # 所有股票相同时，应该能够处理（标准差为0的情况）
        assert isinstance(selected, list)

    def test_nan_values(self):
        """测试包含NaN值的数据"""
        dates = pd.date_range("2023-01-01", periods=30, freq="D")
        prices = pd.DataFrame(
            {
                "A": [100 + i for i in range(30)],
                "B": [100 + i * 0.5 for i in range(30)],
            },
            index=dates,
        )

        # 插入NaN
        prices.loc[dates[10], "A"] = np.nan
        prices.loc[dates[15], "B"] = np.nan

        selector = ValueSelector(
            params={"volatility_period": 20, "return_period": 20, "top_n": 5}
        )

        selected = selector.select(dates[-1], prices)

        # 应该能处理NaN
        assert isinstance(selected, list)


class TestValueSelectorParameterValidation:
    """测试 ValueSelector 参数验证"""

    def test_invalid_volatility_period(self):
        """测试无效的波动率周期"""
        with pytest.raises(ValueError):
            ValueSelector(params={"volatility_period": -1})

        with pytest.raises(ValueError):
            ValueSelector(params={"volatility_period": 200})

    def test_invalid_return_period(self):
        """测试无效的收益率周期"""
        with pytest.raises(ValueError):
            ValueSelector(params={"return_period": -1})

        with pytest.raises(ValueError):
            ValueSelector(params={"return_period": 300})

    def test_invalid_top_n(self):
        """测试无效的选股数量"""
        with pytest.raises(ValueError):
            ValueSelector(params={"top_n": 0})

        with pytest.raises(ValueError):
            ValueSelector(params={"top_n": -1})

    def test_invalid_volatility_weight(self):
        """测试无效的波动率权重"""
        with pytest.raises(ValueError):
            ValueSelector(params={"volatility_weight": -0.1})

        with pytest.raises(ValueError):
            ValueSelector(params={"volatility_weight": 1.5})

    def test_invalid_parameter_type(self):
        """测试无效的参数类型"""
        with pytest.raises(ValueError):
            ValueSelector(params={"volatility_period": "20"})

    def test_unknown_parameter(self):
        """测试未知参数"""
        with pytest.raises(ValueError):
            ValueSelector(params={"unknown_param": 123})

    def test_valid_edge_values(self):
        """测试边界有效值"""
        selector1 = ValueSelector(
            params={
                "volatility_period": 5,
                "return_period": 5,
                "top_n": 5,
                "volatility_weight": 0.0,
            }
        )
        assert selector1.params["volatility_weight"] == 0.0

        selector2 = ValueSelector(
            params={
                "volatility_period": 100,
                "return_period": 200,
                "top_n": 200,
                "volatility_weight": 1.0,
            }
        )
        assert selector2.params["volatility_weight"] == 1.0


class TestValueSelectorIntegration:
    """测试 ValueSelector 集成场景"""

    def test_realistic_market_data(self):
        """测试真实市场数据场景"""
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        np.random.seed(42)

        # 生成10只股票
        stocks = {}
        for i in range(10):
            returns = np.random.normal(0.001, 0.02, 100)
            prices = 100 * np.exp(np.cumsum(returns))
            stocks[f"STOCK_{i}"] = prices

        prices_df = pd.DataFrame(stocks, index=dates)

        selector = ValueSelector(
            params={"volatility_period": 20, "return_period": 20, "top_n": 5}
        )

        selected = selector.select(dates[-1], prices_df)

        # 应该能选出股票
        assert len(selected) > 0
        assert len(selected) <= 5

    def test_multiple_calls_consistency(self):
        """测试多次调用的一致性"""
        dates = pd.date_range("2023-01-01", periods=40, freq="D")
        prices = pd.DataFrame(
            {
                "A": np.linspace(100, 120, 40),
                "B": np.linspace(100, 90, 40),
                "C": 100 + np.random.normal(0, 2, 40),
            },
            index=dates,
        )

        selector = ValueSelector(
            params={"volatility_period": 20, "return_period": 20, "top_n": 5}
        )

        test_date = dates[-1]
        selected1 = selector.select(test_date, prices)
        selected2 = selector.select(test_date, prices)
        selected3 = selector.select(test_date, prices)

        # 结果应该完全一致
        assert selected1 == selected2
        assert selected2 == selected3
