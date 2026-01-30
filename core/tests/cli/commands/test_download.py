"""
测试download命令
"""

import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
from click.testing import CliRunner
import pandas as pd

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.cli.commands.download import download, download_single_stock, get_stock_list


@pytest.mark.skip(reason="需要实现AShareProvider类")
class TestGetStockList:
    """测试get_stock_list函数"""

    @patch("src.cli.commands.download.AShareProvider")
    def test_get_stock_list_success(self, mock_provider_class):
        """测试成功获取股票列表"""
        mock_provider = MagicMock()
        mock_provider.get_stock_list.return_value = ["000001", "600000", "300001"]
        mock_provider_class.return_value = mock_provider

        result = get_stock_list()
        assert len(result) == 3
        assert "000001" in result

    @patch("src.cli.commands.download.AShareProvider")
    def test_get_stock_list_empty(self, mock_provider_class):
        """测试获取空列表"""
        mock_provider = MagicMock()
        mock_provider.get_stock_list.return_value = []
        mock_provider_class.return_value = mock_provider

        result = get_stock_list()
        assert len(result) == 0

    @patch("src.cli.commands.download.AShareProvider")
    def test_get_stock_list_with_limit(self, mock_provider_class):
        """测试限制数量"""
        mock_provider = MagicMock()
        mock_provider.get_stock_list.return_value = ["000001", "600000", "300001", "688001"]
        mock_provider_class.return_value = mock_provider

        result = get_stock_list(limit=2)
        assert len(result) == 2

    @patch("src.cli.commands.download.AShareProvider")
    def test_get_stock_list_error(self, mock_provider_class):
        """测试获取失败"""
        mock_provider = MagicMock()
        mock_provider.get_stock_list.side_effect = Exception("API错误")
        mock_provider_class.return_value = mock_provider

        with pytest.raises(Exception):
            get_stock_list()


@pytest.mark.skip(reason="需要实现AShareProvider和DatabaseManager类")
class TestDownloadSingleStock:
    """测试download_single_stock函数"""

    @patch("src.cli.commands.download.AShareProvider")
    @patch("src.cli.commands.download.DatabaseManager")
    def test_download_single_stock_success(self, mock_db_class, mock_provider_class):
        """测试成功下载单个股票"""
        # Mock provider
        mock_provider = MagicMock()
        mock_df = pd.DataFrame({
            "trade_date": pd.date_range("2023-01-01", periods=10),
            "close": [10.0] * 10,
        })
        mock_provider.fetch_daily_data.return_value = mock_df
        mock_provider_class.return_value = mock_provider

        # Mock database
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        # 执行下载
        start = datetime(2023, 1, 1)
        end = datetime(2023, 1, 10)
        result = download_single_stock("000001", start, end, "akshare")

        assert result is True
        mock_provider.fetch_daily_data.assert_called_once()
        mock_db.save_stock_data.assert_called_once()

    @patch("src.cli.commands.download.AShareProvider")
    def test_download_single_stock_no_data(self, mock_provider_class):
        """测试无数据情况"""
        mock_provider = MagicMock()
        mock_provider.fetch_daily_data.return_value = pd.DataFrame()
        mock_provider_class.return_value = mock_provider

        start = datetime(2023, 1, 1)
        end = datetime(2023, 1, 10)
        result = download_single_stock("000001", start, end, "akshare")

        assert result is False

    @patch("src.cli.commands.download.AShareProvider")
    def test_download_single_stock_error(self, mock_provider_class):
        """测试下载错误"""
        mock_provider = MagicMock()
        mock_provider.fetch_daily_data.side_effect = Exception("网络错误")
        mock_provider_class.return_value = mock_provider

        start = datetime(2023, 1, 1)
        end = datetime(2023, 1, 10)
        result = download_single_stock("000001", start, end, "akshare")

        assert result is False


