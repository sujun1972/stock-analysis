#!/usr/bin/env python3
"""
三层架构回测集成测试

测试完整的三层架构回测流程，包括选股、入场、退出策略的协同工作

Author: Stock Analysis Core Team
Date: 2026-02-06
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.backtest.backtest_engine import BacktestEngine
from src.strategies.three_layer.selectors import (
    MomentumSelector,
    ValueSelector,
    ExternalSelector
)
from src.strategies.three_layer.entries import (
    MABreakoutEntry,
    RSIOversoldEntry,
    ImmediateEntry
)
from src.strategies.three_layer.exits import (
    ATRStopLossExit,
    FixedStopLossExit,
    TimeBasedExit,
    CombinedExit
)


@pytest.fixture
def realistic_price_data():
    """
    生成更真实的价格数据（包含OHLCV）

    模拟60天、10只股票的数据
    """
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=60, freq='D')
    stocks = [f'60000{i}.SH' for i in range(10)]

    # 生成基础收盘价（有趋势和噪声）
    base_prices = pd.DataFrame(
        index=dates,
        columns=stocks
    )

    for i, stock in enumerate(stocks):
        # 不同股票有不同的趋势和波动率
        trend = np.linspace(10, 10 + i * 0.5, len(dates))
        noise = np.random.randn(len(dates)) * 0.5
        base_prices[stock] = trend + noise

    return base_prices


@pytest.fixture
def sample_ohlcv_data(realistic_price_data):
    """
    基于收盘价生成OHLCV数据
    """
    close_prices = realistic_price_data

    # 为每只股票生成OHLC
    ohlcv_dict = {}
    for stock in close_prices.columns:
        close = close_prices[stock]

        # 模拟OHLCV
        daily_range = close * 0.02  # 2%的日内波动
        ohlcv = pd.DataFrame({
            'open': close + np.random.randn(len(close)) * daily_range * 0.5,
            'high': close + abs(np.random.randn(len(close))) * daily_range,
            'low': close - abs(np.random.randn(len(close))) * daily_range,
            'close': close,
            'volume': np.random.randint(1000000, 10000000, len(close))
        }, index=close.index)

        ohlcv_dict[stock] = ohlcv

    return ohlcv_dict


class TestThreeLayerIntegration:
    """三层架构回测集成测试"""

    def test_momentum_immediate_fixed_stop(self, realistic_price_data):
        """
        测试组合1: 动量选股 + 立即入场 + 固定止损

        这是最简单的组合，适合快速验证
        """
        engine = BacktestEngine(initial_capital=1000000)

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 10.0,
            'enable_stop_loss': True,
            'enable_take_profit': True
        })

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=realistic_price_data,
            start_date='2023-01-20',  # 留出动量计算期
            end_date='2023-02-28',
            rebalance_freq='W',
            commission_rate=0.0003,
            slippage_rate=0.0005
        )

        # 验证回测成功
        assert result.is_success(), f"回测失败: {result.error}"

        # 验证数据完整性
        assert 'equity_curve' in result.data
        assert 'trades' in result.data
        assert 'metrics' in result.data

        equity_curve = result.data['equity_curve']
        metrics = result.data['metrics']

        # 验证净值曲线
        assert len(equity_curve) > 0
        assert equity_curve.iloc[0] == pytest.approx(1000000, rel=0.01)

        # 验证绩效指标
        assert 'total_return' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics

        print(f"\n组合1测试结果:")
        print(f"  总收益率: {metrics['total_return']:.2%}")
        print(f"  夏普比率: {metrics['sharpe_ratio']:.2f}")
        print(f"  最大回撤: {metrics['max_drawdown']:.2%}")
        print(f"  交易次数: {metrics['n_trades']}")

    def test_value_ma_breakout_atr_stop(self, realistic_price_data):
        """
        测试组合2: 价值选股 + 均线突破入场 + ATR动态止损

        更复杂的组合，测试技术指标计算
        """
        engine = BacktestEngine(initial_capital=1000000)

        selector = ValueSelector(params={
            'volatility_period': 20,
            'return_period': 20,
            'top_n': 5,
            'select_low_volatility': True,
            'select_negative_return': True
        })

        entry = MABreakoutEntry(params={
            'short_window': 5,
            'long_window': 20
        })

        exit_strategy = ATRStopLossExit(params={
            'atr_period': 14,
            'atr_multiplier': 2.0
        })

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=realistic_price_data,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success(), f"回测失败: {result.error}"

        metrics = result.data['metrics']

        print(f"\n组合2测试结果:")
        print(f"  总收益率: {metrics['total_return']:.2%}")
        print(f"  交易次数: {metrics['n_trades']}")

    def test_external_selector_rsi_entry_time_exit(self, realistic_price_data):
        """
        测试组合3: 外部选股 + RSI超卖入场 + 时间止损

        测试外部选股和RSI指标
        """
        engine = BacktestEngine(initial_capital=1000000)

        # 手动指定股票池（需要转换为逗号分隔的字符串）
        manual_stocks_list = realistic_price_data.columns[:6].tolist()
        manual_stocks_str = ','.join(manual_stocks_list)

        selector = ExternalSelector(params={
            'source': 'manual',
            'manual_stocks': manual_stocks_str
        })

        entry = RSIOversoldEntry(params={
            'rsi_period': 14,
            'oversold_threshold': 30
        })

        exit_strategy = TimeBasedExit(params={
            'holding_period': 10,
            'count_trading_days_only': False
        })

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=realistic_price_data,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success(), f"回测失败: {result.error}"

        metrics = result.data['metrics']
        trades = result.data['trades']

        print(f"\n组合3测试结果:")
        print(f"  总收益率: {metrics['total_return']:.2%}")
        print(f"  交易次数: {len(trades)}")

    def test_combined_exit_strategy(self, realistic_price_data):
        """
        测试组合退出策略

        组合多个退出策略（OR逻辑）
        """
        engine = BacktestEngine(initial_capital=1000000)

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})

        # 组合退出策略：固定止损 OR 时间止损
        sub_strategies = [
            FixedStopLossExit(params={
                'stop_loss_pct': -8.0,
                'take_profit_pct': 15.0
            }),
            TimeBasedExit(params={
                'holding_period': 15
            })
        ]
        exit_strategy = CombinedExit(strategies=sub_strategies)

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=realistic_price_data,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success(), f"回测失败: {result.error}"

        metrics = result.data['metrics']

        print(f"\n组合退出策略测试结果:")
        print(f"  总收益率: {metrics['total_return']:.2%}")
        print(f"  最大回撤: {metrics['max_drawdown']:.2%}")

    def test_different_rebalance_frequencies(self, realistic_price_data):
        """
        测试不同调仓频率的影响

        比较日频、周频、月频的回测结果
        """
        engine = BacktestEngine(initial_capital=1000000)

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 10.0
        })

        results = {}

        for freq, label in [('D', '日频'), ('W', '周频'), ('M', '月频')]:
            result = engine.backtest_three_layer(
                selector=selector,
                entry=entry,
                exit_strategy=exit_strategy,
                prices=realistic_price_data,
                start_date='2023-01-20',
                end_date='2023-02-28',
                rebalance_freq=freq
            )

            assert result.is_success(), f"{label}回测失败"
            results[label] = result.data['metrics']

        print(f"\n不同调仓频率对比:")
        for label, metrics in results.items():
            print(f"  {label}:")
            print(f"    总收益率: {metrics['total_return']:.2%}")
            print(f"    交易次数: {metrics['n_trades']}")

    def test_capital_deployment(self, realistic_price_data):
        """
        测试资金部署和持仓管理

        验证买卖逻辑的正确性
        """
        engine = BacktestEngine(initial_capital=1000000)

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})  # 修改为5
        entry = ImmediateEntry(params={'max_stocks': 5})  # 修改为5
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -10.0})

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=realistic_price_data,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success()

        trades = result.data['trades']
        equity_curve = result.data['equity_curve']

        # 验证交易成对（每次买入最终都应该有对应的卖出）
        if len(trades) > 0:
            buy_trades = trades[trades['direction'] == 'buy']
            sell_trades = trades[trades['direction'] == 'sell']

            # 买入数量应该 >= 卖出数量（可能还有持仓）
            assert len(buy_trades) >= len(sell_trades)

            print(f"\n资金部署测试:")
            print(f"  买入交易: {len(buy_trades)} 笔")
            print(f"  卖出交易: {len(sell_trades)} 笔")
            print(f"  初始资金: ¥{1000000:,.0f}")
            print(f"  最终资金: ¥{equity_curve.iloc[-1]:,.0f}")

    def test_stop_loss_trigger(self, realistic_price_data):
        """
        测试止损触发

        创建一个会触发止损的场景
        """
        engine = BacktestEngine(initial_capital=1000000)

        # 修改价格数据，让某些股票下跌
        modified_prices = realistic_price_data.copy()
        # 让前3只股票在后半段持续下跌
        for stock in modified_prices.columns[:3]:
            modified_prices.loc['2023-02-01':, stock] *= 0.9  # 下跌10%

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -5.0,  # 严格止损
            'enable_stop_loss': True
        })

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=modified_prices,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success()

        trades = result.data['trades']

        # 应该有卖出交易（止损触发）
        if len(trades) > 0:
            sell_trades = trades[trades['direction'] == 'sell']
            assert len(sell_trades) > 0, "应该有止损卖出"

            print(f"\n止损触发测试:")
            print(f"  卖出交易: {len(sell_trades)} 笔")

    def test_multiple_strategy_combinations(self, realistic_price_data):
        """
        测试多种策略组合

        验证架构的灵活性
        """
        engine = BacktestEngine(initial_capital=1000000)

        # 定义多种组合
        combinations = [
            {
                'name': '动量+立即+固定止损',
                'selector': MomentumSelector(params={'lookback_period': 20, 'top_n': 5}),
                'entry': ImmediateEntry(params={'max_stocks': 5}),
                'exit': FixedStopLossExit(params={'stop_loss_pct': -5.0})
            },
            {
                'name': '动量+均线突破+ATR止损',
                'selector': MomentumSelector(params={'lookback_period': 20, 'top_n': 5}),
                'entry': MABreakoutEntry(params={'short_window': 5, 'long_window': 20}),
                'exit': ATRStopLossExit(params={'atr_period': 14, 'atr_multiplier': 2.0})
            },
            {
                'name': '价值+RSI+时间止损',
                'selector': ValueSelector(params={
                    'volatility_period': 20,
                    'return_period': 20,
                    'top_n': 5
                }),
                'entry': RSIOversoldEntry(params={'rsi_period': 14, 'oversold_threshold': 30}),
                'exit': TimeBasedExit(params={'holding_period': 10})
            }
        ]

        print(f"\n多策略组合测试:")

        for combo in combinations:
            result = engine.backtest_three_layer(
                selector=combo['selector'],
                entry=combo['entry'],
                exit_strategy=combo['exit'],
                prices=realistic_price_data,
                start_date='2023-01-20',
                end_date='2023-02-28',
                rebalance_freq='W'
            )

            assert result.is_success(), f"{combo['name']} 回测失败"

            metrics = result.data['metrics']
            print(f"  {combo['name']}:")
            print(f"    收益率: {metrics['total_return']:.2%}")
            print(f"    夏普: {metrics['sharpe_ratio']:.2f}")


class TestThreeLayerEdgeCases:
    """测试边界情况和异常处理"""

    def test_no_candidate_stocks(self, realistic_price_data):
        """测试选股器返回空列表的情况"""
        from src.strategies.three_layer.base.stock_selector import StockSelector

        class EmptySelector(StockSelector):
            @property
            def id(self):
                return "empty"

            @property
            def name(self):
                return "Empty Selector"

            @classmethod
            def get_parameters(cls):
                return []

            def select(self, date, prices):
                return []  # 总是返回空列表

        engine = BacktestEngine(initial_capital=1000000)
        entry = ImmediateEntry()
        exit_strategy = FixedStopLossExit()

        result = engine.backtest_three_layer(
            selector=EmptySelector(),
            entry=entry,
            exit_strategy=exit_strategy,
            prices=realistic_price_data,
            start_date='2023-01-01',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success()
        # 应该没有交易
        assert len(result.data['trades']) == 0

    def test_no_entry_signals(self, realistic_price_data):
        """测试入场策略不产生信号的情况"""
        from src.strategies.three_layer.base.entry_strategy import EntryStrategy

        class NoEntryStrategy(EntryStrategy):
            @property
            def id(self):
                return "no_entry"

            @property
            def name(self):
                return "No Entry"

            @classmethod
            def get_parameters(cls):
                return []

            def generate_entry_signals(self, candidate_stocks, data, date):
                return {}  # 总是返回空字典

        engine = BacktestEngine(initial_capital=1000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        exit_strategy = FixedStopLossExit()

        result = engine.backtest_three_layer(
            selector=selector,
            entry=NoEntryStrategy(),
            exit_strategy=exit_strategy,
            prices=realistic_price_data,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success()
        # 应该没有买入交易
        if len(result.data['trades']) > 0:
            buy_trades = result.data['trades'][result.data['trades']['direction'] == 'buy']
            assert len(buy_trades) == 0


class TestThreeLayerRobustness:
    """测试系统健壮性和错误处理"""

    def test_missing_price_data(self, realistic_price_data):
        """测试价格数据缺失的情况"""
        engine = BacktestEngine(initial_capital=1000000)

        # 制造缺失数据
        incomplete_prices = realistic_price_data.copy()
        incomplete_prices.iloc[10:20, :3] = np.nan  # 某些股票缺失10天数据

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=incomplete_prices,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        # 应该能够处理缺失数据，不会崩溃
        assert result.is_success()

    def test_extreme_volatility(self, realistic_price_data):
        """测试极端波动情况"""
        engine = BacktestEngine(initial_capital=1000000)

        # 制造极端波动
        volatile_prices = realistic_price_data.copy()
        for stock in volatile_prices.columns[:3]:
            # 模拟暴涨暴跌
            volatile_prices.loc['2023-02-01':, stock] *= np.random.choice([0.7, 1.3], size=len(volatile_prices.loc['2023-02-01':]))

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -10.0,
            'take_profit_pct': 20.0
        })

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=volatile_prices,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success()
        print(f"\n极端波动测试: 最大回撤={result.data['metrics']['max_drawdown']:.2%}")

    def test_single_stock_available(self, realistic_price_data):
        """测试只有1只股票可用的情况"""
        engine = BacktestEngine(initial_capital=1000000)

        # 只保留1只股票
        single_stock_prices = realistic_price_data.iloc[:, :1]

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=single_stock_prices,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success()

    def test_very_short_backtest_period(self, realistic_price_data):
        """测试非常短的回测周期"""
        engine = BacktestEngine(initial_capital=1000000)

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        # 只回测5天
        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=realistic_price_data,
            start_date='2023-02-15',
            end_date='2023-02-20',
            rebalance_freq='W'
        )

        assert result.is_success()

    def test_all_stocks_suspended(self, realistic_price_data):
        """测试所有股票停牌的情况"""
        engine = BacktestEngine(initial_capital=1000000)

        # 模拟停牌（价格不变 + 成交量为0）
        suspended_prices = realistic_price_data.copy()
        # 让所有股票在某段时间停牌
        suspended_price = suspended_prices.loc['2023-02-09', :].values
        suspended_prices.loc['2023-02-10':'2023-02-15', :] = suspended_price

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=suspended_prices,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success()


class TestThreeLayerPerformance:
    """测试性能相关场景"""

    def test_large_stock_pool(self):
        """测试大规模股票池（100只股票）"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=120, freq='D')
        stocks = [f'60{i:04d}.SH' for i in range(100)]  # 100只股票

        # 生成价格数据
        prices = pd.DataFrame(
            index=dates,
            columns=stocks
        )

        for i, stock in enumerate(stocks):
            trend = np.linspace(10, 12, len(dates))
            noise = np.random.randn(len(dates)) * 0.5
            prices[stock] = trend + noise

        engine = BacktestEngine(initial_capital=1000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 10})
        entry = ImmediateEntry(params={'max_stocks': 10})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        import time
        start_time = time.time()

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=prices,
            start_date='2023-01-20',
            end_date='2023-04-30',
            rebalance_freq='W'
        )

        elapsed_time = time.time() - start_time

        assert result.is_success()
        print(f"\n大规模股票池测试:")
        print(f"  股票数量: {len(stocks)}")
        print(f"  回测天数: {len(dates)}")
        print(f"  耗时: {elapsed_time:.2f}秒")
        print(f"  交易次数: {result.data['metrics']['n_trades']}")

    def test_daily_rebalance_high_frequency(self, realistic_price_data):
        """测试日频调仓（高频交易）"""
        engine = BacktestEngine(initial_capital=1000000)

        selector = MomentumSelector(params={'lookback_period': 5, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = TimeBasedExit(params={'holding_period': 3})  # 只持有3天

        import time
        start_time = time.time()

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=realistic_price_data,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='D'  # 日频调仓
        )

        elapsed_time = time.time() - start_time

        assert result.is_success()
        print(f"\n高频交易测试:")
        print(f"  耗时: {elapsed_time:.2f}秒")
        print(f"  交易次数: {result.data['metrics']['n_trades']}")


class TestThreeLayerDataIntegrity:
    """测试数据完整性和一致性"""

    def test_trade_records_consistency(self, realistic_price_data):
        """测试交易记录的一致性"""
        engine = BacktestEngine(initial_capital=1000000)

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=realistic_price_data,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W',
            commission_rate=0.0003
        )

        assert result.is_success()

        trades = result.data['trades']

        if len(trades) > 0:
            # 验证交易记录必须字段
            required_fields = ['stock_code', 'direction', 'price', 'shares', 'date']
            for field in required_fields:
                assert field in trades.columns, f"缺少字段: {field}"

            # 验证交易价格和数量为正
            assert (trades['price'] > 0).all(), "交易价格必须为正"
            assert (trades['shares'] > 0).all(), "交易数量必须为正"

            # 验证买卖方向
            assert trades['direction'].isin(['buy', 'sell']).all()

            print(f"\n交易记录一致性测试通过:")
            print(f"  总交易数: {len(trades)}")

    def test_equity_curve_continuity(self, realistic_price_data):
        """测试净值曲线的连续性"""
        engine = BacktestEngine(initial_capital=1000000)

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=realistic_price_data,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success()

        equity_curve = result.data['equity_curve']

        # 验证净值曲线连续性
        assert len(equity_curve) > 0
        assert equity_curve.iloc[0] == pytest.approx(1000000, rel=0.01)
        assert not equity_curve.isna().any(), "净值曲线不应有缺失值"
        assert (equity_curve > 0).all(), "净值必须为正"

        print(f"\n净值曲线连续性测试通过:")
        print(f"  数据点数: {len(equity_curve)}")

    def test_metrics_calculation_accuracy(self, realistic_price_data):
        """测试指标计算的准确性"""
        engine = BacktestEngine(initial_capital=1000000)

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=realistic_price_data,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success()

        metrics = result.data['metrics']
        equity_curve = result.data['equity_curve']

        # 验证关键指标存在
        required_metrics = ['total_return', 'sharpe_ratio', 'max_drawdown', 'n_trades']
        for metric in required_metrics:
            assert metric in metrics, f"缺少指标: {metric}"

        # 验证总收益率计算
        expected_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        assert abs(metrics['total_return'] - expected_return) < 0.01, "总收益率计算不准确"

        # 验证最大回撤为负值或0
        assert metrics['max_drawdown'] <= 0, "最大回撤应为负值或0"

        print(f"\n指标计算准确性测试通过:")
        print(f"  总收益率: {metrics['total_return']:.2%}")
        print(f"  最大回撤: {metrics['max_drawdown']:.2%}")


