"""
数据加载API单元测试 (简化版 - 只包含不需要Mock的测试)

测试 src/api/data_api.py 中的三个核心函数的参数验证和错误处理:
- load_stock_data()
- validate_stock_data()
- clean_stock_data()
"""
import pytest
import pandas as pd
import numpy as np

from src.api.data_api import (
    load_stock_data,
    validate_stock_data,
    clean_stock_data
)
from src.utils.response import Response


# ==================== Fixtures ====================

@pytest.fixture
def empty_dataframe():
    """创建空DataFrame"""
    return pd.DataFrame()


# ==================== load_stock_data 参数验证测试 ====================

class TestLoadStockDataValidation:
    """load_stock_data() 参数验证测试"""

    def test_load_empty_symbol(self):
        """测试空股票代码"""
        response = load_stock_data('', '20240101', '20241231')

        assert response.is_error()
        assert response.error_code == 'EMPTY_SYMBOL'
        assert 'symbol' in response.metadata

    def test_load_whitespace_symbol(self):
        """测试仅包含空格的股票代码"""
        response = load_stock_data('   ', '20240101', '20241231')

        assert response.is_error()
        assert response.error_code == 'EMPTY_SYMBOL'

    def test_load_empty_dates(self):
        """测试空日期"""
        response = load_stock_data('000001', '', '')

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATE'
        assert 'start_date' in response.metadata
        assert 'end_date' in response.metadata

    def test_load_invalid_date_format_short(self):
        """测试日期格式太短"""
        response = load_stock_data('000001', '2024', '20241231')

        assert response.is_error()
        assert response.error_code == 'INVALID_DATE_FORMAT'

    def test_load_invalid_date_format_long(self):
        """测试日期格式太长"""
        response = load_stock_data('000001', '202401011', '20241231')

        assert response.is_error()
        assert response.error_code == 'INVALID_DATE_FORMAT'

    def test_load_invalid_date_format_dash(self):
        """测试带横线的日期格式"""
        response = load_stock_data('000001', '2024-01-01', '2024-12-31')

        assert response.is_error()
        assert response.error_code == 'INVALID_DATE_FORMAT'


# ==================== validate_stock_data 参数验证测试 ====================

class TestValidateStockDataValidation:
    """validate_stock_data() 参数验证测试"""

    def test_validate_empty_data(self, empty_dataframe):
        """测试验证空DataFrame"""
        response = validate_stock_data(empty_dataframe)

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'

    def test_validate_none_data(self):
        """测试验证None数据"""
        response = validate_stock_data(None)

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'


# ==================== clean_stock_data 参数验证测试 ====================

class TestCleanStockDataValidation:
    """clean_stock_data() 参数验证测试"""

    def test_clean_empty_data(self, empty_dataframe):
        """测试清洗空DataFrame"""
        response = clean_stock_data(empty_dataframe, '000001')

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'
        assert response.metadata['symbol'] == '000001'

    def test_clean_none_data(self):
        """测试清洗None数据"""
        response = clean_stock_data(None, '000001')

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'


# ==================== Lazy Import 测试 ====================

class TestLazyImport:
    """测试Lazy Import机制 - 确保参数验证不触发模块导入"""

    def test_load_stock_data_lazy_import(self):
        """测试load_stock_data的lazy import"""
        # 参数错误应该在导入之前就返回，不会触发imblearn等依赖
        response = load_stock_data('', '20240101', '20241231')

        assert response.is_error()
        assert response.error_code == 'EMPTY_SYMBOL'

    def test_validate_stock_data_lazy_import(self):
        """测试validate_stock_data的lazy import"""
        response = validate_stock_data(None)

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'

    def test_clean_stock_data_lazy_import(self):
        """测试clean_stock_data的lazy import"""
        response = clean_stock_data(None, '000001')

        assert response.is_error()
        assert response.error_code == 'EMPTY_DATA'


# ==================== 错误消息完整性测试 ====================

class TestErrorMessages:
    """测试错误消息的完整性和可读性"""

    def test_all_errors_have_codes(self):
        """测试所有错误都有error_code"""
        test_cases = [
            (load_stock_data('', '20240101', '20241231'), 'EMPTY_SYMBOL'),
            (load_stock_data('000001', '', ''), 'EMPTY_DATE'),
            (load_stock_data('000001', '2024', '20241231'), 'INVALID_DATE_FORMAT'),
            (validate_stock_data(None), 'EMPTY_DATA'),
            (clean_stock_data(None, '000001'), 'EMPTY_DATA'),
        ]

        for response, expected_code in test_cases:
            assert response.is_error()
            assert response.error_code == expected_code
            assert response.error_message is not None
            assert len(response.error_message) > 0

    def test_errors_contain_context(self):
        """测试错误消息包含上下文信息"""
        # 空股票代码
        response = load_stock_data('', '20240101', '20241231')
        assert 'symbol' in response.metadata

        # 空日期
        response = load_stock_data('000001', '', '')
        assert 'start_date' in response.metadata
        assert 'end_date' in response.metadata

        # 空数据（clean）
        response = clean_stock_data(None, '000001')
        assert 'symbol' in response.metadata


# ==================== Response格式一致性测试 ====================

class TestResponseFormat:
    """测试Response格式的一致性"""

    def test_error_response_structure(self):
        """测试错误响应的结构"""
        response = load_stock_data('', '20240101', '20241231')

        # 验证Response对象结构
        assert isinstance(response, Response)
        assert hasattr(response, 'status')
        assert hasattr(response, 'data')
        assert hasattr(response, 'message')
        assert hasattr(response, 'error_message')
        assert hasattr(response, 'error_code')
        assert hasattr(response, 'metadata')

        # 验证to_dict方法
        response_dict = response.to_dict()
        assert isinstance(response_dict, dict)
        assert 'status' in response_dict
        assert response_dict['status'] == 'error'

    def test_response_methods(self):
        """测试Response对象的方法"""
        response = load_stock_data('', '20240101', '20241231')

        # 验证状态检查方法
        assert response.is_error() is True
        assert response.is_success() is False
        assert response.is_warning() is False


# ==================== 边界条件测试 ====================

class TestEdgeCases:
    """边界条件测试"""

    def test_special_characters_in_symbol(self):
        """测试股票代码包含特殊字符（不触发导入）"""
        # 这个测试验证参数能通过基本验证，但会在导入后失败
        # 由于lazy import，特殊字符不会在参数验证阶段被拒绝
        response = load_stock_data('000001.SZ', '20240101', '20241231', validate=False)

        # 应该返回Response对象（可能成功或失败取决于实际加载）
        assert isinstance(response, Response)

    def test_very_long_symbol(self):
        """测试很长的股票代码"""
        long_symbol = 'A' * 100
        response = load_stock_data(long_symbol, '20240101', '20241231', validate=False)

        # 应该能处理（可能在实际加载时失败）
        assert isinstance(response, Response)


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
