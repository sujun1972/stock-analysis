"""
测试 AkShare 异常类
"""

import pytest
from src.providers.akshare.exceptions import (
    AkShareError,
    AkShareImportError,
    AkShareDataError,
    AkShareRateLimitError,
    AkShareTimeoutError,
    AkShareNetworkError
)


class TestAkShareExceptions:
    """测试 AkShare 异常类层次结构"""

    def test_base_exception(self):
        """测试基础异常类"""
        error = AkShareError("测试错误")
        assert isinstance(error, Exception)
        assert str(error) == "测试错误"

    def test_import_error_inheritance(self):
        """测试导入错误继承关系"""
        error = AkShareImportError("导入失败")
        assert isinstance(error, AkShareError)
        assert isinstance(error, Exception)
        assert str(error) == "导入失败"

    def test_data_error_inheritance(self):
        """测试数据错误继承关系"""
        error = AkShareDataError("数据获取失败")
        assert isinstance(error, AkShareError)
        assert isinstance(error, Exception)

    def test_rate_limit_error_inheritance(self):
        """测试限流错误继承关系"""
        error = AkShareRateLimitError("IP 限流")
        assert isinstance(error, AkShareError)
        assert isinstance(error, Exception)

    def test_timeout_error_inheritance(self):
        """测试超时错误继承关系"""
        error = AkShareTimeoutError("请求超时")
        assert isinstance(error, AkShareError)
        assert isinstance(error, Exception)

    def test_network_error_inheritance(self):
        """测试网络错误继承关系"""
        error = AkShareNetworkError("网络错误")
        assert isinstance(error, AkShareError)
        assert isinstance(error, Exception)

    def test_exception_with_cause(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("原始错误")
            except ValueError as e:
                raise AkShareDataError("包装错误") from e
        except AkShareDataError as error:
            assert str(error) == "包装错误"
            assert isinstance(error.__cause__, ValueError)
            assert str(error.__cause__) == "原始错误"

    def test_raise_and_catch_specific_error(self):
        """测试捕获特定异常"""
        with pytest.raises(AkShareRateLimitError) as exc_info:
            raise AkShareRateLimitError("限流测试")

        assert "限流测试" in str(exc_info.value)

    def test_catch_base_exception(self):
        """测试捕获基类异常"""
        with pytest.raises(AkShareError):
            raise AkShareDataError("数据错误")

    def test_exception_message_empty(self):
        """测试空错误消息"""
        error = AkShareError("")
        assert str(error) == ""

    def test_exception_message_multiline(self):
        """测试多行错误消息"""
        message = """错误详情：
        1. 网络连接失败
        2. 请检查网络设置"""
        error = AkShareNetworkError(message)
        assert "网络连接失败" in str(error)
        assert "网络设置" in str(error)

    def test_all_exceptions_importable(self):
        """测试所有异常都可以导入"""
        exceptions = [
            AkShareError,
            AkShareImportError,
            AkShareDataError,
            AkShareRateLimitError,
            AkShareTimeoutError,
            AkShareNetworkError
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, Exception)
            # 测试实例化
            exc = exc_class("测试")
            assert isinstance(exc, Exception)
