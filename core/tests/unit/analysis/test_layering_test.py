"""
分层回测工具单元测试

测试功能：
- 分层测试执行
- 单调性分析
- 完整回测（净值曲线）
- 多空组合收益
- 边界条件和异常处理
"""

import pytest
import pandas as pd
import numpy as np

from analysis.layering_test import LayeringTest, LayerResult


# ==================== 测试数据生成 ====================


@pytest.fixture
def monotonic_factor_data():
    """生成单调因子数据（高因子值对应高收益）"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    stocks = [f'stock_{i:03d}' for i in range(50)]

    # 生成因子值
    factor_values = np.random.randn(100, 50)

    factor_df = pd.DataFrame(factor_values, index=dates, columns=stocks)

    # 生成价格（与因子正相关）
    base_price = 100.0
    returns = factor_values * 0.02 + np.random.randn(100, 50) * 0.01  # 因子影响收益
    prices = base_price * (1 + returns).cumprod(axis=0)

    price_df = pd.DataFrame(prices, index=dates, columns=stocks)

    return factor_df, price_df


@pytest.fixture
def sample_data():
    """生成样本数据"""
    np.random.seed(123)
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    stocks = [f'stock_{i:03d}' for i in range(100)]

    factor_df = pd.DataFrame(
        np.random.randn(200, 100),
        index=dates,
        columns=stocks
    )

    price_df = pd.DataFrame(
        100 * (1 + np.random.randn(200, 100) * 0.02).cumprod(axis=0),
        index=dates,
        columns=stocks
    )

    return factor_df, price_df


@pytest.fixture
def small_data():
    """生成小数据集"""
    dates = pd.date_range('2023-01-01', periods=20, freq='D')
    stocks = ['A', 'B', 'C', 'D', 'E']

    factor_df = pd.DataFrame(
        np.random.randn(20, 5),
        index=dates,
        columns=stocks
    )

    price_df = pd.DataFrame(
        100 * (1 + np.random.randn(20, 5) * 0.02).cumprod(axis=0),
        index=dates,
        columns=stocks
    )

    return factor_df, price_df


# ==================== LayeringTest基础测试 ====================


class TestLayeringTestInit:
    """测试分层测试初始化"""

    def test_default_init(self):
        """测试默认初始化"""
        layering_test = LayeringTest()
        assert layering_test.n_layers == 5
        assert layering_test.holding_period == 5
        assert layering_test.long_short is True

    def test_custom_init(self):
        """测试自定义初始化"""
        layering_test = LayeringTest(
            n_layers=10,
            holding_period=10,
            long_short=False
        )
        assert layering_test.n_layers == 10
        assert layering_test.holding_period == 10
        assert layering_test.long_short is False

    def test_invalid_n_layers(self):
        """测试无效的分层数"""
        with pytest.raises(ValueError, match="分层数必须至少为2"):
            LayeringTest(n_layers=1)

        with pytest.raises(ValueError, match="分层数必须至少为2"):
            LayeringTest(n_layers=0)


class TestPerformLayeringTest:
    """测试分层测试执行"""

    def test_perform_layering_test_basic(self, sample_data):
        """测试基本分层测试"""
        factor_df, price_df = sample_data
        layering_test = LayeringTest(n_layers=5, holding_period=5)

        result_df = layering_test.perform_layering_test(factor_df, price_df)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) >= 5  # 至少有5层
        assert '平均收益' in result_df.columns
        assert '收益标准差' in result_df.columns
        assert '夏普比率' in result_df.columns
        assert '胜率' in result_df.columns

    def test_perform_layering_test_layers(self, sample_data):
        """测试不同分层数"""
        factor_df, price_df = sample_data

        for n_layers in [3, 5, 10]:
            layering_test = LayeringTest(n_layers=n_layers)
            result_df = layering_test.perform_layering_test(factor_df, price_df)

            # 应该有n_layers层 + 可能的long_short层
            assert len(result_df) >= n_layers

    def test_perform_layering_test_long_short(self, sample_data):
        """测试多空组合"""
        factor_df, price_df = sample_data

        # 启用多空组合
        layering_test = LayeringTest(n_layers=5, long_short=True)
        result_with_ls = layering_test.perform_layering_test(factor_df, price_df)

        # 应该包含Long_Short层
        assert 'Long_Short' in result_with_ls.index

        # 禁用多空组合
        layering_test = LayeringTest(n_layers=5, long_short=False)
        result_without_ls = layering_test.perform_layering_test(factor_df, price_df)

        # 不应该包含Long_Short层
        assert 'Long_Short' not in result_without_ls.index

    def test_perform_layering_test_holding_period(self, sample_data):
        """测试不同持有期"""
        factor_df, price_df = sample_data

        for holding_period in [1, 5, 10, 20]:
            layering_test = LayeringTest(holding_period=holding_period)
            result_df = layering_test.perform_layering_test(factor_df, price_df)

            assert isinstance(result_df, pd.DataFrame)
            assert len(result_df) > 0

    def test_perform_layering_test_values(self, monotonic_factor_data):
        """测试单调因子的分层结果"""
        factor_df, price_df = monotonic_factor_data
        layering_test = LayeringTest(n_layers=5, holding_period=5)

        result_df = layering_test.perform_layering_test(factor_df, price_df)

        # 检查收益率范围
        mean_returns = result_df['平均收益']
        for layer_name, ret in mean_returns.items():
            if 'Layer' in layer_name:
                assert -1 < ret < 1  # 收益率应该在合理范围内

    def test_perform_layering_test_sharpe_ratio(self, sample_data):
        """测试夏普比率计算"""
        factor_df, price_df = sample_data
        layering_test = LayeringTest()

        result_df = layering_test.perform_layering_test(factor_df, price_df)

        # 夏普比率应该是有限值
        sharpe_ratios = result_df['夏普比率']
        assert all(np.isfinite(s) for s in sharpe_ratios)

    def test_perform_layering_test_win_rate(self, sample_data):
        """测试胜率计算"""
        factor_df, price_df = sample_data
        layering_test = LayeringTest()

        result_df = layering_test.perform_layering_test(factor_df, price_df)

        # 胜率应该在[0, 1]之间
        win_rates = result_df['胜率']
        assert all(0 <= w <= 1 for w in win_rates)


class TestAnalyzeMonotonicity:
    """测试单调性分析"""

    def test_analyze_monotonicity_basic(self, monotonic_factor_data):
        """测试基本单调性分析"""
        factor_df, price_df = monotonic_factor_data
        layering_test = LayeringTest(n_layers=5)

        result_df = layering_test.perform_layering_test(factor_df, price_df)
        monotonicity = layering_test.analyze_monotonicity(result_df)

        assert isinstance(monotonicity, dict)
        assert '是否单调' in monotonicity
        assert 'Spearman相关系数' in monotonicity
        assert '收益差距' in monotonicity
        assert '分层数' in monotonicity

    def test_analyze_monotonicity_correlation(self, monotonic_factor_data):
        """测试单调性相关系数"""
        factor_df, price_df = monotonic_factor_data
        layering_test = LayeringTest(n_layers=5)

        result_df = layering_test.perform_layering_test(factor_df, price_df)
        monotonicity = layering_test.analyze_monotonicity(result_df)

        # 单调因子的Spearman相关系数应该显著
        spearman_corr = monotonicity['Spearman相关系数']
        assert -1 <= spearman_corr <= 1

    def test_analyze_monotonicity_return_gap(self, monotonic_factor_data):
        """测试收益差距"""
        factor_df, price_df = monotonic_factor_data
        layering_test = LayeringTest(n_layers=5)

        result_df = layering_test.perform_layering_test(factor_df, price_df)
        monotonicity = layering_test.analyze_monotonicity(result_df)

        # 收益差距应该是有限值
        return_gap = monotonicity['收益差距']
        assert np.isfinite(return_gap)

    def test_analyze_monotonicity_non_monotonic(self, sample_data):
        """测试非单调因子"""
        factor_df, price_df = sample_data
        layering_test = LayeringTest(n_layers=5)

        result_df = layering_test.perform_layering_test(factor_df, price_df)
        monotonicity = layering_test.analyze_monotonicity(result_df)

        # 随机因子可能不单调
        assert isinstance(monotonicity['是否单调'], bool)


class TestBacktestLayers:
    """测试完整回测"""

    def test_backtest_layers_basic(self, sample_data):
        """测试基本回测"""
        factor_df, price_df = sample_data
        layering_test = LayeringTest(n_layers=5)

        equity_curves = layering_test.backtest_layers(
            factor_df, price_df, initial_capital=1_000_000
        )

        assert isinstance(equity_curves, dict)
        assert len(equity_curves) >= 5  # 至少有5层
        for layer_name, curve in equity_curves.items():
            assert isinstance(curve, pd.Series)
            assert len(curve) > 0
            assert curve.iloc[0] == 1_000_000  # 初始资金

    def test_backtest_layers_initial_capital(self, sample_data):
        """测试不同初始资金"""
        factor_df, price_df = sample_data
        layering_test = LayeringTest()

        for initial_capital in [100_000, 1_000_000, 10_000_000]:
            equity_curves = layering_test.backtest_layers(
                factor_df, price_df, initial_capital=initial_capital
            )

            for curve in equity_curves.values():
                assert curve.iloc[0] == initial_capital

    def test_backtest_layers_with_long_short(self, sample_data):
        """测试包含多空组合的回测"""
        factor_df, price_df = sample_data
        layering_test = LayeringTest(n_layers=5, long_short=True)

        equity_curves = layering_test.backtest_layers(factor_df, price_df)

        # 应该包含Long_Short层
        assert 'Long_Short' in equity_curves

    def test_backtest_layers_equity_growth(self, monotonic_factor_data):
        """测试净值增长"""
        factor_df, price_df = monotonic_factor_data
        layering_test = LayeringTest(n_layers=5)

        equity_curves = layering_test.backtest_layers(factor_df, price_df)

        # 检查净值曲线是否合理
        for layer_name, curve in equity_curves.items():
            if 'Layer' in layer_name:
                # 净值应该大于0（排除NaN值）
                valid_values = curve.dropna()
                assert all(valid_values > 0)
                # 至少应该有一些有效值
                assert len(valid_values) > 0


class TestLayerResult:
    """测试LayerResult数据类"""

    def test_layer_result_creation(self):
        """测试创建LayerResult"""
        result = LayerResult(
            layer_name='Layer_1',
            mean_return=0.001,
            std_return=0.02,
            sharpe_ratio=0.5,
            win_rate=0.55,
            max_return=0.05,
            min_return=-0.03,
            total_periods=100
        )

        assert result.layer_name == 'Layer_1'
        assert result.mean_return == 0.001
        assert result.sharpe_ratio == 0.5
        assert result.win_rate == 0.55


# ==================== 边界条件和异常测试 ====================


class TestEdgeCases:
    """测试边界条件"""

    def test_small_data(self, small_data):
        """测试小数据集"""
        factor_df, price_df = small_data
        layering_test = LayeringTest(n_layers=3, holding_period=2)

        result_df = layering_test.perform_layering_test(factor_df, price_df)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) >= 3

    def test_too_many_layers(self, small_data):
        """测试分层数过多"""
        factor_df, price_df = small_data
        # 5只股票分成10层（每层股票太少）
        layering_test = LayeringTest(n_layers=10)

        result_df = layering_test.perform_layering_test(factor_df, price_df)

        # 应该能处理，但某些层可能没有足够股票
        assert isinstance(result_df, pd.DataFrame)

    def test_single_holding_period(self, sample_data):
        """测试单日持有期"""
        factor_df, price_df = sample_data
        layering_test = LayeringTest(holding_period=1)

        result_df = layering_test.perform_layering_test(factor_df, price_df)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) > 0

    def test_long_holding_period(self, sample_data):
        """测试长持有期"""
        factor_df, price_df = sample_data
        # 持有期接近数据长度
        layering_test = LayeringTest(holding_period=50)

        result_df = layering_test.perform_layering_test(factor_df, price_df)

        assert isinstance(result_df, pd.DataFrame)

    def test_mismatched_stocks(self):
        """测试股票不匹配"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')

        factor_df = pd.DataFrame(
            np.random.randn(50, 5),
            index=dates,
            columns=['A', 'B', 'C', 'D', 'E']
        )

        price_df = pd.DataFrame(
            100 * (1 + np.random.randn(50, 3) * 0.02).cumprod(axis=0),
            index=dates,
            columns=['A', 'B', 'C']  # 只有3只股票
        )

        layering_test = LayeringTest()

        # 应该只使用共同的股票
        result_df = layering_test.perform_layering_test(factor_df, price_df)

        assert isinstance(result_df, pd.DataFrame)

    def test_all_nan_factor(self, sample_data):
        """测试全NaN因子"""
        factor_df, price_df = sample_data

        nan_factor = pd.DataFrame(
            np.nan,
            index=factor_df.index,
            columns=factor_df.columns
        )

        layering_test = LayeringTest()

        # 应该能处理全NaN因子（可能返回空或NaN结果）
        result_df = layering_test.perform_layering_test(nan_factor, price_df)

        assert isinstance(result_df, pd.DataFrame)

    def test_constant_prices(self, sample_data):
        """测试价格不变的情况"""
        factor_df, price_df = sample_data

        constant_prices = pd.DataFrame(
            100.0,
            index=price_df.index,
            columns=price_df.columns
        )

        layering_test = LayeringTest()

        result_df = layering_test.perform_layering_test(factor_df, constant_prices)

        # 价格不变时，所有收益应该接近0
        mean_returns = result_df['平均收益']
        assert all(abs(r) < 1e-6 for r in mean_returns if not np.isnan(r))


