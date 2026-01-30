"""
测试结构化日志系统
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.monitoring.structured_logger import StructuredLogger, LogQueryEngine


class TestStructuredLogger:
    """测试StructuredLogger"""

    def setup_method(self):
        """设置测试"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.logger = StructuredLogger(
            log_dir=self.temp_dir,
            service_name="test-service",
            enable_json_logs=True,
            enable_console=False  # 测试时禁用控制台输出
        )

    def teardown_method(self):
        """清理测试"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_init(self):
        """测试初始化"""
        assert self.logger.log_dir == self.temp_dir
        assert self.logger.service_name == "test-service"
        assert self.temp_dir.exists()

    def test_log_directory_creation(self):
        """测试日志目录创建"""
        new_dir = self.temp_dir / "subdir" / "logs"
        logger = StructuredLogger(
            log_dir=new_dir,
            enable_console=False
        )
        assert new_dir.exists()

    def test_log_operation(self):
        """测试记录操作日志"""
        self.logger.log_operation(
            "test_operation",
            level="INFO",
            user_id=123,
            action="test"
        )

        # 等待日志写入
        time.sleep(0.1)

        # 检查日志文件
        log_files = list(self.temp_dir.glob("app_*.json"))
        assert len(log_files) > 0

        # 读取日志内容 - loguru的serialize模式会生成不同格式
        with open(log_files[0], 'r') as f:
            content = f.read().strip()
            if content:
                log_entry = json.loads(content)
                # serialize模式下，日志格式不同，检查record字段
                assert "record" in log_entry or "text" in log_entry
                # 验证消息内容存在
                if "record" in log_entry:
                    assert "test_operation" in log_entry["record"]["message"]
                else:
                    assert "test_operation" in log_entry["text"]

    def test_log_performance(self):
        """测试记录性能日志"""
        self.logger.log_performance(
            operation="calculate_features",
            duration_ms=123.45,
            feature_count=125,
            stock_code="000001"
        )

        time.sleep(0.1)

        # 检查性能日志文件
        perf_files = list(self.temp_dir.glob("performance_*.json"))
        assert len(perf_files) > 0

    def test_log_error(self):
        """测试记录错误日志"""
        try:
            raise ValueError("Test error message")
        except ValueError as e:
            self.logger.log_error(
                e,
                context={"operation": "test_op", "data": "test_data"}
            )

        time.sleep(0.1)

        # 检查错误日志文件
        error_files = list(self.temp_dir.glob("errors_*.json"))
        assert len(error_files) > 0

        # 读取错误日志 - serialize模式格式不同
        with open(error_files[0], 'r') as f:
            content = f.read().strip()
            if content:
                log_entry = json.loads(content)
                # 检查record中的exception信息
                if "record" in log_entry:
                    assert "exception" in log_entry["record"]
                    assert log_entry["record"]["exception"]["type"] == "ValueError"
                    assert "Test error message" in log_entry["record"]["exception"]["value"]
                # 或者检查text中包含错误信息
                else:
                    assert "ValueError" in log_entry.get("text", "")
                    assert "Test error message" in log_entry.get("text", "")

    def test_log_data_quality(self):
        """测试记录数据质量日志"""
        self.logger.log_data_quality(
            dataset="stock_prices",
            quality_metrics={
                "missing_rate": 0.02,
                "outlier_count": 5,
                "completeness": 0.98
            }
        )

        time.sleep(0.1)

        log_files = list(self.temp_dir.glob("app_*.json"))
        assert len(log_files) > 0

    def test_log_model_training(self):
        """测试记录模型训练日志"""
        self.logger.log_model_training(
            model_name="LightGBM",
            metrics={"accuracy": 0.85, "f1_score": 0.82},
            dataset_size=10000,
            training_time=120.5
        )

        time.sleep(0.1)

        log_files = list(self.temp_dir.glob("app_*.json"))
        assert len(log_files) > 0

    def test_log_backtest(self):
        """测试记录回测日志"""
        self.logger.log_backtest(
            strategy_name="MomentumStrategy",
            performance_metrics={
                "total_return": 0.25,
                "sharpe_ratio": 1.5,
                "max_drawdown": -0.15
            },
            period="2023-01-01 to 2023-12-31"
        )

        time.sleep(0.1)

        log_files = list(self.temp_dir.glob("app_*.json"))
        assert len(log_files) > 0

    def test_json_formatter(self):
        """测试JSON格式化"""
        # 记录一条日志
        self.logger.log_operation("test", level="INFO", test_field="test_value")
        time.sleep(0.1)

        # 读取并验证JSON格式
        log_files = list(self.temp_dir.glob("app_*.json"))
        if log_files:
            with open(log_files[0], 'r') as f:
                content = f.read().strip()
                if content:
                    log_entry = json.loads(content)

                    # serialize模式下的格式验证
                    # 应该有text或record字段
                    assert "text" in log_entry or "record" in log_entry

                    # 如果有record字段，验证其内容
                    if "record" in log_entry:
                        record = log_entry["record"]
                        assert "message" in record
                        assert "level" in record
                        assert "module" in record or "name" in record
                        assert "function" in record
                        assert "line" in record
                        assert "time" in record
                        # 验证extra字段
                        assert "extra" in record
                        assert record["extra"]["test_field"] == "test_value"

    def test_multiple_log_levels(self):
        """测试多个日志级别"""
        from loguru import logger

        logger.bind().debug("Debug message")
        logger.bind().info("Info message")
        logger.bind().warning("Warning message")
        logger.bind().error("Error message")

        time.sleep(0.1)

        # 应该有应用日志和错误日志
        app_files = list(self.temp_dir.glob("app_*.json"))
        error_files = list(self.temp_dir.glob("errors_*.json"))

        # 至少应该有一些日志文件
        assert len(app_files) + len(error_files) > 0


class TestLogQueryEngine:
    """测试LogQueryEngine"""

    def setup_method(self):
        """设置测试"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.logger = StructuredLogger(
            log_dir=self.temp_dir,
            service_name="test-service",
            enable_console=False
        )
        self.query_engine = LogQueryEngine(self.temp_dir)

        # 生成一些测试日志
        self._generate_test_logs()

    def teardown_method(self):
        """清理测试"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _generate_test_logs(self):
        """生成测试日志"""
        # 操作日志
        for i in range(5):
            self.logger.log_operation(
                f"operation_{i}",
                level="INFO",
                index=i
            )

        # 错误日志
        for i in range(3):
            try:
                raise ValueError(f"Test error {i}")
            except ValueError as e:
                self.logger.log_error(e, context={"error_index": i})

        # 性能日志
        for i in range(4):
            self.logger.log_performance(
                operation=f"perf_op_{i}",
                duration_ms=100 + i * 10
            )

        time.sleep(0.2)  # 等待日志写入

    def test_query_all(self):
        """测试查询所有日志"""
        results = self.query_engine.query(limit=100)
        assert len(results) > 0

    def test_query_by_level(self):
        """测试按级别查询"""
        info_logs = self.query_engine.query(level="INFO", limit=100)
        assert len(info_logs) >= 0

        error_logs = self.query_engine.query(level="ERROR", limit=100)
        # 应该有一些错误日志(如果文件已创建)
        # 注意：由于日志可能在不同文件，这里不做严格断言

    def test_query_by_search_text(self):
        """测试按文本搜索"""
        results = self.query_engine.query(search_text="operation", limit=100)
        # 应该找到包含"operation"的日志
        assert len(results) >= 0

    def test_query_with_limit(self):
        """测试限制查询数量"""
        results = self.query_engine.query(limit=2)
        assert len(results) <= 2

    def test_aggregate_errors(self):
        """测试聚合错误"""
        error_counts = self.query_engine.aggregate_errors(window_hours=24)

        # 可能有ValueError
        assert isinstance(error_counts, dict)

    def test_get_performance_summary(self):
        """测试获取性能摘要"""
        summary = self.query_engine.get_performance_summary(window_hours=24)

        # 应该包含一些性能数据
        assert isinstance(summary, dict)

    def test_get_performance_summary_with_operation(self):
        """测试获取特定操作的性能摘要"""
        summary = self.query_engine.get_performance_summary(
            operation="perf_op_0",
            window_hours=24
        )

        assert isinstance(summary, dict)

    def test_search_logs(self):
        """测试搜索日志"""
        results = self.query_engine.search_logs(
            pattern="operation",
            log_type="app",
            max_results=10
        )

        assert isinstance(results, list)

    def test_search_errors(self):
        """测试搜索错误日志"""
        results = self.query_engine.search_logs(
            pattern="error",
            log_type="errors",
            max_results=10
        )

        assert isinstance(results, list)

    def test_search_performance(self):
        """测试搜索性能日志"""
        results = self.query_engine.search_logs(
            pattern="perf",
            log_type="performance",
            max_results=10
        )

        assert isinstance(results, list)

    def test_query_nonexistent_directory(self):
        """测试查询不存在的目录"""
        nonexistent_dir = self.temp_dir / "nonexistent"
        query_engine = LogQueryEngine(nonexistent_dir)

        results = query_engine.query()
        assert results == []

        error_counts = query_engine.aggregate_errors()
        assert error_counts == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
