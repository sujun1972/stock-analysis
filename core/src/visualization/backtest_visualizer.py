"""
回测结果可视化

提供回测结果的各种可视化功能，包括净值曲线、回撤分析、收益分布、持仓分析等。
"""

from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from loguru import logger

from .base_visualizer import BaseVisualizer


class BacktestVisualizer(BaseVisualizer):
    """回测结果可视化器"""

    def __init__(self, theme: str = "default_theme"):
        """
        初始化回测可视化器

        Args:
            theme: 主题名称
        """
        super().__init__(theme)

    def plot_equity_curve(
        self,
        equity_curve: pd.Series,
        benchmark_curve: Optional[pd.Series] = None,
        title: str = "策略净值曲线",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制净值曲线

        Args:
            equity_curve: 策略净值曲线（Series，索引为日期）
            benchmark_curve: 基准净值曲线（可选）
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        fig = self.create_figure(
            title=title, x_label="日期", y_label="净值"
        )

        # 添加策略净值曲线
        fig.add_trace(
            go.Scatter(
                x=equity_curve.index,
                y=equity_curve.values,
                name="策略净值",
                line=dict(color=self.get_color("primary"), width=2),
                hovertemplate="日期: %{x}<br>净值: %{y:.4f}<extra></extra>",
            )
        )

        # 添加基准净值曲线
        if benchmark_curve is not None:
            fig.add_trace(
                go.Scatter(
                    x=benchmark_curve.index,
                    y=benchmark_curve.values,
                    name="基准净值",
                    line=dict(
                        color=self.get_color("benchmark"),
                        width=2,
                        dash="dash",
                    ),
                    hovertemplate="日期: %{x}<br>净值: %{y:.4f}<extra></extra>",
                )
            )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_cumulative_returns(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        title: str = "累计收益率",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制累计收益率曲线

        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列（可选）
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        # 计算累计收益率
        cum_returns = (1 + returns).cumprod() - 1

        fig = self.create_figure(
            title=title, x_label="日期", y_label="累计收益率"
        )

        # 添加策略累计收益
        fig.add_trace(
            go.Scatter(
                x=cum_returns.index,
                y=cum_returns.values * 100,
                name="策略收益",
                line=dict(color=self.get_color("primary"), width=2),
                hovertemplate="日期: %{x}<br>收益率: %{y:.2f}%<extra></extra>",
            )
        )

        # 添加基准累计收益
        if benchmark_returns is not None:
            cum_bench = (1 + benchmark_returns).cumprod() - 1
            fig.add_trace(
                go.Scatter(
                    x=cum_bench.index,
                    y=cum_bench.values * 100,
                    name="基准收益",
                    line=dict(
                        color=self.get_color("benchmark"),
                        width=2,
                        dash="dash",
                    ),
                    hovertemplate="日期: %{x}<br>收益率: %{y:.2f}%<extra></extra>",
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

    def plot_drawdown(
        self,
        equity_curve: pd.Series,
        title: str = "回撤曲线",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制回撤曲线

        Args:
            equity_curve: 净值曲线
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        # 计算回撤
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max

        fig = self.create_figure(
            title=title, x_label="日期", y_label="回撤"
        )

        # 添加回撤曲线
        fig.add_trace(
            go.Scatter(
                x=drawdown.index,
                y=drawdown.values * 100,
                name="回撤",
                fill="tozeroy",
                line=dict(color=self.get_color("negative"), width=1),
                fillcolor=f"rgba(220, 53, 69, 0.3)",
                hovertemplate="日期: %{x}<br>回撤: %{y:.2f}%<extra></extra>",
            )
        )

        # 找到最大回撤点
        max_dd_idx = drawdown.idxmin()
        max_dd_value = drawdown.min()

        # 标注最大回撤
        fig.add_annotation(
            x=max_dd_idx,
            y=max_dd_value * 100,
            text=f"最大回撤: {max_dd_value * 100:.2f}%",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor=self.get_color("negative"),
            ax=-50,
            ay=-30,
        )

        # 添加零线
        fig.add_hline(
            y=0, line_dash="dot", line_color="gray", opacity=0.5
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_underwater(
        self,
        equity_curve: pd.Series,
        title: str = "水下曲线（回撤期分析）",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制水下曲线（回撤期分析）

        Args:
            equity_curve: 净值曲线
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        # 计算回撤
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max

        # 识别回撤期
        is_in_drawdown = drawdown < 0
        drawdown_periods = []
        start = None

        for i, (date, in_dd) in enumerate(is_in_drawdown.items()):
            if in_dd and start is None:
                start = date
            elif not in_dd and start is not None:
                drawdown_periods.append((start, is_in_drawdown.index[i - 1]))
                start = None

        # 处理最后一个回撤期
        if start is not None:
            drawdown_periods.append((start, is_in_drawdown.index[-1]))

        fig = self.create_figure(
            title=title, x_label="日期", y_label="回撤"
        )

        # 绘制回撤曲线
        fig.add_trace(
            go.Scatter(
                x=drawdown.index,
                y=drawdown.values * 100,
                name="回撤",
                fill="tozeroy",
                line=dict(color=self.get_color("negative"), width=1),
                fillcolor=f"rgba(220, 53, 69, 0.2)",
                hovertemplate="日期: %{x}<br>回撤: %{y:.2f}%<extra></extra>",
            )
        )

        # 高亮显示Top 5最大回撤期
        top_periods = sorted(
            drawdown_periods,
            key=lambda p: drawdown.loc[p[0] : p[1]].min(),
        )[:5]

        for i, (start, end) in enumerate(top_periods):
            max_dd = drawdown.loc[start:end].min()
            fig.add_vrect(
                x0=start,
                x1=end,
                fillcolor=self.get_color("negative"),
                opacity=0.1,
                line_width=0,
                annotation_text=f"#{i+1}: {max_dd*100:.2f}%",
                annotation_position="top left",
            )

        # 添加零线
        fig.add_hline(
            y=0, line_dash="dot", line_color="gray", opacity=0.5
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_returns_distribution(
        self,
        returns: pd.Series,
        title: str = "收益分布",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制收益分布直方图

        Args:
            returns: 收益率序列
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        fig = self.create_figure(
            title=title, x_label="日收益率 (%)", y_label="频数"
        )

        # 计算统计指标
        mean_return = returns.mean() * 100
        std_return = returns.std() * 100
        skewness = returns.skew()
        kurtosis = returns.kurtosis()

        # 绘制直方图
        fig.add_trace(
            go.Histogram(
                x=returns.values * 100,
                nbinsx=50,
                name="收益分布",
                marker_color=self.get_color("primary"),
                opacity=0.7,
                hovertemplate="收益率: %{x:.2f}%<br>频数: %{y}<extra></extra>",
            )
        )

        # 添加统计信息
        fig.add_annotation(
            text=(
                f"均值: {mean_return:.2f}%<br>"
                f"标准差: {std_return:.2f}%<br>"
                f"偏度: {skewness:.2f}<br>"
                f"峰度: {kurtosis:.2f}"
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

    def plot_monthly_returns_heatmap(
        self,
        returns: pd.Series,
        title: str = "月度收益热力图",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制月度收益热力图

        Args:
            returns: 收益率序列
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        # 计算月度收益
        monthly_returns = returns.resample("M").apply(
            lambda x: (1 + x).prod() - 1
        )

        # 构建年×月矩阵
        years = monthly_returns.index.year.unique()
        months = range(1, 13)

        data = []
        for year in years:
            row = []
            for month in months:
                try:
                    value = monthly_returns[
                        (monthly_returns.index.year == year)
                        & (monthly_returns.index.month == month)
                    ].iloc[0]
                    row.append(value * 100)
                except:
                    row.append(np.nan)
            data.append(row)

        # 创建热力图
        fig = go.Figure(
            data=go.Heatmap(
                z=data,
                x=[
                    "1月",
                    "2月",
                    "3月",
                    "4月",
                    "5月",
                    "6月",
                    "7月",
                    "8月",
                    "9月",
                    "10月",
                    "11月",
                    "12月",
                ],
                y=[str(year) for year in years],
                colorscale=[
                    [0, self.get_color("negative")],
                    [0.5, "white"],
                    [1, self.get_color("positive")],
                ],
                zmid=0,
                text=[[f"{val:.2f}%" if not np.isnan(val) else "" for val in row] for row in data],
                texttemplate="%{text}",
                textfont={"size": 10},
                hovertemplate="年份: %{y}<br>月份: %{x}<br>收益率: %{z:.2f}%<extra></extra>",
                colorbar=dict(title="收益率 (%)"),
            )
        )

        fig.update_layout(
            title={
                "text": title,
                "font": {"size": self.style.get("title_size", 14)},
                "x": 0.5,
                "xanchor": "center",
            },
            xaxis_title="月份",
            yaxis_title="年份",
            height=max(400, len(years) * 40),
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_rolling_metrics(
        self,
        returns: pd.Series,
        window: int = 252,
        title: str = "滚动指标",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制滚动指标（夏普比率、波动率）

        Args:
            returns: 收益率序列
            window: 滚动窗口（交易日）
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        # 计算滚动指标
        rolling_sharpe = (
            returns.rolling(window).mean()
            / returns.rolling(window).std()
            * np.sqrt(252)
        )
        rolling_vol = returns.rolling(window).std() * np.sqrt(252) * 100

        # 创建双Y轴图表
        fig = make_subplots(
            rows=2,
            cols=1,
            subplot_titles=("滚动夏普比率", "滚动年化波动率"),
            vertical_spacing=0.12,
        )

        # 滚动夏普比率
        fig.add_trace(
            go.Scatter(
                x=rolling_sharpe.index,
                y=rolling_sharpe.values,
                name=f"{window}日夏普比率",
                line=dict(color=self.get_color("primary"), width=2),
                hovertemplate="日期: %{x}<br>夏普比率: %{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

        # 滚动波动率
        fig.add_trace(
            go.Scatter(
                x=rolling_vol.index,
                y=rolling_vol.values,
                name=f"{window}日波动率",
                line=dict(color=self.get_color("benchmark"), width=2),
                hovertemplate="日期: %{x}<br>波动率: %{y:.2f}%<extra></extra>",
            ),
            row=2,
            col=1,
        )

        # 添加零线到夏普比率图
        fig.add_hline(
            y=0,
            line_dash="dot",
            line_color="gray",
            opacity=0.5,
            row=1,
            col=1,
        )

        # 更新布局
        fig.update_layout(
            title_text=title,
            height=600,
            showlegend=False,
            hovermode="x unified",
        )

        fig.update_xaxes(title_text="日期", row=2, col=1)
        fig.update_yaxes(title_text="夏普比率", row=1, col=1)
        fig.update_yaxes(title_text="波动率 (%)", row=2, col=1)

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_position_heatmap(
        self,
        positions: pd.DataFrame,
        title: str = "持仓热力图",
        top_n: int = 20,
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制持仓热力图

        Args:
            positions: 持仓DataFrame（索引为日期，列为股票代码，值为持仓权重）
            title: 图表标题
            top_n: 显示前N只股票
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        # 选择持仓权重最大的前N只股票
        avg_weights = positions.abs().mean().sort_values(ascending=False)
        top_stocks = avg_weights.head(top_n).index

        # 提取数据
        data = positions[top_stocks].T.values

        # 创建热力图
        fig = go.Figure(
            data=go.Heatmap(
                z=data * 100,
                x=positions.index,
                y=top_stocks,
                colorscale=[
                    [0, self.get_color("short")],
                    [0.5, "white"],
                    [1, self.get_color("long")],
                ],
                zmid=0,
                hovertemplate="日期: %{x}<br>股票: %{y}<br>权重: %{z:.2f}%<extra></extra>",
                colorbar=dict(title="持仓权重 (%)"),
            )
        )

        fig.update_layout(
            title={
                "text": title,
                "font": {"size": self.style.get("title_size", 14)},
                "x": 0.5,
                "xanchor": "center",
            },
            xaxis_title="日期",
            yaxis_title="股票代码",
            height=max(400, top_n * 25),
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_turnover_rate(
        self,
        positions: pd.DataFrame,
        title: str = "换手率",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制换手率曲线

        Args:
            positions: 持仓DataFrame
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        # 计算换手率
        turnover = positions.diff().abs().sum(axis=1) / 2

        fig = self.create_figure(
            title=title, x_label="日期", y_label="换手率"
        )

        # 添加换手率曲线
        fig.add_trace(
            go.Scatter(
                x=turnover.index,
                y=turnover.values * 100,
                name="换手率",
                line=dict(color=self.get_color("primary"), width=2),
                fill="tozeroy",
                fillcolor=f"rgba(31, 119, 180, 0.2)",
                hovertemplate="日期: %{x}<br>换手率: %{y:.2f}%<extra></extra>",
            )
        )

        # 添加平均换手率线
        avg_turnover = turnover.mean() * 100
        fig.add_hline(
            y=avg_turnover,
            line_dash="dash",
            line_color=self.get_color("benchmark"),
            annotation_text=f"平均换手率: {avg_turnover:.2f}%",
            annotation_position="right",
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig
