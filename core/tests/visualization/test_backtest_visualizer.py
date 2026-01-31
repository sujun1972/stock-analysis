"""
测试回测结果可视化
"""

import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import tempfile
from pathlib import Path

from src.visualization.backtest_visualizer import BacktestVisualizer


class TestBacktestVisualizer:
    """测试BacktestVisualizer类"""

    @pytest.fixture
    def visualizer(self):
        """创建可视化器实例"""
        return BacktestVisualizer()

    @pytest.fixture
    def sample_equity_curve(self):
        """创建示例净值曲线"""
        dates = pd.date_range(start="2023-01-01", periods=252, freq="D")
        # 模拟上涨趋势 + 噪声
        values = np.cumprod(1 + np.random.randn(252) * 0.01 + 0.0003)
        return pd.Series(values, index=dates)

    @pytest.fixture
    def sample_returns(self):
        """创建示例收益率序列"""
        dates = pd.date_range(start="2023-01-01", periods=252, freq="D")
        returns = np.random.randn(252) * 0.01 + 0.0003
        return pd.Series(returns, index=dates)

    @pytest.fixture
    def sample_positions(self):
        """创建示例持仓数据"""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        stocks = [f"股票{i:03d}" for i in range(10)]

        # 生成随机持仓权重
        data = np.random.randn(100, 10) * 0.05
        data = data / np.abs(data).sum(axis=1, keepdims=True)  # 归一化

        return pd.DataFrame(data, index=dates, columns=stocks)

    def test_init(self, visualizer):
        """测试初始化"""
        assert visualizer is not None
        assert visualizer.theme_name == "default_theme"

    def test_plot_equity_curve(self, visualizer, sample_equity_curve):
        """测试绘制净值曲线"""
        fig = visualizer.plot_equity_curve(sample_equity_curve)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert fig.data[0].name == "策略净值"
        assert len(fig.data[0].x) == len(sample_equity_curve)

    def test_plot_equity_curve_with_benchmark(
        self, visualizer, sample_equity_curve
    ):
        """测试绘制净值曲线（含基准）"""
        # 创建基准曲线
        benchmark = sample_equity_curve * 0.8 + np.random.randn(len(sample_equity_curve)) * 0.05

        fig = visualizer.plot_equity_curve(
            sample_equity_curve, benchmark_curve=benchmark
        )

        assert len(fig.data) == 2
        assert fig.data[0].name == "策略净值"
        assert fig.data[1].name == "基准净值"

    def test_plot_equity_curve_save(
        self, visualizer, sample_equity_curve
    ):
        """测试保存净值曲线"""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "equity.html"
            fig = visualizer.plot_equity_curve(
                sample_equity_curve, save_path=str(save_path)
            )

            assert save_path.exists()

    def test_plot_cumulative_returns(self, visualizer, sample_returns):
        """测试绘制累计收益率"""
        fig = visualizer.plot_cumulative_returns(sample_returns)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert fig.data[0].name == "策略收益"

    def test_plot_cumulative_returns_with_benchmark(
        self, visualizer, sample_returns
    ):
        """测试绘制累计收益率（含基准）"""
        benchmark_returns = sample_returns * 0.7 + np.random.randn(len(sample_returns)) * 0.005

        fig = visualizer.plot_cumulative_returns(
            sample_returns, benchmark_returns=benchmark_returns
        )

        assert len(fig.data) == 2
        assert fig.data[1].name == "基准收益"

    def test_plot_drawdown(self, visualizer, sample_equity_curve):
        """测试绘制回撤曲线"""
        fig = visualizer.plot_drawdown(sample_equity_curve)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert fig.data[0].name == "回撤"

        # 检查最大回撤标注
        assert len(fig.layout.annotations) >= 1

    def test_plot_drawdown_values(self, visualizer):
        """测试回撤计算正确性"""
        # 创建一个已知回撤的净值曲线
        dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
        equity = pd.Series([1.0, 1.2, 1.0, 0.9, 1.1], index=dates)

        fig = visualizer.plot_drawdown(equity)

        # 回撤应该是负值
        drawdown_values = fig.data[0].y
        assert all(dd <= 0 for dd in drawdown_values)

    def test_plot_underwater(self, visualizer, sample_equity_curve):
        """测试绘制水下曲线"""
        fig = visualizer.plot_underwater(sample_equity_curve)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert fig.data[0].name == "回撤"

    def test_plot_returns_distribution(self, visualizer, sample_returns):
        """测试绘制收益分布"""
        fig = visualizer.plot_returns_distribution(sample_returns)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1

        # 检查统计信息标注
        assert len(fig.layout.annotations) >= 1
        annotation_text = fig.layout.annotations[0].text
        assert "均值" in annotation_text
        assert "标准差" in annotation_text
        assert "偏度" in annotation_text
        assert "峰度" in annotation_text

    def test_plot_monthly_returns_heatmap(self, visualizer, sample_returns):
        """测试绘制月度收益热力图"""
        fig = visualizer.plot_monthly_returns_heatmap(sample_returns)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert isinstance(fig.data[0], go.Heatmap)

    def test_plot_monthly_returns_heatmap_multiline(self, visualizer):
        """测试月度热力图（跨年数据）"""
        # 创建跨年数据
        dates = pd.date_range(start="2021-01-01", periods=750, freq="D")
        returns = pd.Series(np.random.randn(750) * 0.01, index=dates)

        fig = visualizer.plot_monthly_returns_heatmap(returns)

        # 应该有多行（多年）
        assert fig.data[0].z is not None
        assert len(fig.data[0].z) >= 2  # 至少2年

    def test_plot_rolling_metrics(self, visualizer, sample_returns):
        """测试绘制滚动指标"""
        fig = visualizer.plot_rolling_metrics(
            sample_returns, window=60
        )

        assert isinstance(fig, go.Figure)
        # 应该有2个子图（夏普比率和波动率）
        assert len(fig.data) == 2

    def test_plot_rolling_metrics_custom_window(
        self, visualizer, sample_returns
    ):
        """测试自定义窗口的滚动指标"""
        fig = visualizer.plot_rolling_metrics(
            sample_returns, window=30
        )

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2

    def test_plot_position_heatmap(self, visualizer, sample_positions):
        """测试绘制持仓热力图"""
        fig = visualizer.plot_position_heatmap(sample_positions, top_n=5)

        assert isinstance(fig, go.Figure)
        assert isinstance(fig.data[0], go.Heatmap)

        # 应该只显示top 5股票
        assert len(fig.data[0].y) == 5

    def test_plot_position_heatmap_all_stocks(
        self, visualizer, sample_positions
    ):
        """测试显示所有股票的持仓热力图"""
        n_stocks = sample_positions.shape[1]
        fig = visualizer.plot_position_heatmap(
            sample_positions, top_n=n_stocks
        )

        assert len(fig.data[0].y) == n_stocks

    def test_plot_turnover_rate(self, visualizer, sample_positions):
        """测试绘制换手率"""
        fig = visualizer.plot_turnover_rate(sample_positions)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert fig.data[0].name == "换手率"

        # 检查平均换手率线
        hlines = [
            shape for shape in fig.layout.shapes if shape.type == "line"
        ]
        assert len(hlines) >= 1

    def test_plot_turnover_rate_values(self, visualizer):
        """测试换手率计算"""
        # 创建简单的持仓变化
        dates = pd.date_range(start="2023-01-01", periods=3, freq="D")
        positions = pd.DataFrame(
            [[0.5, 0.5], [0.3, 0.7], [0.6, 0.4]],
            index=dates,
            columns=["股票A", "股票B"],
        )

        fig = visualizer.plot_turnover_rate(positions)

        # 第一天换手率应该是0（没有前一天数据）
        # 第二天换手率 = (|0.3-0.5| + |0.7-0.5|) / 2 = 0.2
        turnover_values = fig.data[0].y
        assert turnover_values[0] == 0  # NaN会被处理
        # 注意：实际值是百分比形式

    def test_empty_data(self, visualizer):
        """测试空数据处理"""
        empty_series = pd.Series([], dtype=float)

        with pytest.raises(Exception):
            # 空数据应该抛出异常或正确处理
            visualizer.plot_equity_curve(empty_series)

    def test_single_point_data(self, visualizer):
        """测试单点数据"""
        single_point = pd.Series(
            [1.0], index=[datetime(2023, 1, 1)]
        )

        # 单点数据应该能够绘制
        fig = visualizer.plot_equity_curve(single_point)
        assert len(fig.data) >= 1

    def test_with_nan_values(self, visualizer):
        """测试含NaN值的数据"""
        dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
        equity = pd.Series([1.0, 1.1, np.nan, 1.15, 1.2, np.nan, 1.25, 1.3, 1.35, 1.4], index=dates)

        # 应该能够处理NaN值
        fig = visualizer.plot_equity_curve(equity)
        assert isinstance(fig, go.Figure)

    def test_negative_returns(self, visualizer):
        """测试负收益场景"""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        # 大部分为负收益
        returns = pd.Series(np.random.randn(100) * 0.01 - 0.001, index=dates)

        fig = visualizer.plot_cumulative_returns(returns)
        assert isinstance(fig, go.Figure)

        # 累计收益应该是负的
        cum_returns = fig.data[0].y
        assert cum_returns[-1] < 0

    def test_high_volatility(self, visualizer):
        """测试高波动场景"""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        # 高波动收益
        returns = pd.Series(np.random.randn(100) * 0.05, index=dates)

        fig = visualizer.plot_returns_distribution(returns)
        assert isinstance(fig, go.Figure)
