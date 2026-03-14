"""
API 响应模型的单元测试（v2.0 增强版）
"""

import pytest
from datetime import datetime

from app.models.api_response import ApiResponse, DeprecationWarning


class TestDeprecationWarning:
    """测试 DeprecationWarning 模型"""

    def test_create_deprecation_warning(self):
        """测试创建弃用警告"""
        warning = DeprecationWarning(
            deprecated=True,
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/api/new-endpoint",
            reason="使用新 API",
        )

        assert warning.deprecated is True
        assert warning.deprecated_since == "2.0"
        assert warning.removal_date == "2026-09-01"
        assert warning.alternative == "/api/new-endpoint"
        assert warning.reason == "使用新 API"

    def test_deprecation_warning_minimal(self):
        """测试最小弃用警告"""
        warning = DeprecationWarning(deprecated_since="2.0")

        assert warning.deprecated is True
        assert warning.deprecated_since == "2.0"
        assert warning.removal_date is None
        assert warning.alternative is None
        assert warning.reason is None

    def test_deprecation_warning_model_dump(self):
        """测试弃用警告的模型序列化"""
        warning = DeprecationWarning(
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/api/new-endpoint",
        )

        data = warning.model_dump()

        assert data["deprecated"] is True
        assert data["deprecated_since"] == "2.0"
        assert data["removal_date"] == "2026-09-01"
        assert data["alternative"] == "/api/new-endpoint"


class TestApiResponseWithVersioning:
    """测试带版本信息的 ApiResponse"""

    def test_success_with_version(self):
        """测试带版本的成功响应"""
        response = ApiResponse.success(
            data={"user_id": "123"}, api_version="2.0"
        )

        assert response.code == 200
        assert response.message == "success"
        assert response.data == {"user_id": "123"}
        assert response.api_version == "2.0"
        assert response.deprecation is None

    def test_success_without_version(self):
        """测试不带版本的成功响应"""
        response = ApiResponse.success(data={"user_id": "123"})

        assert response.code == 200
        assert response.api_version is None

    def test_to_dict_with_version(self):
        """测试转换为字典（含版本）"""
        response = ApiResponse.success(
            data={"user_id": "123"}, api_version="2.0"
        )

        result = response.to_dict()

        assert result["code"] == 200
        assert result["success"] is True
        assert result["api_version"] == "2.0"

    def test_to_dict_without_version(self):
        """测试转换为字典（不含版本）"""
        response = ApiResponse.success(data={"user_id": "123"})

        result = response.to_dict()

        assert result["code"] == 200
        assert result["success"] is True
        assert "api_version" not in result


class TestApiResponseWithDeprecation:
    """测试带弃用警告的 ApiResponse"""

    def test_success_with_deprecation(self):
        """测试带弃用警告的成功响应"""
        deprecation = DeprecationWarning(
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/api/new-endpoint",
        )

        response = ApiResponse.success(
            data={"result": "data"}, deprecation=deprecation
        )

        assert response.code == 200
        assert response.deprecation is not None
        assert response.deprecation.deprecated is True
        assert response.deprecation.deprecated_since == "2.0"

    def test_to_dict_with_deprecation(self):
        """测试转换为字典（含弃用警告）"""
        deprecation = DeprecationWarning(
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/api/new-endpoint",
        )

        response = ApiResponse.success(
            data={"result": "data"}, deprecation=deprecation
        )

        result = response.to_dict()

        assert result["code"] == 200
        assert "deprecation" in result
        assert result["deprecation"]["deprecated"] is True
        assert result["deprecation"]["deprecated_since"] == "2.0"
        assert result["deprecation"]["removal_date"] == "2026-09-01"

    def test_to_dict_without_deprecation(self):
        """测试转换为字典（不含弃用警告）"""
        response = ApiResponse.success(data={"result": "data"})

        result = response.to_dict()

        assert result["code"] == 200
        assert "deprecation" not in result


