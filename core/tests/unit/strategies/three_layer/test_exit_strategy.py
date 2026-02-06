"""
ExitStrategy 基类单元测试

Test cases for ExitStrategy base class
"""

import pytest
import pandas as pd
from typing import Any, Dict, List

from src.strategies.three_layer.base import ExitStrategy, Position


# ============================================================================
# 测试用具体实现类
# ============================================================================

class ConcreteExit(ExitStrategy):
    """具体的退出策略实现（用于测试）"""

    @property
    def name(self) -> str:
        return "测试退出策略"

    @property
    def id(self) -> str:
        return "test_exit"

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
            },
            {
                "name": "take_profit_pct",
                "label": "止盈百分比",
                "type": "float",
                "default": 10.0,
                "min": 1.0,
                "max": 50.0,
                "description": "盈利达到此百分比时卖出"
            },
            {
                "name": "holding_period",
                "label": "持仓天数",
                "type": "integer",
                "default": 10,
                "min": 1,
                "max": 100,
                "description": "持仓超过此天数后强制卖出"
            },
            {
                "name": "use_time_exit",
                "label": "使用时间退出",
                "type": "boolean",
                "default": False,
                "description": "是否使用时间退出"
            },
            {
                "name": "exit_mode",
                "label": "退出模式",
                "type": "select",
                "default": "stop_loss",
                "options": [
                    {"value": "stop_loss", "label": "止损"},
                    {"value": "take_profit", "label": "止盈"},
                    {"value": "both", "label": "止损止盈"},
                ],
                "description": "退出模式"
            },
        ]

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> List[str]:
        """简单的退出策略：固定止损止盈"""
        exit_stocks = []
        stop_loss_pct = self.params.get("stop_loss_pct", -5.0)
        take_profit_pct = self.params.get("take_profit_pct", 10.0)

        for stock, position in positions.items():
            pnl_pct = position.unrealized_pnl_pct

            # 触发止损
            if pnl_pct <= stop_loss_pct:
                exit_stocks.append(stock)

            # 触发止盈
            elif pnl_pct >= take_profit_pct:
                exit_stocks.append(stock)

        return exit_stocks


# ============================================================================
# 测试夹具 (Fixtures)
# ============================================================================

@pytest.fixture
def sample_positions():
    """创建示例持仓数据"""
    positions = {
        'A': Position(
            stock_code='A',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=10.0,
            shares=100,
            current_price=11.0,  # 盈利10%
            unrealized_pnl=100.0,
            unrealized_pnl_pct=10.0
        ),
        'B': Position(
            stock_code='B',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=20.0,
            shares=50,
            current_price=19.0,  # 亏损5%
            unrealized_pnl=-50.0,
            unrealized_pnl_pct=-5.0
        ),
        'C': Position(
            stock_code='C',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=15.0,
            shares=80,
            current_price=15.3,  # 盈利2%
            unrealized_pnl=24.0,
            unrealized_pnl_pct=2.0
        ),
    }
    return positions


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


# ============================================================================
# 基本功能测试
# ============================================================================

class TestExitStrategyBasic:
    """测试 ExitStrategy 基本功能"""

    def test_exit_creation_with_default_params(self):
        """测试使用默认参数创建退出策略"""
        exit_strategy = ConcreteExit()

        assert exit_strategy.name == "测试退出策略"
        assert exit_strategy.id == "test_exit"
        assert exit_strategy.params == {}

    def test_exit_creation_with_custom_params(self):
        """测试使用自定义参数创建退出策略"""
        params = {
            'stop_loss_pct': -10.0,
            'take_profit_pct': 20.0,
            'holding_period': 15,
            'use_time_exit': True,
            'exit_mode': 'both'
        }
        exit_strategy = ConcreteExit(params=params)

        assert exit_strategy.params == params

    def test_exit_name_property(self):
        """测试 name 属性"""
        exit_strategy = ConcreteExit()
        assert exit_strategy.name == "测试退出策略"
        assert isinstance(exit_strategy.name, str)

    def test_exit_id_property(self):
        """测试 id 属性"""
        exit_strategy = ConcreteExit()
        assert exit_strategy.id == "test_exit"
        assert isinstance(exit_strategy.id, str)

    def test_get_parameters_class_method(self):
        """测试 get_parameters 类方法"""
        params = ConcreteExit.get_parameters()

        assert len(params) == 5
        assert all(isinstance(p, dict) for p in params)

        # 检查参数名称
        param_names = [p["name"] for p in params]
        assert 'stop_loss_pct' in param_names
        assert 'take_profit_pct' in param_names
        assert 'holding_period' in param_names
        assert 'use_time_exit' in param_names
        assert 'exit_mode' in param_names

    def test_generate_exit_signals_method_exists(self):
        """测试 generate_exit_signals 方法存在"""
        exit_strategy = ConcreteExit()
        assert hasattr(exit_strategy, 'generate_exit_signals')
        assert callable(exit_strategy.generate_exit_signals)

    def test_repr_method(self):
        """测试 __repr__ 方法"""
        exit_strategy = ConcreteExit(params={'stop_loss_pct': -10.0})
        repr_str = repr(exit_strategy)

        assert "测试退出策略" in repr_str
        assert "test_exit" in repr_str
        assert "stop_loss_pct" in repr_str


