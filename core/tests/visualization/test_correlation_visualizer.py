"""
测试相关性分析可视化
"""

import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from src.visualization.correlation_visualizer import CorrelationVisualizer


class TestCorrelationVisualizer:
    """测试CorrelationVisualizer类"""

    @pytest.fixture
    def visualizer(self):
        """创建可视化器实例"""
        return CorrelationVisualizer()

    @pytest.fixture
    def sample_correlation_matrix(self):
        """创建示例相关性矩阵"""
        factors = [f"因子{i}" for i in range(1, 6)]
        # 创建一个对称的相关性矩阵
        np.random.seed(42)
        matrix = np.random.rand(5, 5)
        matrix = (matrix + matrix.T) / 2  # 对称化
        np.fill_diagonal(matrix, 1.0)  # 对角线为1
        # 确保在[-1, 1]范围内
        matrix = np.clip(matrix, -1, 1)

        return pd.DataFrame(matrix, index=factors, columns=factors)

    @pytest.fixture
    def sample_vif_df(self):
        """创建示例VIF数据"""
        return pd.DataFrame(
            {
                "factor": ["因子A", "因子B", "因子C", "因子D", "因子E"],
                "VIF": [2.5, 8.3, 15.6, 3.2, 1.8],
            }
        )

    @pytest.fixture
    def sample_factor_series(self):
        """创建示例因子序列"""
        dates = pd.date_range(start="2023-01-01", periods=252, freq="D")
        factor1 = pd.Series(
            np.random.randn(252), index=dates, name="因子1"
        )
        factor2 = pd.Series(
            np.random.randn(252), index=dates, name="因子2"
        )
        return factor1, factor2

    def test_init(self, visualizer):
        """测试初始化"""
        assert visualizer is not None
        assert visualizer.theme_name == "default_theme"

    def test_plot_correlation_heatmap(
        self, visualizer, sample_correlation_matrix
    ):
        """测试绘制相关性热力图"""
        fig = visualizer.plot_correlation_heatmap(
            sample_correlation_matrix
        )

        assert isinstance(fig, go.Figure)
        assert isinstance(fig.data[0], go.Heatmap)

        # 检查数据形状
        assert fig.data[0].z.shape == (5, 5)

        # 检查颜色范围
        assert fig.data[0].zmin == -1
        assert fig.data[0].zmax == 1

    def test_plot_correlation_heatmap_with_clustering(
        self, visualizer, sample_correlation_matrix
    ):
        """测试带聚类的相关性热力图"""
        fig = visualizer.plot_correlation_heatmap(
            sample_correlation_matrix, cluster=True
        )

        assert isinstance(fig, go.Figure)
        # 聚类后数据仍应该是5x5
        assert fig.data[0].z.shape == (5, 5)

    def test_plot_correlation_network(
        self, visualizer, sample_correlation_matrix
    ):
        """测试绘制相关性网络图"""
        fig = visualizer.plot_correlation_network(
            sample_correlation_matrix, threshold=0.5
        )

        assert isinstance(fig, go.Figure)
        # 应该有节点和边
        assert len(fig.data) >= 1

    def test_plot_correlation_network_high_threshold(
        self, visualizer, sample_correlation_matrix
    ):
        """测试高阈值的网络图"""
        # 高阈值应该减少连接
        fig = visualizer.plot_correlation_network(
            sample_correlation_matrix, threshold=0.9
        )

        assert isinstance(fig, go.Figure)

    def test_plot_correlation_network_low_threshold(
        self, visualizer, sample_correlation_matrix
    ):
        """测试低阈值的网络图"""
        # 低阈值应该增加连接
        fig = visualizer.plot_correlation_network(
            sample_correlation_matrix, threshold=0.1
        )

        assert isinstance(fig, go.Figure)

    def test_plot_factor_clustering(
        self, visualizer, sample_correlation_matrix
    ):
        """测试绘制因子聚类树状图"""
        fig = visualizer.plot_factor_clustering(
            sample_correlation_matrix
        )

        assert isinstance(fig, go.Figure)
        # 树状图应该有数据
        assert len(fig.data) >= 1

    def test_plot_vif_analysis(self, visualizer, sample_vif_df):
        """测试绘制VIF分析"""
        fig = visualizer.plot_vif_analysis(sample_vif_df, threshold=10.0)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert isinstance(fig.data[0], go.Bar)

        # 检查阈值线
        hlines = [
            shape for shape in fig.layout.shapes if shape.type == "line"
        ]
        assert len(hlines) >= 1

    def test_plot_vif_analysis_all_low(self, visualizer):
        """测试所有VIF都低于阈值"""
        vif_df = pd.DataFrame(
            {
                "factor": ["因子A", "因子B", "因子C"],
                "VIF": [2.5, 3.2, 1.8],
            }
        )

        fig = visualizer.plot_vif_analysis(vif_df, threshold=10.0)

        # 应该有"无多重共线性"的标注，检查最后一个annotation（第一个是阈值线）
        annotation_text = fig.layout.annotations[-1].text
        assert "无多重共线性" in annotation_text

    def test_plot_vif_analysis_some_high(self, visualizer, sample_vif_df):
        """测试部分VIF超过阈值"""
        fig = visualizer.plot_vif_analysis(sample_vif_df, threshold=10.0)

        # 应该有多重共线性警告，检查最后一个annotation（第一个是阈值线）
        annotation_text = fig.layout.annotations[-1].text
        assert "多重共线性风险" in annotation_text

    def test_plot_rolling_correlation(
        self, visualizer, sample_factor_series
    ):
        """测试绘制滚动相关性"""
        factor1, factor2 = sample_factor_series

        fig = visualizer.plot_rolling_correlation(
            factor1, factor2, window=60
        )

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1

        # 检查平均相关性线
        hlines = [
            shape for shape in fig.layout.shapes if shape.type == "line"
        ]
        assert len(hlines) >= 1

    def test_plot_rolling_correlation_custom_window(
        self, visualizer, sample_factor_series
    ):
        """测试自定义窗口的滚动相关性"""
        factor1, factor2 = sample_factor_series

        fig = visualizer.plot_rolling_correlation(
            factor1, factor2, window=30
        )

        assert isinstance(fig, go.Figure)

    def test_perfect_correlation(self, visualizer):
        """测试完全相关的情况"""
        factors = ["因子A", "因子B", "因子C"]
        # 完全正相关
        matrix = pd.DataFrame(
            [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]],
            index=factors,
            columns=factors,
        )

        fig = visualizer.plot_correlation_heatmap(matrix)

        assert isinstance(fig, go.Figure)

    def test_negative_correlation(self, visualizer):
        """测试负相关场景"""
        factors = ["因子A", "因子B"]
        # 负相关
        matrix = pd.DataFrame(
            [[1.0, -0.8], [-0.8, 1.0]],
            index=factors,
            columns=factors,
        )

        fig = visualizer.plot_correlation_heatmap(matrix)

        assert isinstance(fig, go.Figure)
        # 应该有负相关的颜色

    def test_zero_correlation(self, visualizer):
        """测试零相关场景"""
        factors = ["因子A", "因子B", "因子C"]
        # 几乎无相关
        matrix = pd.DataFrame(
            [[1.0, 0.01, -0.02], [0.01, 1.0, 0.03], [-0.02, 0.03, 1.0]],
            index=factors,
            columns=factors,
        )

        fig = visualizer.plot_correlation_heatmap(matrix)

        assert isinstance(fig, go.Figure)

    def test_single_factor(self, visualizer):
        """测试单个因子"""
        matrix = pd.DataFrame([[1.0]], index=["因子A"], columns=["因子A"])

        fig = visualizer.plot_correlation_heatmap(matrix)

        assert isinstance(fig, go.Figure)

    def test_many_factors(self, visualizer):
        """测试多因子场景（如20个）"""
        n = 20
        factors = [f"因子{i}" for i in range(1, n + 1)]

        np.random.seed(42)
        matrix = np.random.rand(n, n)
        matrix = (matrix + matrix.T) / 2
        np.fill_diagonal(matrix, 1.0)
        matrix = np.clip(matrix, -1, 1)

        corr_matrix = pd.DataFrame(matrix, index=factors, columns=factors)

        fig = visualizer.plot_correlation_heatmap(corr_matrix)

        assert isinstance(fig, go.Figure)
        assert fig.data[0].z.shape == (n, n)

    def test_asymmetric_matrix_warning(self, visualizer):
        """测试非对称矩阵（应该仍能绘制）"""
        factors = ["因子A", "因子B", "因子C"]
        # 非对称矩阵
        matrix = pd.DataFrame(
            [[1.0, 0.5, 0.3], [0.6, 1.0, 0.4], [0.2, 0.3, 1.0]],
            index=factors,
            columns=factors,
        )

        fig = visualizer.plot_correlation_heatmap(matrix)

        assert isinstance(fig, go.Figure)

    def test_vif_extreme_values(self, visualizer):
        """测试VIF极端值"""
        vif_df = pd.DataFrame(
            {
                "factor": ["因子A", "因子B", "因子C"],
                "VIF": [1.1, 50.0, 100.0],  # 极高VIF
            }
        )

        fig = visualizer.plot_vif_analysis(vif_df, threshold=10.0)

        assert isinstance(fig, go.Figure)

    def test_correlation_matrix_with_nan(self, visualizer):
        """测试含NaN的相关性矩阵"""
        factors = ["因子A", "因子B", "因子C"]
        matrix = pd.DataFrame(
            [[1.0, 0.5, np.nan], [0.5, 1.0, 0.3], [np.nan, 0.3, 1.0]],
            index=factors,
            columns=factors,
        )

        # 应该能够处理NaN
        fig = visualizer.plot_correlation_heatmap(matrix)

        assert isinstance(fig, go.Figure)
