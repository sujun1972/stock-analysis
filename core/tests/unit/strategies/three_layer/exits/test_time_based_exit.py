"""
TimeBasedExit 单元测试

Test cases for TimeBasedExit exit strategy
"""

import pytest
import pandas as pd

from src.strategies.three_layer.exits import TimeBasedExit
from src.strategies.three_layer.base import Position


# ============================================================================
# 测试夹具 (Fixtures)
# ============================================================================

@pytest.fixture
def sample_stock_data():
    """创建示例股票数据（用于交易日计算）"""
    # 创建20个交易日的数据
    dates = pd.date_range('2023-01-01', periods=20, freq='D')

    data = {
        'A': pd.DataFrame({
            'close': [10.0 + i * 0.1 for i in range(20)],
            'volume': [1000] * 20,
        }, index=dates),
        'B': pd.DataFrame({
            'close': [20.0 + i * 0.2 for i in range(20)],
            'volume': [2000] * 20,
        }, index=dates),
    }
    return data


@pytest.fixture
def sample_positions():
    """创建示例持仓"""
    return {
        'DAY_5': Position(
            stock_code='DAY_5',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=100.0,
            shares=10,
            current_price=105.0,
            unrealized_pnl=50.0,
            unrealized_pnl_pct=5.0
        ),
        'DAY_10': Position(
            stock_code='DAY_10',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=100.0,
            shares=10,
            current_price=110.0,
            unrealized_pnl=100.0,
            unrealized_pnl_pct=10.0
        ),
        'DAY_15': Position(
            stock_code='DAY_15',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=100.0,
            shares=10,
            current_price=115.0,
            unrealized_pnl=150.0,
            unrealized_pnl_pct=15.0
        ),
    }


# ============================================================================
# 基本功能测试
# ============================================================================

class TestTimeBasedExitBasic:
    """测试 TimeBasedExit 基本功能"""

    def test_exit_creation_with_default_params(self):
        """测试使用默认参数创建退出策略"""
        exit_strategy = TimeBasedExit()
        assert exit_strategy.name == "时间止损"
        assert exit_strategy.id == "time_based"

    def test_exit_creation_with_custom_params(self):
        """测试使用自定义参数创建退出策略"""
        params = {
            'holding_period': 20,
            'count_trading_days_only': True
        }
        exit_strategy = TimeBasedExit(params=params)
        assert exit_strategy.params == params

    def test_get_parameters_class_method(self):
        """测试 get_parameters 类方法"""
        params = TimeBasedExit.get_parameters()
        assert len(params) == 2

        param_names = [p["name"] for p in params]
        assert 'holding_period' in param_names
        assert 'count_trading_days_only' in param_names


# ============================================================================
# 参数验证测试
# ============================================================================

class TestTimeBasedExitParameterValidation:
    """测试参数验证功能"""

    def test_valid_holding_period(self):
        """测试有效的持仓天数"""
        exit_strategy = TimeBasedExit(params={'holding_period': 15})
        assert exit_strategy.params['holding_period'] == 15

    def test_holding_period_below_min(self):
        """测试持仓天数低于最小值"""
        with pytest.raises(ValueError, match="不能小于 1"):
            TimeBasedExit(params={'holding_period': 0})

    def test_holding_period_above_max(self):
        """测试持仓天数超过最大值"""
        with pytest.raises(ValueError, match="不能大于 100"):
            TimeBasedExit(params={'holding_period': 150})

    def test_unknown_parameter(self):
        """测试未知参数"""
        with pytest.raises(ValueError, match="未知参数"):
            TimeBasedExit(params={'unknown_param': 'value'})


# ============================================================================
# generate_exit_signals() 方法测试
# ============================================================================

