"""
API 版本管理和弃用警告的单元测试
"""

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from app.core.api_versioning import (
    APIVersion,
    DeprecationInfo,
    api_version,
    check_api_version,
    deprecated,
)


class TestAPIVersion:
    """测试 APIVersion 类"""

    def test_current_version(self):
        """测试当前版本"""
        assert APIVersion.CURRENT_VERSION == "2.0"

    def test_previous_version(self):
        """测试上一个版本"""
        assert APIVersion.PREVIOUS_VERSION == "1.0"

    def test_supported_versions(self):
        """测试支持的版本列表"""
        assert "1.0" in APIVersion.SUPPORTED_VERSIONS
        assert "2.0" in APIVersion.SUPPORTED_VERSIONS
        assert len(APIVersion.SUPPORTED_VERSIONS) == 2

    def test_is_supported_valid_version(self):
        """测试有效版本检查"""
        assert APIVersion.is_supported("1.0") is True
        assert APIVersion.is_supported("2.0") is True

    def test_is_supported_invalid_version(self):
        """测试无效版本检查"""
        assert APIVersion.is_supported("3.0") is False
        assert APIVersion.is_supported("0.9") is False

    def test_get_default_version(self):
        """测试获取默认版本"""
        assert APIVersion.get_default_version() == "2.0"


class TestDeprecationInfo:
    """测试 DeprecationInfo 类"""

    def test_basic_deprecation_info(self):
        """测试基本弃用信息"""
        info = DeprecationInfo(
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/api/new-endpoint",
            reason="使用新的 API",
        )

        assert info.deprecated_since == "2.0"
        assert info.removal_date == "2026-09-01"
        assert info.alternative == "/api/new-endpoint"
        assert info.reason == "使用新的 API"

    def test_to_dict(self):
        """测试转换为字典"""
        info = DeprecationInfo(
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/api/new-endpoint",
            reason="使用新的 API",
        )

        result = info.to_dict()

        assert result["deprecated"] is True
        assert result["deprecated_since"] == "2.0"
        assert result["removal_date"] == "2026-09-01"
        assert result["alternative"] == "/api/new-endpoint"
        assert result["reason"] == "使用新的 API"

    def test_to_warning_message_full(self):
        """测试生成完整警告消息"""
        info = DeprecationInfo(
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/api/new-endpoint",
            reason="使用新的 API",
        )

        message = info.to_warning_message()

        assert "deprecated since version 2.0" in message
        assert "2026-09-01" in message
        assert "/api/new-endpoint" in message
        assert "使用新的 API" in message

    def test_to_warning_message_minimal(self):
        """测试生成最小警告消息"""
        info = DeprecationInfo(deprecated_since="2.0")

        message = info.to_warning_message()

        assert "deprecated since version 2.0" in message
        assert "removal_date" not in message.lower()
        assert "alternative" not in message.lower()


class TestDeprecatedDecorator:
    """测试 @deprecated 装饰器"""

    def test_deprecated_async_endpoint(self):
        """测试异步端点的弃用装饰器"""
        app = FastAPI()

        @app.get("/old-endpoint")
        @deprecated(
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/new-endpoint",
            reason="使用新 API",
        )
        async def old_endpoint():
            return {"message": "old endpoint"}

        client = TestClient(app)
        response = client.get("/old-endpoint")

        # 检查响应体中的弃用信息
        data = response.json()
        assert "deprecation" in data
        assert data["deprecation"]["deprecated"] is True
        assert data["deprecation"]["deprecated_since"] == "2.0"
        assert data["deprecation"]["removal_date"] == "2026-09-01"
        assert data["deprecation"]["alternative"] == "/new-endpoint"

    def test_deprecated_without_optional_fields(self):
        """测试没有可选字段的弃用装饰器"""
        app = FastAPI()

        @app.get("/old-endpoint")
        @deprecated(deprecated_since="2.0")
        async def old_endpoint():
            return {"message": "old endpoint"}

        client = TestClient(app)
        response = client.get("/old-endpoint")

        # 检查响应体中的弃用信息
        data = response.json()
        assert "deprecation" in data
        assert data["deprecation"]["deprecated"] is True
        assert data["deprecation"]["deprecated_since"] == "2.0"

        # 可选字段应为 None
        assert data["deprecation"]["removal_date"] is None
        assert data["deprecation"]["alternative"] is None


