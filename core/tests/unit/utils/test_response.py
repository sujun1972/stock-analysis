"""
测试统一API返回格式模块 (src/utils/response.py)

测试覆盖:
- Response类的基本功能
- ResponseStatus枚举
- 成功/错误/警告响应的创建
- 状态检查方法
- 字典转换
- 便捷函数
"""
import pytest
from dataclasses import asdict

from src.utils.response import (
    Response,
    ResponseStatus,
    success,
    error,
    warning
)


class TestResponseStatus:
    """测试ResponseStatus枚举"""

    def test_status_values(self):
        """测试状态值"""
        assert ResponseStatus.SUCCESS.value == "success"
        assert ResponseStatus.ERROR.value == "error"
        assert ResponseStatus.WARNING.value == "warning"

    def test_status_members(self):
        """测试枚举成员"""
        assert len(ResponseStatus) == 3
        assert ResponseStatus.SUCCESS in ResponseStatus
        assert ResponseStatus.ERROR in ResponseStatus
        assert ResponseStatus.WARNING in ResponseStatus


class TestResponseCreation:
    """测试Response创建"""

    def test_success_creation(self):
        """测试创建成功响应"""
        resp = Response.success(
            data={'result': [1, 2, 3]},
            message="操作成功",
            count=3
        )

        assert resp.status == ResponseStatus.SUCCESS
        assert resp.data == {'result': [1, 2, 3]}
        assert resp.message == "操作成功"
        assert resp.metadata == {'count': 3}
        assert resp.error_message is None
        assert resp.error_code is None

    def test_success_creation_minimal(self):
        """测试最小参数创建成功响应"""
        resp = Response.success()

        assert resp.status == ResponseStatus.SUCCESS
        assert resp.data is None
        assert resp.message == "操作成功"  # 默认消息
        assert resp.metadata == {}

    def test_success_creation_with_data_only(self):
        """测试仅带数据的成功响应"""
        resp = Response.success(data={'key': 'value'})

        assert resp.status == ResponseStatus.SUCCESS
        assert resp.data == {'key': 'value'}
        assert resp.message == "操作成功"

    def test_success_creation_with_metadata(self):
        """测试带元数据的成功响应"""
        resp = Response.success(
            data=[1, 2, 3],
            message="计算完成",
            elapsed_time="2.5s",
            n_features=125,
            n_samples=1000
        )

        assert resp.metadata['elapsed_time'] == "2.5s"
        assert resp.metadata['n_features'] == 125
        assert resp.metadata['n_samples'] == 1000

    def test_error_creation(self):
        """测试创建错误响应"""
        resp = Response.error(
            error="文件不存在",
            error_code="FILE_NOT_FOUND",
            path="/tmp/data.csv"
        )

        assert resp.status == ResponseStatus.ERROR
        assert resp.error_message == "文件不存在"
        assert resp.error_code == "FILE_NOT_FOUND"
        assert resp.metadata == {'path': '/tmp/data.csv'}
        assert resp.data is None

    def test_error_creation_minimal(self):
        """测试最小参数创建错误响应"""
        resp = Response.error(error="操作失败")

        assert resp.status == ResponseStatus.ERROR
        assert resp.error_message == "操作失败"
        assert resp.error_code is None
        assert resp.metadata == {}

    def test_error_creation_with_data(self):
        """测试带部分数据的错误响应"""
        resp = Response.error(
            error="训练提前停止",
            error_code="EARLY_STOPPING",
            data={'best_iteration': 50, 'best_score': 0.75},
            reason="验证集性能下降"
        )

        assert resp.status == ResponseStatus.ERROR
        assert resp.data == {'best_iteration': 50, 'best_score': 0.75}
        assert resp.metadata['reason'] == "验证集性能下降"

    def test_warning_creation(self):
        """测试创建警告响应"""
        resp = Response.warning(
            message="部分数据缺失",
            data={'processed': True},
            missing_count=10
        )

        assert resp.status == ResponseStatus.WARNING
        assert resp.message == "部分数据缺失"
        assert resp.data == {'processed': True}
        assert resp.metadata == {'missing_count': 10}
        assert resp.error_message is None

    def test_warning_creation_minimal(self):
        """测试最小参数创建警告响应"""
        resp = Response.warning(message="注意事项")

        assert resp.status == ResponseStatus.WARNING
        assert resp.message == "注意事项"
        assert resp.data is None
        assert resp.metadata == {}


class TestResponseStatusChecks:
    """测试响应状态检查方法"""

    def test_is_success_on_success_response(self):
        """测试成功响应的is_success方法"""
        resp = Response.success(data=[1, 2, 3])
        assert resp.is_success() is True
        assert resp.is_error() is False
        assert resp.is_warning() is False

    def test_is_error_on_error_response(self):
        """测试错误响应的is_error方法"""
        resp = Response.error(error="失败")
        assert resp.is_success() is False
        assert resp.is_error() is True
        assert resp.is_warning() is False

    def test_is_warning_on_warning_response(self):
        """测试警告响应的is_warning方法"""
        resp = Response.warning(message="警告")
        assert resp.is_success() is False
        assert resp.is_error() is False
        assert resp.is_warning() is True


class TestResponseToDictConversion:
    """测试Response转字典"""

    def test_success_to_dict(self):
        """测试成功响应转字典"""
        resp = Response.success(
            data={'count': 100},
            message="查询成功",
            elapsed="0.5s"
        )
        result = resp.to_dict()

        assert result['status'] == 'success'
        assert result['message'] == '查询成功'
        assert result['data'] == {'count': 100}
        assert result['metadata'] == {'elapsed': '0.5s'}
        assert 'error' not in result
        assert 'error_code' not in result

    def test_error_to_dict(self):
        """测试错误响应转字典"""
        resp = Response.error(
            error="验证失败",
            error_code="VALIDATION_ERROR",
            field="price"
        )
        result = resp.to_dict()

        assert result['status'] == 'error'
        assert result['error'] == '验证失败'
        assert result['error_code'] == 'VALIDATION_ERROR'
        assert result['metadata'] == {'field': 'price'}
        assert 'data' not in result

    def test_warning_to_dict(self):
        """测试警告响应转字典"""
        resp = Response.warning(
            message="部分失败",
            data={'processed': 50},
            failed_count=5
        )
        result = resp.to_dict()

        assert result['status'] == 'warning'
        assert result['message'] == '部分失败'
        assert result['data'] == {'processed': 50}
        assert result['metadata'] == {'failed_count': 5}

    def test_to_dict_empty_fields_excluded(self):
        """测试空字段被排除"""
        resp = Response.success()
        result = resp.to_dict()

        # 应该只有status和message(因为有默认值)
        assert 'status' in result
        assert 'message' in result
        # 这些应该不存在(因为为None或空字典)
        assert 'error' not in result
        assert 'error_code' not in result
        # metadata为空字典时不应该包含
        if not resp.metadata:
            assert 'metadata' not in result

    def test_to_dict_with_none_data(self):
        """测试data为None时不包含在字典中"""
        resp = Response.success(data=None, message="完成")
        result = resp.to_dict()

        assert 'data' not in result

    def test_to_dict_with_empty_message(self):
        """测试message为空字符串时不包含在字典中"""
        resp = Response(status=ResponseStatus.SUCCESS, message="")
        result = resp.to_dict()

        assert 'message' not in result


class TestResponseRepresentation:
    """测试Response字符串表示"""

    def test_success_repr(self):
        """测试成功响应的repr"""
        resp = Response.success(data={'count': 10}, message="完成")
        repr_str = repr(resp)

        assert "status=SUCCESS" in repr_str
        assert "message='完成'" in repr_str
        assert "data=<dict>" in repr_str

    def test_error_repr(self):
        """测试错误响应的repr"""
        resp = Response.error(error="失败", error_code="ERR001")
        repr_str = repr(resp)

        assert "status=ERROR" in repr_str
        assert "error_code='ERR001'" in repr_str

    def test_warning_repr(self):
        """测试警告响应的repr"""
        resp = Response.warning(message="注意", data=[1, 2, 3])
        repr_str = repr(resp)

        assert "status=WARNING" in repr_str
        assert "data=<list>" in repr_str

    def test_repr_without_data(self):
        """测试无data的repr"""
        resp = Response.success(message="完成")
        repr_str = repr(resp)

        assert "status=SUCCESS" in repr_str
        assert "message='完成'" in repr_str
        # 不应该有data
        assert "data=" not in repr_str or "data=<NoneType>" not in repr_str


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_success_function(self):
        """测试success便捷函数"""
        resp = success(data=[1, 2, 3], message="完成", count=3)

        assert isinstance(resp, Response)
        assert resp.status == ResponseStatus.SUCCESS
        assert resp.data == [1, 2, 3]
        assert resp.message == "完成"
        assert resp.metadata == {'count': 3}

    def test_error_function(self):
        """测试error便捷函数"""
        resp = error(error="失败", error_code="ERR001", reason="超时")

        assert isinstance(resp, Response)
        assert resp.status == ResponseStatus.ERROR
        assert resp.error_message == "失败"
        assert resp.error_code == "ERR001"
        assert resp.metadata == {'reason': '超时'}

    def test_warning_function(self):
        """测试warning便捷函数"""
        resp = warning(message="部分失败", data=[], failed_count=2)

        assert isinstance(resp, Response)
        assert resp.status == ResponseStatus.WARNING
        assert resp.message == "部分失败"
        assert resp.data == []
        assert resp.metadata == {'failed_count': 2}


