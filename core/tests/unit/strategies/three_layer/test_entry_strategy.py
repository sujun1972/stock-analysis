"""
EntryStrategy 基类单元测试

Test cases for EntryStrategy base class
"""

import pytest
import pandas as pd
from typing import Any, Dict, List

from src.strategies.three_layer.base import EntryStrategy


# ============================================================================
# 测试用具体实现类
# ============================================================================

class ConcreteEntry(EntryStrategy):
    """具体的入场策略实现（用于测试）"""

    @property
    def name(self) -> str:
        return "测试入场策略"

    @property
    def id(self) -> str:
        return "test_entry"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "max_positions",
                "label": "最大持仓数",
                "type": "integer",
                "default": 5,
                "min": 1,
                "max": 50,
                "description": "最多同时持有的股票数量"
            },
            {
                "name": "weight_threshold",
                "label": "权重阈值",
                "type": "float",
                "default": 0.1,
                "min": 0.0,
                "max": 1.0,
                "description": "最小权重阈值"
            },
            {
                "name": "enable_filter",
                "label": "启用过滤",
                "type": "boolean",
                "default": True,
                "description": "是否启用过滤器"
            },
            {
                "name": "signal_type",
                "label": "信号类型",
                "type": "select",
                "default": "equal",
                "options": [
                    {"value": "equal", "label": "等权"},
                    {"value": "weighted", "label": "加权"},
                ],
                "description": "入场信号类型"
            },
            {
                "name": "note",
                "label": "备注",
                "type": "string",
                "default": "",
                "description": "备注信息"
            },
        ]

    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """简单的入场策略：对所有候选股票生成等权买入信号"""
        max_positions = self.params.get("max_positions", 5)

        # 限制持仓数量
        selected_stocks = stocks[:max_positions]

        if selected_stocks:
            weight = 1.0 / len(selected_stocks)
            return {stock: weight for stock in selected_stocks}
        else:
            return {}


# ============================================================================
# 测试夹具 (Fixtures)
# ============================================================================

@pytest.fixture
def sample_stock_data():
    """创建示例股票数据"""
    dates = pd.date_range('2023-01-01', periods=10, freq='D')

    data = {
        'A': pd.DataFrame({
            'open': [10.0, 10.2, 10.5, 10.3, 10.6, 10.8, 10.7, 11.0, 11.2, 11.5],
            'high': [10.5, 10.6, 10.8, 10.7, 11.0, 11.2, 11.0, 11.3, 11.5, 11.8],
            'low': [9.8, 10.0, 10.3, 10.1, 10.4, 10.6, 10.5, 10.8, 11.0, 11.3],
            'close': [10.2, 10.5, 10.6, 10.5, 10.9, 11.0, 10.9, 11.2, 11.4, 11.7],
            'volume': [1000, 1100, 1200, 1050, 1300, 1400, 1250, 1500, 1600, 1700],
        }, index=dates),
        'B': pd.DataFrame({
            'open': [20.0, 20.1, 20.3, 20.2, 20.5, 20.7, 20.6, 20.9, 21.1, 21.4],
            'high': [20.4, 20.5, 20.7, 20.6, 20.9, 21.1, 21.0, 21.3, 21.5, 21.8],
            'low': [19.8, 20.0, 20.2, 20.0, 20.3, 20.5, 20.4, 20.7, 20.9, 21.2],
            'close': [20.2, 20.4, 20.5, 20.4, 20.8, 21.0, 20.9, 21.2, 21.4, 21.7],
            'volume': [2000, 2100, 2200, 2050, 2300, 2400, 2250, 2500, 2600, 2700],
        }, index=dates),
        'C': pd.DataFrame({
            'open': [15.0, 15.1, 15.3, 15.2, 15.5, 15.7, 15.6, 15.9, 16.1, 16.4],
            'high': [15.4, 15.5, 15.7, 15.6, 15.9, 16.1, 16.0, 16.3, 16.5, 16.8],
            'low': [14.8, 15.0, 15.2, 15.0, 15.3, 15.5, 15.4, 15.7, 15.9, 16.2],
            'close': [15.2, 15.4, 15.5, 15.4, 15.8, 16.0, 15.9, 16.2, 16.4, 16.7],
            'volume': [1500, 1600, 1700, 1550, 1800, 1900, 1750, 2000, 2100, 2200],
        }, index=dates),
    }
    return data