class TestTimeBasedExitGenerateSignals:
    """测试 generate_exit_signals() 方法"""

    def test_generate_signals_returns_list(self, sample_positions, sample_stock_data):
        """测试返回列表类型"""
        exit_strategy = TimeBasedExit(params={'holding_period': 10})
        signals = exit_strategy.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-15')
        )
        assert isinstance(signals, list)

    def test_exit_after_holding_period(self, sample_stock_data):
        """测试持仓达到期限后触发"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=11.0,
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
        }

        exit_strategy = TimeBasedExit(params={'holding_period': 10})

        # 第10天不应该触发（< 10天）
        signals_day9 = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-10')
        )
        assert 'A' not in signals_day9

        # 第11天应该触发（= 10天）
        signals_day10 = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-11')
        )
        assert 'A' in signals_day10

        # 第12天应该触发（> 10天）
        signals_day11 = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-12')
        )
        assert 'A' in signals_day11

    def test_calendar_days_calculation(self, sample_stock_data):
        """测试日历天数计算"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=11.0,
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
        }

        exit_strategy = TimeBasedExit(params={
            'holding_period': 10,
            'count_trading_days_only': False  # 使用日历天数
        })

        # 2023-01-01 到 2023-01-11 = 10天
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-11')
        )
        assert 'A' in signals

    def test_multiple_positions_with_different_entry_dates(self, sample_stock_data):
        """测试不同入场日期的多个持仓"""
        positions = {
            'OLD': Position(
                stock_code='OLD',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=11.0,
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
            'NEW': Position(
                stock_code='NEW',
                entry_date=pd.Timestamp('2023-01-10'),
                entry_price=10.0,
                shares=100,
                current_price=11.0,
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
        }

        exit_strategy = TimeBasedExit(params={'holding_period': 10})

        # 在2023-01-15检查
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-15')
        )

        # OLD: 2023-01-01 入场，已持仓14天，应该触发
        # NEW: 2023-01-10 入场，只持仓5天，不应该触发
        assert 'OLD' in signals
        assert 'NEW' not in signals

    def test_empty_positions(self, sample_stock_data):
        """测试空持仓"""
        exit_strategy = TimeBasedExit(params={'holding_period': 10})
        signals = exit_strategy.generate_exit_signals(
            {},
            sample_stock_data,
            pd.Timestamp('2023-01-15')
        )
        assert signals == []

    def test_exact_holding_period_boundary(self, sample_stock_data):
        """测试持仓期限边界值"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=11.0,
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
        }

        exit_strategy = TimeBasedExit(params={'holding_period': 10})

        # 刚好10天应该触发（>=）
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-11')  # 10天后
        )
        assert 'A' in signals

    def test_profit_or_loss_doesnt_matter(self, sample_stock_data):
        """测试盈亏状态不影响时间退出"""
        positions = {
            'PROFIT': Position(
                stock_code='PROFIT',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=15.0,  # 盈利
                unrealized_pnl=500.0,
                unrealized_pnl_pct=50.0
            ),
            'LOSS': Position(
                stock_code='LOSS',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=5.0,  # 亏损
                unrealized_pnl=-500.0,
                unrealized_pnl_pct=-50.0
            ),
        }

        exit_strategy = TimeBasedExit(params={'holding_period': 10})

        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-15')
        )

        # 无论盈亏，到期都应该触发
        assert 'PROFIT' in signals
        assert 'LOSS' in signals

    def test_missing_stock_data_fallback_to_calendar_days(self, sample_stock_data):
        """测试缺少股票数据时回退到日历天数"""
        positions = {
            'MISSING': Position(
                stock_code='MISSING',  # 数据中不存在
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=11.0,
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
        }

        exit_strategy = TimeBasedExit(params={
            'holding_period': 10,
            'count_trading_days_only': True  # 即使设置只计算交易日
        })

        # 数据缺失时应该回退到日历天数
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-11')
        )
        assert 'MISSING' in signals


# ============================================================================
# 边界情况测试
# ============================================================================

class TestTimeBasedExitEdgeCases:
    """测试边界情况"""

    def test_same_day_entry_and_check(self, sample_stock_data):
        """测试入场当天检查"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-10'),
                entry_price=10.0,
                shares=100,
                current_price=10.0,
                unrealized_pnl=0.0,
                unrealized_pnl_pct=0.0
            ),
        }

        exit_strategy = TimeBasedExit(params={'holding_period': 1})

        # 入场当天，持仓0天
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-10')
        )

        # 持仓期限为1天时，入场当天（0天）不应该触发
        assert 'A' not in signals

    def test_minimum_holding_period(self, sample_stock_data):
        """测试最小持仓期限"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-10'),
                entry_price=10.0,
                shares=100,
                current_price=11.0,
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
        }

        exit_strategy = TimeBasedExit(params={'holding_period': 1})

        # 第1天不触发
        signals_day0 = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-10')
        )
        assert 'A' not in signals_day0

        # 第2天触发
        signals_day1 = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-11')
        )
        assert 'A' in signals_day1

    def test_very_long_holding_period(self, sample_stock_data):
        """测试很长的持仓期限"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=11.0,
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
        }

        exit_strategy = TimeBasedExit(params={'holding_period': 100})

        # 只持仓19天，不应该触发
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-20')
        )
        assert 'A' not in signals


