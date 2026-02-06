"""
StockSelector 基类单元测试

Test cases for StockSelector base class
"""

import pytest
import pandas as pd
from typing import List

from src.strategies.three_layer.base import StockSelector, SelectorParameter


# ============================================================================
# 测试用具体实现类
# ============================================================================

class ConcreteSelector(StockSelector):
    """具体的选股器实现（用于测试）"""

    @property
    def name(self) -> str:
        return "测试选股器"

    @property
    def id(self) -> str:
        return "test_selector"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="top_n",
                label="选股数量",
                type="integer",
                default=10,
                min_value=1,
                max_value=100,
                description="选择前 N 只股票"
            ),
            SelectorParameter(
                name="threshold",
                label="阈值",
                type="float",
                default=0.5,
                min_value=0.0,
                max_value=1.0,
                description="筛选阈值"
            ),
            SelectorParameter(
                name="use_filter",
                label="使用过滤",
                type="boolean",
                default=True,
                description="是否使用过滤器"
            ),
            SelectorParameter(
                name="method",
                label="方法",
                type="select",
                default="momentum",
                options=[
                    {"value": "momentum", "label": "动量"},
                    {"value": "value", "label": "价值"},
                ],
                description="选股方法"
            ),
            SelectorParameter(
                name="comment",
                label="备注",
                type="string",
                default="",
                description="备注信息"
            ),
        ]

    def select(self, date: pd.Timestamp, market_data: pd.DataFrame) -> List[str]:
        """简单的选股逻辑：选择价格最高的前 top_n 只股票"""
        top_n = self.params.get("top_n", 10)
        try:
            current_prices = market_data.loc[date].dropna()
            return current_prices.nlargest(top_n).index.tolist()
        except KeyError:
            return []


# ============================================================================
# 测试夹具 (Fixtures)
# ============================================================================

@pytest.fixture
def sample_market_data():
    """创建示例市场数据"""
    dates = pd.date_range('2023-01-01', periods=10, freq='D')
    stocks = ['A', 'B', 'C', 'D', 'E']

    data = pd.DataFrame(
        {
            'A': [10.0, 10.5, 11.0, 10.8, 11.2, 11.5, 11.3, 11.8, 12.0, 12.2],
            'B': [20.0, 20.2, 20.4, 20.1, 20.5, 20.8, 20.6, 21.0, 21.2, 21.5],
            'C': [15.0, 14.8, 15.2, 15.5, 15.3, 15.8, 16.0, 15.9, 16.2, 16.5],
            'D': [8.0, 8.2, 8.1, 8.3, 8.5, 8.4, 8.6, 8.8, 8.7, 9.0],
            'E': [12.0, 12.1, 12.3, 12.2, 12.5, 12.4, 12.7, 12.9, 13.0, 13.2],
        },
        index=dates
    )
    return data


# ============================================================================
# 基本功能测试
# ============================================================================

class TestStockSelectorBasic:
    """测试 StockSelector 基本功能"""

    def test_selector_creation_with_default_params(self):
        """测试使用默认参数创建选股器"""
        selector = ConcreteSelector()

        assert selector.name == "测试选股器"
        assert selector.id == "test_selector"
        assert selector.params == {}

    def test_selector_creation_with_custom_params(self):
        """测试使用自定义参数创建选股器"""
        params = {
            'top_n': 20,
            'threshold': 0.7,
            'use_filter': False,
            'method': 'value',
            'comment': 'test comment'
        }
        selector = ConcreteSelector(params=params)

        assert selector.params == params

    def test_selector_name_property(self):
        """测试 name 属性"""
        selector = ConcreteSelector()
        assert selector.name == "测试选股器"
        assert isinstance(selector.name, str)

    def test_selector_id_property(self):
        """测试 id 属性"""
        selector = ConcreteSelector()
        assert selector.id == "test_selector"
        assert isinstance(selector.id, str)

    def test_get_parameters_class_method(self):
        """测试 get_parameters 类方法"""
        params = ConcreteSelector.get_parameters()

        assert len(params) == 5
        assert all(isinstance(p, SelectorParameter) for p in params)

        # 检查参数名称
        param_names = [p.name for p in params]
        assert 'top_n' in param_names
        assert 'threshold' in param_names
        assert 'use_filter' in param_names
        assert 'method' in param_names
        assert 'comment' in param_names

    def test_select_method_exists(self):
        """测试 select 方法存在"""
        selector = ConcreteSelector()
        assert hasattr(selector, 'select')
        assert callable(selector.select)

    def test_repr_method(self):
        """测试 __repr__ 方法"""
        selector = ConcreteSelector(params={'top_n': 20})
        repr_str = repr(selector)

        assert "测试选股器" in repr_str
        assert "test_selector" in repr_str
        assert "top_n" in repr_str


