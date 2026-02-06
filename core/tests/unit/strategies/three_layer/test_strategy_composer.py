"""
StrategyComposer 单元测试

Test cases for StrategyComposer class
"""

import pytest
import pandas as pd
from typing import Any, Dict, List

from src.strategies.three_layer.base import (
    StrategyComposer,
    StockSelector,
    EntryStrategy,
    ExitStrategy,
    SelectorParameter,
    Position,
)


# ============================================================================
# 测试用具体实现类
# ============================================================================

class MockSelector(StockSelector):
    """模拟选股器"""

    @property
    def name(self) -> str:
        return "模拟选股器"

    @property
    def id(self) -> str:
        return "mock_selector"

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
            )
        ]

    def select(self, date: pd.Timestamp, market_data: pd.DataFrame) -> List[str]:
        return []


class MockEntry(EntryStrategy):
    """模拟入场策略"""

    @property
    def name(self) -> str:
        return "模拟入场策略"

    @property
    def id(self) -> str:
        return "mock_entry"

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
            }
        ]

    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        return {}


class MockExit(ExitStrategy):
    """模拟退出策略"""

    @property
    def name(self) -> str:
        return "模拟退出策略"

    @property
    def id(self) -> str:
        return "mock_exit"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "stop_loss_pct",
                "label": "止损百分比",
                "type": "float",
                "default": -5.0,
                "min": -20.0,
                "max": -1.0,
                "description": "亏损达到此百分比时卖出"
            }
        ]

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> List[str]:
        return []


# ============================================================================
# 测试夹具 (Fixtures)
# ============================================================================

@pytest.fixture
def mock_selector():
    """创建模拟选股器"""
    return MockSelector(params={'top_n': 20})


@pytest.fixture
def mock_entry():
    """创建模拟入场策略"""
    return MockEntry(params={'max_positions': 10})


@pytest.fixture
def mock_exit():
    """创建模拟退出策略"""
    return MockExit(params={'stop_loss_pct': -5.0})


@pytest.fixture
def composer(mock_selector, mock_entry, mock_exit):
    """创建策略组合器"""
    return StrategyComposer(
        selector=mock_selector,
        entry=mock_entry,
        exit_strategy=mock_exit,
        rebalance_freq='W'
    )


# ============================================================================
# 基本功能测试
# ============================================================================

class TestStrategyComposerBasic:
    """测试 StrategyComposer 基本功能"""

    def test_composer_creation(self, mock_selector, mock_entry, mock_exit):
        """测试创建组合器"""
        composer = StrategyComposer(
            selector=mock_selector,
            entry=mock_entry,
            exit_strategy=mock_exit,
            rebalance_freq='W'
        )

        assert composer.selector == mock_selector
        assert composer.entry == mock_entry
        assert composer.exit == mock_exit
        assert composer.rebalance_freq == 'W'

    def test_composer_with_different_frequencies(self, mock_selector, mock_entry, mock_exit):
        """测试不同的调仓频率"""
        # 日频
        composer_d = StrategyComposer(
            selector=mock_selector,
            entry=mock_entry,
            exit_strategy=mock_exit,
            rebalance_freq='D'
        )
        assert composer_d.rebalance_freq == 'D'

        # 周频
        composer_w = StrategyComposer(
            selector=mock_selector,
            entry=mock_entry,
            exit_strategy=mock_exit,
            rebalance_freq='W'
        )
        assert composer_w.rebalance_freq == 'W'

        # 月频
        composer_m = StrategyComposer(
            selector=mock_selector,
            entry=mock_entry,
            exit_strategy=mock_exit,
            rebalance_freq='M'
        )
        assert composer_m.rebalance_freq == 'M'

    def test_composer_default_frequency(self, mock_selector, mock_entry, mock_exit):
        """测试默认调仓频率"""
        composer = StrategyComposer(
            selector=mock_selector,
            entry=mock_entry,
            exit_strategy=mock_exit
        )

        assert composer.rebalance_freq == 'W'  # 默认为周频


# ============================================================================
# 参数验证测试
# ============================================================================

class TestStrategyComposerValidation:
    """测试参数验证功能"""

    def test_invalid_selector_type(self, mock_entry, mock_exit):
        """测试无效的选股器类型"""
        with pytest.raises(TypeError, match="必须是 StockSelector 的实例"):
            StrategyComposer(
                selector="not_a_selector",  # 字符串而不是 StockSelector
                entry=mock_entry,
                exit_strategy=mock_exit
            )

    def test_invalid_entry_type(self, mock_selector, mock_exit):
        """测试无效的入场策略类型"""
        with pytest.raises(TypeError, match="必须是 EntryStrategy 的实例"):
            StrategyComposer(
                selector=mock_selector,
                entry="not_an_entry",  # 字符串而不是 EntryStrategy
                exit_strategy=mock_exit
            )

    def test_invalid_exit_type(self, mock_selector, mock_entry):
        """测试无效的退出策略类型"""
        with pytest.raises(TypeError, match="必须是 ExitStrategy 的实例"):
            StrategyComposer(
                selector=mock_selector,
                entry=mock_entry,
                exit_strategy="not_an_exit"  # 字符串而不是 ExitStrategy
            )

    def test_invalid_rebalance_freq(self, mock_selector, mock_entry, mock_exit):
        """测试无效的调仓频率"""
        with pytest.raises(ValueError, match="无效的选股频率"):
            StrategyComposer(
                selector=mock_selector,
                entry=mock_entry,
                exit_strategy=mock_exit,
                rebalance_freq='Y'  # 无效的频率
            )

    def test_validate_method_valid_composer(self, composer):
        """测试验证有效的组合器"""
        result = composer.validate()

        assert result['valid'] is True
        assert result['errors'] == []

    def test_validate_method_invalid_params(self, mock_entry, mock_exit):
        """测试验证无效参数的组合器"""
        # 创建一个参数超出范围的选股器时应该抛出异常
        with pytest.raises(ValueError, match="不能大于 100"):
            bad_selector = MockSelector(params={'top_n': 200})  # 超过最大值100


# ============================================================================
# 元数据获取测试
# ============================================================================

class TestStrategyComposerMetadata:
    """测试元数据获取功能"""

    def test_get_metadata_structure(self, composer):
        """测试元数据结构"""
        metadata = composer.get_metadata()

        assert 'selector' in metadata
        assert 'entry' in metadata
        assert 'exit' in metadata
        assert 'rebalance_freq' in metadata

    def test_get_metadata_selector(self, composer):
        """测试选股器元数据"""
        metadata = composer.get_metadata()
        selector_meta = metadata['selector']

        assert selector_meta['id'] == 'mock_selector'
        assert selector_meta['name'] == '模拟选股器'
        assert 'parameters' in selector_meta
        assert 'current_params' in selector_meta
        assert selector_meta['current_params'] == {'top_n': 20}

    def test_get_metadata_entry(self, composer):
        """测试入场策略元数据"""
        metadata = composer.get_metadata()
        entry_meta = metadata['entry']

        assert entry_meta['id'] == 'mock_entry'
        assert entry_meta['name'] == '模拟入场策略'
        assert 'parameters' in entry_meta
        assert 'current_params' in entry_meta
        assert entry_meta['current_params'] == {'max_positions': 10}

    def test_get_metadata_exit(self, composer):
        """测试退出策略元数据"""
        metadata = composer.get_metadata()
        exit_meta = metadata['exit']

        assert exit_meta['id'] == 'mock_exit'
        assert exit_meta['name'] == '模拟退出策略'
        assert 'parameters' in exit_meta
        assert 'current_params' in exit_meta
        assert exit_meta['current_params'] == {'stop_loss_pct': -5.0}

    def test_get_metadata_rebalance_freq(self, composer):
        """测试调仓频率元数据"""
        metadata = composer.get_metadata()

        assert metadata['rebalance_freq'] == 'W'


# ============================================================================
# 辅助方法测试
# ============================================================================

class TestStrategyComposerHelpers:
    """测试辅助方法"""

    def test_get_strategy_combination_id(self, composer):
        """测试获取策略组合ID"""
        combo_id = composer.get_strategy_combination_id()

        assert combo_id == "mock_selector__mock_entry__mock_exit__W"
        assert isinstance(combo_id, str)

    def test_get_strategy_combination_name(self, composer):
        """测试获取策略组合名称"""
        combo_name = composer.get_strategy_combination_name()

        assert "模拟选股器" in combo_name
        assert "模拟入场策略" in combo_name
        assert "模拟退出策略" in combo_name
        assert "周频" in combo_name

    def test_combination_name_with_different_freq(self, mock_selector, mock_entry, mock_exit):
        """测试不同频率的组合名称"""
        # 日频
        composer_d = StrategyComposer(
            selector=mock_selector,
            entry=mock_entry,
            exit_strategy=mock_exit,
            rebalance_freq='D'
        )
        assert "日频" in composer_d.get_strategy_combination_name()

        # 月频
        composer_m = StrategyComposer(
            selector=mock_selector,
            entry=mock_entry,
            exit_strategy=mock_exit,
            rebalance_freq='M'
        )
        assert "月频" in composer_m.get_strategy_combination_name()

    def test_get_all_parameters(self, composer):
        """测试获取所有参数"""
        all_params = composer.get_all_parameters()

        assert 'selector_params' in all_params
        assert 'entry_params' in all_params
        assert 'exit_params' in all_params
        assert 'rebalance_freq' in all_params

        assert all_params['selector_params'] == {'top_n': 20}
        assert all_params['entry_params'] == {'max_positions': 10}
        assert all_params['exit_params'] == {'stop_loss_pct': -5.0}
        assert all_params['rebalance_freq'] == 'W'

    def test_repr_method(self, composer):
        """测试 __repr__ 方法"""
        repr_str = repr(composer)

        assert "StrategyComposer" in repr_str
        assert "selector=" in repr_str
        assert "entry=" in repr_str
        assert "exit=" in repr_str
        assert "rebalance_freq=" in repr_str

    def test_str_method(self, composer):
        """测试 __str__ 方法"""
        str_repr = str(composer)

        # 应该返回可读的组合名称
        assert "模拟选股器" in str_repr
        assert "模拟入场策略" in str_repr
        assert "模拟退出策略" in str_repr


# ============================================================================
# 边界情况测试
# ============================================================================

class TestStrategyComposerEdgeCases:
    """测试边界情况"""

    def test_composer_with_empty_params(self):
        """测试使用空参数的策略"""
        selector = MockSelector(params={})
        entry = MockEntry(params={})
        exit_strategy = MockExit(params={})

        composer = StrategyComposer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            rebalance_freq='W'
        )

        metadata = composer.get_metadata()
        assert metadata['selector']['current_params'] == {}
        assert metadata['entry']['current_params'] == {}
        assert metadata['exit']['current_params'] == {}

    def test_composer_validates_nested_params(self, mock_entry, mock_exit):
        """测试嵌套参数验证"""
        # 创建参数有效的选股器
        good_selector = MockSelector(params={'top_n': 50})
        composer = StrategyComposer(
            selector=good_selector,
            entry=mock_entry,
            exit_strategy=mock_exit,
            rebalance_freq='W'
        )

        validation = composer.validate()
        assert validation['valid'] is True


# ============================================================================
# 集成测试
# ============================================================================

class TestStrategyComposerIntegration:
    """集成测试"""

    def test_full_workflow(self, mock_selector, mock_entry, mock_exit):
        """测试完整工作流程"""
        # 1. 创建组合器
        composer = StrategyComposer(
            selector=mock_selector,
            entry=mock_entry,
            exit_strategy=mock_exit,
            rebalance_freq='W'
        )

        # 2. 验证组合器
        validation = composer.validate()
        assert validation['valid'] is True

        # 3. 获取元数据
        metadata = composer.get_metadata()
        assert metadata is not None

        # 4. 获取组合ID和名称
        combo_id = composer.get_strategy_combination_id()
        combo_name = composer.get_strategy_combination_name()
        assert combo_id is not None
        assert combo_name is not None

        # 5. 获取所有参数
        all_params = composer.get_all_parameters()
        assert all_params is not None

    def test_create_multiple_composers(self, mock_selector, mock_entry, mock_exit):
        """测试创建多个组合器"""
        composers = []

        for freq in ['D', 'W', 'M']:
            composer = StrategyComposer(
                selector=mock_selector,
                entry=mock_entry,
                exit_strategy=mock_exit,
                rebalance_freq=freq
            )
            composers.append(composer)

        # 验证所有组合器
        assert len(composers) == 3
        assert composers[0].rebalance_freq == 'D'
        assert composers[1].rebalance_freq == 'W'
        assert composers[2].rebalance_freq == 'M'

        # ID应该不同
        ids = [c.get_strategy_combination_id() for c in composers]
        assert len(set(ids)) == 3  # 所有ID都不同

    def test_composer_with_different_strategies(self):
        """测试使用不同策略组合"""
        # 组合1
        composer1 = StrategyComposer(
            selector=MockSelector(params={'top_n': 10}),
            entry=MockEntry(params={'max_positions': 5}),
            exit_strategy=MockExit(params={'stop_loss_pct': -5.0}),
            rebalance_freq='W'
        )

        # 组合2
        composer2 = StrategyComposer(
            selector=MockSelector(params={'top_n': 20}),
            entry=MockEntry(params={'max_positions': 10}),
            exit_strategy=MockExit(params={'stop_loss_pct': -10.0}),
            rebalance_freq='M'
        )

        # 两个组合应该不同
        assert composer1.get_strategy_combination_id() != composer2.get_strategy_combination_id()

        # 参数应该不同
        params1 = composer1.get_all_parameters()
        params2 = composer2.get_all_parameters()
        assert params1 != params2


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
