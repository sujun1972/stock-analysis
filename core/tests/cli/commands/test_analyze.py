"""
测试analyze命令
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

from src.cli.commands.analyze import analyze, load_factor_data


class TestLoadFactorData:
    """测试load_factor_data函数"""

    def test_load_factor_data_basic(self):
        """测试基本加载"""
        result = load_factor_data("MOM_20")

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_load_factor_data_with_dates(self):
        """测试指定日期范围"""
        from datetime import datetime
        start = datetime(2023, 1, 1)
        end = datetime(2023, 12, 31)

        result = load_factor_data("VOL_20", start_date=start, end_date=end)

        assert isinstance(result, pd.DataFrame)


class TestAnalyzeCommand:
    """测试analyze命令组"""

    def test_analyze_help(self, cli_runner):
        """测试help信息"""
        result = cli_runner.invoke(analyze, ["--help"])
        assert result.exit_code == 0
        assert "因子" in result.output or "analyze" in result.output.lower()


@pytest.mark.skip(reason="需要实现ICCalculator类")
class TestICCommand:
    """测试ic子命令"""

    def test_ic_help(self, cli_runner):
        """测试ic help信息"""
        result = cli_runner.invoke(analyze, ["ic", "--help"])
        assert result.exit_code == 0
        assert "IC" in result.output or "信息系数" in result.output

    @patch("src.cli.commands.analyze.ICCalculator")
    @patch("src.cli.commands.analyze.load_factor_data")
    def test_ic_basic(self, mock_load, mock_ic_class, cli_runner):
        """测试基本IC计算"""
        # Mock数据
        mock_df = pd.DataFrame({
            "000001": np.random.randn(100),
            "600000": np.random.randn(100)
        })
        mock_load.return_value = mock_df

        # Mock IC计算器
        mock_ic = MagicMock()
        mock_ic.calculate_ic_timeseries.return_value = pd.Series(np.random.randn(100) * 0.05)
        mock_ic_class.return_value = mock_ic

        result = cli_runner.invoke(
            analyze,
            ["ic", "--factor", "MOM_20"]
        )

        mock_load.assert_called()
        mock_ic.calculate_ic_timeseries.assert_called_once()

    @patch("src.cli.commands.analyze.ICCalculator")
    @patch("src.cli.commands.analyze.load_factor_data")
    def test_ic_with_period(self, mock_load, mock_ic_class, cli_runner):
        """测试指定预测周期"""
        mock_df = pd.DataFrame({"000001": np.random.randn(100)})
        mock_load.return_value = mock_df

        mock_ic = MagicMock()
        mock_ic.calculate_ic_timeseries.return_value = pd.Series(np.random.randn(100) * 0.05)
        mock_ic_class.return_value = mock_ic

        result = cli_runner.invoke(
            analyze,
            ["ic", "--factor", "MOM_20", "--period", "10"]
        )

        mock_ic.calculate_ic_timeseries.assert_called_once()


@pytest.mark.skip(reason="需要实现因子分析相关类")
class TestQuantilesCommand:
    """测试quantiles子命令"""

    def test_quantiles_help(self, cli_runner):
        """测试quantiles help信息"""
        result = cli_runner.invoke(analyze, ["quantiles", "--help"])
        assert result.exit_code == 0

    @patch("src.cli.commands.analyze.load_factor_data")
    def test_quantiles_basic(self, mock_load, cli_runner):
        """测试基本分层回测"""
        mock_df = pd.DataFrame({
            "000001": np.random.randn(100),
            "600000": np.random.randn(100)
        })
        mock_load.return_value = mock_df

        result = cli_runner.invoke(
            analyze,
            ["quantiles", "--factor", "MOM_20", "--layers", "5"]
        )

        mock_load.assert_called()

    @patch("src.cli.commands.analyze.load_factor_data")
    def test_quantiles_with_10_layers(self, mock_load, cli_runner):
        """测试10分层"""
        mock_df = pd.DataFrame({
            "000001": np.random.randn(100)
        })
        mock_load.return_value = mock_df

        result = cli_runner.invoke(
            analyze,
            ["quantiles", "--factor", "VOL_20", "--layers", "10"]
        )

        mock_load.assert_called()


@pytest.mark.skip(reason="需要实现因子分析相关类")
class TestCorrCommand:
    """测试corr子命令"""

    def test_corr_help(self, cli_runner):
        """测试corr help信息"""
        result = cli_runner.invoke(analyze, ["corr", "--help"])
        assert result.exit_code == 0

    @patch("src.cli.commands.analyze.load_factor_data")
    def test_corr_multiple_factors(self, mock_load, cli_runner):
        """测试多因子相关性"""
        mock_df = pd.DataFrame(np.random.randn(100, 10))
        mock_load.return_value = mock_df

        result = cli_runner.invoke(
            analyze,
            ["corr", "--factors", "MOM_20,VOL_20,RSI_14"]
        )

        # 应该加载3次
        assert mock_load.call_count == 3

    @patch("src.cli.commands.analyze.load_factor_data")
    def test_corr_all_factors(self, mock_load, cli_runner):
        """测试所有因子相关性"""
        mock_df = pd.DataFrame(np.random.randn(100, 10))
        mock_load.return_value = mock_df

        result = cli_runner.invoke(
            analyze,
            ["corr", "--factors", "all"]
        )

        # 应该加载多次
        assert mock_load.call_count >= 1


@pytest.mark.skip(reason="需要实现因子分析相关类")
class TestBatchCommand:
    """测试batch子命令"""

    def test_batch_help(self, cli_runner):
        """测试batch help信息"""
        result = cli_runner.invoke(analyze, ["batch", "--help"])
        assert result.exit_code == 0

    @patch("src.cli.commands.analyze.load_factor_data")
    def test_batch_basic(self, mock_load, cli_runner):
        """测试批量分析"""
        mock_df = pd.DataFrame(np.random.randn(100, 10))
        mock_load.return_value = mock_df

        result = cli_runner.invoke(
            analyze,
            ["batch"]
        )

        # 应该加载多个因子
        assert mock_load.call_count >= 1

    @patch("src.cli.commands.analyze.load_factor_data")
    def test_batch_with_output(self, mock_load, cli_runner, temp_dir):
        """测试批量分析并保存报告"""
        mock_df = pd.DataFrame(np.random.randn(100, 10))
        mock_load.return_value = mock_df

        output_file = temp_dir / "analysis.html"

        result = cli_runner.invoke(
            analyze,
            ["batch", "--output", str(output_file)]
        )

        # 验证文件被创建
        assert output_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