class TestApiResponseWithVersionAndDeprecation:
    """测试同时带版本和弃用警告的 ApiResponse"""

    def test_both_version_and_deprecation(self):
        """测试同时包含版本和弃用警告"""
        deprecation = DeprecationWarning(
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/api/v2/endpoint",
        )

        response = ApiResponse.success(
            data={"result": "data"}, api_version="1.0", deprecation=deprecation
        )

        assert response.api_version == "1.0"
        assert response.deprecation is not None
        assert response.deprecation.deprecated is True

    def test_to_dict_with_both(self):
        """测试转换为字典（含版本和弃用警告）"""
        deprecation = DeprecationWarning(
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/api/v2/endpoint",
        )

        response = ApiResponse.success(
            data={"result": "data"}, api_version="1.0", deprecation=deprecation
        )

        result = response.to_dict()

        assert result["api_version"] == "1.0"
        assert "deprecation" in result
        assert result["deprecation"]["deprecated"] is True


class TestApiResponseAllMethods:
    """测试 ApiResponse 的所有便捷方法（带版本支持）"""

    def test_success_method(self):
        """测试 success 方法"""
        response = ApiResponse.success(
            data={"value": 123}, api_version="2.0"
        )

        assert response.code == 200
        assert response.message == "success"
        assert response.api_version == "2.0"

    def test_created_method(self):
        """测试 created 方法"""
        response = ApiResponse.created(data={"id": "abc123"})

        assert response.code == 201
        assert response.message == "created"

    def test_no_content_method(self):
        """测试 no_content 方法"""
        response = ApiResponse.no_content()

        assert response.code == 204
        assert response.message == "no content"
        assert response.data is None

    def test_bad_request_method(self):
        """测试 bad_request 方法"""
        response = ApiResponse.bad_request(
            message="参数错误", data={"error_code": "VALIDATION_ERROR"}
        )

        assert response.code == 400
        assert response.message == "参数错误"

    def test_unauthorized_method(self):
        """测试 unauthorized 方法"""
        response = ApiResponse.unauthorized(message="未授权")

        assert response.code == 401
        assert response.message == "未授权"

    def test_forbidden_method(self):
        """测试 forbidden 方法"""
        response = ApiResponse.forbidden(message="权限不足")

        assert response.code == 403
        assert response.message == "权限不足"

    def test_not_found_method(self):
        """测试 not_found 方法"""
        response = ApiResponse.not_found(
            message="资源不存在", data={"resource_id": "123"}
        )

        assert response.code == 404
        assert response.message == "资源不存在"

    def test_conflict_method(self):
        """测试 conflict 方法"""
        response = ApiResponse.conflict(message="资源冲突")

        assert response.code == 409
        assert response.message == "资源冲突"

    def test_internal_error_method(self):
        """测试 internal_error 方法"""
        response = ApiResponse.internal_error(message="服务器错误")

        assert response.code == 500
        assert response.message == "服务器错误"

    def test_warning_method(self):
        """测试 warning 方法"""
        response = ApiResponse.warning(
            data={"result": "data"},
            message="质量较低",
            warning_code="LOW_QUALITY",
            quality_score=0.75,
        )

        assert response.code == 206
        assert response.message == "质量较低"
        assert response.data["warning_code"] == "LOW_QUALITY"
        assert response.data["quality_score"] == 0.75

    def test_paginated_method(self):
        """测试 paginated 方法"""
        items = [{"id": 1}, {"id": 2}]
        response = ApiResponse.paginated(
            items=items, total=100, page=1, page_size=20
        )

        assert response.code == 200
        assert response.data["items"] == items
        assert response.data["total"] == 100
        assert response.data["page"] == 1
        assert response.data["page_size"] == 20
        assert response.data["total_pages"] == 5


class TestApiResponseTimestamp:
    """测试 ApiResponse 时间戳功能"""

    def test_automatic_timestamp(self):
        """测试自动生成时间戳"""
        response = ApiResponse.success(data={"value": 123})

        assert response.timestamp is not None
        assert len(response.timestamp) > 0

        # 验证是 ISO 格式
        datetime.fromisoformat(response.timestamp)

    def test_timestamp_in_to_dict(self):
        """测试字典中包含时间戳"""
        response = ApiResponse.success(data={"value": 123})
        result = response.to_dict()

        assert "timestamp" in result
        assert result["timestamp"] == response.timestamp


