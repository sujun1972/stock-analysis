"""
测试CLI输出工具模块
"""

import pytest
from io import StringIO
from unittest.mock import patch, MagicMock
from rich.console import Console

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.cli.utils.output import (
    get_console,
    create_console,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_table,
    format_percentage,
    format_number,
)


class TestGetConsole:
    """测试get_console函数"""

    def test_get_console_returns_console(self):
        """测试get_console返回Console实例"""
        console = get_console()
        assert isinstance(console, Console)

    def test_get_console_returns_same_instance(self):
        """测试get_console返回单例"""
        console1 = get_console()
        console2 = get_console()
        assert console1 is console2


class TestCreateConsole:
    """测试create_console函数"""

    def test_create_console_default(self):
        """测试默认创建Console"""
        console = create_console()
        assert isinstance(console, Console)

    def test_create_console_no_color(self):
        """测试禁用彩色输出"""
        console = create_console(no_color=True, force_new=True)
        assert console.no_color is True

    def test_create_console_with_width(self):
        """测试指定宽度"""
        console = create_console(width=100, force_new=True)
        assert console.width == 100


class TestPrintFunctions:
    """测试打印函数"""

    @patch("src.cli.utils.output.get_console")
    def test_print_success(self, mock_get_console):
        """测试成功消息打印"""
        mock_console = MagicMock()
        mock_get_console.return_value = mock_console

        print_success("测试成功")
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "测试成功" in call_args
        assert "✓" in call_args

    @patch("src.cli.utils.output.get_console")
    def test_print_error(self, mock_get_console):
        """测试错误消息打印"""
        mock_console = MagicMock()
        mock_get_console.return_value = mock_console

        print_error("测试错误")
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "测试错误" in call_args
        assert "✗" in call_args

    @patch("src.cli.utils.output.get_console")
    def test_print_warning(self, mock_get_console):
        """测试警告消息打印"""
        mock_console = MagicMock()
        mock_get_console.return_value = mock_console

        print_warning("测试警告")
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "测试警告" in call_args
        assert "⚠" in call_args

    @patch("src.cli.utils.output.get_console")
    def test_print_info(self, mock_get_console):
        """测试信息消息打印"""
        mock_console = MagicMock()
        mock_get_console.return_value = mock_console

        print_info("测试信息")
        mock_console.print.assert_called_once()

    @patch("src.cli.utils.output.get_console")
    def test_print_info_with_bold(self, mock_get_console):
        """测试加粗信息打印"""
        mock_console = MagicMock()
        mock_get_console.return_value = mock_console

        print_info("测试加粗", bold=True)
        mock_console.print.assert_called_once()


class TestPrintTable:
    """测试表格打印"""

    @patch("src.cli.utils.output.get_console")
    def test_print_table_basic(self, mock_get_console):
        """测试基本表格打印"""
        mock_console = MagicMock()
        mock_get_console.return_value = mock_console

        data = {"键1": "值1", "键2": "值2"}
        print_table(data)

        mock_console.print.assert_called_once()
        # 验证传入的是Table对象
        table = mock_console.print.call_args[0][0]
        assert hasattr(table, "add_row")

    @patch("src.cli.utils.output.get_console")
    def test_print_table_with_title(self, mock_get_console):
        """测试带标题的表格打印"""
        mock_console = MagicMock()
        mock_get_console.return_value = mock_console

        data = {"键1": "值1"}
        print_table(data, title="测试标题")

        mock_console.print.assert_called_once()

    @patch("src.cli.utils.output.get_console")
    def test_print_table_empty(self, mock_get_console):
        """测试空数据表格"""
        mock_console = MagicMock()
        mock_get_console.return_value = mock_console

        data = {}
        print_table(data)

        mock_console.print.assert_called_once()


class TestFormatPercentage:
    """测试百分比格式化"""

    def test_format_percentage_positive(self):
        """测试正数格式化"""
        result = format_percentage(0.1234)
        assert "12.34" in result
        assert "%" in result

    def test_format_percentage_negative(self):
        """测试负数格式化"""
        result = format_percentage(-0.05)
        assert "-5.00" in result

    def test_format_percentage_zero(self):
        """测试零值格式化"""
        result = format_percentage(0.0)
        assert "0.00" in result

    def test_format_percentage_custom_decimals(self):
        """测试自定义小数位"""
        result = format_percentage(0.12345, decimals=3)
        assert "12.345" in result

    def test_format_percentage_with_sign(self):
        """测试带符号格式化"""
        result = format_percentage(0.05, show_sign=True)
        assert "+5.00" in result


class TestFormatNumber:
    """测试数字格式化"""

    def test_format_number_integer(self):
        """测试整数格式化"""
        result = format_number(1000)
        assert "1,000" in result or "1000" in result

    def test_format_number_float(self):
        """测试浮点数格式化"""
        result = format_number(1234.5678, decimals=2)
        assert "1,234.57" in result or "1234.57" in result

    def test_format_number_large(self):
        """测试大数字格式化"""
        result = format_number(1000000)
        assert "1,000,000" in result or "1000000" in result

    def test_format_number_zero(self):
        """测试零值格式化"""
        result = format_number(0)
        assert "0" in result

    def test_format_number_negative(self):
        """测试负数格式化"""
        result = format_number(-1234.56, decimals=2)
        assert "-" in result
        assert "1,234.56" in result or "1234.56" in result


class TestIntegration:
    """集成测试"""

    def test_all_print_functions_work(self):
        """测试所有打印函数都能正常工作"""
        # 这个测试只验证函数不会抛出异常
        try:
            print_success("成功")
            print_error("错误")
            print_warning("警告")
            print_info("信息")
            print_table({"测试": "数据"})
        except Exception as e:
            pytest.fail(f"打印函数抛出异常: {e}")

    def test_format_functions_work(self):
        """测试所有格式化函数都能正常工作"""
        try:
            result1 = format_percentage(0.12)
            result2 = format_number(1234.56)
            assert isinstance(result1, str)
            assert isinstance(result2, str)
        except Exception as e:
            pytest.fail(f"格式化函数抛出异常: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