class TestResponseDataTypes:
    """测试不同数据类型的Response"""

    def test_response_with_dataframe_like_object(self):
        """测试带DataFrame类对象的响应"""
        # 模拟DataFrame对象
        class MockDataFrame:
            def __init__(self):
                self.shape = (100, 10)

        df = MockDataFrame()
        resp = Response.success(data=df, message="数据处理完成")

        assert resp.data.shape == (100, 10)
        assert resp.is_success()

    def test_response_with_list(self):
        """测试带列表的响应"""
        resp = Response.success(data=[1, 2, 3, 4, 5])
        assert isinstance(resp.data, list)
        assert len(resp.data) == 5

    def test_response_with_dict(self):
        """测试带字典的响应"""
        data = {'sharpe': 1.5, 'return': 0.25, 'trades': 150}
        resp = Response.success(data=data)
        assert isinstance(resp.data, dict)
        assert resp.data['sharpe'] == 1.5

    def test_response_with_primitive_types(self):
        """测试带基本类型的响应"""
        # 整数
        resp1 = Response.success(data=42)
        assert resp1.data == 42

        # 浮点数
        resp2 = Response.success(data=3.14)
        assert resp2.data == 3.14

        # 字符串
        resp3 = Response.success(data="结果")
        assert resp3.data == "结果"

        # 布尔值
        resp4 = Response.success(data=True)
        assert resp4.data is True

    def test_response_with_none_data(self):
        """测试data为None的响应"""
        resp = Response.success(data=None, message="操作完成，无返回数据")
        assert resp.data is None
        assert resp.is_success()


class TestResponseMetadata:
    """测试元数据功能"""

    def test_metadata_with_various_types(self):
        """测试各种类型的元数据"""
        resp = Response.success(
            data=[1, 2, 3],
            count=3,
            elapsed_time=2.5,
            is_cached=True,
            tags=['feature', 'alpha'],
            config={'window': 20}
        )

        assert resp.metadata['count'] == 3
        assert resp.metadata['elapsed_time'] == 2.5
        assert resp.metadata['is_cached'] is True
        assert resp.metadata['tags'] == ['feature', 'alpha']
        assert resp.metadata['config'] == {'window': 20}

    def test_empty_metadata(self):
        """测试空元数据"""
        resp = Response.success(data=[1, 2, 3])
        assert resp.metadata == {}

    def test_metadata_in_error_response(self):
        """测试错误响应中的元数据"""
        resp = Response.error(
            error="API调用失败",
            error_code="API_ERROR",
            provider="akshare",
            stock_code="000001",
            retry_count=3,
            last_error="Timeout"
        )

        assert resp.metadata['provider'] == 'akshare'
        assert resp.metadata['stock_code'] == '000001'
        assert resp.metadata['retry_count'] == 3
        assert resp.metadata['last_error'] == 'Timeout'


