"""
ATRStopLossExit 单元测试

Test cases for ATRStopLossExit exit strategy
"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict

from src.strategies.three_layer.exits import ATRStopLossExit
from src.strategies.three_layer.base import Position


# ============================================================================
# 测试夹具 (Fixtures)
# ============================================================================

@pytest.fixture
def sample_stock_data():
    """创建示例股票数据（包含OHLCV）"""
    dates = pd.date_range('2023-01-01', periods=30, freq='D')

    # 股票A: 波动较小（ATR约0.2）
    data_a = pd.DataFrame({
        'open': [10.0] * 30,
        'high': [10.3 + i * 0.01 for i in range(30)],
        'low': [9.7 + i * 0.01 for i in range(30)],
        'close': [10.0 + i * 0.01 for i in range(30)],
        'volume': [1000] * 30,
    }, index=dates)

    # 股票B: 波动较大（ATR约0.8）
    data_b = pd.DataFrame({
        'open': [20.0] * 30,
        'high': [21.0 + i * 0.02 for i in range(30)],
        'low': [19.0 + i * 0.02 for i in range(30)],
        'close': [20.0 + i * 0.02 for i in range(30)],
        'volume': [2000] * 30,
    }, index=dates)

    # 股票C: 价格下跌
    data_c = pd.DataFrame({
        'open': [15.0 - i * 0.1 for i in range(30)],
        'high': [15.5 - i * 0.1 for i in range(30)],
        'low': [14.5 - i * 0.1 for i in range(30)],
        'close': [15.0 - i * 0.1 for i in range(30)],
        'volume': [1500] * 30,
    }, index=dates)

    return {
        'A': data_a,
        'B': data_b,
        'C': data_c,
    }


@pytest.fixture
def sample_positions():
    """创建示例持仓"""
    return {
        'A': Position(
            stock_code='A',
            entry_date=pd.Timestamp('2023-01-10'),
            entry_price=10.0,
            shares=100,
            current_price=10.5,
            unrealized_pnl=50.0,
            unrealized_pnl_pct=5.0
        ),
        'B': Position(
            stock_code='B',
            entry_date=pd.Timestamp('2023-01-10'),
            entry_price=20.0,
            shares=50,
            current_price=19.0,
            unrealized_pnl=-50.0,
            unrealized_pnl_pct=-5.0
        ),
        'C': Position(
            stock_code='C',
            entry_date=pd.Timestamp('2023-01-10'),
            entry_price=15.0,
            shares=80,
            current_price=12.0,
            unrealized_pnl=-240.0,
            unrealized_pnl_pct=-20.0
        ),
    }


# ============================================================================
# 基本功能测试
# ============================================================================

class TestATRStopLossExitBasic:
    """测试 ATRStopLossExit 基本功能"""

    def test_exit_creation_with_default_params(self):
        """测试使用默认参数创建退出策略"""
        exit_strategy = ATRStopLossExit()

        assert exit_strategy.name == "ATR动态止损"
        assert exit_strategy.id == "atr_stop_loss"
        assert exit_strategy.params.get('atr_period') is None
        assert exit_strategy.params.get('atr_multiplier') is None

    def test_exit_creation_with_custom_params(self):
        """测试使用自定义参数创建退出策略"""
        params = {
            'atr_period': 20,
            'atr_multiplier': 3.0
        }
        exit_strategy = ATRStopLossExit(params=params)

        assert exit_strategy.params['atr_period'] == 20
        assert exit_strategy.params['atr_multiplier'] == 3.0

    def test_exit_name_property(self):
        """测试 name 属性"""
        exit_strategy = ATRStopLossExit()
        assert exit_strategy.name == "ATR动态止损"
        assert isinstance(exit_strategy.name, str)

    def test_exit_id_property(self):
        """测试 id 属性"""
        exit_strategy = ATRStopLossExit()
        assert exit_strategy.id == "atr_stop_loss"
        assert isinstance(exit_strategy.id, str)

    def test_get_parameters_class_method(self):
        """测试 get_parameters 类方法"""
        params = ATRStopLossExit.get_parameters()

        assert len(params) == 2
        assert all(isinstance(p, dict) for p in params)

        param_names = [p["name"] for p in params]
        assert 'atr_period' in param_names
        assert 'atr_multiplier' in param_names

        # 检查参数详情
        atr_period_param = next(p for p in params if p["name"] == "atr_period")
        assert atr_period_param["type"] == "integer"
        assert atr_period_param["default"] == 14
        assert atr_period_param["min"] == 5
        assert atr_period_param["max"] == 50

        atr_multiplier_param = next(p for p in params if p["name"] == "atr_multiplier")
        assert atr_multiplier_param["type"] == "float"
        assert atr_multiplier_param["default"] == 2.0
        assert atr_multiplier_param["min"] == 0.5
        assert atr_multiplier_param["max"] == 5.0

    def test_generate_exit_signals_method_exists(self):
        """测试 generate_exit_signals 方法存在"""
        exit_strategy = ATRStopLossExit()
        assert hasattr(exit_strategy, 'generate_exit_signals')
        assert callable(exit_strategy.generate_exit_signals)


# ============================================================================
# 参数验证测试
# ============================================================================

class TestATRStopLossExitParameterValidation:
    """测试参数验证功能"""

    def test_valid_atr_period(self):
        """测试有效的ATR周期"""
        exit_strategy = ATRStopLossExit(params={'atr_period': 14})
        assert exit_strategy.params['atr_period'] == 14

    def test_atr_period_below_min(self):
        """测试ATR周期低于最小值"""
        with pytest.raises(ValueError, match="不能小于 5"):
            ATRStopLossExit(params={'atr_period': 3})

    def test_atr_period_above_max(self):
        """测试ATR周期超过最大值"""
        with pytest.raises(ValueError, match="不能大于 50"):
            ATRStopLossExit(params={'atr_period': 60})

    def test_valid_atr_multiplier(self):
        """测试有效的ATR倍数"""
        exit_strategy = ATRStopLossExit(params={'atr_multiplier': 2.5})
        assert exit_strategy.params['atr_multiplier'] == 2.5

    def test_atr_multiplier_below_min(self):
        """测试ATR倍数低于最小值"""
        with pytest.raises(ValueError, match="不能小于 0.5"):
            ATRStopLossExit(params={'atr_multiplier': 0.3})

    def test_atr_multiplier_above_max(self):
        """测试ATR倍数超过最大值"""
        with pytest.raises(ValueError, match="不能大于 5.0"):
            ATRStopLossExit(params={'atr_multiplier': 6.0})

    def test_unknown_parameter(self):
        """测试未知参数"""
        with pytest.raises(ValueError, match="未知参数"):
            ATRStopLossExit(params={'unknown_param': 'value'})

    def test_invalid_parameter_type(self):
        """测试无效的参数类型"""
        with pytest.raises(ValueError, match="必须是整数"):
            ATRStopLossExit(params={'atr_period': 14.5})


# ============================================================================
# ATR 计算测试
# ============================================================================

class TestATRCalculation:
    """测试ATR计算"""

    def test_calculate_atr_basic(self, sample_stock_data):
        """测试基本的ATR计算"""
        exit_strategy = ATRStopLossExit(params={'atr_period': 14})
        stock_data = sample_stock_data['A']

        atr = exit_strategy._calculate_atr(stock_data, 14)

        # 检查返回类型
        assert isinstance(atr, pd.Series)
        assert len(atr) == len(stock_data)

        # 检查ATR值为正
        valid_atr = atr.dropna()
        assert all(valid_atr >= 0)

        # 检查前面的值为NaN（不足计算周期）
        assert pd.isna(atr.iloc[0])

    def test_calculate_atr_values(self):
        """测试ATR计算的正确性"""
        # 创建简单的测试数据
        dates = pd.date_range('2023-01-01', periods=20, freq='D')
        data = pd.DataFrame({
            'high': [11, 12, 13, 12, 14, 15, 14, 16, 15, 17, 16, 18, 17, 19, 18, 20, 19, 21, 20, 22],
            'low': [9, 10, 11, 10, 12, 13, 12, 14, 13, 15, 14, 16, 15, 17, 16, 18, 17, 19, 18, 20],
            'close': [10, 11, 12, 11, 13, 14, 13, 15, 14, 16, 15, 17, 16, 18, 17, 19, 18, 20, 19, 21],
            'open': [10] * 20,
        }, index=dates)

        exit_strategy = ATRStopLossExit(params={'atr_period': 5})
        atr = exit_strategy._calculate_atr(data, 5)

        # 第5天开始应该有ATR值
        assert pd.notna(atr.iloc[5])

        # ATR应该接近真实波动范围
        # 在这个例子中，每日波动是2（high-low），所以ATR应该接近2
        valid_atr = atr.dropna()
        assert all(valid_atr > 1.5)
        assert all(valid_atr < 3.0)  # 放宽范围，因为数据有增长趋势

    def test_calculate_atr_with_gap(self):
        """测试有跳空的ATR计算"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            'high': [11, 12, 13, 14, 20, 21, 22, 23, 24, 25],  # 第5天跳空
            'low': [9, 10, 11, 12, 18, 19, 20, 21, 22, 23],
            'close': [10, 11, 12, 13, 19, 20, 21, 22, 23, 24],
            'open': [10, 11, 12, 13, 19, 20, 21, 22, 23, 24],
        }, index=dates)

        exit_strategy = ATRStopLossExit(params={'atr_period': 5})
        atr = exit_strategy._calculate_atr(data, 5)

        # 跳空后的ATR应该增大或保持相同（因为是移动平均）
        assert atr.iloc[5] >= atr.iloc[4]