# ============================================================================
# 集成测试
# ============================================================================

class TestTimeBasedExitIntegration:
    """集成测试"""

    def test_full_workflow(self, sample_positions, sample_stock_data):
        """测试完整工作流程"""
        exit_strategy = TimeBasedExit(params={'holding_period': 10})

        signals = exit_strategy.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-15')
        )

        # 验证结果
        assert isinstance(signals, list)
        assert all(isinstance(s, str) for s in signals)

    def test_progressive_dates(self, sample_stock_data):
        """测试随着时间推移的信号变化"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=11.0,
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
        }

        exit_strategy = TimeBasedExit(params={'holding_period': 10})

        # 测试多个日期
        dates = [
            (pd.Timestamp('2023-01-05'), False),  # 4天，不触发
            (pd.Timestamp('2023-01-10'), False),  # 9天，不触发
            (pd.Timestamp('2023-01-11'), True),   # 10天，触发
            (pd.Timestamp('2023-01-15'), True),   # 14天，触发
        ]

        for date, should_trigger in dates:
            signals = exit_strategy.generate_exit_signals(
                positions,
                sample_stock_data,
                date
            )
            if should_trigger:
                assert 'A' in signals, f"应该在 {date} 触发"
            else:
                assert 'A' not in signals, f"不应该在 {date} 触发"

    def test_missing_stock_data_fallback_to_calendar_days(self):
        """测试股票数据缺失时回退到日历天数"""
        positions = {
            'MISSING': Position(
                stock_code='MISSING',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=11.0,
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
        }

        exit_strategy = TimeBasedExit(params={
            'holding_period': 10,
            'count_trading_days_only': True
        })

        # 数据中没有MISSING股票
        data = {}

        # 11天后（日历天数）
        signals = exit_strategy.generate_exit_signals(
            positions,
            data,
            pd.Timestamp('2023-01-12')
        )

        # 应该使用日历天数，11天 >= 10天，触发退出
        assert 'MISSING' in signals

    def test_trading_days_calculation_exception(self, sample_stock_data):
        """测试交易日计算异常情况"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=11.0,
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
        }

        # 创建异常数据（无法正常计算mask）
        bad_data = {
            'A': pd.DataFrame({
                'close': [10.0],
                'open': [10.0],
                'high': [10.0],
                'low': [10.0]
            })  # 没有日期索引
        }

        exit_strategy = TimeBasedExit(params={
            'holding_period': 5,
            'count_trading_days_only': True
        })

        # 应该捕获异常并回退到日历天数
        signals = exit_strategy.generate_exit_signals(
            positions,
            bad_data,
            pd.Timestamp('2023-01-10')
        )

        # 9天日历天数 >= 5天，应该触发
        assert 'A' in signals

    def test_edge_case_min_holding_period(self):
        """测试最小持仓期（1天）的边界情况"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=11.0,
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
        }

        exit_strategy = TimeBasedExit(params={'holding_period': 1})

        # 当天就应该触发（0天 >= 1天会在次日触发）
        signals = exit_strategy.generate_exit_signals(
            positions,
            {},
            pd.Timestamp('2023-01-02')
        )

        assert 'A' in signals


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