# ============================================================================
# Position 数据类测试
# ============================================================================

class TestPositionDataClass:
    """测试 Position 数据类"""

    def test_position_creation(self):
        """测试创建 Position"""
        position = Position(
            stock_code='TEST',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=100.0,
            shares=10,
            current_price=110.0,
            unrealized_pnl=100.0,
            unrealized_pnl_pct=10.0
        )

        assert position.stock_code == 'TEST'
        assert position.entry_date == pd.Timestamp('2023-01-01')
        assert position.entry_price == 100.0
        assert position.shares == 10
        assert position.current_price == 110.0
        assert position.unrealized_pnl == 100.0
        assert position.unrealized_pnl_pct == 10.0

    def test_position_profit(self):
        """测试盈利持仓"""
        position = Position(
            stock_code='A',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=10.0,
            shares=100,
            current_price=12.0,  # 盈利20%
            unrealized_pnl=200.0,
            unrealized_pnl_pct=20.0
        )

        assert position.unrealized_pnl > 0
        assert position.unrealized_pnl_pct > 0

    def test_position_loss(self):
        """测试亏损持仓"""
        position = Position(
            stock_code='B',
            entry_date=pd.Timestamp('2023-01-01'),
            entry_price=20.0,
            shares=50,
            current_price=18.0,  # 亏损10%
            unrealized_pnl=-100.0,
            unrealized_pnl_pct=-10.0
        )

        assert position.unrealized_pnl < 0
        assert position.unrealized_pnl_pct < 0


# ============================================================================
# 参数验证测试
# ============================================================================

class TestExitStrategyParameterValidation:
    """测试参数验证功能"""

    def test_valid_stop_loss_parameter(self):
        """测试有效的止损参数"""
        exit_strategy = ConcreteExit(params={'stop_loss_pct': -8.0})
        assert exit_strategy.params['stop_loss_pct'] == -8.0

    def test_stop_loss_below_min(self):
        """测试止损参数低于最小值"""
        with pytest.raises(ValueError, match="不能小于 -20.0"):
            ConcreteExit(params={'stop_loss_pct': -25.0})

    def test_stop_loss_above_max(self):
        """测试止损参数超过最大值"""
        with pytest.raises(ValueError, match="不能大于 -1.0"):
            ConcreteExit(params={'stop_loss_pct': 0.0})

    def test_valid_take_profit_parameter(self):
        """测试有效的止盈参数"""
        exit_strategy = ConcreteExit(params={'take_profit_pct': 15.0})
        assert exit_strategy.params['take_profit_pct'] == 15.0

    def test_take_profit_below_min(self):
        """测试止盈参数低于最小值"""
        with pytest.raises(ValueError, match="不能小于 1.0"):
            ConcreteExit(params={'take_profit_pct': 0.5})

    def test_take_profit_above_max(self):
        """测试止盈参数超过最大值"""
        with pytest.raises(ValueError, match="不能大于 50.0"):
            ConcreteExit(params={'take_profit_pct': 60.0})

    def test_valid_holding_period_parameter(self):
        """测试有效的持仓天数参数"""
        exit_strategy = ConcreteExit(params={'holding_period': 20})
        assert exit_strategy.params['holding_period'] == 20

    def test_unknown_parameter(self):
        """测试未知参数"""
        with pytest.raises(ValueError, match="未知参数"):
            ConcreteExit(params={'unknown': 'value'})


# ============================================================================
# generate_exit_signals() 方法测试
# ============================================================================

