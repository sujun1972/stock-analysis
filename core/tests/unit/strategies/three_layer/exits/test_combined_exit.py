"""
CombinedExit 单元测试

Test cases for CombinedExit exit strategy
"""

import pytest
import pandas as pd

from src.strategies.three_layer.exits import (
    CombinedExit,
    ATRStopLossExit,
    FixedStopLossExit,
    TimeBasedExit
)
from src.strategies.three_layer.base import Position


# ============================================================================
# 测试夹具 (Fixtures)
# ============================================================================

@pytest.fixture
def sample_positions():
    """创建示例持仓"""
    return {
        'PROFIT_15': Position(
            stock_code='PROFIT_15',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=100.0,
            shares=10,
            current_price=115.0,  # 盈利15%
            unrealized_pnl=150.0,
            unrealized_pnl_pct=15.0
        ),
        'LOSS_10': Position(
            stock_code='LOSS_10',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=100.0,
            shares=10,
            current_price=90.0,  # 亏损10%
            unrealized_pnl=-100.0,
            unrealized_pnl_pct=-10.0
        ),
        'NORMAL': Position(
            stock_code='NORMAL',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=100.0,
            shares=10,
            current_price=102.0,  # 盈利2%
            unrealized_pnl=20.0,
            unrealized_pnl_pct=2.0
        ),
        'OLD_POSITION': Position(
            stock_code='OLD_POSITION',
            entry_date=pd.Timestamp('2023-01-01'),  # 15天前
            entry_price=100.0,
            shares=10,
            current_price=103.0,
            unrealized_pnl=30.0,
            unrealized_pnl_pct=3.0
        ),
    }


@pytest.fixture
def sample_stock_data():
    """创建示例股票数据"""
    dates = pd.date_range('2023-01-01', periods=20, freq='D')

    return {
        'PROFIT_15': pd.DataFrame({
            'open': [100.0] * 20,
            'high': [120.0] * 20,
            'low': [100.0] * 20,
            'close': [115.0] * 20,
            'volume': [1000] * 20,
        }, index=dates),
        'LOSS_10': pd.DataFrame({
            'open': [100.0] * 20,
            'high': [100.0] * 20,
            'low': [80.0] * 20,
            'close': [90.0] * 20,
            'volume': [1000] * 20,
        }, index=dates),
        'NORMAL': pd.DataFrame({
            'open': [100.0] * 20,
            'high': [105.0] * 20,
            'low': [98.0] * 20,
            'close': [102.0] * 20,
            'volume': [1000] * 20,
        }, index=dates),
        'OLD_POSITION': pd.DataFrame({
            'open': [100.0] * 20,
            'high': [105.0] * 20,
            'low': [98.0] * 20,
            'close': [103.0] * 20,
            'volume': [1000] * 20,
        }, index=dates),
    }


# ============================================================================
# 基本功能测试
# ============================================================================

class TestCombinedExitBasic:
    """测试 CombinedExit 基本功能"""

    def test_exit_creation_with_strategies(self):
        """测试使用策略列表创建组合退出"""
        strategies = [
            FixedStopLossExit(params={'stop_loss_pct': -5.0}),
            TimeBasedExit(params={'holding_period': 10})
        ]
        combined = CombinedExit(strategies=strategies)

        assert combined.id == "combined"
        assert len(combined.strategies) == 2
        assert "固定止损止盈" in combined.name
        assert "时间止损" in combined.name

    def test_exit_creation_without_strategies_raises_error(self):
        """测试不提供策略列表时抛出错误"""
        with pytest.raises(ValueError, match="至少需要一个子策略"):
            CombinedExit(strategies=[])

    def test_get_parameters_class_method(self):
        """测试 get_parameters 类方法"""
        params = CombinedExit.get_parameters()
        # 组合策略不定义自己的参数
        assert len(params) == 0

    def test_name_property_includes_all_strategies(self):
        """测试名称包含所有子策略"""
        strategies = [
            FixedStopLossExit(params={'stop_loss_pct': -5.0}),
            TimeBasedExit(params={'holding_period': 10}),
            ATRStopLossExit(params={'atr_period': 14})
        ]
        combined = CombinedExit(strategies=strategies)

        assert "固定止损止盈" in combined.name
        assert "时间止损" in combined.name
        assert "ATR动态止损" in combined.name


# ============================================================================
# generate_exit_signals() 方法测试
# ============================================================================

class TestCombinedExitGenerateSignals:
    """测试 generate_exit_signals() 方法"""

    def test_generate_signals_returns_list(self, sample_positions, sample_stock_data):
        """测试返回列表类型"""
        strategies = [FixedStopLossExit(params={'stop_loss_pct': -5.0})]
        combined = CombinedExit(strategies=strategies)

        signals = combined.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-15')
        )
        assert isinstance(signals, list)

    def test_single_strategy_triggers(self, sample_positions, sample_stock_data):
        """测试单个策略触发"""
        strategies = [
            FixedStopLossExit(params={'stop_loss_pct': -5.0})
        ]
        combined = CombinedExit(strategies=strategies)

        signals = combined.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-15')
        )

        # LOSS_10 亏损10%，应该触发止损
        assert 'LOSS_10' in signals
        # NORMAL 盈利2%，不应该触发
        assert 'NORMAL' not in signals

    def test_multiple_strategies_or_logic(self, sample_positions, sample_stock_data):
        """测试多个策略的OR逻辑"""
        strategies = [
            FixedStopLossExit(params={
                'stop_loss_pct': -5.0,
                'take_profit_pct': 12.0
            }),
            TimeBasedExit(params={'holding_period': 10})
        ]
        combined = CombinedExit(strategies=strategies)

        signals = combined.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-16')  # 15天后
        )

        # LOSS_10: 亏损10% -> 触发止损
        # PROFIT_15: 盈利15% -> 触发止盈
        # OLD_POSITION: 持仓15天 -> 触发时间止损
        # NORMAL: 持仓15天也会触发时间止损
        assert 'LOSS_10' in signals
        assert 'PROFIT_15' in signals
        assert 'OLD_POSITION' in signals
        # NORMAL也会触发时间止损（持仓15天 > 10天）
        assert 'NORMAL' in signals

    def test_any_strategy_triggers_exit(self, sample_positions, sample_stock_data):
        """测试任意策略触发即退出"""
        # 设置多个策略，确保至少一个会触发
        strategies = [
            FixedStopLossExit(params={'stop_loss_pct': -20.0}),  # 不会触发（最小值）
            TimeBasedExit(params={'holding_period': 5}),  # 会触发
        ]
        combined = CombinedExit(strategies=strategies)

        signals = combined.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-10')
        )

        # 虽然止损不会触发，但时间止损会触发
        # 所有持仓都超过5天
        assert len(signals) == len(sample_positions)

    def test_empty_positions(self, sample_stock_data):
        """测试空持仓"""
        strategies = [
            FixedStopLossExit(params={'stop_loss_pct': -5.0}),
            TimeBasedExit(params={'holding_period': 10})
        ]
        combined = CombinedExit(strategies=strategies)

        signals = combined.generate_exit_signals(
            {},
            sample_stock_data,
            pd.Timestamp('2023-01-15')
        )
        assert signals == []

    def test_no_triggers(self, sample_stock_data):
        """测试所有策略都不触发"""
        positions = {
            'NORMAL': Position(
                stock_code='NORMAL',
                entry_date=pd.Timestamp('2023-01-10'),  # 最近入场
                entry_price=100.0,
                shares=10,
                current_price=102.0,  # 小幅盈利
                unrealized_pnl=20.0,
                unrealized_pnl_pct=2.0
            ),
        }

        strategies = [
            FixedStopLossExit(params={
                'stop_loss_pct': -10.0,
                'take_profit_pct': 20.0
            }),
            TimeBasedExit(params={'holding_period': 100})
        ]
        combined = CombinedExit(strategies=strategies)

        signals = combined.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-15')
        )

        # 不应该触发任何策略
        assert signals == []

    def test_deduplication_of_exit_signals(self, sample_positions, sample_stock_data):
        """测试退出信号去重"""
        # 设置两个都会触发同一股票的策略
        strategies = [
            FixedStopLossExit(params={'stop_loss_pct': -5.0}),
            FixedStopLossExit(params={'stop_loss_pct': -8.0}),
        ]
        combined = CombinedExit(strategies=strategies)

        signals = combined.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-15')
        )

        # LOSS_10应该只出现一次（虽然两个策略都触发）
        assert signals.count('LOSS_10') == 1


# ============================================================================
# 策略组合测试
# ============================================================================

class TestCombinedExitStrategyMix:
    """测试不同策略组合"""

    def test_stop_loss_and_time_based(self, sample_positions, sample_stock_data):
        """测试止损 + 时间限制组合"""
        strategies = [
            FixedStopLossExit(params={'stop_loss_pct': -5.0}),
            TimeBasedExit(params={'holding_period': 10})
        ]
        combined = CombinedExit(strategies=strategies)

        signals = combined.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-16')
        )

        # 应该触发止损和时间限制
        assert 'LOSS_10' in signals  # 止损触发
        assert 'OLD_POSITION' in signals  # 时间触发

    def test_three_strategy_combination(self, sample_positions, sample_stock_data):
        """测试三种策略组合"""
        strategies = [
            FixedStopLossExit(params={
                'stop_loss_pct': -5.0,
                'take_profit_pct': 12.0
            }),
            TimeBasedExit(params={'holding_period': 10}),
            ATRStopLossExit(params={
                'atr_period': 14,
                'atr_multiplier': 1.0
            })
        ]
        combined = CombinedExit(strategies=strategies)

        signals = combined.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-16')
        )

        # 多个策略应该能触发不同的股票
        assert isinstance(signals, list)
        assert len(signals) >= 2  # 至少有止损和时间限制触发


# ============================================================================
# 错误处理测试
# ============================================================================

class TestCombinedExitErrorHandling:
    """测试错误处理"""

    def test_strategy_error_doesnt_stop_execution(self, sample_positions, sample_stock_data):
        """测试子策略错误不影响其他策略执行"""
        class BuggyExit(FixedStopLossExit):
            def generate_exit_signals(self, positions, data, date):
                raise RuntimeError("故意的错误")

        strategies = [
            BuggyExit(params={'stop_loss_pct': -5.0}),  # 会报错
            TimeBasedExit(params={'holding_period': 10})  # 正常工作
        ]
        combined = CombinedExit(strategies=strategies)

        # 即使第一个策略报错，第二个策略仍应该执行
        signals = combined.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-16')
        )

        # 时间策略应该仍然能触发
        assert 'OLD_POSITION' in signals


# ============================================================================
# 辅助方法测试
# ============================================================================

class TestCombinedExitHelperMethods:
    """测试辅助方法"""

    def test_get_strategy_summary(self):
        """测试获取策略摘要"""
        strategies = [
            FixedStopLossExit(params={'stop_loss_pct': -5.0}),
            TimeBasedExit(params={'holding_period': 10})
        ]
        combined = CombinedExit(strategies=strategies)

        summary = combined.get_strategy_summary()

        assert summary['type'] == 'combined'
        assert summary['num_strategies'] == 2
        assert len(summary['strategies']) == 2

        # 检查策略详情
        assert summary['strategies'][0]['id'] == 'fixed_stop_loss'
        assert summary['strategies'][1]['id'] == 'time_based'

    def test_repr_method(self):
        """测试字符串表示"""
        strategies = [
            FixedStopLossExit(params={'stop_loss_pct': -5.0}),
            TimeBasedExit(params={'holding_period': 10})
        ]
        combined = CombinedExit(strategies=strategies)

        repr_str = repr(combined)

        assert "CombinedExit" in repr_str
        assert "固定止损止盈" in repr_str
        assert "时间止损" in repr_str


# ============================================================================
# 集成测试
# ============================================================================

class TestCombinedExitIntegration:
    """集成测试"""

    def test_full_workflow(self, sample_positions, sample_stock_data):
        """测试完整工作流程"""
        strategies = [
            FixedStopLossExit(params={
                'stop_loss_pct': -5.0,
                'take_profit_pct': 12.0
            }),
            TimeBasedExit(params={'holding_period': 10}),
            ATRStopLossExit(params={
                'atr_period': 14,
                'atr_multiplier': 2.0
            })
        ]
        combined = CombinedExit(strategies=strategies)

        # 获取摘要
        summary = combined.get_strategy_summary()
        assert summary['num_strategies'] == 3

        # 生成信号
        signals = combined.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-16')
        )

        # 验证结果
        assert isinstance(signals, list)
        assert all(isinstance(s, str) for s in signals)
        assert all(s in sample_positions for s in signals)

    def test_realistic_trading_scenario(self, sample_stock_data):
        """测试真实交易场景"""
        # 模拟一个真实的交易场景
        positions = {
            # 快速盈利，触发止盈
            'QUICK_PROFIT': Position(
                stock_code='PROFIT_15',
                entry_date=pd.Timestamp('2023-01-14'),
                entry_price=100.0,
                shares=10,
                current_price=115.0,
                unrealized_pnl=150.0,
                unrealized_pnl_pct=15.0
            ),
            # 长期持有，触发时间限制
            'LONG_HOLD': Position(
                stock_code='OLD_POSITION',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=100.0,
                shares=10,
                current_price=105.0,
                unrealized_pnl=50.0,
                unrealized_pnl_pct=5.0
            ),
            # 亏损严重，触发止损
            'HEAVY_LOSS': Position(
                stock_code='LOSS_10',
                entry_date=pd.Timestamp('2023-01-10'),
                entry_price=100.0,
                shares=10,
                current_price=85.0,
                unrealized_pnl=-150.0,
                unrealized_pnl_pct=-15.0
            ),
            # 正常持仓，不触发
            'NORMAL_HOLD': Position(
                stock_code='NORMAL',
                entry_date=pd.Timestamp('2023-01-14'),
                entry_price=100.0,
                shares=10,
                current_price=102.0,
                unrealized_pnl=20.0,
                unrealized_pnl_pct=2.0
            ),
        }

        # 综合策略：止损止盈 + 时间限制
        strategies = [
            FixedStopLossExit(params={
                'stop_loss_pct': -10.0,
                'take_profit_pct': 10.0
            }),
            TimeBasedExit(params={'holding_period': 10})
        ]
        combined = CombinedExit(strategies=strategies)

        signals = combined.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-16')
        )

        # QUICK_PROFIT: 盈利15% -> 触发止盈
        # LONG_HOLD: 持仓15天 -> 触发时间
        # HEAVY_LOSS: 亏损15% -> 触发止损
        # NORMAL_HOLD: 不触发
        assert 'QUICK_PROFIT' in signals
        assert 'LONG_HOLD' in signals
        assert 'HEAVY_LOSS' in signals
        assert 'NORMAL_HOLD' not in signals


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