class TestApiVersionDecorator:
    """测试 @api_version 装饰器"""

    def test_api_version_decorator(self):
        """测试 API 版本装饰器"""
        app = FastAPI()

        @app.get("/v2-endpoint")
        @api_version("2.0")
        async def v2_endpoint():
            return {"message": "v2 endpoint"}

        client = TestClient(app)
        response = client.get("/v2-endpoint")

        # 检查响应体
        data = response.json()
        assert data["api_version"] == "2.0"


class TestCheckApiVersion:
    """测试 check_api_version 函数"""

    def test_version_from_header(self):
        """测试从 Header 获取版本"""

        class MockRequest:
            def __init__(self):
                self.headers = {"X-API-Version": "1.0"}
                self.query_params = {}

        request = MockRequest()
        version = check_api_version(request)

        assert version == "1.0"

    def test_version_from_query_param(self):
        """测试从查询参数获取版本"""

        class MockRequest:
            def __init__(self):
                self.headers = {}
                self.query_params = {"api_version": "1.0"}

        request = MockRequest()
        version = check_api_version(request)

        assert version == "1.0"

    def test_default_version(self):
        """测试默认版本"""

        class MockRequest:
            def __init__(self):
                self.headers = {}
                self.query_params = {}

        request = MockRequest()
        version = check_api_version(request)

        assert version == APIVersion.CURRENT_VERSION

    def test_header_priority_over_query(self):
        """测试 Header 优先级高于查询参数"""

        class MockRequest:
            def __init__(self):
                self.headers = {"X-API-Version": "2.0"}
                self.query_params = {"api_version": "1.0"}

        request = MockRequest()
        version = check_api_version(request)

        assert version == "2.0"

    def test_unsupported_version_raises_error(self):
        """测试不支持的版本抛出异常"""

        class MockRequest:
            def __init__(self):
                self.headers = {"X-API-Version": "3.0"}
                self.query_params = {}

        request = MockRequest()

        with pytest.raises(ValueError) as exc_info:
            check_api_version(request)

        assert "not supported" in str(exc_info.value)
        assert "3.0" in str(exc_info.value)


class TestDeprecatedAndVersionTogether:
    """测试弃用警告和版本信息一起使用"""

    def test_deprecated_and_version_decorators(self):
        """测试同时使用两个装饰器"""
        app = FastAPI()

        @app.get("/old-v1-endpoint")
        @deprecated(
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/v2-endpoint",
        )
        @api_version("1.0")
        async def old_v1_endpoint():
            return {"message": "old v1 endpoint"}

        client = TestClient(app)
        response = client.get("/old-v1-endpoint")

        # 检查响应体
        data = response.json()
        assert "deprecation" in data
        assert data["api_version"] == "1.0"


class TestRealWorldScenarios:
    """测试真实世界场景"""

    def test_migration_from_v1_to_v2(self):
        """测试从 v1 迁移到 v2 的场景"""
        app = FastAPI()

        # v1 端点（已弃用）
        @app.get("/api/v1/strategies")
        @deprecated(
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/api/v2/strategies",
            reason="使用新的统一策略系统",
        )
        @api_version("1.0")
        async def get_strategies_v1():
            return {"strategies": ["strategy1", "strategy2"]}

        # v2 端点（当前版本）
        @app.get("/api/v2/strategies")
        @api_version("2.0")
        async def get_strategies_v2():
            return {
                "code": 200,
                "message": "success",
                "data": {"strategies": ["strategy1", "strategy2"]},
            }

        client = TestClient(app)

        # 测试 v1 端点
        v1_response = client.get("/api/v1/strategies")
        v1_data = v1_response.json()
        assert "deprecation" in v1_data
        assert v1_data["api_version"] == "1.0"

        # 测试 v2 端点
        v2_response = client.get("/api/v2/strategies")
        v2_data = v2_response.json()
        assert "deprecation" not in v2_data
        assert v2_data["api_version"] == "2.0"

    def test_gradual_deprecation(self):
        """测试渐进式弃用"""
        app = FastAPI()

        # 阶段 1: 标记为弃用但仍然可用
        @app.get("/api/old-feature")
        @deprecated(
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/api/new-feature",
        )
        async def old_feature():
            return {"status": "deprecated but working"}

        # 阶段 2: 新功能
        @app.get("/api/new-feature")
        @api_version("2.0")
        async def new_feature():
            return {"status": "new and improved"}

        client = TestClient(app)

        # 旧功能仍然可用但有警告
        old_response = client.get("/api/old-feature")
        assert old_response.status_code == 200
        assert "deprecation" in old_response.json()

        # 新功能正常工作
        new_response = client.get("/api/new-feature")
        assert new_response.status_code == 200
        assert "deprecation" not in new_response.json()
