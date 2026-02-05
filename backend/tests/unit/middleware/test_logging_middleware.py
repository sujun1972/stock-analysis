"""
日志中间件单元测试
测试HTTP请求/响应日志记录功能
"""

import json
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from loguru import logger

from app.middleware.logging import LoggingMiddleware, logging_middleware


class TestLoggingMiddleware:
    """日志中间件测试"""

    @pytest.fixture
    def app_with_middleware(self, tmp_path):
        """创建带日志中间件的测试应用"""
        app = FastAPI()

        # 配置临时日志文件
        log_file = tmp_path / "test_requests.json"
        logger.remove()
        logger.add(
            str(log_file),
            serialize=True,
            level="INFO",
        )

        # 添加日志中间件
        app.add_middleware(LoggingMiddleware)

        # 定义测试路由
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        @app.get("/slow")
        async def slow_endpoint():
            import time

            time.sleep(1.1)  # 模拟慢请求
            return {"message": "slow"}

        return app, log_file

    def test_successful_request_logging(self, app_with_middleware):
        """测试成功请求的日志记录"""
        app, log_file = app_with_middleware
        client = TestClient(app)

        # 发送请求
        response = client.get("/test")
        assert response.status_code == 200

        # 读取日志
        with open(log_file, "r", encoding="utf-8") as f:
            logs = [json.loads(line) for line in f.readlines()]

        # 应该有两条日志：请求日志和响应日志
        assert len(logs) >= 2

        # 验证请求日志
        request_log = logs[0]
        assert request_log["record"]["extra"]["method"] == "GET"
        assert request_log["record"]["extra"]["path"] == "/test"

        # 验证响应日志（可能是第二条或更后面的日志）
        response_logs = [log for log in logs if "status_code" in log["record"]["extra"]]
        assert len(response_logs) >= 1
        response_log = response_logs[0]
        assert response_log["record"]["extra"]["status_code"] == 200
        assert "duration_ms" in response_log["record"]["extra"]
        assert response_log["record"]["extra"]["performance"] is True

        # 清理
        logger.remove()

    def test_error_request_logging(self, app_with_middleware):
        """测试错误请求的日志记录"""
        app, log_file = app_with_middleware
        client = TestClient(app, raise_server_exceptions=False)

        # 发送会导致错误的请求
        response = client.get("/error")
        assert response.status_code == 500

        # 读取日志
        with open(log_file, "r", encoding="utf-8") as f:
            logs = [json.loads(line) for line in f.readlines()]

        # 应该有错误日志
        error_logs = [log for log in logs if log["record"]["level"]["name"] == "ERROR"]
        assert len(error_logs) >= 1

        error_log = error_logs[0]
        assert error_log["record"]["extra"]["method"] == "GET"
        assert error_log["record"]["extra"]["path"] == "/error"
        assert "error_type" in error_log["record"]["extra"]

        # 清理
        logger.remove()

    def test_slow_request_warning(self, app_with_middleware):
        """测试慢请求警告"""
        app, log_file = app_with_middleware
        client = TestClient(app)

        # 发送慢请求
        response = client.get("/slow")
        assert response.status_code == 200

        # 读取日志
        with open(log_file, "r", encoding="utf-8") as f:
            logs = [json.loads(line) for line in f.readlines()]

        # 应该有慢请求警告
        warning_logs = [log for log in logs if log["record"]["level"]["name"] == "WARNING"]
        assert len(warning_logs) >= 1

        warning_log = warning_logs[0]
        assert "慢请求警告" in warning_log["record"]["message"]
        assert warning_log["record"]["extra"]["duration_ms"] > 1000

        # 清理
        logger.remove()

    def test_request_context_extraction(self, app_with_middleware, tmp_path):
        """测试请求上下文提取"""
        app, log_file = app_with_middleware
        client = TestClient(app)

        # 发送带自定义请求头的请求
        response = client.get(
            "/test",
            headers={
                "X-Request-ID": "test-request-123",
                "User-Agent": "TestClient/1.0",
            },
        )
        assert response.status_code == 200

        # 读取日志
        with open(log_file, "r", encoding="utf-8") as f:
            logs = [json.loads(line) for line in f.readlines()]

        # 找到请求日志
        request_log = logs[0]
        assert request_log["record"]["extra"]["request_id"] == "test-request-123"
        assert request_log["record"]["extra"]["user_agent"] == "TestClient/1.0"
        assert "client_ip" in request_log["record"]["extra"]

        # 清理
        logger.remove()


class TestLoggingMiddlewareFunction:
    """测试轻量级日志中间件函数"""

    @pytest.fixture
    def app_with_function_middleware(self, tmp_path):
        """创建使用函数式中间件的测试应用"""
        app = FastAPI()

        # 配置临时日志文件
        log_file = tmp_path / "test_function.json"
        logger.remove()
        logger.add(
            str(log_file),
            serialize=True,
            level="INFO",
        )

        # 添加函数式中间件
        app.middleware("http")(logging_middleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        return app, log_file

    def test_function_middleware_logging(self, app_with_function_middleware):
        """测试函数式中间件的日志记录"""
        app, log_file = app_with_function_middleware
        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200

        # 读取日志
        with open(log_file, "r", encoding="utf-8") as f:
            logs = [json.loads(line) for line in f.readlines()]

        # 应该有请求和响应日志
        assert len(logs) >= 2

        # 验证日志包含基本信息
        request_log = logs[0]
        assert "请求" in request_log["record"]["message"]
        assert request_log["record"]["extra"]["method"] == "GET"
        assert request_log["record"]["extra"]["path"] == "/test"

        # 清理
        logger.remove()


class TestLoggingMiddlewareIntegration:
    """日志中间件集成测试"""

    def test_middleware_with_query_params(self, tmp_path):
        """测试带查询参数的请求日志"""
        app = FastAPI()
        log_file = tmp_path / "query_params.json"

        logger.remove()
        logger.add(
            str(log_file),
            serialize=True,
            level="INFO",
        )

        app.add_middleware(LoggingMiddleware)

        @app.get("/search")
        async def search(q: str = ""):
            return {"query": q}

        client = TestClient(app)
        response = client.get("/search?q=test&limit=10")
        assert response.status_code == 200

        with open(log_file, "r", encoding="utf-8") as f:
            logs = [json.loads(line) for line in f.readlines()]

        request_log = logs[0]
        # 查询参数应该被记录
        assert "query_params" in request_log["record"]["extra"]
        assert "q=test" in request_log["record"]["extra"]["query_params"]

        # 清理
        logger.remove()

    def test_middleware_performance_metrics(self, tmp_path):
        """测试性能指标记录"""
        app = FastAPI()
        log_file = tmp_path / "performance.json"

        logger.remove()
        logger.add(
            str(log_file),
            serialize=True,
            level="INFO",
        )

        app.add_middleware(LoggingMiddleware)

        @app.get("/api")
        async def api_endpoint():
            return {"data": "test"}

        client = TestClient(app)
        response = client.get("/api")
        assert response.status_code == 200

        with open(log_file, "r", encoding="utf-8") as f:
            logs = [json.loads(line) for line in f.readlines()]

        # 找到性能日志
        perf_logs = [log for log in logs if log["record"]["extra"].get("performance")]
        assert len(perf_logs) >= 1

        perf_log = perf_logs[0]
        assert "duration_ms" in perf_log["record"]["extra"]
        assert perf_log["record"]["extra"]["duration_ms"] >= 0
        assert perf_log["record"]["extra"]["status_code"] == 200

        # 清理
        logger.remove()
