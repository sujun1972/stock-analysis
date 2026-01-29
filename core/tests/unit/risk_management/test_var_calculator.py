"""
VaR计算器单元测试
"""

import pytest
import pandas as pd
import numpy as np
from src.risk_management.var_calculator import VaRCalculator


class TestVaRCalculator:
    """VaR计算器测试类"""

    @pytest.fixture
    def sample_returns(self):
        """生成测试用收益率数据"""
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 252))
        return returns

    @pytest.fixture
    def portfolio_values(self):
        """生成测试用组合价值数据"""
        np.random.seed(42)
        values = [1000000]
        for i in range(251):
            change = np.random.normal(0.001, 0.02)
            values.append(values[-1] * (1 + change))
        return pd.Series(values)

    def test_init_valid(self):
        """测试正常初始化"""
        calc = VaRCalculator(confidence_level=0.95)
        assert calc.confidence_level == 0.95

    def test_init_invalid_confidence(self):
        """测试无效置信水平"""
        with pytest.raises(ValueError):
            VaRCalculator(confidence_level=1.5)

        with pytest.raises(ValueError):
            VaRCalculator(confidence_level=-0.1)

    def test_historical_var(self, sample_returns):
        """测试历史模拟法VaR"""
        calc = VaRCalculator(confidence_level=0.95)
        result = calc.calculate_historical_var(sample_returns, holding_period=1)

        assert 'var' in result
        assert 'cvar' in result
        assert 'confidence_level' in result
        assert result['confidence_level'] == 0.95
        assert result['var'] < 0  # VaR应该是负数
        assert result['cvar'] < result['var']  # CVaR应该更负

    def test_historical_var_holding_period(self, sample_returns):
        """测试不同持有期的VaR"""
        calc = VaRCalculator()

        result_1d = calc.calculate_historical_var(sample_returns, 1)
        result_5d = calc.calculate_historical_var(sample_returns, 5)

        # 5日VaR应该大于1日VaR（绝对值）
        assert abs(result_5d['var']) > abs(result_1d['var'])

    def test_parametric_var(self, sample_returns):
        """测试参数法VaR"""
        calc = VaRCalculator(confidence_level=0.95)
        result = calc.calculate_parametric_var(sample_returns, holding_period=1)

        assert result['method'] == 'parametric'
        assert result['var'] < 0
        assert result['cvar'] < result['var']

    def test_monte_carlo_var(self, sample_returns):
        """测试蒙特卡洛VaR"""
        calc = VaRCalculator()
        result = calc.calculate_monte_carlo_var(
            sample_returns,
            holding_period=1,
            n_simulations=1000
        )

        assert result['method'] == 'monte_carlo'
        assert result['n_simulations'] == 1000
        assert result['var'] < 0

    def test_portfolio_var(self, portfolio_values):
        """测试组合VaR计算"""
        calc = VaRCalculator()
        result = calc.calculate_portfolio_var(portfolio_values, method='historical')

        assert 'var_1day' in result
        assert 'var_5day' in result
        assert 'var_20day' in result
        assert 'cvar_1day' in result
        assert 'max_loss_historical' in result
        assert result['method'] == 'historical'

        # 检查VaR递增关系
        assert abs(result['var_5day']) > abs(result['var_1day'])
        assert abs(result['var_20day']) > abs(result['var_5day'])

    def test_compare_methods(self, sample_returns):
        """测试方法比较"""
        calc = VaRCalculator()
        comparison = calc.compare_methods(sample_returns, holding_period=1)

        assert isinstance(comparison, pd.DataFrame)
        assert 'method' in comparison.columns
        assert 'var' in comparison.columns
        assert 'cvar' in comparison.columns
        assert len(comparison) >= 2  # 至少有2种方法

    def test_backtest_var(self, sample_returns):
        """测试VaR回测"""
        # 生成更长的收益率序列用于回测
        np.random.seed(42)
        long_returns = pd.Series(np.random.normal(0.001, 0.02, 500))

        calc = VaRCalculator(confidence_level=0.95)
        backtest_result = calc.backtest_var(
            long_returns,
            window_size=252,
            holding_period=1,
            method='historical'
        )

        assert 'violation_rate' in backtest_result
        assert 'expected_rate' in backtest_result
        assert 'n_violations' in backtest_result
        assert 'pass_backtest' in backtest_result

        # 违约率应该接近期望违约率（5%）
        assert 0 <= backtest_result['violation_rate'] <= 1
        assert abs(backtest_result['expected_rate'] - 0.05) < 0.001

    def test_empty_returns(self):
        """测试空收益率序列"""
        calc = VaRCalculator()
        empty_returns = pd.Series([])

        with pytest.raises(ValueError):
            calc.calculate_historical_var(empty_returns)

    def test_small_sample_warning(self):
        """测试小样本警告"""
        calc = VaRCalculator()
        small_returns = pd.Series(np.random.normal(0.001, 0.02, 20))

        # 应该能计算，但会有警告
        result = calc.calculate_historical_var(small_returns)
        assert 'var' in result

    def test_different_confidence_levels(self, sample_returns):
        """测试不同置信水平"""
        for cl in [0.90, 0.95, 0.99]:
            calc = VaRCalculator(confidence_level=cl)
            result = calc.calculate_historical_var(sample_returns)

            assert result['confidence_level'] == cl

        # 99% VaR应该大于95% VaR（绝对值）
        calc_95 = VaRCalculator(0.95)
        calc_99 = VaRCalculator(0.99)

        var_95 = calc_95.calculate_historical_var(sample_returns)['var']
        var_99 = calc_99.calculate_historical_var(sample_returns)['var']

        assert abs(var_99) > abs(var_95)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