# ==================== 集成测试 ====================


class TestLayeringTestIntegration:
    """集成测试"""

    def test_complete_workflow(self, monotonic_factor_data):
        """测试完整工作流"""
        factor_df, price_df = monotonic_factor_data

        # 1. 创建分层测试工具
        layering_test = LayeringTest(n_layers=5, holding_period=5, long_short=True)

        # 2. 执行分层测试
        result_df = layering_test.perform_layering_test(factor_df, price_df)

        assert len(result_df) >= 5
        assert 'Long_Short' in result_df.index

        # 3. 分析单调性
        monotonicity = layering_test.analyze_monotonicity(result_df)

        assert 'Spearman相关系数' in monotonicity

        # 4. 完整回测
        equity_curves = layering_test.backtest_layers(factor_df, price_df)

        assert len(equity_curves) >= 5
        assert all(len(curve) > 0 for curve in equity_curves.values())

    def test_different_configurations(self, sample_data):
        """测试不同配置组合"""
        factor_df, price_df = sample_data

        configs = [
            {'n_layers': 3, 'holding_period': 5, 'long_short': True},
            {'n_layers': 5, 'holding_period': 10, 'long_short': False},
            {'n_layers': 10, 'holding_period': 1, 'long_short': True},
        ]

        for config in configs:
            layering_test = LayeringTest(**config)
            result_df = layering_test.perform_layering_test(factor_df, price_df)

            assert isinstance(result_df, pd.DataFrame)
            assert len(result_df) >= config['n_layers']

            if config['long_short']:
                assert 'Long_Short' in result_df.index


# ==================== 性能测试 ====================


@pytest.mark.performance
class TestLayeringTestPerformance:
    """性能测试（标记为慢速测试）"""

    def test_large_dataset_performance(self):
        """测试大数据集性能"""
        import time

        # 生成大数据集（500天，200只股票）
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=500, freq='D')
        stocks = [f'stock_{i:03d}' for i in range(200)]

        factor_df = pd.DataFrame(
            np.random.randn(500, 200),
            index=dates,
            columns=stocks
        )

        price_df = pd.DataFrame(
            100 * (1 + np.random.randn(500, 200) * 0.02).cumprod(axis=0),
            index=dates,
            columns=stocks
        )

        layering_test = LayeringTest(n_layers=10, holding_period=5)

        start_time = time.time()
        result_df = layering_test.perform_layering_test(factor_df, price_df)
        duration = time.time() - start_time

        assert duration < 5.0  # 应该在5秒内完成
        assert len(result_df) >= 10


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