class TestResponseRealWorldScenarios:
    """测试真实世界场景"""

    def test_feature_calculation_success(self):
        """测试特征计算成功场景"""
        resp = Response.success(
            data={'features': 'mock_dataframe', 'columns': 125},
            message="特征计算完成",
            n_features=125,
            n_samples=1000,
            elapsed_time="2.5s",
            cache_hit=False
        )

        assert resp.is_success()
        assert resp.data['columns'] == 125
        assert resp.metadata['n_features'] == 125
        assert resp.to_dict()['status'] == 'success'

    def test_data_validation_error(self):
        """测试数据验证错误场景"""
        resp = Response.error(
            error="股票代码不能为空",
            error_code="EMPTY_STOCK_CODE",
            field="stock_code",
            value="",
            validator="validate_stock_code"
        )

        assert resp.is_error()
        assert resp.error_message == "股票代码不能为空"
        assert resp.error_code == "EMPTY_STOCK_CODE"
        assert resp.metadata['field'] == 'stock_code'

    def test_partial_data_warning(self):
        """测试部分数据警告场景"""
        resp = Response.warning(
            message="部分数据缺失，已使用前向填充",
            data={'processed': True, 'rows': 995},
            missing_count=5,
            fill_method="forward",
            affected_columns=['close', 'volume']
        )

        assert resp.is_warning()
        assert resp.data['rows'] == 995
        assert resp.metadata['missing_count'] == 5

    def test_backtest_result_success(self):
        """测试回测结果成功场景"""
        resp = Response.success(
            data={
                'sharpe_ratio': 1.52,
                'annualized_return': 0.25,
                'max_drawdown': -0.15,
                'total_trades': 150
            },
            message="回测完成",
            strategy="MomentumStrategy",
            period="2024-01-01至2024-12-31",
            execution_time="5.2s"
        )

        assert resp.is_success()
        assert resp.data['sharpe_ratio'] == 1.52
        assert resp.metadata['strategy'] == 'MomentumStrategy'

    def test_model_training_error_with_partial_results(self):
        """测试模型训练错误但有部分结果场景"""
        resp = Response.error(
            error="训练提前停止",
            error_code="EARLY_STOPPING",
            data={
                'best_iteration': 50,
                'best_score': 0.75,
                'validation_score': 0.72
            },
            reason="验证集性能连续下降",
            epochs_completed=50,
            total_epochs=100
        )

        assert resp.is_error()
        assert resp.data['best_iteration'] == 50
        assert resp.metadata['epochs_completed'] == 50

    def test_data_provider_fallback_warning(self):
        """测试数据提供者降级警告场景"""
        resp = Response.warning(
            message="主数据源失败，已切换到备用数据源",
            data={'source': 'tushare', 'data': 'mock_df'},
            primary_provider='akshare',
            fallback_provider='tushare',
            primary_error='Connection timeout'
        )

        assert resp.is_warning()
        assert resp.data['source'] == 'tushare'
        assert resp.metadata['fallback_provider'] == 'tushare'


class TestResponseEdgeCases:
    """测试边界情况"""

    def test_response_with_very_long_message(self):
        """测试超长消息"""
        long_message = "A" * 1000
        resp = Response.success(message=long_message)
        assert len(resp.message) == 1000
        assert resp.is_success()

    def test_response_with_special_characters_in_message(self):
        """测试消息中的特殊字符"""
        special_message = "错误: 文件'data.csv'不存在 (路径: /tmp/data.csv)"
        resp = Response.error(error=special_message)
        assert resp.error_message == special_message

    def test_response_with_unicode_characters(self):
        """测试Unicode字符"""
        resp = Response.success(
            message="数据处理完成 ✓",
            data={'中文': '测试', 'emoji': '🚀'}
        )
        assert resp.message == "数据处理完成 ✓"
        assert resp.data['中文'] == '测试'

    def test_response_with_large_metadata(self):
        """测试大量元数据"""
        metadata = {f'key_{i}': f'value_{i}' for i in range(100)}
        resp = Response.success(data=[1, 2, 3], **metadata)
        assert len(resp.metadata) == 100

    def test_response_with_nested_dict_data(self):
        """测试嵌套字典数据"""
        nested_data = {
            'level1': {
                'level2': {
                    'level3': {
                        'value': 42
                    }
                }
            }
        }
        resp = Response.success(data=nested_data)
        assert resp.data['level1']['level2']['level3']['value'] == 42

    def test_response_with_empty_string_message(self):
        """测试空字符串消息"""
        resp = Response(status=ResponseStatus.SUCCESS, message="")
        assert resp.message == ""
        result_dict = resp.to_dict()
        assert 'message' not in result_dict  # 空字符串不应包含在字典中

    def test_response_with_zero_values(self):
        """测试值为0的情况"""
        resp = Response.success(
            data=0,
            count=0,
            elapsed_time=0.0
        )
        assert resp.data == 0
        assert resp.metadata['count'] == 0
        assert resp.metadata['elapsed_time'] == 0.0


class TestResponseEquality:
    """测试Response相等性比较"""

    def test_same_success_responses(self):
        """测试相同的成功响应"""
        resp1 = Response.success(data=[1, 2, 3], message="完成", count=3)
        resp2 = Response.success(data=[1, 2, 3], message="完成", count=3)

        # dataclass会自动生成__eq__方法
        assert resp1.status == resp2.status
        assert resp1.data == resp2.data
        assert resp1.message == resp2.message
        assert resp1.metadata == resp2.metadata

    def test_different_responses(self):
        """测试不同的响应"""
        resp1 = Response.success(data=[1, 2, 3])
        resp2 = Response.error(error="失败")

        assert resp1.status != resp2.status


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