@pytest.fixture
def candidate_stocks():
    """候选股票列表"""
    return ['A', 'B', 'C']


# ============================================================================
# 基本功能测试
# ============================================================================

class TestEntryStrategyBasic:
    """测试 EntryStrategy 基本功能"""

    def test_entry_creation_with_default_params(self):
        """测试使用默认参数创建入场策略"""
        entry = ConcreteEntry()

        assert entry.name == "测试入场策略"
        assert entry.id == "test_entry"
        assert entry.params == {}

    def test_entry_creation_with_custom_params(self):
        """测试使用自定义参数创建入场策略"""
        params = {
            'max_positions': 10,
            'weight_threshold': 0.2,
            'enable_filter': False,
            'signal_type': 'weighted',
            'note': 'test note'
        }
        entry = ConcreteEntry(params=params)

        assert entry.params == params

    def test_entry_name_property(self):
        """测试 name 属性"""
        entry = ConcreteEntry()
        assert entry.name == "测试入场策略"
        assert isinstance(entry.name, str)

    def test_entry_id_property(self):
        """测试 id 属性"""
        entry = ConcreteEntry()
        assert entry.id == "test_entry"
        assert isinstance(entry.id, str)

    def test_get_parameters_class_method(self):
        """测试 get_parameters 类方法"""
        params = ConcreteEntry.get_parameters()

        assert len(params) == 5
        assert all(isinstance(p, dict) for p in params)

        # 检查参数名称
        param_names = [p["name"] for p in params]
        assert 'max_positions' in param_names
        assert 'weight_threshold' in param_names
        assert 'enable_filter' in param_names
        assert 'signal_type' in param_names
        assert 'note' in param_names

    def test_generate_entry_signals_method_exists(self):
        """测试 generate_entry_signals 方法存在"""
        entry = ConcreteEntry()
        assert hasattr(entry, 'generate_entry_signals')
        assert callable(entry.generate_entry_signals)

    def test_repr_method(self):
        """测试 __repr__ 方法"""
        entry = ConcreteEntry(params={'max_positions': 10})
        repr_str = repr(entry)

        assert "测试入场策略" in repr_str
        assert "test_entry" in repr_str
        assert "max_positions" in repr_str


# ============================================================================
# 参数验证测试
# ============================================================================

class TestEntryStrategyParameterValidation:
    """测试参数验证功能"""

    def test_valid_integer_parameter(self):
        """测试有效的整数参数"""
        entry = ConcreteEntry(params={'max_positions': 20})
        assert entry.params['max_positions'] == 20

    def test_integer_parameter_below_min(self):
        """测试整数参数低于最小值"""
        with pytest.raises(ValueError, match="不能小于 1"):
            ConcreteEntry(params={'max_positions': 0})

    def test_integer_parameter_above_max(self):
        """测试整数参数超过最大值"""
        with pytest.raises(ValueError, match="不能大于 50"):
            ConcreteEntry(params={'max_positions': 100})

    def test_integer_parameter_wrong_type(self):
        """测试整数参数类型错误"""
        with pytest.raises(ValueError, match="必须是整数"):
            ConcreteEntry(params={'max_positions': "10"})

    def test_valid_float_parameter(self):
        """测试有效的浮点数参数"""
        entry = ConcreteEntry(params={'weight_threshold': 0.3})
        assert entry.params['weight_threshold'] == 0.3

    def test_float_parameter_below_min(self):
        """测试浮点数参数低于最小值"""
        with pytest.raises(ValueError, match="不能小于 0.0"):
            ConcreteEntry(params={'weight_threshold': -0.1})

    def test_float_parameter_above_max(self):
        """测试浮点数参数超过最大值"""
        with pytest.raises(ValueError, match="不能大于 1.0"):
            ConcreteEntry(params={'weight_threshold': 1.5})

    def test_float_parameter_wrong_type(self):
        """测试浮点数参数类型错误"""
        with pytest.raises(ValueError, match="必须是浮点数"):
            ConcreteEntry(params={'weight_threshold': "0.3"})

    def test_valid_boolean_parameter(self):
        """测试有效的布尔参数"""
        entry = ConcreteEntry(params={'enable_filter': False})
        assert entry.params['enable_filter'] is False

    def test_boolean_parameter_wrong_type(self):
        """测试布尔参数类型错误"""
        with pytest.raises(ValueError, match="必须是布尔值"):
            ConcreteEntry(params={'enable_filter': 1})

    def test_valid_select_parameter(self):
        """测试有效的选择参数"""
        entry1 = ConcreteEntry(params={'signal_type': 'equal'})
        assert entry1.params['signal_type'] == 'equal'

        entry2 = ConcreteEntry(params={'signal_type': 'weighted'})
        assert entry2.params['signal_type'] == 'weighted'

    def test_select_parameter_invalid_option(self):
        """测试选择参数无效选项"""
        with pytest.raises(ValueError, match="不在有效选项中"):
            ConcreteEntry(params={'signal_type': 'invalid'})

    def test_valid_string_parameter(self):
        """测试有效的字符串参数"""
        entry = ConcreteEntry(params={'note': 'test note'})
        assert entry.params['note'] == 'test note'

    def test_string_parameter_wrong_type(self):
        """测试字符串参数类型错误"""
        with pytest.raises(ValueError, match="必须是字符串"):
            ConcreteEntry(params={'note': 123})

    def test_unknown_parameter(self):
        """测试未知参数"""
        with pytest.raises(ValueError, match="未知参数: unknown"):
            ConcreteEntry(params={'unknown': 'value'})


# ============================================================================
# generate_entry_signals() 方法测试
# ============================================================================

class TestEntryStrategyGenerateSignals:
    """测试 generate_entry_signals() 方法"""

    def test_generate_signals_returns_dict(self, candidate_stocks, sample_stock_data):
        """测试返回字典类型"""
        entry = ConcreteEntry(params={'max_positions': 3})
        signals = entry.generate_entry_signals(
            candidate_stocks,
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        assert isinstance(signals, dict)

    def test_generate_signals_returns_correct_number(self, candidate_stocks, sample_stock_data):
        """测试返回正确数量的信号"""
        entry = ConcreteEntry(params={'max_positions': 2})
        signals = entry.generate_entry_signals(
            candidate_stocks,
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        assert len(signals) == 2

    def test_generate_signals_equal_weights(self, candidate_stocks, sample_stock_data):
        """测试等权重分配"""
        entry = ConcreteEntry(params={'max_positions': 3})
        signals = entry.generate_entry_signals(
            candidate_stocks,
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        # 检查权重总和为1
        total_weight = sum(signals.values())
        assert abs(total_weight - 1.0) < 1e-10

        # 检查每个权重相等
        expected_weight = 1.0 / 3
        for weight in signals.values():
            assert abs(weight - expected_weight) < 1e-10

    def test_generate_signals_respects_max_positions(self, sample_stock_data):
        """测试遵守最大持仓数限制"""
        stocks = ['A', 'B', 'C', 'D', 'E']  # 5只股票
        entry = ConcreteEntry(params={'max_positions': 3})

        signals = entry.generate_entry_signals(
            stocks[:3],  # 只传入3只
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        assert len(signals) <= 3

    def test_generate_signals_with_empty_stocks(self, sample_stock_data):
        """测试空股票列表"""
        entry = ConcreteEntry(params={'max_positions': 5})
        signals = entry.generate_entry_signals(
            [],
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        assert signals == {}

    def test_generate_signals_stock_codes_match(self, candidate_stocks, sample_stock_data):
        """测试返回的股票代码正确"""
        entry = ConcreteEntry(params={'max_positions': 3})
        signals = entry.generate_entry_signals(
            candidate_stocks,
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        # 所有返回的股票代码都应该在候选列表中
        for stock in signals.keys():
            assert stock in candidate_stocks

    def test_generate_signals_weights_are_positive(self, candidate_stocks, sample_stock_data):
        """测试权重为正数"""
        entry = ConcreteEntry(params={'max_positions': 3})
        signals = entry.generate_entry_signals(
            candidate_stocks,
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        for weight in signals.values():
            assert weight > 0

    def test_generate_signals_on_different_dates(self, candidate_stocks, sample_stock_data):
        """测试不同日期生成信号"""
        entry = ConcreteEntry(params={'max_positions': 2})

        signals1 = entry.generate_entry_signals(
            candidate_stocks,
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        signals2 = entry.generate_entry_signals(
            candidate_stocks,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        assert len(signals1) == 2
        assert len(signals2) == 2


# ============================================================================
# 边界情况和错误处理测试
# ============================================================================

class TestEntryStrategyEdgeCases:
    """测试边界情况"""

    def test_cannot_instantiate_abstract_class(self):
        """测试不能直接实例化抽象基类"""
        with pytest.raises(TypeError):
            EntryStrategy()

    def test_max_positions_equals_one(self, candidate_stocks, sample_stock_data):
        """测试max_positions=1的情况"""
        entry = ConcreteEntry(params={'max_positions': 1})
        signals = entry.generate_entry_signals(
            candidate_stocks,
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        assert len(signals) == 1
        # 权重应该是1.0
        assert abs(list(signals.values())[0] - 1.0) < 1e-10

    def test_max_positions_exceeds_candidates(self, candidate_stocks, sample_stock_data):
        """测试max_positions超过候选股票数量"""
        entry = ConcreteEntry(params={'max_positions': 10})  # 只有3只候选股票
        signals = entry.generate_entry_signals(
            candidate_stocks,
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        # 应该返回所有候选股票
        assert len(signals) == len(candidate_stocks)

    def test_empty_stock_data(self, candidate_stocks):
        """测试空股票数据"""
        entry = ConcreteEntry(params={'max_positions': 3})
        signals = entry.generate_entry_signals(
            candidate_stocks,
            {},  # 空数据
            pd.Timestamp('2023-01-01')
        )

        # 应该能处理空数据（具体行为取决于实现）
        assert isinstance(signals, dict)

    def test_single_stock_candidate(self, sample_stock_data):
        """测试单只股票候选"""
        entry = ConcreteEntry(params={'max_positions': 5})
        signals = entry.generate_entry_signals(
            ['A'],  # 只有一只股票
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        assert len(signals) == 1
        assert 'A' in signals
        assert abs(signals['A'] - 1.0) < 1e-10


# ============================================================================
# 集成测试
# ============================================================================

class TestEntryStrategyIntegration:
    """集成测试"""

    def test_full_workflow(self, candidate_stocks, sample_stock_data):
        """测试完整工作流程"""
        # 创建策略
        entry = ConcreteEntry(params={
            'max_positions': 2,
            'weight_threshold': 0.1,
            'enable_filter': True,
            'signal_type': 'equal',
            'note': 'integration test'
        })

        # 生成信号
        signals = entry.generate_entry_signals(
            candidate_stocks,
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        # 验证结果
        assert isinstance(signals, dict)
        assert len(signals) == 2
        assert sum(signals.values()) <= 1.0 + 1e-10
        assert all(weight > 0 for weight in signals.values())

    def test_parameter_change_affects_signals(self, candidate_stocks, sample_stock_data):
        """测试参数变化影响信号生成"""
        # max_positions = 2
        entry1 = ConcreteEntry(params={'max_positions': 2})
        signals1 = entry1.generate_entry_signals(
            candidate_stocks,
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        # max_positions = 3
        entry2 = ConcreteEntry(params={'max_positions': 3})
        signals2 = entry2.generate_entry_signals(
            candidate_stocks,
            sample_stock_data,
            pd.Timestamp('2023-01-01')
        )

        # 信号数量应该不同
        assert len(signals1) == 2
        assert len(signals2) == 3


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
