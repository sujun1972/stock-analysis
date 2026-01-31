"""
基础可视化类

提供统一的配色方案、样式配置和通用绘图方法。
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import yaml
import plotly.graph_objects as go
import plotly.io as pio
from loguru import logger


class BaseVisualizer:
    """可视化基类"""

    def __init__(self, theme: str = "default_theme"):
        """
        初始化可视化器

        Args:
            theme: 主题名称，可选 "default_theme" 或 "dark_theme"
        """
        self.theme_name = theme
        self.theme_config = self._load_theme(theme)
        self.colors = self.theme_config["colors"]
        self.style = self.theme_config["style"]

    def _load_theme(self, theme: str) -> Dict[str, Any]:
        """
        加载主题配置

        Args:
            theme: 主题名称

        Returns:
            主题配置字典
        """
        config_path = Path(__file__).parent / "config" / "themes.yaml"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                themes = yaml.safe_load(f)

            if theme not in themes:
                logger.warning(
                    f"Theme '{theme}' not found, using 'default_theme'"
                )
                theme = "default_theme"

            return themes[theme]

        except Exception as e:
            logger.error(f"Failed to load theme config: {e}")
            # 返回默认配置
            return {
                "colors": {
                    "primary": "#1f77b4",
                    "benchmark": "#ff7f0e",
                    "long": "#2ca02c",
                    "short": "#d62728",
                    "positive": "#28a745",
                    "negative": "#dc3545",
                    "neutral": "#6c757d",
                },
                "style": {
                    "figure_size": [12, 6],
                    "dpi": 100,
                    "font_family": "sans-serif",
                    "title_size": 14,
                    "label_size": 12,
                    "legend_size": 10,
                    "grid_alpha": 0.3,
                    "grid_style": "--",
                },
            }

    def get_color(self, color_name: str) -> str:
        """
        获取颜色值

        Args:
            color_name: 颜色名称

        Returns:
            颜色值（十六进制）
        """
        return self.colors.get(color_name, "#000000")

    def get_figure_size(self) -> Tuple[int, int]:
        """
        获取图表尺寸

        Returns:
            (宽度, 高度)
        """
        size = self.style.get("figure_size", [12, 6])
        return tuple(size)

    def create_figure(
        self,
        title: str = "",
        x_label: str = "",
        y_label: str = "",
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> go.Figure:
        """
        创建基础图表对象

        Args:
            title: 图表标题
            x_label: X轴标签
            y_label: Y轴标签
            width: 图表宽度（像素）
            height: 图表高度（像素）

        Returns:
            Plotly图表对象
        """
        # 默认尺寸
        if width is None:
            width = self.style.get("figure_size", [12, 6])[0] * 80
        if height is None:
            height = self.style.get("figure_size", [12, 6])[1] * 80

        # 创建图表
        fig = go.Figure()

        # 应用样式
        fig.update_layout(
            title={
                "text": title,
                "font": {"size": self.style.get("title_size", 14)},
                "x": 0.5,
                "xanchor": "center",
            },
            xaxis_title=x_label,
            yaxis_title=y_label,
            font={
                "family": self.style.get("font_family", "sans-serif"),
                "size": self.style.get("label_size", 12),
            },
            width=width,
            height=height,
            hovermode="x unified",
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99,
                bgcolor="rgba(255, 255, 255, 0.8)",
            ),
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor="rgba(128, 128, 128, {})".format(
                    self.style.get("grid_alpha", 0.3)
                ),
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor="rgba(128, 128, 128, {})".format(
                    self.style.get("grid_alpha", 0.3)
                ),
            ),
        )

        # 如果是暗色主题，应用暗色背景
        if "background" in self.style:
            fig.update_layout(
                plot_bgcolor=self.style["background"],
                paper_bgcolor=self.style["background"],
                font_color=self.style.get("text_color", "#eff0f1"),
            )

        return fig

    def save_figure(
        self,
        fig: go.Figure,
        save_path: str,
        format: str = "html",
        **kwargs,
    ) -> None:
        """
        保存图表

        Args:
            fig: Plotly图表对象
            save_path: 保存路径
            format: 保存格式，可选 "html", "png", "pdf", "svg"
            **kwargs: 额外参数传递给 plotly.io.write_*
        """
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if format == "html":
                fig.write_html(str(save_path), **kwargs)
            elif format == "png":
                fig.write_image(str(save_path), format="png", **kwargs)
            elif format == "pdf":
                fig.write_image(str(save_path), format="pdf", **kwargs)
            elif format == "svg":
                fig.write_image(str(save_path), format="svg", **kwargs)
            else:
                logger.warning(
                    f"Unknown format '{format}', using 'html' instead"
                )
                fig.write_html(str(save_path), **kwargs)

            logger.info(f"Figure saved to {save_path}")

        except Exception as e:
            logger.error(f"Failed to save figure: {e}")
            raise

    def add_trace(
        self,
        fig: go.Figure,
        x: Any,
        y: Any,
        name: str,
        color: Optional[str] = None,
        mode: str = "lines",
        **kwargs,
    ) -> go.Figure:
        """
        添加轨迹到图表

        Args:
            fig: Plotly图表对象
            x: X轴数据
            y: Y轴数据
            name: 轨迹名称
            color: 颜色（可选，如果为None则使用默认颜色）
            mode: 绘图模式，可选 "lines", "markers", "lines+markers"
            **kwargs: 额外参数传递给 go.Scatter

        Returns:
            更新后的图表对象
        """
        trace_kwargs = {
            "x": x,
            "y": y,
            "name": name,
            "mode": mode,
        }

        if color is not None:
            trace_kwargs["line"] = {"color": color}

        trace_kwargs.update(kwargs)
        fig.add_trace(go.Scatter(**trace_kwargs))

        return fig

    def format_percentage(self, value: float, decimals: int = 2) -> str:
        """
        格式化百分比

        Args:
            value: 数值（0.1 表示 10%）
            decimals: 小数位数

        Returns:
            格式化后的字符串
        """
        return f"{value * 100:.{decimals}f}%"

    def format_number(self, value: float, decimals: int = 2) -> str:
        """
        格式化数字

        Args:
            value: 数值
            decimals: 小数位数

        Returns:
            格式化后的字符串
        """
        return f"{value:.{decimals}f}"

    def get_color_scale(
        self, n_colors: int, color_type: str = "sequential"
    ) -> List[str]:
        """
        生成颜色刻度

        Args:
            n_colors: 颜色数量
            color_type: 颜色类型，可选 "sequential", "diverging", "qualitative"

        Returns:
            颜色列表
        """
        if color_type == "sequential":
            # 蓝色渐变
            return [
                f"rgb({int(31 + i * 200 / n_colors)}, "
                f"{int(119 + i * 100 / n_colors)}, "
                f"{int(180 + i * 50 / n_colors)})"
                for i in range(n_colors)
            ]
        elif color_type == "diverging":
            # 红-白-绿渐变
            colors = []
            for i in range(n_colors):
                if i < n_colors / 2:
                    # 红到白
                    ratio = i / (n_colors / 2)
                    colors.append(
                        f"rgb({214}, {39 + int(ratio * 216)}, "
                        f"{40 + int(ratio * 215)})"
                    )
                else:
                    # 白到绿
                    ratio = (i - n_colors / 2) / (n_colors / 2)
                    colors.append(
                        f"rgb({255 - int(ratio * 211)}, "
                        f"{255 - int(ratio * 91)}, "
                        f"{255 - int(ratio * 195)})"
                    )
            return colors
        else:  # qualitative
            # 使用预定义颜色
            base_colors = [
                self.get_color("primary"),
                self.get_color("benchmark"),
                self.get_color("long"),
                self.get_color("short"),
                self.get_color("positive"),
                self.get_color("negative"),
                self.get_color("neutral"),
            ]
            return [base_colors[i % len(base_colors)] for i in range(n_colors)]
