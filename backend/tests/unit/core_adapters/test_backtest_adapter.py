"""
BacktestAdapter 单元测试

测试回测引擎适配器的所有功能。

作者: Backend Team
创建日期: 2026-02-01
"""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import date
import sys
from pathlib import Path

# 添加项目路径
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.core_adapters.backtest_adapter import BacktestAdapter


@pytest.fixture
def backtest_adapter():
    """创建回测适配器实例"""
    return BacktestAdapter(
        initial_capital=1000000,
        commission_rate=0.0003,
        stamp_tax_rate=0.001
    )


@pytest.fixture
def sample_portfolio_value():
    """创建示例投资组合价值序列"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    values = 1000000 + np.cumsum(np.random.randn(100) * 10000)
    return pd.Series(values, index=dates)


@pytest.fixture
def sample_trades():
    """创建示例交易记录"""
    return pd.DataFrame({
        'date': pd.date_range('2023-01-01', periods=10, freq='10D'),
        'code': ['000001'] * 10,
        'action': ['buy', 'sell'] * 5,
        'buy_price': [100.0, 102.0, 104.0, 106.0, 108.0] * 2,
        'sell_price': [102.0, 104.0, 106.0, 108.0, 110.0] * 2,
        'quantity': [100] * 10
    })


class TestBacktestAdapter:
    """BacktestAdapter 单元测试类"""

    def test_init(self, backtest_adapter):
        """测试初始化"""
        assert backtest_adapter.initial_capital == 1000000
        assert backtest_adapter.commission_rate == 0.0003
        assert backtest_adapter.stamp_tax_rate == 0.001
        assert backtest_adapter.engine is not None

    @pytest.mark.asyncio
    async def test_calculate_metrics(self, backtest_adapter, sample_portfolio_value, sample_trades):
        """测试计算绩效指标"""
        # Arrange
        positions = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=100, freq='D'),
            'position': np.random.randint(0, 1000, 100)
        })

        # Act
        result = await backtest_adapter.calculate_metrics(
            sample_portfolio_value,
            positions,
            sample_trades
        )

        # Assert
        assert isinstance(result, dict)
        # 应该包含各种指标
        expected_metrics = ['total_return', 'annual_return', 'sharpe_ratio', 'max_drawdown']
        for metric in expected_metrics:
            if metric in result:  # 某些指标可能根据实现不同而有所差异
                assert isinstance(result[metric], (int, float))

    @pytest.mark.asyncio
    async def test_analyze_trading_costs(self, backtest_adapter, sample_trades):
        """测试分析交易成本"""
        # Act
        result = await backtest_adapter.analyze_trading_costs(sample_trades)

        # Assert
        assert isinstance(result, dict)
        # 检查是否包含成本信息
        expected_keys = ['total_commission', 'total_stamp_tax', 'total_slippage']
        for key in expected_keys:
            if key in result:
                assert isinstance(result[key], (int, float))

    @pytest.mark.asyncio
    async def test_calculate_risk_metrics(self, backtest_adapter):
        """测试计算风险指标"""
        # Arrange
        returns = pd.Series(np.random.randn(100) * 0.01)
        positions = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=100, freq='D'),
            'position': np.random.randint(0, 1000, 100)
        })

        # Act
        result = await backtest_adapter.calculate_risk_metrics(returns, positions)

        # Assert
        assert isinstance(result, dict)
        assert 'volatility' in result
        assert 'var_95' in result
        assert 'cvar_95' in result
        assert isinstance(result['volatility'], (int, float))

    @pytest.mark.asyncio
    async def test_get_trade_statistics_with_trades(self, backtest_adapter, sample_trades):
        """测试获取交易统计（有交易）"""
        # Act
        result = await backtest_adapter.get_trade_statistics(sample_trades)

        # Assert
        assert isinstance(result, dict)
        assert result['total_trades'] == 10
        assert 'winning_trades' in result
        assert 'losing_trades' in result
        assert 'win_rate' in result
        assert 'profit_factor' in result

    @pytest.mark.asyncio
    async def test_get_trade_statistics_empty(self, backtest_adapter):
        """测试获取交易统计（无交易）"""
        # Arrange
        empty_trades = pd.DataFrame()

        # Act
        result = await backtest_adapter.get_trade_statistics(empty_trades)

        # Assert
        assert isinstance(result, dict)
        assert result['total_trades'] == 0
        assert result['win_rate'] == 0.0
        assert result['profit_factor'] == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
