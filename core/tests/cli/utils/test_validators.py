"""
测试CLI参数验证工具模块
"""

import pytest
from datetime import datetime
from pathlib import Path
import click

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.cli.utils.validators import (
    validate_stock_symbol,
    validate_date_range,
    validate_path,
    StockSymbolType,
    SymbolListType,
    DateRangeType,
)


class TestValidateStockSymbol:
    """测试股票代码验证"""

    def test_valid_symbol(self):
        """测试有效的股票代码"""
        valid_symbols = ["000001", "600000", "300001", "688001"]
        for symbol in valid_symbols:
            result = validate_stock_symbol(symbol)
            assert result == symbol

    def test_invalid_length(self):
        """测试无效长度"""
        invalid_symbols = ["00001", "0000001", "123", "12"]
        for symbol in invalid_symbols:
            with pytest.raises(click.BadParameter):
                validate_stock_symbol(symbol)

    def test_invalid_characters(self):
        """测试无效字符"""
        invalid_symbols = ["00000a", "60000x", "SH600000", "abc123"]
        for symbol in invalid_symbols:
            with pytest.raises(click.BadParameter):
                validate_stock_symbol(symbol)

    def test_with_whitespace(self):
        """测试带空白字符的代码"""
        result = validate_stock_symbol("  000001  ")
        assert result == "000001"

    def test_empty_string(self):
        """测试空字符串"""
        with pytest.raises(click.BadParameter):
            validate_stock_symbol("")

    def test_none_value(self):
        """测试None值"""
        with pytest.raises((click.BadParameter, AttributeError)):
            validate_stock_symbol(None)


class TestValidateDateRange:
    """测试日期范围验证"""

    def test_valid_range(self):
        """测试有效的日期范围"""
        start = datetime(2023, 1, 1)
        end = datetime(2023, 12, 31)
        start_result, end_result = validate_date_range(start, end)
        assert start_result == start
        assert end_result == end

    def test_same_date(self):
        """测试相同日期"""
        date = datetime(2023, 6, 1)
        start_result, end_result = validate_date_range(date, date)
        assert start_result == date
        assert end_result == date

    def test_reversed_range(self):
        """测试反向日期范围"""
        start = datetime(2023, 12, 31)
        end = datetime(2023, 1, 1)
        with pytest.raises(click.BadParameter):
            validate_date_range(start, end)

    def test_none_start(self):
        """测试start为None"""
        end = datetime(2023, 12, 31)
        start_result, end_result = validate_date_range(None, end)
        assert start_result is None
        assert end_result == end

    def test_none_end(self):
        """测试end为None"""
        start = datetime(2023, 1, 1)
        start_result, end_result = validate_date_range(start, None)
        assert start_result == start
        assert end_result is None

    def test_both_none(self):
        """测试都为None"""
        start_result, end_result = validate_date_range(None, None)
        assert start_result is None
        assert end_result is None

    def test_future_dates(self):
        """测试未来日期"""
        start = datetime(2030, 1, 1)
        end = datetime(2030, 12, 31)
        # 应该允许未来日期（某些场景可能需要）
        start_result, end_result = validate_date_range(start, end)
        assert start_result == start
        assert end_result == end