# ============================================================================
# 参数验证测试
# ============================================================================

class TestStockSelectorParameterValidation:
    """测试参数验证功能"""

    def test_valid_integer_parameter(self):
        """测试有效的整数参数"""
        selector = ConcreteSelector(params={'top_n': 50})
        assert selector.params['top_n'] == 50

    def test_integer_parameter_below_min(self):
        """测试整数参数低于最小值"""
        with pytest.raises(ValueError, match="不能小于 1"):
            ConcreteSelector(params={'top_n': 0})

    def test_integer_parameter_above_max(self):
        """测试整数参数超过最大值"""
        with pytest.raises(ValueError, match="不能大于 100"):
            ConcreteSelector(params={'top_n': 150})

    def test_integer_parameter_wrong_type(self):
        """测试整数参数类型错误"""
        with pytest.raises(ValueError, match="必须是整数"):
            ConcreteSelector(params={'top_n': "50"})

    def test_valid_float_parameter(self):
        """测试有效的浮点数参数"""
        selector = ConcreteSelector(params={'threshold': 0.75})
        assert selector.params['threshold'] == 0.75

    def test_float_parameter_below_min(self):
        """测试浮点数参数低于最小值"""
        with pytest.raises(ValueError, match="不能小于 0.0"):
            ConcreteSelector(params={'threshold': -0.1})

    def test_float_parameter_above_max(self):
        """测试浮点数参数超过最大值"""
        with pytest.raises(ValueError, match="不能大于 1.0"):
            ConcreteSelector(params={'threshold': 1.5})

    def test_float_parameter_wrong_type(self):
        """测试浮点数参数类型错误"""
        with pytest.raises(ValueError, match="必须是浮点数"):
            ConcreteSelector(params={'threshold': "0.5"})

    def test_float_parameter_accepts_integer(self):
        """测试浮点数参数接受整数"""
        # 浮点数参数应该接受整数
        selector = ConcreteSelector(params={'threshold': 1})
        assert selector.params['threshold'] == 1

    def test_valid_boolean_parameter(self):
        """测试有效的布尔参数"""
        selector = ConcreteSelector(params={'use_filter': False})
        assert selector.params['use_filter'] is False

    def test_boolean_parameter_wrong_type(self):
        """测试布尔参数类型错误"""
        with pytest.raises(ValueError, match="必须是布尔值"):
            ConcreteSelector(params={'use_filter': 1})

    def test_valid_select_parameter(self):
        """测试有效的选择参数"""
        selector = ConcreteSelector(params={'method': 'momentum'})
        assert selector.params['method'] == 'momentum'

        selector2 = ConcreteSelector(params={'method': 'value'})
        assert selector2.params['method'] == 'value'

    def test_select_parameter_invalid_option(self):
        """测试选择参数无效选项"""
        with pytest.raises(ValueError, match="不在有效选项中"):
            ConcreteSelector(params={'method': 'invalid'})

    def test_valid_string_parameter(self):
        """测试有效的字符串参数"""
        selector = ConcreteSelector(params={'comment': 'test comment'})
        assert selector.params['comment'] == 'test comment'

    def test_string_parameter_wrong_type(self):
        """测试字符串参数类型错误"""
        with pytest.raises(ValueError, match="必须是字符串"):
            ConcreteSelector(params={'comment': 123})

    def test_unknown_parameter(self):
        """测试未知参数"""
        with pytest.raises(ValueError, match="未知参数: unknown"):
            ConcreteSelector(params={'unknown': 'value'})

    def test_multiple_parameters(self):
        """测试多个参数同时设置"""
        params = {
            'top_n': 30,
            'threshold': 0.6,
            'use_filter': True,
            'method': 'momentum',
            'comment': 'multi params test'
        }
        selector = ConcreteSelector(params=params)
        assert selector.params == params

    def test_empty_parameters(self):
        """测试空参数"""
        selector = ConcreteSelector(params={})
        assert selector.params == {}


# ============================================================================
# select() 方法测试
# ============================================================================

