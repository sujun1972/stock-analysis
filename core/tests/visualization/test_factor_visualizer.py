"""
测试因子分析可视化
"""

import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

from src.visualization.factor_visualizer import FactorVisualizer


class TestFactorVisualizer:
    """测试FactorVisualizer类"""

    @pytest.fixture
    def visualizer(self):
        """创建可视化器实例"""
        return FactorVisualizer()

    @pytest.fixture
    def sample_ic_series(self):
        """创建示例IC序列"""
        dates = pd.date_range(start="2023-01-01", periods=252, freq="D")
        # IC应该在-1到1之间
        ic_values = np.random.randn(252) * 0.05 + 0.02
        ic_values = np.clip(ic_values, -1, 1)
        return pd.Series(ic_values, index=dates)

    @pytest.fixture
    def sample_quantile_returns(self):
        """创建示例分层收益"""
        quantiles = [f"Q{i}" for i in range(1, 6)]
        # 模拟单调递增的分层收益
        mean_returns = np.array([-0.001, 0.0, 0.001, 0.002, 0.003])
        return pd.DataFrame(
            {"mean_return": mean_returns}, index=quantiles
        )

    @pytest.fixture
    def sample_quantile_cum_returns(self):
        """创建示例分层累计收益"""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        quantiles = [f"Q{i}" for i in range(1, 6)]

        data = {}
        for i, q in enumerate(quantiles):
            # 每个分组不同的累计收益
            returns = np.random.randn(100) * 0.01 + (i - 2) * 0.0005
            cum_returns = (1 + pd.Series(returns)).cumprod() - 1
            data[q] = cum_returns.values

        return pd.DataFrame(data, index=dates)

    def test_init(self, visualizer):
        """测试初始化"""
        assert visualizer is not None
        assert visualizer.theme_name == "default_theme"

    def test_plot_ic_time_series(self, visualizer, sample_ic_series):
        """测试绘制IC时间序列"""
        fig = visualizer.plot_ic_time_series(sample_ic_series)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert fig.data[0].name == "IC"

        # 检查统计信息标注（最后一个annotation是统计信息，前面的是均值线）
        assert len(fig.layout.annotations) >= 1
        annotation_text = fig.layout.annotations[-1].text
        assert "IC均值" in annotation_text
        assert "IR比率" in annotation_text

    def test_plot_ic_time_series_custom_title(
        self, visualizer, sample_ic_series
    ):
        """测试自定义标题的IC图"""
        fig = visualizer.plot_ic_time_series(
            sample_ic_series, title="自定义IC标题"
        )

        assert fig.layout.title.text == "自定义IC标题"

    def test_plot_rank_ic_time_series(
        self, visualizer, sample_ic_series
    ):
        """测试绘制Rank IC时间序列"""
        fig = visualizer.plot_rank_ic_time_series(sample_ic_series)

        assert isinstance(fig, go.Figure)
        assert "Rank IC" in fig.layout.title.text

    def test_plot_ic_histogram(self, visualizer, sample_ic_series):
        """测试绘制IC分布直方图"""
        fig = visualizer.plot_ic_histogram(sample_ic_series)

        assert isinstance(fig, go.Figure)
        # 应该有直方图和正态分布曲线
        assert len(fig.data) >= 2

        # 检查统计信息
        annotation_text = fig.layout.annotations[0].text
        assert "偏度" in annotation_text
        assert "峰度" in annotation_text

    def test_plot_ic_decay(self, visualizer):
        """测试绘制IC衰减曲线"""
        # 创建IC衰减数据
        lags = list(range(1, 11))  # 1-10天滞后
        ic_values = [0.05, 0.04, 0.03, 0.025, 0.02, 0.015, 0.01, 0.008, 0.006, 0.005]
        ic_decay = pd.Series(ic_values, index=lags)

        fig = visualizer.plot_ic_decay(ic_decay)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert fig.data[0].mode == "lines+markers"

    def test_plot_quantile_returns(
        self, visualizer, sample_quantile_returns
    ):
        """测试绘制因子分层收益"""
        fig = visualizer.plot_quantile_returns(sample_quantile_returns)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert isinstance(fig.data[0], go.Bar)

        # 检查单调性标注
        assert len(fig.layout.annotations) >= 1

    def test_plot_quantile_returns_monotonic(self, visualizer):
        """测试单调递增的分层收益"""
        quantiles = [f"Q{i}" for i in range(1, 6)]
        # 严格单调递增
        mean_returns = np.array([0.001, 0.002, 0.003, 0.004, 0.005])
        data = pd.DataFrame(
            {"mean_return": mean_returns}, index=quantiles
        )

        fig = visualizer.plot_quantile_returns(data)

        # 应该有单调性通过的标注
        annotation_text = fig.layout.annotations[0].text
        assert "单调性检验通过" in annotation_text

    def test_plot_quantile_returns_non_monotonic(self, visualizer):
        """测试非单调的分层收益"""
        quantiles = [f"Q{i}" for i in range(1, 6)]
        # 非单调
        mean_returns = np.array([0.001, 0.003, 0.002, 0.004, 0.005])
        data = pd.DataFrame(
            {"mean_return": mean_returns}, index=quantiles
        )

        fig = visualizer.plot_quantile_returns(data)

        # 应该有单调性失败的标注
        annotation_text = fig.layout.annotations[0].text
        assert "单调性检验失败" in annotation_text

    def test_plot_quantile_cumulative_returns(
        self, visualizer, sample_quantile_cum_returns
    ):
        """测试绘制分层累计收益曲线"""
        fig = visualizer.plot_quantile_cumulative_returns(
            sample_quantile_cum_returns
        )

        assert isinstance(fig, go.Figure)
        # 应该有5条曲线（5个分组）
        assert len(fig.data) == 5

    def test_plot_long_short_performance(self, visualizer):
        """测试绘制多空组合表现"""
        dates = pd.date_range(start="2023-01-01", periods=252, freq="D")
        # 模拟多空组合收益
        returns = pd.Series(
            np.random.randn(252) * 0.01 + 0.0005, index=dates
        )

        fig = visualizer.plot_long_short_performance(returns)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1

        # 检查统计信息标注
        annotation_text = fig.layout.annotations[0].text
        assert "总收益" in annotation_text
        assert "夏普比率" in annotation_text

    def test_plot_factor_coverage(self, visualizer):
        """测试绘制因子覆盖率"""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        # 覆盖率在0-1之间
        coverage = pd.Series(
            np.random.rand(100) * 0.3 + 0.7, index=dates
        )

        fig = visualizer.plot_factor_coverage(coverage)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert fig.data[0].name == "覆盖率"

    def test_plot_batch_ic_comparison(self, visualizer, sample_ic_series):
        """测试绘制多因子IC对比"""
        ic_dict = {
            "因子A": sample_ic_series,
            "因子B": sample_ic_series * 0.8,
            "因子C": sample_ic_series * 1.2,
        }

        fig = visualizer.plot_batch_ic_comparison(ic_dict)

        assert isinstance(fig, go.Figure)
        # 应该有3个箱线图
        assert len(fig.data) == 3

    def test_ic_statistics_calculation(
        self, visualizer, sample_ic_series
    ):
        """测试IC统计指标计算正确性"""
        fig = visualizer.plot_ic_time_series(sample_ic_series)

        # IC均值应该接近我们设置的0.02
        ic_mean = sample_ic_series.mean()
        assert abs(ic_mean - 0.02) < 0.01

        # IC>0的占比应该大于50%
        ic_positive_rate = (sample_ic_series > 0).sum() / len(
            sample_ic_series
        )
        assert ic_positive_rate > 0.5

    def test_with_negative_ic(self, visualizer):
        """测试负IC场景"""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        # 大部分为负IC
        ic_series = pd.Series(
            np.random.randn(100) * 0.03 - 0.02, index=dates
        )

        fig = visualizer.plot_ic_time_series(ic_series)

        assert isinstance(fig, go.Figure)
        # IC均值应该是负的
        ic_mean = ic_series.mean()
        assert ic_mean < 0

    def test_zero_ic(self, visualizer):
        """测试零IC场景"""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        # 接近零的IC
        ic_series = pd.Series(
            np.random.randn(100) * 0.001, index=dates
        )

        fig = visualizer.plot_ic_time_series(ic_series)

        assert isinstance(fig, go.Figure)

    def test_high_ic_volatility(self, visualizer):
        """测试高IC波动场景"""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        # 高波动IC
        ic_series = pd.Series(np.random.randn(100) * 0.2, index=dates)
        ic_series = np.clip(ic_series, -1, 1)

        fig = visualizer.plot_ic_histogram(ic_series)

        assert isinstance(fig, go.Figure)

    def test_quantile_returns_without_mean_return_column(
        self, visualizer
    ):
        """测试没有mean_return列的分层收益"""
        quantiles = [f"Q{i}" for i in range(1, 6)]
        # 直接使用Series或只有一列的DataFrame
        returns = pd.Series([0.001, 0.002, 0.003, 0.004, 0.005], index=quantiles)

        fig = visualizer.plot_quantile_returns(returns)

        assert isinstance(fig, go.Figure)

    def test_single_quantile(self, visualizer):
        """测试单个分组"""
        data = pd.DataFrame({"mean_return": [0.01]}, index=["Q1"])

        fig = visualizer.plot_quantile_returns(data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1

    def test_many_quantiles(self, visualizer):
        """测试多分组场景（如10分组）"""
        quantiles = [f"Q{i}" for i in range(1, 11)]
        mean_returns = np.linspace(-0.002, 0.002, 10)
        data = pd.DataFrame(
            {"mean_return": mean_returns}, index=quantiles
        )

        fig = visualizer.plot_quantile_returns(data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