class TestValidatePath:
    """测试路径验证"""

    def test_valid_existing_path(self, tmp_path):
        """测试有效的存在路径"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        result = validate_path(str(test_file), must_exist=True)
        assert result == Path(test_file)

    def test_valid_non_existing_path(self, tmp_path):
        """测试有效的不存在路径"""
        test_path = tmp_path / "new_file.txt"
        result = validate_path(str(test_path), must_exist=False)
        assert result == test_path

    def test_must_exist_but_not_exists(self, tmp_path):
        """测试要求存在但实际不存在"""
        test_path = tmp_path / "not_exists.txt"
        with pytest.raises(click.BadParameter):
            validate_path(str(test_path), must_exist=True)

    def test_directory_validation(self, tmp_path):
        """测试目录验证"""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # 验证目录存在
        result = validate_path(str(test_dir), must_exist=True, is_dir=True)
        assert result == test_dir

    def test_file_validation(self, tmp_path):
        """测试文件验证"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        result = validate_path(str(test_file), must_exist=True, is_dir=False)
        assert result == test_file

    def test_is_dir_but_got_file(self, tmp_path):
        """测试期望目录但得到文件"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        with pytest.raises(click.BadParameter):
            validate_path(str(test_file), must_exist=True, is_dir=True)

    def test_is_file_but_got_dir(self, tmp_path):
        """测试期望文件但得到目录"""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        with pytest.raises(click.BadParameter):
            validate_path(str(test_dir), must_exist=True, is_dir=False)


class TestStockSymbolType:
    """测试StockSymbolType类"""

    def test_convert_valid(self):
        """测试转换有效代码"""
        symbol_type = StockSymbolType()
        result = symbol_type.convert("000001", None, None)
        assert result == "000001"

    def test_convert_invalid(self):
        """测试转换无效代码"""
        symbol_type = StockSymbolType()
        with pytest.raises(click.BadParameter):
            symbol_type.convert("invalid", None, None)

    def test_name(self):
        """测试类型名称"""
        symbol_type = StockSymbolType()
        assert symbol_type.name == "STOCK_SYMBOL"


class TestSymbolListType:
    """测试SymbolListType类"""

    def test_convert_single_symbol(self):
        """测试单个代码"""
        list_type = SymbolListType()
        result = list_type.convert("000001", None, None)
        assert result == ["000001"]

    def test_convert_multiple_symbols(self):
        """测试多个代码"""
        list_type = SymbolListType()
        result = list_type.convert("000001,600000,300001", None, None)
        assert result == ["000001", "600000", "300001"]

    def test_convert_with_spaces(self):
        """测试带空格的代码列表"""
        list_type = SymbolListType()
        result = list_type.convert(" 000001 , 600000 , 300001 ", None, None)
        assert result == ["000001", "600000", "300001"]

    def test_convert_all(self):
        """测试'all'关键字"""
        list_type = SymbolListType()
        result = list_type.convert("all", None, None)
        assert result == "all"

    def test_convert_invalid_in_list(self):
        """测试列表中包含无效代码"""
        list_type = SymbolListType()
        with pytest.raises(click.BadParameter):
            list_type.convert("000001,invalid,600000", None, None)

    def test_convert_empty_string(self):
        """测试空字符串"""
        list_type = SymbolListType()
        with pytest.raises(click.BadParameter):
            list_type.convert("", None, None)

    def test_name(self):
        """测试类型名称"""
        list_type = SymbolListType()
        assert list_type.name == "SYMBOL_LIST"


class TestDateRangeType:
    """测试DateRangeType类"""

    def test_convert_valid_range(self):
        """测试有效的日期范围"""
        range_type = DateRangeType()
        result = range_type.convert("2023-01-01:2023-12-31", None, None)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] == datetime(2023, 1, 1)
        assert result[1] == datetime(2023, 12, 31)

    def test_convert_single_date(self):
        """测试单个日期"""
        range_type = DateRangeType()
        result = range_type.convert("2023-06-15", None, None)
        assert isinstance(result, tuple)
        assert result[0] == datetime(2023, 6, 15)
        assert result[1] == datetime(2023, 6, 15)

    def test_convert_invalid_format(self):
        """测试无效格式"""
        range_type = DateRangeType()
        with pytest.raises(click.BadParameter):
            range_type.convert("invalid-date", None, None)

    def test_convert_reversed_range(self):
        """测试反向范围"""
        range_type = DateRangeType()
        with pytest.raises(click.BadParameter):
            range_type.convert("2023-12-31:2023-01-01", None, None)

    def test_name(self):
        """测试类型名称"""
        range_type = DateRangeType()
        assert range_type.name == "DATE_RANGE"


class TestEdgeCases:
    """测试边界情况"""

    def test_symbol_with_leading_zeros(self):
        """测试带前导零的代码"""
        result = validate_stock_symbol("000001")
        assert result == "000001"

    def test_symbol_list_with_duplicates(self):
        """测试包含重复代码的列表"""
        list_type = SymbolListType()
        result = list_type.convert("000001,000001,600000", None, None)
        # 应该保留重复项（由调用者决定如何处理）
        assert len(result) == 3

    def test_date_boundary(self):
        """测试日期边界"""
        start = datetime(2023, 1, 1, 0, 0, 0)
        end = datetime(2023, 1, 1, 23, 59, 59)
        start_result, end_result = validate_date_range(start, end)
        assert start_result <= end_result


class TestIntegration:
    """集成测试"""

    def test_full_symbol_validation_flow(self):
        """测试完整的代码验证流程"""
        # 单个代码验证
        symbol = validate_stock_symbol("000001")
        assert symbol == "000001"

        # 列表验证
        list_type = SymbolListType()
        symbols = list_type.convert("000001,600000", None, None)
        assert len(symbols) == 2

    def test_full_date_validation_flow(self):
        """测试完整的日期验证流程"""
        # 单个范围验证
        start = datetime(2023, 1, 1)
        end = datetime(2023, 12, 31)
        start_result, end_result = validate_date_range(start, end)
        assert start_result < end_result

        # DateRangeType验证
        range_type = DateRangeType()
        result = range_type.convert("2023-01-01:2023-12-31", None, None)
        assert isinstance(result, tuple)

    def test_full_path_validation_flow(self, tmp_path):
        """测试完整的路径验证流程"""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        # 验证存在的文件
        result = validate_path(str(test_file), must_exist=True)
        assert result.exists()

        # 验证不存在的文件
        new_file = tmp_path / "new.txt"
        result = validate_path(str(new_file), must_exist=False)
        assert not result.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
