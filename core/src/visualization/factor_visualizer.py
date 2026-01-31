"""
因子分析可视化

提供因子分析的各种可视化功能，包括IC时间序列、因子分层收益、相关性分析等。
"""

from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from loguru import logger

from .base_visualizer import BaseVisualizer


class FactorVisualizer(BaseVisualizer):
    """因子分析可视化器"""

    def __init__(self, theme: str = "default_theme"):
        """
        初始化因子可视化器

        Args:
            theme: 主题名称
        """
        super().__init__(theme)

    def plot_ic_time_series(
        self,
        ic_series: pd.Series,
        title: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制IC时间序列

        Args:
            ic_series: IC序列（索引为日期）
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        if title is None:
            title = "IC时间序列"

        # 计算统计指标
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        ic_ir = ic_mean / ic_std if ic_std != 0 else 0
        ic_positive_rate = (ic_series > 0).sum() / len(ic_series)

        fig = self.create_figure(
            title=title, x_label="日期", y_label="IC值"
        )

        # 绘制IC条形图
        colors = [
            self.get_color("positive") if ic > 0 else self.get_color("negative")
            for ic in ic_series.values
        ]

        fig.add_trace(
            go.Bar(
                x=ic_series.index,
                y=ic_series.values,
                name="IC",
                marker_color=colors,
                hovertemplate="日期: %{x}<br>IC: %{y:.4f}<extra></extra>",
            )
        )

        # 添加均值线
        fig.add_hline(
            y=ic_mean,
            line_dash="dash",
            line_color=self.get_color("primary"),
            annotation_text=f"均值: {ic_mean:.4f}",
            annotation_position="right",
        )

        # 添加零线
        fig.add_hline(
            y=0, line_dash="dot", line_color="gray", opacity=0.5
        )

        # 添加统计信息
        fig.add_annotation(
            text=(
                f"IC均值: {ic_mean:.4f}<br>"
                f"IC标准差: {ic_std:.4f}<br>"
                f"IR比率: {ic_ir:.4f}<br>"
                f"IC>0占比: {ic_positive_rate*100:.2f}%"
            ),
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.98,
            xanchor="left",
            yanchor="top",
            showarrow=False,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="gray",
            borderwidth=1,
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_rank_ic_time_series(
        self,
        rank_ic_series: pd.Series,
        title: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制Rank IC时间序列

        Args:
            rank_ic_series: Rank IC序列
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        if title is None:
            title = "Rank IC时间序列"

        return self.plot_ic_time_series(
            rank_ic_series, title=title, save_path=save_path
        )

    def plot_ic_histogram(
        self,
        ic_series: pd.Series,
        title: str = "IC分布直方图",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制IC分布直方图

        Args:
            ic_series: IC序列
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        fig = self.create_figure(
            title=title, x_label="IC值", y_label="频数"
        )

        # 计算统计指标
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        skewness = ic_series.skew()
        kurtosis = ic_series.kurtosis()

        # 绘制直方图
        fig.add_trace(
            go.Histogram(
                x=ic_series.values,
                nbinsx=50,
                name="IC分布",
                marker_color=self.get_color("primary"),
                opacity=0.7,
                hovertemplate="IC: %{x:.4f}<br>频数: %{y}<extra></extra>",
            )
        )

        # 添加正态分布曲线
        x_range = np.linspace(
            ic_series.min(), ic_series.max(), 100
        )
        normal_curve = stats.norm.pdf(x_range, ic_mean, ic_std)
        # 缩放到直方图的尺度
        normal_curve = (
            normal_curve
            * len(ic_series)
            * (ic_series.max() - ic_series.min())
            / 50
        )

        fig.add_trace(
            go.Scatter(
                x=x_range,
                y=normal_curve,
                name="正态分布",
                line=dict(
                    color=self.get_color("benchmark"), width=2, dash="dash"
                ),
                hovertemplate="IC: %{x:.4f}<br>密度: %{y:.4f}<extra></extra>",
            )
        )

        # 添加统计信息
        fig.add_annotation(
            text=(
                f"均值: {ic_mean:.4f}<br>"
                f"标准差: {ic_std:.4f}<br>"
                f"偏度: {skewness:.4f}<br>"
                f"峰度: {kurtosis:.4f}"
            ),
            xref="paper",
            yref="paper",
            x=0.98,
            y=0.98,
            xanchor="right",
            yanchor="top",
            showarrow=False,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="gray",
            borderwidth=1,
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_ic_decay(
        self,
        ic_decay: pd.Series,
        title: str = "IC衰减分析",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制IC衰减曲线

        Args:
            ic_decay: IC衰减序列（索引为滞后期数）
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        fig = self.create_figure(
            title=title, x_label="滞后期数（天）", y_label="IC值"
        )

        # 绘制IC衰减曲线
        fig.add_trace(
            go.Scatter(
                x=ic_decay.index,
                y=ic_decay.values,
                name="IC衰减",
                mode="lines+markers",
                line=dict(color=self.get_color("primary"), width=2),
                marker=dict(size=8),
                hovertemplate="滞后期: %{x}天<br>IC: %{y:.4f}<extra></extra>",
            )
        )

        # 添加零线
        fig.add_hline(
            y=0, line_dash="dot", line_color="gray", opacity=0.5
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_quantile_returns(
        self,
        quantile_returns: pd.DataFrame,
        title: str = "因子分层收益",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制因子分层收益条形图

        Args:
            quantile_returns: 分层收益DataFrame（索引为分组，列包含"mean_return"等）
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        fig = self.create_figure(
            title=title, x_label="分组", y_label="平均收益率 (%)"
        )

        # 提取数据
        if "mean_return" in quantile_returns.columns:
            returns = quantile_returns["mean_return"].values * 100
        else:
            returns = quantile_returns.values * 100

        # 绘制条形图
        colors = [
            self.get_color("positive") if r > 0 else self.get_color("negative")
            for r in returns
        ]

        fig.add_trace(
            go.Bar(
                x=quantile_returns.index,
                y=returns,
                name="分组收益",
                marker_color=colors,
                hovertemplate="分组: %{x}<br>收益率: %{y:.2f}%<extra></extra>",
            )
        )

        # 添加零线
        fig.add_hline(
            y=0, line_dash="dot", line_color="gray", opacity=0.5
        )

        # 检查单调性
        is_monotonic = all(
            returns[i] <= returns[i + 1] for i in range(len(returns) - 1)
        ) or all(
            returns[i] >= returns[i + 1] for i in range(len(returns) - 1)
        )

        # 添加单调性标注
        if is_monotonic:
            fig.add_annotation(
                text="✓ 单调性检验通过",
                xref="paper",
                yref="paper",
                x=0.02,
                y=0.98,
                xanchor="left",
                yanchor="top",
                showarrow=False,
                bgcolor="rgba(40, 167, 69, 0.2)",
                bordercolor=self.get_color("positive"),
                borderwidth=1,
            )
        else:
            fig.add_annotation(
                text="✗ 单调性检验失败",
                xref="paper",
                yref="paper",
                x=0.02,
                y=0.98,
                xanchor="left",
                yanchor="top",
                showarrow=False,
                bgcolor="rgba(220, 53, 69, 0.2)",
                bordercolor=self.get_color("negative"),
                borderwidth=1,
            )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_quantile_cumulative_returns(
        self,
        quantile_cum_returns: pd.DataFrame,
        title: str = "分层累计收益曲线",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制分层累计收益曲线

        Args:
            quantile_cum_returns: 分层累计收益DataFrame（索引为日期，列为分组）
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        fig = self.create_figure(
            title=title, x_label="日期", y_label="累计收益率 (%)"
        )

        # 获取颜色刻度
        n_quantiles = len(quantile_cum_returns.columns)
        colors = self.get_color_scale(n_quantiles, "sequential")

        # 绘制每个分组的累计收益曲线
        for i, col in enumerate(quantile_cum_returns.columns):
            fig.add_trace(
                go.Scatter(
                    x=quantile_cum_returns.index,
                    y=quantile_cum_returns[col].values * 100,
                    name=f"分组{col}",
                    line=dict(color=colors[i], width=2),
                    hovertemplate=f"日期: %{{x}}<br>分组{col}收益: %{{y:.2f}}%<extra></extra>",
                )
            )

        # 添加零线
        fig.add_hline(
            y=0, line_dash="dot", line_color="gray", opacity=0.5
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_long_short_performance(
        self,
        long_short_returns: pd.Series,
        title: str = "多空组合表现",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制多空组合净值曲线

        Args:
            long_short_returns: 多空组合收益率序列
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        # 计算累计收益
        cum_returns = (1 + long_short_returns).cumprod()

        fig = self.create_figure(
            title=title, x_label="日期", y_label="净值"
        )

        # 绘制净值曲线
        fig.add_trace(
            go.Scatter(
                x=cum_returns.index,
                y=cum_returns.values,
                name="多空组合",
                line=dict(color=self.get_color("primary"), width=2),
                fill="tozeroy",
                fillcolor=f"rgba(31, 119, 180, 0.2)",
                hovertemplate="日期: %{x}<br>净值: %{y:.4f}<extra></extra>",
            )
        )

        # 计算统计指标
        total_return = cum_returns.iloc[-1] - 1
        annual_return = (
            (1 + total_return) ** (252 / len(long_short_returns)) - 1
        )
        annual_vol = long_short_returns.std() * np.sqrt(252)
        sharpe = annual_return / annual_vol if annual_vol != 0 else 0

        # 添加统计信息
        fig.add_annotation(
            text=(
                f"总收益: {total_return*100:.2f}%<br>"
                f"年化收益: {annual_return*100:.2f}%<br>"
                f"年化波动: {annual_vol*100:.2f}%<br>"
                f"夏普比率: {sharpe:.2f}"
            ),
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.98,
            xanchor="left",
            yanchor="top",
            showarrow=False,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="gray",
            borderwidth=1,
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_factor_coverage(
        self,
        coverage: pd.Series,
        title: str = "因子覆盖率",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制因子覆盖率时间序列

        Args:
            coverage: 覆盖率序列（比例值，0-1）
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        fig = self.create_figure(
            title=title, x_label="日期", y_label="覆盖率 (%)"
        )

        # 绘制覆盖率曲线
        fig.add_trace(
            go.Scatter(
                x=coverage.index,
                y=coverage.values * 100,
                name="覆盖率",
                line=dict(color=self.get_color("primary"), width=2),
                fill="tozeroy",
                fillcolor=f"rgba(31, 119, 180, 0.2)",
                hovertemplate="日期: %{x}<br>覆盖率: %{y:.2f}%<extra></extra>",
            )
        )

        # 添加平均覆盖率线
        avg_coverage = coverage.mean() * 100
        fig.add_hline(
            y=avg_coverage,
            line_dash="dash",
            line_color=self.get_color("benchmark"),
            annotation_text=f"平均: {avg_coverage:.2f}%",
            annotation_position="right",
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_batch_ic_comparison(
        self,
        ic_dict: Dict[str, pd.Series],
        title: str = "多因子IC对比",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制多个因子的IC对比箱线图

        Args:
            ic_dict: 因子IC字典，键为因子名称，值为IC序列
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        fig = self.create_figure(
            title=title, x_label="因子", y_label="IC值"
        )

        # 绘制箱线图
        for factor_name, ic_series in ic_dict.items():
            fig.add_trace(
                go.Box(
                    y=ic_series.values,
                    name=factor_name,
                    boxmean="sd",  # 显示均值和标准差
                    hovertemplate=f"{factor_name}<br>IC: %{{y:.4f}}<extra></extra>",
                )
            )

        # 添加零线
        fig.add_hline(
            y=0, line_dash="dot", line_color="gray", opacity=0.5
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig
