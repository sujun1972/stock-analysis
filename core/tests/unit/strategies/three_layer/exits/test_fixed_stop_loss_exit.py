"""
FixedStopLossExit 单元测试

Test cases for FixedStopLossExit exit strategy
"""

import pytest
import pandas as pd

from src.strategies.three_layer.exits import FixedStopLossExit
from src.strategies.three_layer.base import Position


# ============================================================================
# 测试夹具 (Fixtures)
# ============================================================================

@pytest.fixture
def sample_positions():
    """创建示例持仓"""
    return {
        'PROFIT_10': Position(
            stock_code='PROFIT_10',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=100.0,
            shares=10,
            current_price=110.0,  # 盈利10%
            unrealized_pnl=100.0,
            unrealized_pnl_pct=10.0
        ),
        'LOSS_5': Position(
            stock_code='LOSS_5',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=100.0,
            shares=10,
            current_price=95.0,  # 亏损5%
            unrealized_pnl=-50.0,
            unrealized_pnl_pct=-5.0
        ),
        'PROFIT_2': Position(
            stock_code='PROFIT_2',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=100.0,
            shares=10,
            current_price=102.0,  # 盈利2%
            unrealized_pnl=20.0,
            unrealized_pnl_pct=2.0
        ),
        'LOSS_15': Position(
            stock_code='LOSS_15',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=100.0,
            shares=10,
            current_price=85.0,  # 亏损15%
            unrealized_pnl=-150.0,
            unrealized_pnl_pct=-15.0
        ),
    }


@pytest.fixture
def sample_stock_data():
    """创建示例股票数据（简单数据，此策略不使用）"""
    return {}


# ============================================================================
# 基本功能测试
# ============================================================================

class TestFixedStopLossExitBasic:
    """测试 FixedStopLossExit 基本功能"""

    def test_exit_creation_with_default_params(self):
        """测试使用默认参数创建退出策略"""
        exit_strategy = FixedStopLossExit()
        assert exit_strategy.name == "固定止损止盈"
        assert exit_strategy.id == "fixed_stop_loss"

    def test_exit_creation_with_custom_params(self):
        """测试使用自定义参数创建退出策略"""
        params = {
            'stop_loss_pct': -10.0,
            'take_profit_pct': 20.0,
            'enable_stop_loss': True,
            'enable_take_profit': False
        }
        exit_strategy = FixedStopLossExit(params=params)
        assert exit_strategy.params == params

    def test_get_parameters_class_method(self):
        """测试 get_parameters 类方法"""
        params = FixedStopLossExit.get_parameters()
        assert len(params) == 4

        param_names = [p["name"] for p in params]
        assert 'stop_loss_pct' in param_names
        assert 'take_profit_pct' in param_names
        assert 'enable_stop_loss' in param_names
        assert 'enable_take_profit' in param_names


# ============================================================================
# 参数验证测试
# ============================================================================

class TestFixedStopLossExitParameterValidation:
    """测试参数验证功能"""

    def test_valid_stop_loss_parameter(self):
        """测试有效的止损参数"""
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -8.0})
        assert exit_strategy.params['stop_loss_pct'] == -8.0

    def test_stop_loss_below_min(self):
        """测试止损参数低于最小值"""
        with pytest.raises(ValueError, match="不能小于 -20.0"):
            FixedStopLossExit(params={'stop_loss_pct': -25.0})

    def test_stop_loss_above_max(self):
        """测试止损参数超过最大值（应为负数）"""
        with pytest.raises(ValueError, match="不能大于 -1.0"):
            FixedStopLossExit(params={'stop_loss_pct': 0.0})

    def test_valid_take_profit_parameter(self):
        """测试有效的止盈参数"""
        exit_strategy = FixedStopLossExit(params={'take_profit_pct': 15.0})
        assert exit_strategy.params['take_profit_pct'] == 15.0

    def test_take_profit_below_min(self):
        """测试止盈参数低于最小值"""
        with pytest.raises(ValueError, match="不能小于 1.0"):
            FixedStopLossExit(params={'take_profit_pct': 0.5})

    def test_take_profit_above_max(self):
        """测试止盈参数超过最大值"""
        with pytest.raises(ValueError, match="不能大于 50.0"):
            FixedStopLossExit(params={'take_profit_pct': 60.0})


# ============================================================================
# generate_exit_signals() 方法测试
# ============================================================================

class TestFixedStopLossExitGenerateSignals:
    """测试 generate_exit_signals() 方法"""

    def test_generate_signals_returns_list(self, sample_positions, sample_stock_data):
        """测试返回列表类型"""
        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 10.0
        })
        signals = exit_strategy.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )
        assert isinstance(signals, list)

    def test_stop_loss_trigger(self, sample_stock_data):
        """测试止损触发"""
        positions = {
            'LOSS_10': Position(
                stock_code='LOSS_10',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=90.0,  # 亏损10%
                unrealized_pnl=-100.0,
                unrealized_pnl_pct=-10.0
            ),
        }

        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 亏损10%应该触发-5%的止损
        assert 'LOSS_10' in signals

    def test_take_profit_trigger(self, sample_stock_data):
        """测试止盈触发"""
        positions = {
            'PROFIT_20': Position(
                stock_code='PROFIT_20',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=120.0,  # 盈利20%
                unrealized_pnl=200.0,
                unrealized_pnl_pct=20.0
            ),
        }

        exit_strategy = FixedStopLossExit(params={'take_profit_pct': 10.0})
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 盈利20%应该触发10%的止盈
        assert 'PROFIT_20' in signals

    def test_no_exit_within_range(self, sample_stock_data):
        """测试在止损止盈范围内不触发"""
        positions = {
            'PROFIT_3': Position(
                stock_code='PROFIT_3',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=103.0,  # 盈利3%
                unrealized_pnl=30.0,
                unrealized_pnl_pct=3.0
            ),
        }

        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 10.0
        })
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 盈利3%不应该触发（在-5%到10%范围内）
        assert 'PROFIT_3' not in signals

    def test_multiple_positions_trigger(self, sample_positions, sample_stock_data):
        """测试多个持仓同时触发"""
        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 10.0
        })
        signals = exit_strategy.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # PROFIT_10: 盈利10% -> 触发止盈
        # LOSS_5: 亏损5% -> 触发止损
        # PROFIT_2: 盈利2% -> 不触发
        # LOSS_15: 亏损15% -> 触发止损
        assert 'PROFIT_10' in signals
        assert 'LOSS_5' in signals
        assert 'PROFIT_2' not in signals
        assert 'LOSS_15' in signals

    def test_empty_positions(self, sample_stock_data):
        """测试空持仓"""
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})
        signals = exit_strategy.generate_exit_signals(
            {},
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )
        assert signals == []

    def test_disable_stop_loss(self, sample_stock_data):
        """测试禁用止损"""
        positions = {
            'LOSS_10': Position(
                stock_code='LOSS_10',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=90.0,  # 亏损10%
                unrealized_pnl=-100.0,
                unrealized_pnl_pct=-10.0
            ),
        }

        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -5.0,
            'enable_stop_loss': False  # 禁用止损
        })
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 禁用止损后不应该触发
        assert 'LOSS_10' not in signals

    def test_disable_take_profit(self, sample_stock_data):
        """测试禁用止盈"""
        positions = {
            'PROFIT_20': Position(
                stock_code='PROFIT_20',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=120.0,  # 盈利20%
                unrealized_pnl=200.0,
                unrealized_pnl_pct=20.0
            ),
        }

        exit_strategy = FixedStopLossExit(params={
            'take_profit_pct': 10.0,
            'enable_take_profit': False  # 禁用止盈
        })
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 禁用止盈后不应该触发
        assert 'PROFIT_20' not in signals

    def test_only_stop_loss_enabled(self, sample_stock_data):
        """测试只启用止损"""
        positions = {
            'LOSS_10': Position(
                stock_code='LOSS_10',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=90.0,
                unrealized_pnl=-100.0,
                unrealized_pnl_pct=-10.0
            ),
            'PROFIT_20': Position(
                stock_code='PROFIT_20',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=120.0,
                unrealized_pnl=200.0,
                unrealized_pnl_pct=20.0
            ),
        }

        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 10.0,
            'enable_stop_loss': True,
            'enable_take_profit': False
        })
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 只有止损应该触发
        assert 'LOSS_10' in signals
        assert 'PROFIT_20' not in signals


# ============================================================================
# 边界情况测试
# ============================================================================

class TestFixedStopLossExitEdgeCases:
    """测试边界情况"""

    def test_stop_loss_equals_current_pnl(self, sample_stock_data):
        """测试止损值等于当前盈亏"""
        positions = {
            'LOSS_5': Position(
                stock_code='LOSS_5',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=95.0,  # 亏损5%
                unrealized_pnl=-50.0,
                unrealized_pnl_pct=-5.0
            ),
        }

        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 刚好达到止损应该触发（<=）
        assert 'LOSS_5' in signals

    def test_take_profit_equals_current_pnl(self, sample_stock_data):
        """测试止盈值等于当前盈亏"""
        positions = {
            'PROFIT_10': Position(
                stock_code='PROFIT_10',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=110.0,  # 盈利10%
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
        }

        exit_strategy = FixedStopLossExit(params={'take_profit_pct': 10.0})
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 刚好达到止盈应该触发（>=）
        assert 'PROFIT_10' in signals

    def test_zero_pnl(self, sample_stock_data):
        """测试零盈亏"""
        positions = {
            'ZERO': Position(
                stock_code='ZERO',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=100.0,  # 零盈亏
                unrealized_pnl=0.0,
                unrealized_pnl_pct=0.0
            ),
        }

        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 10.0
        })
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 零盈亏不应该触发
        assert 'ZERO' not in signals

    def test_extreme_loss(self, sample_stock_data):
        """测试极端亏损"""
        positions = {
            'EXTREME_LOSS': Position(
                stock_code='EXTREME_LOSS',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=10.0,  # 亏损90%
                unrealized_pnl=-900.0,
                unrealized_pnl_pct=-90.0
            ),
        }

        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 极端亏损应该触发止损
        assert 'EXTREME_LOSS' in signals

    def test_extreme_profit(self, sample_stock_data):
        """测试极端盈利"""
        positions = {
            'EXTREME_PROFIT': Position(
                stock_code='EXTREME_PROFIT',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=300.0,  # 盈利200%
                unrealized_pnl=2000.0,
                unrealized_pnl_pct=200.0
            ),
        }

        exit_strategy = FixedStopLossExit(params={'take_profit_pct': 10.0})
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 极端盈利应该触发止盈
        assert 'EXTREME_PROFIT' in signals


# ============================================================================
# 集成测试
# ============================================================================

class TestFixedStopLossExitIntegration:
    """集成测试"""

    def test_full_workflow(self, sample_positions, sample_stock_data):
        """测试完整工作流程"""
        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 10.0,
            'enable_stop_loss': True,
            'enable_take_profit': True
        })

        signals = exit_strategy.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 验证结果
        assert isinstance(signals, list)
        assert all(isinstance(s, str) for s in signals)
        assert all(s in sample_positions for s in signals)

    def test_parameter_change_affects_signals(self, sample_stock_data):
        """测试参数变化影响信号生成"""
        positions = {
            'LOSS_7': Position(
                stock_code='LOSS_7',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=93.0,  # 亏损7%
                unrealized_pnl=-70.0,
                unrealized_pnl_pct=-7.0
            ),
        }

        # 止损-5%：应该触发
        exit1 = FixedStopLossExit(params={'stop_loss_pct': -5.0})
        signals1 = exit1.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )
        assert 'LOSS_7' in signals1

        # 止损-10%：不应该触发
        exit2 = FixedStopLossExit(params={'stop_loss_pct': -10.0})
        signals2 = exit2.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )
        assert 'LOSS_7' not in signals2


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
