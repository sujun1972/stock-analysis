"""
ExternalSelector 单元测试
"""

import pytest
import pandas as pd
import json
from unittest.mock import Mock, patch

from src.strategies.three_layer.selectors import ExternalSelector


class TestExternalSelectorBasic:
    """测试 ExternalSelector 基本功能"""

    def test_id_and_name(self):
        """测试选股器ID和名称"""
        selector = ExternalSelector()
        assert selector.id == "external"
        assert selector.name == "外部数据源选股器"

    def test_get_parameters(self):
        """测试参数定义"""
        params = ExternalSelector.get_parameters()
        assert len(params) == 7

        param_names = [p.name for p in params]
        assert "source" in param_names
        assert "api_endpoint" in param_names
        assert "api_timeout" in param_names
        assert "manual_stocks" in param_names
        assert "api_method" in param_names
        assert "api_headers" in param_names
        assert "max_stocks" in param_names

    def test_default_parameters(self):
        """测试默认参数"""
        selector = ExternalSelector()
        params = selector.get_parameters()

        defaults = {p.name: p.default for p in params}
        assert defaults["source"] == "manual"
        assert defaults["api_endpoint"] == ""
        assert defaults["api_timeout"] == 10
        assert defaults["manual_stocks"] == ""
        assert defaults["api_method"] == "GET"
        assert defaults["max_stocks"] == 100


class TestExternalSelectorManualMode:
    """测试 ExternalSelector 手动输入模式"""

    def test_manual_stocks_basic(self):
        """测试手动输入基本功能"""
        selector = ExternalSelector(
            params={"source": "manual", "manual_stocks": "600000.SH,000001.SZ,000002.SZ"}
        )

        test_date = pd.Timestamp("2023-06-01")
        prices = pd.DataFrame()  # 手动模式不需要价格数据

        selected = selector.select(test_date, prices)

        assert len(selected) == 3
        assert "600000.SH" in selected
        assert "000001.SZ" in selected
        assert "000002.SZ" in selected

    def test_manual_stocks_with_spaces(self):
        """测试手动输入包含空格"""
        selector = ExternalSelector(
            params={
                "source": "manual",
                "manual_stocks": " 600000.SH , 000001.SZ , 000002.SZ ",
            }
        )

        test_date = pd.Timestamp("2023-06-01")
        selected = selector.select(test_date, pd.DataFrame())

        # 应该正确处理空格
        assert len(selected) == 3
        assert "600000.SH" in selected

    def test_manual_stocks_empty(self):
        """测试手动输入为空"""
        selector = ExternalSelector(params={"source": "manual", "manual_stocks": ""})

        test_date = pd.Timestamp("2023-06-01")
        selected = selector.select(test_date, pd.DataFrame())

        assert len(selected) == 0

    def test_manual_stocks_single(self):
        """测试单个股票"""
        selector = ExternalSelector(
            params={"source": "manual", "manual_stocks": "600000.SH"}
        )

        test_date = pd.Timestamp("2023-06-01")
        selected = selector.select(test_date, pd.DataFrame())

        assert len(selected) == 1
        assert selected[0] == "600000.SH"

    def test_manual_stocks_max_limit(self):
        """测试最大股票数量限制"""
        # 生成150只股票
        stocks = ",".join([f"STOCK_{i}" for i in range(150)])

        selector = ExternalSelector(
            params={"source": "manual", "manual_stocks": stocks, "max_stocks": 100}
        )

        test_date = pd.Timestamp("2023-06-01")
        selected = selector.select(test_date, pd.DataFrame())

        # 应该被截断为100只
        assert len(selected) == 100