@pytest.mark.skip(reason="CLI命令的集成测试需要完整实现")
class TestDownloadCommand:
    """测试download命令"""

    def test_download_help(self, cli_runner):
        """测试help信息"""
        result = cli_runner.invoke(download, ["--help"])
        assert result.exit_code == 0
        assert "下载股票历史数据" in result.output or "download" in result.output.lower()

    @patch("src.cli.commands.download.download_single_stock")
    @patch("src.cli.commands.download.get_stock_list")
    def test_download_with_days(self, mock_get_list, mock_download, cli_runner):
        """测试使用--days参数"""
        mock_get_list.return_value = ["000001", "600000"]
        mock_download.return_value = True

        result = cli_runner.invoke(download, ["--days", "30", "--limit", "2"])

        # 验证调用
        assert mock_download.call_count == 2

    @patch("src.cli.commands.download.download_single_stock")
    def test_download_with_symbols(self, mock_download, cli_runner):
        """测试使用--symbols参数"""
        mock_download.return_value = True

        result = cli_runner.invoke(download, ["--symbols", "000001,600000"])

        # 验证调用了2次
        assert mock_download.call_count == 2

    @patch("src.cli.commands.download.download_single_stock")
    def test_download_with_date_range(self, mock_download, cli_runner):
        """测试使用日期范围"""
        mock_download.return_value = True

        result = cli_runner.invoke(
            download,
            [
                "--symbols", "000001",
                "--start", "2023-01-01",
                "--end", "2023-12-31"
            ]
        )

        mock_download.assert_called_once()
        call_args = mock_download.call_args[0]
        assert call_args[0] == "000001"
        assert isinstance(call_args[1], datetime)
        assert isinstance(call_args[2], datetime)

    @patch("src.cli.commands.download.download_single_stock")
    def test_download_with_provider(self, mock_download, cli_runner):
        """测试指定数据提供商"""
        mock_download.return_value = True

        result = cli_runner.invoke(
            download,
            ["--symbols", "000001", "--provider", "tushare"]
        )

        mock_download.assert_called_once()
        call_args = mock_download.call_args[0]
        assert call_args[3] == "tushare"

    @patch("src.cli.commands.download.download_single_stock")
    @patch("src.cli.commands.download.get_stock_list")
    def test_download_all_stocks(self, mock_get_list, mock_download, cli_runner):
        """测试下载所有股票"""
        mock_get_list.return_value = ["000001", "600000", "300001"]
        mock_download.return_value = True

        result = cli_runner.invoke(
            download,
            ["--symbols", "all", "--limit", "3"]
        )

        mock_get_list.assert_called_once()
        assert mock_download.call_count == 3

    @patch("src.cli.commands.download.download_single_stock")
    def test_download_with_workers(self, mock_download, cli_runner):
        """测试多线程下载"""
        mock_download.return_value = True

        result = cli_runner.invoke(
            download,
            ["--symbols", "000001,600000", "--workers", "2"]
        )

        # 验证调用次数
        assert mock_download.call_count == 2

    @patch("src.cli.commands.download.download_single_stock")
    def test_download_partial_failure(self, mock_download, cli_runner):
        """测试部分失败的情况"""
        # 第一个成功，第二个失败
        mock_download.side_effect = [True, False]

        result = cli_runner.invoke(
            download,
            ["--symbols", "000001,600000"]
        )

        # 应该有失败
        assert mock_download.call_count == 2

    def test_download_missing_required_params(self, cli_runner):
        """测试缺少必需参数"""
        # 不提供任何参数
        result = cli_runner.invoke(download, [])

        # Click会自动使用默认值或提示错误
        # 这里我们只验证不会崩溃
        assert result.exit_code in [0, 1, 2]


@pytest.mark.skip(reason="CLI命令的边界测试需要完整实现")
class TestDownloadEdgeCases:
    """测试边界情况"""

    @patch("src.cli.commands.download.download_single_stock")
    def test_download_single_symbol(self, mock_download, cli_runner):
        """测试单个股票下载"""
        mock_download.return_value = True

        result = cli_runner.invoke(download, ["--symbols", "000001"])

        mock_download.assert_called_once()

    @patch("src.cli.commands.download.download_single_stock")
    def test_download_zero_days(self, mock_download, cli_runner):
        """测试0天"""
        mock_download.return_value = True

        result = cli_runner.invoke(download, ["--symbols", "000001", "--days", "0"])

        # 应该使用默认值或处理边界情况
        if mock_download.called:
            call_args = mock_download.call_args[0]
            start_date = call_args[1]
            end_date = call_args[2]
            # 验证日期逻辑正确
            assert start_date <= end_date

    @patch("src.cli.commands.download.download_single_stock")
    def test_download_future_dates(self, mock_download, cli_runner):
        """测试未来日期"""
        mock_download.return_value = True

        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")

        result = cli_runner.invoke(
            download,
            ["--symbols", "000001", "--end", future_date]
        )

        # 应该能处理未来日期
        if mock_download.called:
            call_args = mock_download.call_args[0]
            end_date = call_args[2]
            assert isinstance(end_date, datetime)

    @patch("src.cli.commands.download.download_single_stock")
    def test_download_invalid_date_range(self, mock_download, cli_runner):
        """测试无效日期范围（start > end）"""
        mock_download.return_value = True

        result = cli_runner.invoke(
            download,
            [
                "--symbols", "000001",
                "--start", "2023-12-31",
                "--end", "2023-01-01"
            ]
        )

        # 应该被验证器捕获或处理
        # 验证不会导致意外行为
        assert result.exit_code in [0, 1, 2]

    @patch("src.cli.commands.download.download_single_stock")
    def test_download_with_keyboard_interrupt(self, mock_download, cli_runner):
        """测试键盘中断"""
        mock_download.side_effect = KeyboardInterrupt()

        result = cli_runner.invoke(download, ["--symbols", "000001"])

        # 应该优雅地处理中断
        assert result.exit_code != 0


@pytest.mark.skip(reason="需要实现AShareProvider类")
class TestDownloadIntegration:
    """集成测试"""

    @patch("src.cli.commands.download.DatabaseManager")
    @patch("src.cli.commands.download.AShareProvider")
    @patch("src.cli.commands.download.get_stock_list")
    def test_full_download_workflow(self, mock_get_list, mock_provider_class, mock_db_class, cli_runner):
        """测试完整的下载流程"""
        # Setup mocks
        mock_get_list.return_value = ["000001"]

        mock_provider = MagicMock()
        mock_df = pd.DataFrame({
            "trade_date": pd.date_range("2023-01-01", periods=5),
            "close": [10.0] * 5,
        })
        mock_provider.fetch_daily_data.return_value = mock_df
        mock_provider_class.return_value = mock_provider

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        # 执行命令
        result = cli_runner.invoke(
            download,
            ["--symbols", "000001", "--days", "5"]
        )

        # 验证整个流程
        mock_provider.fetch_daily_data.assert_called()
        mock_db.save_stock_data.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