class TestExitStrategyGenerateSignals:
    """测试 generate_exit_signals() 方法"""

    def test_generate_signals_returns_list(self, sample_positions, sample_stock_data):
        """测试返回列表类型"""
        exit_strategy = ConcreteExit(params={'stop_loss_pct': -5.0, 'take_profit_pct': 10.0})
        signals = exit_strategy.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        assert isinstance(signals, list)

    def test_generate_signals_stop_loss(self, sample_stock_data):
        """测试止损触发"""
        # 创建亏损持仓
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=9.0,  # 亏损10%
                unrealized_pnl=-100.0,
                unrealized_pnl_pct=-10.0
            ),
        }

        exit_strategy = ConcreteExit(params={'stop_loss_pct': -5.0})
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 亏损10%应该触发-5%的止损
        assert 'A' in signals

    def test_generate_signals_take_profit(self, sample_stock_data):
        """测试止盈触发"""
        # 创建盈利持仓
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=12.0,  # 盈利20%
                unrealized_pnl=200.0,
                unrealized_pnl_pct=20.0
            ),
        }

        exit_strategy = ConcreteExit(params={'take_profit_pct': 10.0})
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 盈利20%应该触发10%的止盈
        assert 'A' in signals

    def test_generate_signals_no_exit(self, sample_stock_data):
        """测试不触发退出"""
        # 创建小幅盈利持仓
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=10.3,  # 盈利3%
                unrealized_pnl=30.0,
                unrealized_pnl_pct=3.0
            ),
        }

        exit_strategy = ConcreteExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 10.0
        })
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 盈利3%不应该触发退出
        assert 'A' not in signals

    def test_generate_signals_multiple_positions(self, sample_positions, sample_stock_data):
        """测试多个持仓"""
        exit_strategy = ConcreteExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 10.0
        })
        signals = exit_strategy.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # A: 盈利10% -> 触发止盈
        # B: 亏损5% -> 触发止损
        # C: 盈利2% -> 不触发
        assert 'A' in signals  # 止盈
        assert 'B' in signals  # 止损
        assert 'C' not in signals  # 不触发

    def test_generate_signals_empty_positions(self, sample_stock_data):
        """测试空持仓"""
        exit_strategy = ConcreteExit(params={'stop_loss_pct': -5.0})
        signals = exit_strategy.generate_exit_signals(
            {},
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        assert signals == []

    def test_generate_signals_stock_codes_match(self, sample_positions, sample_stock_data):
        """测试返回的股票代码正确"""
        exit_strategy = ConcreteExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 10.0
        })
        signals = exit_strategy.generate_exit_signals(
            sample_positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 所有返回的股票代码都应该在持仓中
        for stock in signals:
            assert stock in sample_positions


# ============================================================================
# 边界情况和错误处理测试
# ============================================================================

class TestExitStrategyEdgeCases:
    """测试边界情况"""

    def test_cannot_instantiate_abstract_class(self):
        """测试不能直接实例化抽象基类"""
        with pytest.raises(TypeError):
            ExitStrategy()

    def test_stop_loss_equals_current_pnl(self, sample_stock_data):
        """测试止损值等于当前盈亏"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=9.5,  # 亏损5%
                unrealized_pnl=-50.0,
                unrealized_pnl_pct=-5.0
            ),
        }

        exit_strategy = ConcreteExit(params={'stop_loss_pct': -5.0})
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 刚好达到止损应该触发
        assert 'A' in signals

    def test_take_profit_equals_current_pnl(self, sample_stock_data):
        """测试止盈值等于当前盈亏"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=11.0,  # 盈利10%
                unrealized_pnl=100.0,
                unrealized_pnl_pct=10.0
            ),
        }

        exit_strategy = ConcreteExit(params={'take_profit_pct': 10.0})
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 刚好达到止盈应该触发
        assert 'A' in signals

    def test_zero_pnl(self, sample_stock_data):
        """测试零盈亏"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=10.0,  # 零盈亏
                unrealized_pnl=0.0,
                unrealized_pnl_pct=0.0
            ),
        }

        exit_strategy = ConcreteExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 10.0
        })
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 零盈亏不应该触发
        assert 'A' not in signals

    def test_extreme_loss(self, sample_stock_data):
        """测试极端亏损"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=5.0,  # 亏损50%
                unrealized_pnl=-500.0,
                unrealized_pnl_pct=-50.0
            ),
        }

        exit_strategy = ConcreteExit(params={'stop_loss_pct': -5.0})
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 极端亏损应该触发止损
        assert 'A' in signals

    def test_extreme_profit(self, sample_stock_data):
        """测试极端盈利"""
        positions = {
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=20.0,  # 盈利100%
                unrealized_pnl=1000.0,
                unrealized_pnl_pct=100.0
            ),
        }

        exit_strategy = ConcreteExit(params={'take_profit_pct': 10.0})
        signals = exit_strategy.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )

        # 极端盈利应该触发止盈
        assert 'A' in signals


# ============================================================================
# 集成测试
# ============================================================================

class TestExitStrategyIntegration:
    """集成测试"""

    def test_full_workflow(self, sample_positions, sample_stock_data):
        """测试完整工作流程"""
        # 创建策略
        exit_strategy = ConcreteExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 10.0,
            'holding_period': 10,
            'use_time_exit': False,
            'exit_mode': 'both'
        })

        # 生成信号
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
            'A': Position(
                stock_code='A',
                entry_date=pd.Timestamp('2023-01-01'),
                entry_price=10.0,
                shares=100,
                current_price=9.3,  # 亏损7%
                unrealized_pnl=-70.0,
                unrealized_pnl_pct=-7.0
            ),
        }

        # 止损-5%：应该触发
        exit1 = ConcreteExit(params={'stop_loss_pct': -5.0})
        signals1 = exit1.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )
        assert 'A' in signals1

        # 止损-10%：不应该触发
        exit2 = ConcreteExit(params={'stop_loss_pct': -10.0})
        signals2 = exit2.generate_exit_signals(
            positions,
            sample_stock_data,
            pd.Timestamp('2023-01-05')
        )
        assert 'A' not in signals2


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