class TestExternalSelectorCustomAPI:
    """测试 ExternalSelector 自定义API模式"""

    def test_api_mode_success(self):
        """测试API模式成功获取数据"""
        selector = ExternalSelector(
            params={
                "source": "custom_api",
                "api_endpoint": "http://example.com/stocks",
                "api_timeout": 10,
            }
        )

        test_date = pd.Timestamp("2023-06-01")

        # Mock requests.get
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "stocks": ["600000.SH", "000001.SZ", "000002.SZ"]
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            selected = selector.select(test_date, pd.DataFrame())

            assert len(selected) == 3
            assert "600000.SH" in selected

            # 验证API调用参数
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args.kwargs["params"]["date"] == "2023-06-01"

    def test_api_mode_post_method(self):
        """测试API POST方法"""
        selector = ExternalSelector(
            params={
                "source": "custom_api",
                "api_endpoint": "http://example.com/stocks",
                "api_method": "POST",
            }
        )

        test_date = pd.Timestamp("2023-06-01")

        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"stocks": ["600000.SH"]}
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            selected = selector.select(test_date, pd.DataFrame())

            assert len(selected) == 1
            mock_post.assert_called_once()

    def test_api_mode_with_headers(self):
        """测试API自定义请求头"""
        headers_dict = {"Authorization": "Bearer token123"}
        selector = ExternalSelector(
            params={
                "source": "custom_api",
                "api_endpoint": "http://example.com/stocks",
                "api_headers": json.dumps(headers_dict),
            }
        )

        test_date = pd.Timestamp("2023-06-01")

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"stocks": ["600000.SH"]}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            selected = selector.select(test_date, pd.DataFrame())

            # 验证请求头
            call_args = mock_get.call_args
            assert call_args.kwargs["headers"]["Authorization"] == "Bearer token123"

    def test_api_mode_timeout(self):
        """测试API超时"""
        selector = ExternalSelector(
            params={
                "source": "custom_api",
                "api_endpoint": "http://example.com/stocks",
                "api_timeout": 5,
            }
        )

        test_date = pd.Timestamp("2023-06-01")

        with patch("requests.get") as mock_get:
            import requests

            mock_get.side_effect = requests.Timeout()

            selected = selector.select(test_date, pd.DataFrame())

            # 超时应该返回空列表
            assert len(selected) == 0

    def test_api_mode_http_error(self):
        """测试API HTTP错误"""
        selector = ExternalSelector(
            params={
                "source": "custom_api",
                "api_endpoint": "http://example.com/stocks",
            }
        )

        test_date = pd.Timestamp("2023-06-01")

        with patch("requests.get") as mock_get:
            import requests

            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            mock_response.raise_for_status.side_effect = requests.HTTPError(
                response=mock_response
            )

            selected = selector.select(test_date, pd.DataFrame())

            assert len(selected) == 0

    def test_api_mode_missing_stocks_field(self):
        """测试API响应缺少stocks字段"""
        selector = ExternalSelector(
            params={
                "source": "custom_api",
                "api_endpoint": "http://example.com/stocks",
            }
        )

        test_date = pd.Timestamp("2023-06-01")

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"data": ["600000.SH"]}  # 缺少stocks字段
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            selected = selector.select(test_date, pd.DataFrame())

            # 缺少必需字段应该返回空列表
            assert len(selected) == 0

    def test_api_mode_invalid_response_format(self):
        """测试API响应格式错误"""
        selector = ExternalSelector(
            params={
                "source": "custom_api",
                "api_endpoint": "http://example.com/stocks",
            }
        )

        test_date = pd.Timestamp("2023-06-01")

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"stocks": "not_a_list"}  # 不是列表
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            selected = selector.select(test_date, pd.DataFrame())

            assert len(selected) == 0

    def test_api_mode_no_endpoint(self):
        """测试API模式未提供endpoint"""
        selector = ExternalSelector(
            params={"source": "custom_api", "api_endpoint": ""}
        )

        test_date = pd.Timestamp("2023-06-01")
        selected = selector.select(test_date, pd.DataFrame())

        # 未提供endpoint应该返回空列表
        assert len(selected) == 0

    def test_api_mode_invalid_json_response(self):
        """测试API返回无效JSON"""
        selector = ExternalSelector(
            params={
                "source": "custom_api",
                "api_endpoint": "http://example.com/stocks",
            }
        )

        test_date = pd.Timestamp("2023-06-01")

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            selected = selector.select(test_date, pd.DataFrame())

            assert len(selected) == 0


class TestExternalSelectorStarRankerMode:
    """测试 ExternalSelector StarRanker模式"""

    def test_starranker_mode_not_implemented(self):
        """测试StarRanker模式（当前未实现）"""
        selector = ExternalSelector(params={"source": "starranker"})

        test_date = pd.Timestamp("2023-06-01")
        selected = selector.select(test_date, pd.DataFrame())

        # 当前未实现，应该返回空列表
        assert len(selected) == 0