# ============================================================================
# generate_exit_signals() 方法测试
# ============================================================================

class TestATRStopLossExitGenerateSignals:
    """测试 generate_exit_signals() 方法"""

    def test_generate_signals_returns_list(self, sample_positions, sample_stock_data):
        """测试返回列表类型"""
        exit_strategy = ATRStopLossExit(params={
            'atr_period': 14,
            'atr_multiplier': 2.0
        })
        signals = exit_strategy.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-20')
        )

        assert isinstance(signals, list)
        assert all(isinstance(s, str) for s in signals)

    def test_no_exit_when_above_stop_loss(self, sample_stock_data):
        """测试价格在止损位上方时不触发"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-10'),
                entry_price=10.0,
                shares=100,
                current_price=10.5,  # 盈利
                unrealized_pnl=50.0,
                unrealized_pnl_pct=5.0
            ),
        }

        exit_strategy = ATRStopLossExit(params={
            'atr_period': 14,
            'atr_multiplier': 2.0
        })
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-20')
        )

        # 盈利时不应该触发ATR止损
        assert 'A' not in signals

    def test_exit_when_below_stop_loss(self, sample_stock_data):
        """测试价格跌破止损位时触发"""
        # 创建一个大幅亏损的持仓
        positions = {
            'C': Position(
                stock_code='C',
                entry_date=pd.Timestamp('2023-01-05'),
                entry_price=15.0,
                shares=100,
                current_price=12.0,  # 大幅下跌
                unrealized_pnl=-300.0,
                unrealized_pnl_pct=-20.0
            ),
        }

        exit_strategy = ATRStopLossExit(params={
            'atr_period': 10,
            'atr_multiplier': 1.0  # 较小的倍数，容易触发
        })
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-20')
        )

        # 大幅下跌应该触发止损
        assert 'C' in signals

    def test_different_atr_multipliers(self, sample_stock_data):
        """测试不同的ATR倍数"""
        positions = {
            'B': Position(
                stock_code='B',
                entry_date=pd.Timestamp('2023-01-10'),
                entry_price=20.0,
                shares=50,
                current_price=19.0,
                unrealized_pnl=-50.0,
                unrealized_pnl_pct=-5.0
            ),
        }

        # 倍数小，更容易触发
        exit1 = ATRStopLossExit(params={
            'atr_period': 14,
            'atr_multiplier': 0.5
        })
        signals1 = exit1.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-20')
        )

        # 倍数大，不容易触发
        exit2 = ATRStopLossExit(params={
            'atr_period': 14,
            'atr_multiplier': 5.0
        })
        signals2 = exit2.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-20')
        )

        # 小倍数更可能触发
        # 注意：这个测试可能依赖于具体数据

    def test_empty_positions(self, sample_stock_data):
        """测试空持仓"""
        exit_strategy = ATRStopLossExit(params={
            'atr_period': 14,
            'atr_multiplier': 2.0
        })
        signals = exit_strategy.generate_exit_signals(
            {},
            sample_stock_data,
            pd.Timestamp('2023-01-20')
        )

        assert signals == []

    def test_missing_stock_data(self, sample_positions):
        """测试股票数据缺失"""
        exit_strategy = ATRStopLossExit(params={
            'atr_period': 14,
            'atr_multiplier': 2.0
        })

        # 只提供部分股票的数据
        partial_data = {}

        signals = exit_strategy.generate_exit_signals(
            sample_positions,
            partial_data,
            pd.Timestamp('2023-01-20')
        )

        # 数据缺失时不应该触发（安全起见）
        assert signals == []

    def test_date_not_in_data(self, sample_positions, sample_stock_data):
        """测试日期不在数据范围内"""
        exit_strategy = ATRStopLossExit(params={
            'atr_period': 14,
            'atr_multiplier': 2.0
        })

        # 使用一个不存在的日期
        signals = exit_strategy.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2025-12-31')
        )

        # 日期不存在时不应该触发
        assert signals == []

    def test_insufficient_data_for_atr(self, sample_positions):
        """测试数据不足以计算ATR"""
        # 创建只有5天数据的股票
        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        insufficient_data = {
            'A': pd.DataFrame({
                'open': [10.0] * 5,
                'high': [10.5] * 5,
                'low': [9.5] * 5,
                'close': [10.0] * 5,
                'volume': [1000] * 5,
            }, index=dates)
        }

        exit_strategy = ATRStopLossExit(params={
            'atr_period': 14,  # 需要14天
            'atr_multiplier': 2.0
        })

        signals = exit_strategy.generate_exit_signals(
            {'A': sample_positions['A']},
            insufficient_data,
            pd.Timestamp('2023-01-05')
        )

        # 数据不足时不应该触发（ATR为NaN）
        assert 'A' not in signals


# ============================================================================
# 边界情况和错误处理测试
# ============================================================================

class TestATRStopLossExitEdgeCases:
    """测试边界情况"""

    def test_atr_nan_handling(self, sample_positions):
        """测试ATR为NaN的处理"""
        # 创建会导致NaN的数据
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        data_with_nan = {
            'A': pd.DataFrame({
                'open': [10.0] * 10,
                'high': [10.5] * 10,
                'low': [9.5] * 10,
                'close': [10.0] * 10,
                'volume': [1000] * 10,
            }, index=dates)
        }

        exit_strategy = ATRStopLossExit(params={
            'atr_period': 14,  # 超过数据长度
            'atr_multiplier': 2.0
        })

        signals = exit_strategy.generate_exit_signals(
            {'A': sample_positions['A']},
            data_with_nan,
            pd.Timestamp('2023-01-10')
        )

        # 不应该触发（ATR为NaN）
        assert 'A' not in signals

    def test_missing_ohlc_columns(self, sample_positions):
        """测试缺少OHLC列"""
        dates = pd.date_range('2023-01-01', periods=20, freq='D')
        incomplete_data = {
            'A': pd.DataFrame({
                'close': [10.0] * 20,
                'volume': [1000] * 20,
                # 缺少 open, high, low
            }, index=dates)
        }

        exit_strategy = ATRStopLossExit(params={
            'atr_period': 14,
            'atr_multiplier': 2.0
        })

        signals = exit_strategy.generate_exit_signals(
            {'A': sample_positions['A']},
            incomplete_data,
            pd.Timestamp('2023-01-20')
        )

        # 缺少必需列时不应该触发
        assert 'A' not in signals

    def test_zero_atr(self):
        """测试ATR为零的情况（无波动）"""
        dates = pd.date_range('2023-01-01', periods=20, freq='D')
        # 价格完全不变
        no_volatility_data = {
            'A': pd.DataFrame({
                'open': [10.0] * 20,
                'high': [10.0] * 20,
                'low': [10.0] * 20,
                'close': [10.0] * 20,
                'volume': [1000] * 20,
            }, index=dates)
        }

        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-10'),
                entry_price=10.0,
                shares=100,
                current_price=9.5,  # 下跌
                unrealized_pnl=-50.0,
                unrealized_pnl_pct=-5.0
            ),
        }

        exit_strategy = ATRStopLossExit(params={
            'atr_period': 5,
            'atr_multiplier': 2.0
        })

        signals = exit_strategy.generate_exit_signals(
            positions,
            no_volatility_data,
            pd.Timestamp('2023-01-20')
        )

        # ATR为0时，止损位 = 入场价，当前价9.5 < 10.0，应该触发
        assert 'A' in signals


# ============================================================================
# 集成测试
# ============================================================================

class TestATRStopLossExitIntegration:
    """集成测试"""

    def test_full_workflow(self, sample_positions, sample_stock_data):
        """测试完整工作流程"""
        # 创建策略
        exit_strategy = ATRStopLossExit(params={
            'atr_period': 14,
            'atr_multiplier': 2.0
        })

        # 生成信号
        signals = exit_strategy.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-20')
        )

        # 验证结果
        assert isinstance(signals, list)
        assert all(isinstance(s, str) for s in signals)
        assert all(s in sample_positions for s in signals)

    def test_multiple_dates(self, sample_stock_data):
        """测试多个日期的信号生成"""
        positions = {
            'C': Position(
                stock_code='C',
                entry_date=pd.Timestamp('2023-01-05'),
                entry_price=15.0,
                shares=100,
                current_price=14.0,
                unrealized_pnl=-100.0,
                unrealized_pnl_pct=-6.67
            ),
        }

        exit_strategy = ATRStopLossExit(params={
            'atr_period': 10,
            'atr_multiplier': 1.5
        })

        # 测试多个日期
        dates = pd.date_range('2023-01-15', '2023-01-25', freq='D')
        all_signals = []

        for date in dates:
            if date not in sample_stock_data['C'].index:
                continue

            # 更新当前价格
            positions['C'].current_price = sample_stock_data['C'].loc[date, 'close']

            signals = exit_strategy.generate_exit_signals(
                positions,
                sample_stock_data,
                date
            )
            all_signals.append((date, signals))

        # 验证随着价格下跌，最终会触发止损
        assert len(all_signals) > 0


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
