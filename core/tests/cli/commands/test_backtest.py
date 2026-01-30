"""
测试backtest命令
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from click.testing import CliRunner
import pandas as pd
import numpy as np

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.cli.commands.backtest import backtest, calculate_performance_metrics


class TestCalculatePerformanceMetrics:
    """测试calculate_performance_metrics函数"""

    def test_basic_metrics(self):
        """测试基本指标计算"""
        portfolio_value = pd.Series([1000000, 1010000, 1020000, 1015000, 1030000])
        daily_returns = pd.Series([0.0, 0.01, 0.01, -0.005, 0.015])

        metrics = calculate_performance_metrics(portfolio_value, daily_returns)

        assert "总收益率" in metrics
        assert "年化收益率" in metrics
        assert "波动率" in metrics
        assert "夏普比率" in metrics
        assert "最大回撤" in metrics
        assert "胜率" in metrics

    def test_positive_returns(self):
        """测试正收益"""
        portfolio_value = pd.Series([1000000] * 100)
        portfolio_value = portfolio_value * (1 + pd.Series(np.random.uniform(0, 0.01, 100))).cumprod()
        daily_returns = portfolio_value.pct_change().fillna(0)

        metrics = calculate_performance_metrics(portfolio_value, daily_returns)

        assert metrics["总收益率"] > 0
        assert metrics["胜率"] >= 0

    def test_negative_returns(self):
        """测试负收益"""
        portfolio_value = pd.Series([1000000, 990000, 980000, 970000])
        daily_returns = pd.Series([0.0, -0.01, -0.01, -0.01])

        metrics = calculate_performance_metrics(portfolio_value, daily_returns)

        assert metrics["总收益率"] < 0
        assert metrics["最大回撤"] < 0


@pytest.mark.skip(reason="需要实现BacktestEngine类")
class TestBacktestCommand:
    """测试backtest命令"""

    def test_backtest_help(self, cli_runner):
        """测试help信息"""
        result = cli_runner.invoke(backtest, ["--help"])
        assert result.exit_code == 0
        assert "回测" in result.output or "backtest" in result.output.lower()

    @patch("src.cli.commands.backtest.BacktestEngine")
    def test_backtest_momentum_strategy(self, mock_engine_class, cli_runner):
        """测试动量策略回测"""
        # Mock回测引擎
        mock_engine = MagicMock()
        mock_results = {
            "portfolio_value": pd.Series([1000000, 1010000, 1020000]),
            "daily_returns": pd.Series([0.0, 0.01, 0.01]),
            "trades": []
        }
        mock_engine.run_vectorized_backtest.return_value = mock_results
        mock_engine_class.return_value = mock_engine

        result = cli_runner.invoke(
            backtest,
            [
                "--strategy", "momentum",
                "--capital", "1000000"
            ]
        )

        mock_engine.run_vectorized_backtest.assert_called_once()

    @patch("src.cli.commands.backtest.BacktestEngine")
    def test_backtest_with_date_range(self, mock_engine_class, cli_runner):
        """测试指定日期范围"""
        mock_engine = MagicMock()
        mock_results = {
            "portfolio_value": pd.Series([1000000, 1010000]),
            "daily_returns": pd.Series([0.0, 0.01]),
            "trades": []
        }
        mock_engine.run_vectorized_backtest.return_value = mock_results
        mock_engine_class.return_value = mock_engine

        result = cli_runner.invoke(
            backtest,
            [
                "--strategy", "momentum",
                "--start", "2023-01-01",
                "--end", "2023-12-31"
            ]
        )

        mock_engine.run_vectorized_backtest.assert_called_once()

    @patch("src.cli.commands.backtest.BacktestEngine")
    def test_backtest_ml_strategy_without_model(self, mock_engine_class, cli_runner):
        """测试ML策略但未指定模型"""
        result = cli_runner.invoke(
            backtest,
            ["--strategy", "ml"]
        )

        # 应该报错
        assert result.exit_code != 0

    @patch("src.cli.commands.backtest.BacktestEngine")
    def test_backtest_html_report(self, mock_engine_class, cli_runner, temp_dir):
        """测试生成HTML报告"""
        mock_engine = MagicMock()
        mock_results = {
            "portfolio_value": pd.Series([1000000, 1010000]),
            "daily_returns": pd.Series([0.0, 0.01]),
            "trades": []
        }
        mock_engine.run_vectorized_backtest.return_value = mock_results
        mock_engine_class.return_value = mock_engine

        output_file = temp_dir / "backtest.html"

        result = cli_runner.invoke(
            backtest,
            [
                "--strategy", "momentum",
                "--report", "html",
                "--output", str(output_file)
            ]
        )

        # 验证文件被创建
        assert output_file.exists()

    @patch("src.cli.commands.backtest.BacktestEngine")
    def test_backtest_json_report(self, mock_engine_class, cli_runner, temp_dir):
        """测试生成JSON报告"""
        mock_engine = MagicMock()
        mock_results = {
            "portfolio_value": pd.Series([1000000, 1010000]),
            "daily_returns": pd.Series([0.0, 0.01]),
            "trades": []
        }
        mock_engine.run_vectorized_backtest.return_value = mock_results
        mock_engine_class.return_value = mock_engine

        output_file = temp_dir / "backtest.json"

        result = cli_runner.invoke(
            backtest,
            [
                "--strategy", "multi_factor",
                "--report", "json",
                "--output", str(output_file)
            ]
        )

        assert output_file.exists()


@pytest.mark.skip(reason="需要实现BacktestEngine类")
class TestBacktestEdgeCases:
    """测试边界情况"""

    @patch("src.cli.commands.backtest.BacktestEngine")
    def test_backtest_zero_capital(self, mock_engine_class, cli_runner):
        """测试零资金"""
        mock_engine = MagicMock()
        mock_results = {
            "portfolio_value": pd.Series([0, 0]),
            "daily_returns": pd.Series([0.0, 0.0]),
            "trades": []
        }
        mock_engine.run_vectorized_backtest.return_value = mock_results
        mock_engine_class.return_value = mock_engine

        result = cli_runner.invoke(
            backtest,
            [
                "--strategy", "momentum",
                "--capital", "0"
            ]
        )

        # 应该能处理或报错
        assert result.exit_code in [0, 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