class TestExternalSelectorParameterValidation:
    """测试 ExternalSelector 参数验证"""

    def test_invalid_api_timeout(self):
        """测试无效的API超时时间"""
        with pytest.raises(ValueError):
            ExternalSelector(params={"api_timeout": 0})

        with pytest.raises(ValueError):
            ExternalSelector(params={"api_timeout": 100})

    def test_invalid_max_stocks(self):
        """测试无效的最大股票数"""
        with pytest.raises(ValueError):
            ExternalSelector(params={"max_stocks": 0})

        with pytest.raises(ValueError):
            ExternalSelector(params={"max_stocks": 1000})

    def test_invalid_parameter_type(self):
        """测试无效的参数类型"""
        with pytest.raises(ValueError):
            ExternalSelector(params={"api_timeout": "10"})

    def test_unknown_parameter(self):
        """测试未知参数"""
        with pytest.raises(ValueError):
            ExternalSelector(params={"unknown_param": 123})

    def test_valid_edge_values(self):
        """测试边界有效值"""
        selector1 = ExternalSelector(params={"api_timeout": 1, "max_stocks": 1})
        assert selector1.params["api_timeout"] == 1
        assert selector1.params["max_stocks"] == 1

        selector2 = ExternalSelector(params={"api_timeout": 60, "max_stocks": 500})
        assert selector2.params["api_timeout"] == 60
        assert selector2.params["max_stocks"] == 500


class TestExternalSelectorEdgeCases:
    """测试 ExternalSelector 边界情况"""

    def test_unknown_source(self):
        """测试未知的数据源类型"""
        selector = ExternalSelector(params={"source": "unknown_source"})

        test_date = pd.Timestamp("2023-06-01")
        selected = selector.select(test_date, pd.DataFrame())

        # 未知数据源应该返回空列表
        assert len(selected) == 0

    def test_empty_api_response(self):
        """测试API返回空列表"""
        selector = ExternalSelector(
            params={
                "source": "custom_api",
                "api_endpoint": "http://example.com/stocks",
            }
        )

        test_date = pd.Timestamp("2023-06-01")

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"stocks": []}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            selected = selector.select(test_date, pd.DataFrame())

            assert len(selected) == 0

    def test_api_with_metadata(self):
        """测试API返回包含元数据"""
        selector = ExternalSelector(
            params={
                "source": "custom_api",
                "api_endpoint": "http://example.com/stocks",
            }
        )

        test_date = pd.Timestamp("2023-06-01")

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "stocks": ["600000.SH"],
                "date": "2023-06-01",
                "metadata": {"count": 1, "source": "model_v1"},
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            selected = selector.select(test_date, pd.DataFrame())

            # 应该正确提取stocks字段
            assert len(selected) == 1
            assert selected[0] == "600000.SH"


class TestExternalSelectorIntegration:
    """测试 ExternalSelector 集成场景"""

    def test_multiple_calls_consistency(self):
        """测试多次调用的一致性（手动模式）"""
        selector = ExternalSelector(
            params={"source": "manual", "manual_stocks": "A,B,C"}
        )

        test_date = pd.Timestamp("2023-06-01")
        selected1 = selector.select(test_date, pd.DataFrame())
        selected2 = selector.select(test_date, pd.DataFrame())
        selected3 = selector.select(test_date, pd.DataFrame())

        # 结果应该完全一致
        assert selected1 == selected2
        assert selected2 == selected3

    def test_different_dates_manual_mode(self):
        """测试不同日期手动模式"""
        selector = ExternalSelector(
            params={"source": "manual", "manual_stocks": "A,B,C"}
        )

        date1 = pd.Timestamp("2023-06-01")
        date2 = pd.Timestamp("2023-06-02")

        selected1 = selector.select(date1, pd.DataFrame())
        selected2 = selector.select(date2, pd.DataFrame())

        # 手动模式下，不同日期应该返回相同结果
        assert selected1 == selected2

    def test_api_date_parameter(self):
        """测试API调用传递日期参数"""
        selector = ExternalSelector(
            params={
                "source": "custom_api",
                "api_endpoint": "http://example.com/stocks",
            }
        )

        test_date = pd.Timestamp("2023-06-15")

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"stocks": ["A"]}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            selector.select(test_date, pd.DataFrame())

            # 验证日期参数格式
            call_args = mock_get.call_args
            assert call_args.kwargs["params"]["date"] == "2023-06-15"
