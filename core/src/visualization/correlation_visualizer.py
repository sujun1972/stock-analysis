"""
相关性分析可视化

提供因子相关性分析的可视化功能。
"""

from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.figure_factory as ff
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform
from loguru import logger

from .base_visualizer import BaseVisualizer


class CorrelationVisualizer(BaseVisualizer):
    """相关性分析可视化器"""

    def __init__(self, theme: str = "default_theme"):
        """
        初始化相关性可视化器

        Args:
            theme: 主题名称
        """
        super().__init__(theme)

    def plot_correlation_heatmap(
        self,
        correlation_matrix: pd.DataFrame,
        title: str = "因子相关性矩阵",
        save_path: Optional[str] = None,
        cluster: bool = False,
    ) -> go.Figure:
        """
        绘制相关性热力图

        Args:
            correlation_matrix: 相关性矩阵DataFrame
            title: 图表标题
            save_path: 保存路径（可选）
            cluster: 是否进行聚类排序

        Returns:
            Plotly图表对象
        """
        # 如果需要聚类，重新排序
        if cluster:
            # 使用层次聚类
            try:
                # 将相关性转换为距离
                dissimilarity = 1 - correlation_matrix.abs()
                # 聚类
                linkage = hierarchy.linkage(
                    squareform(dissimilarity.values), method="average"
                )
                # 获取排序
                dendro = hierarchy.dendrogram(
                    linkage, no_plot=True
                )
                order = dendro["leaves"]
                # 重新排序
                correlation_matrix = correlation_matrix.iloc[order, order]
            except Exception as e:
                logger.warning(f"Clustering failed: {e}, using original order")

        # 创建热力图
        fig = go.Figure(
            data=go.Heatmap(
                z=correlation_matrix.values,
                x=correlation_matrix.columns,
                y=correlation_matrix.index,
                colorscale=[
                    [0, self.get_color("negative")],
                    [0.5, "white"],
                    [1, self.get_color("positive")],
                ],
                zmid=0,
                zmin=-1,
                zmax=1,
                text=[[f"{val:.2f}" for val in row] for row in correlation_matrix.values],
                texttemplate="%{text}",
                textfont={"size": 8},
                hovertemplate="因子1: %{y}<br>因子2: %{x}<br>相关性: %{z:.3f}<extra></extra>",
                colorbar=dict(title="相关系数"),
            )
        )

        # 更新布局
        fig.update_layout(
            title={
                "text": title,
                "font": {"size": self.style.get("title_size", 14)},
                "x": 0.5,
                "xanchor": "center",
            },
            xaxis_title="因子",
            yaxis_title="因子",
            width=max(600, len(correlation_matrix.columns) * 30),
            height=max(600, len(correlation_matrix.index) * 30),
            xaxis=dict(tickangle=-45),
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_correlation_network(
        self,
        correlation_matrix: pd.DataFrame,
        threshold: float = 0.5,
        title: str = "因子相关性网络",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制相关性网络图

        Args:
            correlation_matrix: 相关性矩阵
            threshold: 相关性阈值，只显示绝对值大于该值的连接
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        # 提取节点和边
        nodes = list(correlation_matrix.columns)
        n_nodes = len(nodes)

        # 计算节点位置（圆形布局）
        angles = np.linspace(0, 2 * np.pi, n_nodes, endpoint=False)
        node_x = np.cos(angles)
        node_y = np.sin(angles)

        # 创建图表
        fig = go.Figure()

        # 添加边
        edge_traces = []
        for i in range(n_nodes):
            for j in range(i + 1, n_nodes):
                corr = correlation_matrix.iloc[i, j]
                if abs(corr) >= threshold:
                    # 边的颜色和宽度根据相关性强度
                    color = (
                        self.get_color("positive")
                        if corr > 0
                        else self.get_color("negative")
                    )
                    width = abs(corr) * 5

                    fig.add_trace(
                        go.Scatter(
                            x=[node_x[i], node_x[j]],
                            y=[node_y[i], node_y[j]],
                            mode="lines",
                            line=dict(color=color, width=width),
                            opacity=abs(corr),
                            hoverinfo="skip",
                            showlegend=False,
                        )
                    )

        # 添加节点
        fig.add_trace(
            go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers+text",
                marker=dict(
                    size=20,
                    color=self.get_color("primary"),
                    line=dict(color="white", width=2),
                ),
                text=nodes,
                textposition="top center",
                hovertemplate="%{text}<extra></extra>",
                showlegend=False,
            )
        )

        # 更新布局
        fig.update_layout(
            title={
                "text": f"{title} (阈值: {threshold})",
                "font": {"size": self.style.get("title_size", 14)},
                "x": 0.5,
                "xanchor": "center",
            },
            showlegend=False,
            hovermode="closest",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            width=800,
            height=800,
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_factor_clustering(
        self,
        correlation_matrix: pd.DataFrame,
        title: str = "因子层次聚类树状图",
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制因子聚类树状图

        Args:
            correlation_matrix: 相关性矩阵
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        # 将相关性转换为距离
        dissimilarity = 1 - correlation_matrix.abs()

        # 层次聚类
        linkage_matrix = hierarchy.linkage(
            squareform(dissimilarity.values), method="average"
        )

        # 创建树状图
        fig = ff.create_dendrogram(
            dissimilarity.values,
            labels=correlation_matrix.columns.tolist(),
            orientation="left",
            linkagefun=lambda x: hierarchy.linkage(x, method="average"),
        )

        # 更新布局
        fig.update_layout(
            title={
                "text": title,
                "font": {"size": self.style.get("title_size", 14)},
                "x": 0.5,
                "xanchor": "center",
            },
            xaxis_title="距离",
            yaxis_title="因子",
            height=max(400, len(correlation_matrix.columns) * 20),
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_vif_analysis(
        self,
        vif_df: pd.DataFrame,
        title: str = "方差膨胀因子（VIF）分析",
        threshold: float = 10.0,
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制VIF分析条形图

        Args:
            vif_df: VIF结果DataFrame（包含'factor'和'VIF'列）
            title: 图表标题
            threshold: VIF阈值，超过该值认为存在多重共线性
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        fig = self.create_figure(
            title=title, x_label="因子", y_label="VIF值"
        )

        # 根据VIF值着色
        colors = [
            self.get_color("positive")
            if vif < threshold
            else self.get_color("negative")
            for vif in vif_df["VIF"]
        ]

        # 绘制条形图
        fig.add_trace(
            go.Bar(
                x=vif_df["factor"],
                y=vif_df["VIF"],
                name="VIF",
                marker_color=colors,
                hovertemplate="因子: %{x}<br>VIF: %{y:.2f}<extra></extra>",
            )
        )

        # 添加阈值线
        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color=self.get_color("benchmark"),
            annotation_text=f"阈值: {threshold}",
            annotation_position="right",
        )

        # 添加说明
        n_high_vif = (vif_df["VIF"] > threshold).sum()
        fig.add_annotation(
            text=(
                f"VIF > {threshold}: {n_high_vif}/{len(vif_df)}<br>"
                f"存在多重共线性风险"
                if n_high_vif > 0
                else "无多重共线性问题"
            ),
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.98,
            xanchor="left",
            yanchor="top",
            showarrow=False,
            bgcolor=(
                "rgba(220, 53, 69, 0.2)"
                if n_high_vif > 0
                else "rgba(40, 167, 69, 0.2)"
            ),
            bordercolor=(
                self.get_color("negative")
                if n_high_vif > 0
                else self.get_color("positive")
            ),
            borderwidth=1,
        )

        # 旋转X轴标签
        fig.update_xaxes(tickangle=-45)

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_rolling_correlation(
        self,
        factor1: pd.Series,
        factor2: pd.Series,
        window: int = 60,
        title: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> go.Figure:
        """
        绘制滚动相关性曲线

        Args:
            factor1: 因子1序列
            factor2: 因子2序列
            window: 滚动窗口
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            Plotly图表对象
        """
        if title is None:
            title = f"{factor1.name} vs {factor2.name} 滚动相关性"

        # 计算滚动相关性（pandas 2.0+兼容语法）
        rolling_corr = factor1.rolling(window).corr(factor2)

        fig = self.create_figure(
            title=title, x_label="日期", y_label="相关系数"
        )

        # 绘制相关性曲线
        fig.add_trace(
            go.Scatter(
                x=rolling_corr.index,
                y=rolling_corr.values,
                name=f"{window}日相关性",
                line=dict(color=self.get_color("primary"), width=2),
                hovertemplate="日期: %{x}<br>相关性: %{y:.3f}<extra></extra>",
            )
        )

        # 添加平均相关性线
        avg_corr = rolling_corr.mean()
        fig.add_hline(
            y=avg_corr,
            line_dash="dash",
            line_color=self.get_color("benchmark"),
            annotation_text=f"平均: {avg_corr:.3f}",
            annotation_position="right",
        )

        # 添加零线
        fig.add_hline(
            y=0, line_dash="dot", line_color="gray", opacity=0.5
        )

        # 保存图表
        if save_path:
            self.save_figure(fig, save_path)

        return fig
