"""
测试基础可视化类
"""

import pytest
import plotly.graph_objects as go
from pathlib import Path
import tempfile

from src.visualization.base_visualizer import BaseVisualizer


class TestBaseVisualizer:
    """测试BaseVisualizer类"""

    @pytest.fixture
    def visualizer(self):
        """创建可视化器实例"""
        return BaseVisualizer(theme="default_theme")

    @pytest.fixture
    def dark_visualizer(self):
        """创建暗色主题可视化器"""
        return BaseVisualizer(theme="dark_theme")

    def test_init_default_theme(self, visualizer):
        """测试默认主题初始化"""
        assert visualizer.theme_name == "default_theme"
        assert "primary" in visualizer.colors
        assert "benchmark" in visualizer.colors
        assert "figure_size" in visualizer.style

    def test_init_dark_theme(self, dark_visualizer):
        """测试暗色主题初始化"""
        assert dark_visualizer.theme_name == "dark_theme"
        assert "background" in dark_visualizer.style
        assert dark_visualizer.style["background"] == "#31363b"

    def test_init_invalid_theme(self):
        """测试无效主题（应回退到默认主题）"""
        viz = BaseVisualizer(theme="invalid_theme")
        assert viz.theme_name == "invalid_theme"
        # 应使用默认配置
        assert viz.colors["primary"] == "#1f77b4"

    def test_get_color(self, visualizer):
        """测试获取颜色"""
        primary = visualizer.get_color("primary")
        assert primary == "#1f77b4"

        benchmark = visualizer.get_color("benchmark")
        assert benchmark == "#ff7f0e"

        # 测试不存在的颜色
        invalid = visualizer.get_color("nonexistent")
        assert invalid == "#000000"  # 默认黑色

    def test_get_figure_size(self, visualizer):
        """测试获取图表尺寸"""
        size = visualizer.get_figure_size()
        assert isinstance(size, tuple)
        assert len(size) == 2
        assert size == (12, 6)

    def test_create_figure(self, visualizer):
        """测试创建基础图表"""
        fig = visualizer.create_figure(
            title="测试图表",
            x_label="X轴",
            y_label="Y轴",
            width=800,
            height=600,
        )

        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "测试图表"
        assert fig.layout.xaxis.title.text == "X轴"
        assert fig.layout.yaxis.title.text == "Y轴"
        assert fig.layout.width == 800
        assert fig.layout.height == 600

    def test_create_figure_default_size(self, visualizer):
        """测试创建图表（默认尺寸）"""
        fig = visualizer.create_figure(title="测试")

        # 默认尺寸应该是 figure_size * 80
        assert fig.layout.width == 12 * 80
        assert fig.layout.height == 6 * 80

    def test_save_figure_html(self, visualizer):
        """测试保存HTML格式"""
        fig = visualizer.create_figure(title="测试")

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "test.html"
            visualizer.save_figure(fig, str(save_path), format="html")

            assert save_path.exists()
            content = save_path.read_text(encoding="utf-8")
            assert "plotly" in content.lower()
            # Plotly会将中文编码为Unicode转义序列或直接包含中文
            assert "测试" in content or "\\u6d4b\\u8bd5" in content

    def test_save_figure_creates_directory(self, visualizer):
        """测试保存时自动创建目录"""
        fig = visualizer.create_figure(title="测试")

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "subdir1" / "subdir2" / "test.html"
            visualizer.save_figure(fig, str(save_path))

            assert save_path.exists()
            assert save_path.parent.exists()

    def test_add_trace(self, visualizer):
        """测试添加轨迹"""
        fig = visualizer.create_figure()

        x = [1, 2, 3, 4, 5]
        y = [10, 15, 13, 17, 20]

        fig = visualizer.add_trace(
            fig,
            x=x,
            y=y,
            name="测试线",
            color="#ff0000",
            mode="lines+markers",
        )

        assert len(fig.data) == 1
        assert fig.data[0].name == "测试线"
        assert fig.data[0].mode == "lines+markers"
        assert fig.data[0].line.color == "#ff0000"

    def test_add_trace_default_color(self, visualizer):
        """测试添加轨迹（默认颜色）"""
        fig = visualizer.create_figure()

        x = [1, 2, 3]
        y = [10, 20, 15]

        fig = visualizer.add_trace(fig, x=x, y=y, name="测试")

        assert len(fig.data) == 1
        # 应该没有设置颜色（使用Plotly默认）
        assert fig.data[0].name == "测试"

    def test_format_percentage(self, visualizer):
        """测试百分比格式化"""
        assert visualizer.format_percentage(0.1234) == "12.34%"
        assert visualizer.format_percentage(0.1234, decimals=1) == "12.3%"
        assert visualizer.format_percentage(-0.056, decimals=2) == "-5.60%"
        assert visualizer.format_percentage(1.0) == "100.00%"

    def test_format_number(self, visualizer):
        """测试数字格式化"""
        assert visualizer.format_number(123.456) == "123.46"
        assert visualizer.format_number(123.456, decimals=1) == "123.5"
        assert visualizer.format_number(-0.123, decimals=3) == "-0.123"

    def test_get_color_scale_sequential(self, visualizer):
        """测试顺序色阶"""
        colors = visualizer.get_color_scale(5, "sequential")

        assert len(colors) == 5
        assert all(color.startswith("rgb(") for color in colors)

    def test_get_color_scale_diverging(self, visualizer):
        """测试发散色阶"""
        colors = visualizer.get_color_scale(10, "diverging")

        assert len(colors) == 10
        assert all(color.startswith("rgb(") for color in colors)

    def test_get_color_scale_qualitative(self, visualizer):
        """测试分类色阶"""
        colors = visualizer.get_color_scale(5, "qualitative")

        assert len(colors) == 5
        # 应该使用预定义颜色
        assert visualizer.get_color("primary") in colors

    def test_get_color_scale_large_n(self, visualizer):
        """测试大数量色阶"""
        colors = visualizer.get_color_scale(20, "qualitative")

        assert len(colors) == 20
        # 应该循环使用颜色

    def test_dark_theme_background(self, dark_visualizer):
        """测试暗色主题背景"""
        fig = dark_visualizer.create_figure(title="暗色主题测试")

        assert fig.layout.plot_bgcolor == "#31363b"
        assert fig.layout.paper_bgcolor == "#31363b"
        assert fig.layout.font.color == "#eff0f1"

    def test_theme_config_structure(self, visualizer):
        """测试主题配置结构"""
        assert "colors" in visualizer.theme_config
        assert "style" in visualizer.theme_config

        # 检查必需的颜色
        required_colors = [
            "primary",
            "benchmark",
            "long",
            "short",
            "positive",
            "negative",
            "neutral",
        ]
        for color in required_colors:
            assert color in visualizer.colors

        # 检查必需的样式
        required_styles = [
            "figure_size",
            "dpi",
            "font_family",
            "title_size",
            "label_size",
        ]
        for style in required_styles:
            assert style in visualizer.style
