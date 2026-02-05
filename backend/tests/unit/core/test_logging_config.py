"""
日志配置单元测试
测试结构化日志配置、日志轮转和JSON格式输出
"""

import json
import tempfile
from pathlib import Path

import pytest
from loguru import logger

from app.core.logging_config import get_logger, json_serializer, setup_logging


class TestLoggingConfig:
    """日志配置测试"""

    def test_setup_logging(self, tmp_path):
        """测试日志系统初始化"""
        # 临时修改日志路径
        import app.core.logging_config as logging_config

        # 保存原始状态
        original_logger = logger

        try:
            # 设置临时日志目录
            logging_config.log_dir = tmp_path

            # 这应该成功执行而不抛出异常
            setup_logging()

            # 验证日志目录已创建
            assert (Path("logs")).exists()

        finally:
            # 恢复原始状态
            logger.remove()

    def test_get_logger(self):
        """测试获取logger实例"""
        test_logger = get_logger()
        assert test_logger is not None
        # Loguru的logger是单例，应该返回同一个实例
        assert test_logger is logger

    def test_json_serializer(self):
        """测试JSON序列化器"""
        # 模拟一个日志记录
        from datetime import datetime

        mock_record = {
            "time": datetime(2025, 2, 5, 12, 0, 0),
            "level": type("Level", (), {"name": "INFO"}),
            "name": "test_logger",
            "message": "Test message",
            "module": "test_module",
            "function": "test_function",
            "line": 42,
            "extra": {"code": "000001", "rows": 1000},
            "exception": None,
        }

        result = json_serializer(mock_record)

        # 验证结果是有效的JSON
        parsed = json.loads(result)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert parsed["module"] == "test_module"
        assert parsed["function"] == "test_function"
        assert parsed["line"] == 42
        assert parsed["context"]["code"] == "000001"
        assert parsed["context"]["rows"] == 1000

    def test_json_serializer_with_exception(self):
        """测试带异常的JSON序列化"""
        from datetime import datetime

        # 创建一个模拟异常
        try:
            raise ValueError("Test error")
        except ValueError as e:
            import sys

            exc_info = sys.exc_info()

            # 模拟异常记录
            mock_record = {
                "time": datetime(2025, 2, 5, 12, 0, 0),
                "level": type("Level", (), {"name": "ERROR"}),
                "name": "test_logger",
                "message": "Error occurred",
                "module": "test_module",
                "function": "test_function",
                "line": 42,
                "extra": {},
                "exception": type(
                    "Exception",
                    (),
                    {
                        "type": type(e),
                        "value": e,
                        "traceback": "Traceback (most recent call last)...",
                    },
                ),
            }

            result = json_serializer(mock_record)
            parsed = json.loads(result)

            # 验证异常信息被正确记录
            assert "exception" in parsed
            assert parsed["exception"]["type"] == "ValueError"
            assert parsed["exception"]["value"] == "Test error"

    def test_structured_logging(self, tmp_path):
        """测试结构化日志记录"""
        # 创建临时日志文件
        log_file = tmp_path / "test.json"

        # 移除所有现有处理器
        logger.remove()

        # 添加临时日志处理器（使用 serialize=True）
        logger.add(
            str(log_file),
            serialize=True,
            level="INFO",
        )

        # 记录带上下文的日志
        logger.bind(code="000001", rows=1000, duration_ms=50).info("Stock data fetched")

        # 读取日志文件
        with open(log_file, "r", encoding="utf-8") as f:
            log_line = f.readline()
            log_entry = json.loads(log_line)

        # 验证日志内容（Loguru 的 serialize 使用 "text" 字段而不是 "message"）
        assert log_entry["record"]["level"]["name"] == "INFO"
        assert "Stock data fetched" in log_entry["text"]
        assert log_entry["record"]["message"] == "Stock data fetched"
        assert log_entry["record"]["extra"]["code"] == "000001"
        assert log_entry["record"]["extra"]["rows"] == 1000
        assert log_entry["record"]["extra"]["duration_ms"] == 50

        # 清理
        logger.remove()

    def test_performance_logging(self, tmp_path):
        """测试性能日志标记"""
        log_file = tmp_path / "performance.json"

        # 移除所有现有处理器
        logger.remove()

        # 添加性能日志处理器（只记录带performance标记的日志）
        logger.add(
            str(log_file),
            serialize=True,
            filter=lambda record: "performance" in record["extra"],
            level="INFO",
        )

        # 记录普通日志（不应该被记录）
        logger.info("Normal log")

        # 记录性能日志（应该被记录）
        logger.bind(performance=True, duration_ms=150).info("API request completed")

        # 读取日志文件
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 应该只有一条日志（性能日志）
        assert len(lines) == 1

        log_entry = json.loads(lines[0])
        assert "API request completed" in log_entry["text"]
        assert log_entry["record"]["message"] == "API request completed"
        assert log_entry["record"]["extra"]["performance"] is True
        assert log_entry["record"]["extra"]["duration_ms"] == 150

        # 清理
        logger.remove()

    def test_log_levels(self, tmp_path):
        """测试不同日志级别"""
        log_file = tmp_path / "levels.json"

        logger.remove()
        logger.add(str(log_file), serialize=True, level="DEBUG")

        # 记录不同级别的日志
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # 读取所有日志
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 4

        levels = [json.loads(line)["record"]["level"]["name"] for line in lines]
        assert levels == ["DEBUG", "INFO", "WARNING", "ERROR"]

        # 清理
        logger.remove()

    def test_log_with_chinese_characters(self, tmp_path):
        """测试中文字符日志"""
        log_file = tmp_path / "chinese.json"

        logger.remove()
        logger.add(str(log_file), serialize=True, level="INFO", encoding="utf-8")

        # 记录包含中文的日志
        logger.bind(stock_name="平安银行", market="深圳").info("获取股票数据成功")

        with open(log_file, "r", encoding="utf-8") as f:
            log_entry = json.loads(f.readline())

        assert "获取股票数据成功" in log_entry["text"]
        assert log_entry["record"]["message"] == "获取股票数据成功"
        assert log_entry["record"]["extra"]["stock_name"] == "平安银行"
        assert log_entry["record"]["extra"]["market"] == "深圳"

        # 清理
        logger.remove()


class TestLoggerIntegration:
    """日志集成测试"""

    def test_logger_in_application_context(self):
        """测试在应用上下文中使用logger"""
        test_logger = get_logger()

        # 应该能够正常记录日志而不抛出异常
        test_logger.info("Application started")
        test_logger.bind(user_id=123).info("User logged in")
        test_logger.error("An error occurred")

    def test_multiple_bindings(self, tmp_path):
        """测试多个绑定"""
        log_file = tmp_path / "bindings.json"

        logger.remove()
        logger.add(str(log_file), serialize=True, level="INFO")

        # 链式绑定多个上下文
        logger.bind(request_id="abc123", user_id=456, endpoint="/api/stocks").info(
            "Request received"
        )

        with open(log_file, "r", encoding="utf-8") as f:
            log_entry = json.loads(f.readline())

        extra = log_entry["record"]["extra"]
        assert extra["request_id"] == "abc123"
        assert extra["user_id"] == 456
        assert extra["endpoint"] == "/api/stocks"

        # 清理
        logger.remove()
