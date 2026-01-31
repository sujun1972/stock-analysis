"""
测试HTML报告生成器
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile

from src.visualization.report_generator import HTMLReportGenerator


class TestHTMLReportGenerator:
    """测试HTMLReportGenerator类"""

    @pytest.fixture
    def generator(self):
        """创建报告生成器实例"""
        return HTMLReportGenerator()

    @pytest.fixture
    def sample_backtest_data(self):
        """创建示例回测数据"""
        dates = pd.date_range(start="2023-01-01", periods=252, freq="D")

        equity_curve = pd.Series(
            np.cumprod(1 + np.random.randn(252) * 0.01 + 0.0003),
            index=dates,
        )

        returns = pd.Series(
            np.random.randn(252) * 0.01 + 0.0003, index=dates
        )

        positions = pd.DataFrame(
            np.random.randn(252, 10) * 0.05,
            index=dates,
            columns=[f"股票{i:03d}" for i in range(10)],
        )
        positions = positions.div(
            positions.abs().sum(axis=1), axis=0
        )  # 归一化

        benchmark_curve = equity_curve * 0.8 + np.random.randn(252) * 0.05
        benchmark_returns = returns * 0.7

        metrics = {
            "总收益率": "45.2%",
            "年化收益率": "18.5%",
            "夏普比率": "1.85",
            "最大回撤": "-12.3%",
            "胜率": "58.7%",
        }

        return {
            "equity_curve": equity_curve,
            "returns": returns,
            "positions": positions,
            "benchmark_curve": benchmark_curve,
            "benchmark_returns": benchmark_returns,
            "metrics": metrics,
        }

    @pytest.fixture
    def sample_factor_data(self):
        """创建示例因子数据"""
        dates = pd.date_range(start="2023-01-01", periods=252, freq="D")

        ic_series = pd.Series(
            np.random.randn(252) * 0.05 + 0.02, index=dates
        )

        quantile_returns = pd.DataFrame(
            {"mean_return": [-0.001, 0.0, 0.001, 0.002, 0.003]},
            index=[f"Q{i}" for i in range(1, 6)],
        )

        quantile_cum_returns = pd.DataFrame(
            {
                f"Q{i}": (
                    1 + pd.Series(np.random.randn(100) * 0.01)
                ).cumprod()
                - 1
                for i in range(1, 6)
            },
            index=pd.date_range(start="2023-01-01", periods=100, freq="D"),
        )

        long_short_returns = pd.Series(
            np.random.randn(252) * 0.01 + 0.0005, index=dates
        )

        metrics = {
            "IC均值": "0.025",
            "IC标准差": "0.048",
            "IR比率": "0.52",
            "IC>0占比": "62.5%",
        }

        return {
            "ic_series": ic_series,
            "quantile_returns": quantile_returns,
            "quantile_cum_returns": quantile_cum_returns,
            "long_short_returns": long_short_returns,
            "metrics": metrics,
        }

    def test_init(self, generator):
        """测试初始化"""
        assert generator is not None
        assert generator.theme == "default_theme"
        assert generator.backtest_viz is not None
        assert generator.factor_viz is not None
        assert generator.corr_viz is not None

    def test_generate_backtest_report(
        self, generator, sample_backtest_data
    ):
        """测试生成回测报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "backtest_report.html"

            generator.generate_backtest_report(
                equity_curve=sample_backtest_data["equity_curve"],
                returns=sample_backtest_data["returns"],
                positions=sample_backtest_data["positions"],
                benchmark_curve=sample_backtest_data["benchmark_curve"],
                benchmark_returns=sample_backtest_data["benchmark_returns"],
                metrics=sample_backtest_data["metrics"],
                strategy_name="测试策略",
                output_path=str(output_path),
            )

            # 检查文件是否生成
            assert output_path.exists()

            # 检查HTML内容
            content = output_path.read_text(encoding="utf-8")
            assert "<!DOCTYPE html>" in content
            assert "测试策略" in content
            assert "plotly" in content.lower()
            assert "回测报告" in content

            # 检查指标是否包含
            for key in sample_backtest_data["metrics"].keys():
                assert key in content

    def test_generate_backtest_report_without_positions(
        self, generator, sample_backtest_data
    ):
        """测试生成回测报告（不包含持仓）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"

            generator.generate_backtest_report(
                equity_curve=sample_backtest_data["equity_curve"],
                returns=sample_backtest_data["returns"],
                strategy_name="简单策略",
                output_path=str(output_path),
            )

            assert output_path.exists()
            content = output_path.read_text(encoding="utf-8")
            assert "简单策略" in content

    def test_generate_backtest_report_without_benchmark(
        self, generator, sample_backtest_data
    ):
        """测试生成回测报告（不包含基准）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"

            generator.generate_backtest_report(
                equity_curve=sample_backtest_data["equity_curve"],
                returns=sample_backtest_data["returns"],
                strategy_name="无基准策略",
                output_path=str(output_path),
            )

            assert output_path.exists()

    def test_generate_backtest_report_without_metrics(
        self, generator, sample_backtest_data
    ):
        """测试生成回测报告（不包含指标）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"

            generator.generate_backtest_report(
                equity_curve=sample_backtest_data["equity_curve"],
                returns=sample_backtest_data["returns"],
                strategy_name="无指标策略",
                output_path=str(output_path),
            )

            assert output_path.exists()

    def test_generate_factor_report(self, generator, sample_factor_data):
        """测试生成因子分析报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "factor_report.html"

            generator.generate_factor_report(
                factor_name="测试因子",
                ic_series=sample_factor_data["ic_series"],
                quantile_returns=sample_factor_data["quantile_returns"],
                quantile_cum_returns=sample_factor_data[
                    "quantile_cum_returns"
                ],
                long_short_returns=sample_factor_data["long_short_returns"],
                metrics=sample_factor_data["metrics"],
                output_path=str(output_path),
            )

            # 检查文件是否生成
            assert output_path.exists()

            # 检查HTML内容
            content = output_path.read_text(encoding="utf-8")
            assert "<!DOCTYPE html>" in content
            assert "测试因子" in content
            assert "因子分析报告" in content

            # 检查指标是否包含
            for key in sample_factor_data["metrics"].keys():
                assert key in content

    def test_generate_factor_report_minimal(
        self, generator, sample_factor_data
    ):
        """测试生成最小化因子报告（仅IC）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "factor_report.html"

            generator.generate_factor_report(
                factor_name="简单因子",
                ic_series=sample_factor_data["ic_series"],
                output_path=str(output_path),
            )

            assert output_path.exists()
            content = output_path.read_text(encoding="utf-8")
            assert "简单因子" in content

    def test_generate_factor_report_without_metrics(
        self, generator, sample_factor_data
    ):
        """测试生成因子报告（不包含指标）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"

            generator.generate_factor_report(
                factor_name="无指标因子",
                ic_series=sample_factor_data["ic_series"],
                output_path=str(output_path),
            )

            assert output_path.exists()

    def test_report_creates_directory(
        self, generator, sample_backtest_data
    ):
        """测试报告自动创建目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = (
                Path(tmpdir) / "subdir1" / "subdir2" / "report.html"
            )

            generator.generate_backtest_report(
                equity_curve=sample_backtest_data["equity_curve"],
                returns=sample_backtest_data["returns"],
                strategy_name="测试",
                output_path=str(output_path),
            )

            assert output_path.exists()
            assert output_path.parent.exists()

    def test_backtest_report_structure(
        self, generator, sample_backtest_data
    ):
        """测试回测报告结构完整性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"

            generator.generate_backtest_report(
                equity_curve=sample_backtest_data["equity_curve"],
                returns=sample_backtest_data["returns"],
                positions=sample_backtest_data["positions"],
                metrics=sample_backtest_data["metrics"],
                strategy_name="结构测试",
                output_path=str(output_path),
            )

            content = output_path.read_text(encoding="utf-8")

            # 检查必需的部分
            assert "<header>" in content
            assert "核心指标" in content or "metrics" in content.lower()
            assert "净值曲线" in content
            assert "回撤分析" in content
            assert "收益分析" in content
            assert "持仓分析" in content
            assert "<footer>" in content

    def test_factor_report_structure(self, generator, sample_factor_data):
        """测试因子报告结构完整性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"

            generator.generate_factor_report(
                factor_name="结构测试因子",
                ic_series=sample_factor_data["ic_series"],
                quantile_returns=sample_factor_data["quantile_returns"],
                long_short_returns=sample_factor_data["long_short_returns"],
                metrics=sample_factor_data["metrics"],
                output_path=str(output_path),
            )

            content = output_path.read_text(encoding="utf-8")

            # 检查必需的部分
            assert "<header>" in content
            assert "IC分析" in content
            assert "分层回测" in content or "quantile" in content.lower()
            assert "多空组合" in content
            assert "<footer>" in content

    def test_report_plotly_cdn(self, generator, sample_backtest_data):
        """测试报告包含Plotly CDN"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"

            generator.generate_backtest_report(
                equity_curve=sample_backtest_data["equity_curve"],
                returns=sample_backtest_data["returns"],
                strategy_name="CDN测试",
                output_path=str(output_path),
            )

            content = output_path.read_text(encoding="utf-8")

            # 应该包含Plotly CDN链接
            assert "cdn.plot.ly" in content or "plotly" in content.lower()

    def test_report_css_styling(self, generator, sample_backtest_data):
        """测试报告包含CSS样式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"

            generator.generate_backtest_report(
                equity_curve=sample_backtest_data["equity_curve"],
                returns=sample_backtest_data["returns"],
                strategy_name="样式测试",
                output_path=str(output_path),
            )

            content = output_path.read_text(encoding="utf-8")

            # 应该包含CSS样式
            assert "<style>" in content
            assert "</style>" in content
            assert ".metric-card" in content or "metric" in content

    def test_report_date_range(self, generator, sample_backtest_data):
        """测试报告包含日期范围"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"

            generator.generate_backtest_report(
                equity_curve=sample_backtest_data["equity_curve"],
                returns=sample_backtest_data["returns"],
                strategy_name="日期测试",
                output_path=str(output_path),
            )

            content = output_path.read_text(encoding="utf-8")

            # 应该包含开始和结束日期
            assert "2023-01-01" in content or "2023" in content

    def test_dark_theme_generator(self, sample_backtest_data):
        """测试暗色主题报告生成器"""
        dark_generator = HTMLReportGenerator(theme="dark_theme")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"

            dark_generator.generate_backtest_report(
                equity_curve=sample_backtest_data["equity_curve"],
                returns=sample_backtest_data["returns"],
                strategy_name="暗色主题",
                output_path=str(output_path),
            )

            assert output_path.exists()

    def test_multiple_reports_same_directory(
        self, generator, sample_backtest_data, sample_factor_data
    ):
        """测试在同一目录生成多个报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backtest_path = Path(tmpdir) / "backtest.html"
            factor_path = Path(tmpdir) / "factor.html"

            generator.generate_backtest_report(
                equity_curve=sample_backtest_data["equity_curve"],
                returns=sample_backtest_data["returns"],
                strategy_name="策略1",
                output_path=str(backtest_path),
            )

            generator.generate_factor_report(
                factor_name="因子1",
                ic_series=sample_factor_data["ic_series"],
                output_path=str(factor_path),
            )

            assert backtest_path.exists()
            assert factor_path.exists()