class TestApiResponseSuccess:
    """测试 ApiResponse success 字段"""

    def test_success_true_for_2xx(self):
        """测试 2xx 状态码的 success 为 true"""
        response = ApiResponse.success(data={})
        assert response.to_dict()["success"] is True

        response = ApiResponse.created(data={})
        assert response.to_dict()["success"] is True

        response = ApiResponse.no_content()
        assert response.to_dict()["success"] is True

    def test_success_false_for_4xx(self):
        """测试 4xx 状态码的 success 为 false"""
        response = ApiResponse.bad_request(message="error")
        assert response.to_dict()["success"] is False

        response = ApiResponse.not_found(message="error")
        assert response.to_dict()["success"] is False

    def test_success_false_for_5xx(self):
        """测试 5xx 状态码的 success 为 false"""
        response = ApiResponse.internal_error(message="error")
        assert response.to_dict()["success"] is False


class TestApiResponseRequestId:
    """测试 ApiResponse request_id 功能"""

    def test_with_request_id(self):
        """测试带 request_id 的响应"""
        response = ApiResponse.success(
            data={"value": 123}, request_id="req_abc123"
        )

        assert response.request_id == "req_abc123"

        result = response.to_dict()
        assert "request_id" in result
        assert result["request_id"] == "req_abc123"

    def test_without_request_id(self):
        """测试不带 request_id 的响应"""
        response = ApiResponse.success(data={"value": 123})

        assert response.request_id is None

        result = response.to_dict()
        assert "request_id" not in result


class TestRealWorldScenarios:
    """测试真实世界场景"""

    def test_deprecated_api_response(self):
        """测试已弃用 API 的完整响应"""
        deprecation = DeprecationWarning(
            deprecated_since="2.0",
            removal_date="2026-09-01",
            alternative="/api/v2/strategies",
            reason="使用新的统一策略系统",
        )

        response = ApiResponse.success(
            data={"strategies": ["s1", "s2"]},
            message="success",
            request_id="req_123",
            api_version="1.0",
            deprecation=deprecation,
        )

        result = response.to_dict()

        # 验证所有字段
        assert result["code"] == 200
        assert result["message"] == "success"
        assert result["success"] is True
        assert result["data"]["strategies"] == ["s1", "s2"]
        assert result["request_id"] == "req_123"
        assert result["api_version"] == "1.0"
        assert result["deprecation"]["deprecated"] is True
        assert result["deprecation"]["removal_date"] == "2026-09-01"

    def test_new_api_response(self):
        """测试新 API 的完整响应"""
        response = ApiResponse.success(
            data={"strategies": ["s1", "s2"]},
            message="success",
            request_id="req_456",
            api_version="2.0",
        )

        result = response.to_dict()

        # 验证所有字段
        assert result["code"] == 200
        assert result["message"] == "success"
        assert result["success"] is True
        assert result["data"]["strategies"] == ["s1", "s2"]
        assert result["request_id"] == "req_456"
        assert result["api_version"] == "2.0"
        assert "deprecation" not in result

    def test_error_response_with_details(self):
        """测试包含详细信息的错误响应"""
        response = ApiResponse.not_found(
            message="策略不存在",
            data={
                "error_code": "STRATEGY_NOT_FOUND",
                "resource_type": "strategy",
                "resource_id": "abc123",
            },
            request_id="req_789",
        )
        # 手动设置 api_version
        response.api_version = "2.0"

        result = response.to_dict()

        assert result["code"] == 404
        assert result["success"] is False
        assert result["data"]["error_code"] == "STRATEGY_NOT_FOUND"
        assert result["data"]["resource_id"] == "abc123"
        assert result["api_version"] == "2.0"

    def test_paginated_response_complete(self):
        """测试完整的分页响应"""
        response = ApiResponse.paginated(
            items=[{"id": 1}, {"id": 2}],
            total=100,
            page=2,
            page_size=20,
            request_id="req_page",
        )

        result = response.to_dict()

        assert result["code"] == 200
        assert result["success"] is True
        assert len(result["data"]["items"]) == 2
        assert result["data"]["total"] == 100
        assert result["data"]["page"] == 2
        assert result["data"]["page_size"] == 20
        assert result["data"]["total_pages"] == 5

    def test_warning_response_with_partial_success(self):
        """测试部分成功的警告响应"""
        response = ApiResponse.warning(
            data={
                "processed": 80,
                "failed": 20,
                "results": [...]
            },
            message="批量操作部分失败",
            warning_code="PARTIAL_FAILURE",
            failure_rate=0.2,
        )

        result = response.to_dict()

        assert result["code"] == 206
        assert result["success"] is True  # 206 仍被视为成功
        assert result["data"]["warning_code"] == "PARTIAL_FAILURE"
        assert result["data"]["failure_rate"] == 0.2