class TestStockSelectorSelectMethod:
    """测试 select() 方法"""

    def test_select_returns_list(self, sample_market_data):
        """测试 select 返回列表"""
        selector = ConcreteSelector(params={'top_n': 3})
        result = selector.select(
            pd.Timestamp('2023-01-01'),
            sample_market_data
        )

        assert isinstance(result, list)

    def test_select_returns_correct_number(self, sample_market_data):
        """测试 select 返回正确数量的股票"""
        selector = ConcreteSelector(params={'top_n': 3})
        result = selector.select(
            pd.Timestamp('2023-01-01'),
            sample_market_data
        )

        assert len(result) == 3

    def test_select_returns_highest_prices(self, sample_market_data):
        """测试 select 返回价格最高的股票"""
        selector = ConcreteSelector(params={'top_n': 3})
        result = selector.select(
            pd.Timestamp('2023-01-01'),
            sample_market_data
        )

        # 2023-01-01 的价格：A=10.0, B=20.0, C=15.0, D=8.0, E=12.0
        # 前3名应该是：B, C, E
        assert set(result) == {'B', 'C', 'E'}

    def test_select_with_different_top_n(self, sample_market_data):
        """测试不同的 top_n 参数"""
        # top_n = 2
        selector1 = ConcreteSelector(params={'top_n': 2})
        result1 = selector1.select(
            pd.Timestamp('2023-01-01'),
            sample_market_data
        )
        assert len(result1) == 2

        # top_n = 5
        selector2 = ConcreteSelector(params={'top_n': 5})
        result2 = selector2.select(
            pd.Timestamp('2023-01-01'),
            sample_market_data
        )
        assert len(result2) == 5

    def test_select_with_invalid_date(self, sample_market_data):
        """测试无效日期返回空列表"""
        selector = ConcreteSelector(params={'top_n': 3})
        result = selector.select(
            pd.Timestamp('2024-01-01'),  # 不在数据范围内
            sample_market_data
        )

        assert result == []

    def test_select_on_different_dates(self, sample_market_data):
        """测试不同日期的选股结果"""
        selector = ConcreteSelector(params={'top_n': 2})

        # 第一天
        result1 = selector.select(
            pd.Timestamp('2023-01-01'),
            sample_market_data
        )
        assert len(result1) == 2

        # 最后一天
        result2 = selector.select(
            pd.Timestamp('2023-01-10'),
            sample_market_data
        )
        assert len(result2) == 2


# ============================================================================
# SelectorParameter 数据类测试
# ============================================================================

class TestSelectorParameter:
    """测试 SelectorParameter 数据类"""

    def test_selector_parameter_creation(self):
        """测试创建 SelectorParameter"""
        param = SelectorParameter(
            name="test_param",
            label="测试参数",
            type="integer",
            default=10,
            min_value=1,
            max_value=100,
            description="这是一个测试参数"
        )

        assert param.name == "test_param"
        assert param.label == "测试参数"
        assert param.type == "integer"
        assert param.default == 10
        assert param.min_value == 1
        assert param.max_value == 100
        assert param.description == "这是一个测试参数"

    def test_selector_parameter_optional_fields(self):
        """测试可选字段的默认值"""
        param = SelectorParameter(
            name="test",
            label="Test",
            type="string",
            default=""
        )

        assert param.min_value is None
        assert param.max_value is None
        assert param.description == ""
        assert param.options is None

    def test_selector_parameter_with_options(self):
        """测试带选项的参数"""
        options = [
            {"value": "opt1", "label": "选项1"},
            {"value": "opt2", "label": "选项2"},
        ]
        param = SelectorParameter(
            name="choice",
            label="选择",
            type="select",
            default="opt1",
            options=options,
            description="选择参数"
        )

        assert param.options == options
        assert len(param.options) == 2


# ============================================================================
# 边界情况和错误处理测试
# ============================================================================

class TestStockSelectorEdgeCases:
    """测试边界情况"""

    def test_cannot_instantiate_abstract_class(self):
        """测试不能直接实例化抽象基类"""
        with pytest.raises(TypeError):
            StockSelector()

    def test_selector_with_nan_values(self):
        """测试包含 NaN 值的数据"""
        import numpy as np

        data = pd.DataFrame(
            {
                'A': [10.0, np.nan, 11.0],
                'B': [20.0, 20.5, np.nan],
                'C': [15.0, 15.5, 16.0],
            },
            index=pd.date_range('2023-01-01', periods=3)
        )

        selector = ConcreteSelector(params={'top_n': 2})
        result = selector.select(pd.Timestamp('2023-01-01'), data)

        # NaN 值应该被自动过滤
        assert len(result) == 2
        assert 'B' in result  # B 在第一天有值
        assert 'C' in result

    def test_selector_with_empty_dataframe(self):
        """测试空 DataFrame"""
        data = pd.DataFrame()

        selector = ConcreteSelector(params={'top_n': 3})
        result = selector.select(pd.Timestamp('2023-01-01'), data)

        assert result == []

    def test_selector_top_n_exceeds_available_stocks(self):
        """测试 top_n 超过可用股票数量"""
        data = pd.DataFrame(
            {
                'A': [10.0],
                'B': [20.0],
            },
            index=[pd.Timestamp('2023-01-01')]
        )

        selector = ConcreteSelector(params={'top_n': 10})  # 只有2只股票
        result = selector.select(pd.Timestamp('2023-01-01'), data)

        # 应该返回所有可用股票
        assert len(result) == 2


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