class TestThreeLayerRealWorldScenarios:
    """测试真实世界场景"""

    def test_bull_market_scenario(self, realistic_price_data):
        """测试牛市场景"""
        # 模拟牛市：所有股票上涨
        bull_prices = realistic_price_data.copy()
        for stock in bull_prices.columns:
            bull_prices[stock] = bull_prices[stock] * np.linspace(1.0, 1.3, len(bull_prices))

        engine = BacktestEngine(initial_capital=1000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -5.0,
            'take_profit_pct': 15.0
        })

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=bull_prices,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success()
        metrics = result.data['metrics']

        # 牛市应该盈利
        print(f"\n牛市场景测试:")
        print(f"  总收益率: {metrics['total_return']:.2%}")
        print(f"  夏普比率: {metrics['sharpe_ratio']:.2f}")

    def test_bear_market_scenario(self, realistic_price_data):
        """测试熊市场景"""
        # 模拟熊市：所有股票下跌
        bear_prices = realistic_price_data.copy()
        for stock in bear_prices.columns:
            bear_prices[stock] = bear_prices[stock] * np.linspace(1.0, 0.8, len(bear_prices))

        engine = BacktestEngine(initial_capital=1000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -3.0,  # 严格止损
            'enable_stop_loss': True
        })

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=bear_prices,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success()
        metrics = result.data['metrics']

        print(f"\n熊市场景测试:")
        print(f"  总收益率: {metrics['total_return']:.2%}")
        print(f"  最大回撤: {metrics['max_drawdown']:.2%}")
        print(f"  止损触发次数: {len(result.data['trades'][result.data['trades']['direction']=='sell'])}")

    def test_sideways_market_scenario(self, realistic_price_data):
        """测试震荡市场景"""
        # 模拟震荡市：价格来回波动
        sideways_prices = realistic_price_data.copy()
        for stock in sideways_prices.columns:
            # 添加周期性波动
            wave = np.sin(np.linspace(0, 4*np.pi, len(sideways_prices))) * 0.5
            sideways_prices[stock] = sideways_prices[stock].iloc[0] + wave

        engine = BacktestEngine(initial_capital=1000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = TimeBasedExit(params={'holding_period': 7})

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=sideways_prices,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success()
        metrics = result.data['metrics']

        print(f"\n震荡市场景测试:")
        print(f"  总收益率: {metrics['total_return']:.2%}")
        print(f"  交易次数: {metrics['n_trades']}")

    def test_sector_rotation_scenario(self, realistic_price_data):
        """测试板块轮动场景"""
        # 模拟板块轮动：不同时间不同股票表现好
        rotation_prices = realistic_price_data.copy()

        # 前半段：前5只股票涨
        rotation_prices.loc[:'2023-02-01', rotation_prices.columns[:5]] *= 1.1

        # 后半段：后5只股票涨
        rotation_prices.loc['2023-02-01':, rotation_prices.columns[5:]] *= 1.1

        engine = BacktestEngine(initial_capital=1000000)
        selector = MomentumSelector(params={'lookback_period': 10, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=rotation_prices,
            start_date='2023-01-20',
            end_date='2023-02-28',
            rebalance_freq='W'
        )

        assert result.is_success()
        metrics = result.data['metrics']

        print(f"\n板块轮动场景测试:")
        print(f"  总收益率: {metrics['total_return']:.2%}")
        print(f"  换手率: {metrics.get('turnover_rate', 'N/A')}")


class TestThreeLayerCommissionAndSlippage:
    """测试交易成本影响"""

    def test_different_commission_rates(self, realistic_price_data):
        """测试不同佣金费率的影响"""
        engine = BacktestEngine(initial_capital=1000000)

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        commission_rates = [0.0, 0.0001, 0.0003, 0.001]
        results = {}

        for rate in commission_rates:
            result = engine.backtest_three_layer(
                selector=selector,
                entry=entry,
                exit_strategy=exit_strategy,
                prices=realistic_price_data,
                start_date='2023-01-20',
                end_date='2023-02-28',
                rebalance_freq='W',
                commission_rate=rate
            )

            assert result.is_success()
            results[rate] = result.data['metrics']['total_return']

        print(f"\n佣金费率影响测试:")
        for rate, ret in results.items():
            print(f"  费率 {rate:.4f}: 收益率 {ret:.2%}")

        # 验证费率越高，收益越低
        assert results[0.0] >= results[0.001]

    def test_different_slippage_rates(self, realistic_price_data):
        """测试不同滑点的影响"""
        engine = BacktestEngine(initial_capital=1000000)

        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        slippage_rates = [0.0, 0.0005, 0.001, 0.002]
        results = {}

        for rate in slippage_rates:
            result = engine.backtest_three_layer(
                selector=selector,
                entry=entry,
                exit_strategy=exit_strategy,
                prices=realistic_price_data,
                start_date='2023-01-20',
                end_date='2023-02-28',
                rebalance_freq='W',
                slippage_rate=rate
            )

            assert result.is_success()
            results[rate] = result.data['metrics']['total_return']

        print(f"\n滑点影响测试:")
        for rate, ret in results.items():
            print(f"  滑点 {rate:.4f}: 收益率 {ret:.2%}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '-s'])
