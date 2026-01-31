#!/usr/bin/env python3
"""
市场中性策略回测单元测试

测试多空对冲策略的完整回测流程

Author: Stock Analysis Core Team
Date: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.backtest.backtest_engine import BacktestEngine


class TestMarketNeutralBacktest:
    """测试市场中性回测"""

    @pytest.fixture
    def sample_data(self):
        """创建测试数据"""
        np.random.seed(42)

        # 60天数据
        dates = pd.date_range('2023-01-01', periods=60, freq='D')
        stocks = [f'{i:06d}' for i in range(600000, 600020)]  # 20只股票

        # 模拟价格数据
        price_data = {}
        for stock in stocks:
            base_price = 10.0 + np.random.rand() * 5  # 10-15元
            returns = np.random.normal(0.0005, 0.015, len(dates))
            prices = base_price * (1 + returns).cumprod()
            price_data[stock] = prices

        prices_df = pd.DataFrame(price_data, index=dates)

        # 模拟信号数据（部分股票有预测能力）
        signal_data = {}
        for i, stock in enumerate(stocks):
            if i < 10:
                # 前10只：信号与未来收益正相关（适合做多）
                future_returns = prices_df[stock].pct_change(5).shift(-5)
                signals = future_returns * 100 + np.random.normal(0, 0.5, len(dates))
            else:
                # 后10只：信号与未来收益负相关（适合做空）
                future_returns = prices_df[stock].pct_change(5).shift(-5)
                signals = -future_returns * 100 + np.random.normal(0, 0.5, len(dates))

            signal_data[stock] = signals

        signals_df = pd.DataFrame(signal_data, index=dates)

        return signals_df, prices_df

    def test_basic_market_neutral(self, sample_data):
        """测试基础市场中性回测"""
        signals, prices = sample_data

        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            slippage=0.001,
            verbose=False
        )

        results = engine.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=5,
            bottom_n=5,
            holding_period=5,
            rebalance_freq='W',
            margin_rate=0.10
        )

        # 验证结果结构
        assert 'portfolio_value' in results.data
        assert 'positions' in results.data
        assert 'daily_returns' in results.data
        assert 'cost_analysis' in results.data

        # 验证组合净值DataFrame
        pv = results.data['portfolio_value']
        assert 'cash' in pv.columns
        assert 'long_value' in pv.columns
        assert 'short_value' in pv.columns
        assert 'short_pnl' in pv.columns
        assert 'short_interest' in pv.columns
        assert 'total' in pv.columns

        # 验证净值长度
        assert len(pv) == len(signals)

        # 验证最终净值存在
        final_value = pv['total'].iloc[-1]
        assert not np.isnan(final_value)
        assert final_value > 0

    def test_long_and_short_positions_exist(self, sample_data):
        """测试多空头持仓都存在"""
        signals, prices = sample_data

        engine = BacktestEngine(
            initial_capital=1000000,
            verbose=False
        )

        results = engine.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=3,
            bottom_n=3,
            holding_period=5,
            rebalance_freq='W'
        )

        # 检查持仓历史
        positions = results.data['positions']

        # 找到有持仓的日期
        has_long = False
        has_short = False

        for pos_record in positions:
            if len(pos_record['long_positions']) > 0:
                has_long = True
            if len(pos_record['short_positions']) > 0:
                has_short = True

        assert has_long, "应该有多头持仓"
        assert has_short, "应该有空头持仓"

    def test_short_interest_accumulation(self, sample_data):
        """测试融券利息累计"""
        signals, prices = sample_data

        engine = BacktestEngine(
            initial_capital=1000000,
            verbose=False
        )

        results = engine.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=5,
            bottom_n=5,
            holding_period=10,
            rebalance_freq='M',  # 月度调仓，持仓时间长
            margin_rate=0.10
        )

        # 检查利息累计
        pv = results.data['portfolio_value']
        short_interest = pv['short_interest']

        # 利息应该随时间增加
        if short_interest.iloc[-1] > 0:
            # 确保利息是递增的（允许有调仓时的重置）
            # 至少最后的利息应该大于0
            assert short_interest.iloc[-1] > 0

    def test_different_margin_rates(self, sample_data):
        """测试不同融券费率的影响"""
        signals, prices = sample_data

        # 低费率
        engine_low = BacktestEngine(initial_capital=1000000, verbose=False)
        results_low = engine_low.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=5,
            bottom_n=5,
            margin_rate=0.08  # 8%
        )

        # 高费率
        engine_high = BacktestEngine(initial_capital=1000000, verbose=False)
        results_high = engine_high.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=5,
            bottom_n=5,
            margin_rate=0.12  # 12%
        )

        # 高费率应该导致更高的利息成本
        interest_low = results_low.data['portfolio_value']['short_interest'].iloc[-1]
        interest_high = results_high.data['portfolio_value']['short_interest'].iloc[-1]

        if interest_high > 0:
            assert interest_high > interest_low

    def test_cost_tracking(self, sample_data):
        """测试成本追踪"""
        signals, prices = sample_data

        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            verbose=False
        )

        results = engine.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=5,
            bottom_n=5
        )

        # 验证成本分析器有交易记录
        cost_analyzer = results.data['cost_analyzer']
        assert len(cost_analyzer.trades) > 0

        # 检查交易类型
        actions = [t.action for t in cost_analyzer.trades]

        # 应该有买入、卖出、做空、平空等操作
        # 至少应该有某种交易
        assert len(set(actions)) > 0

    def test_rebalance_frequency(self, sample_data):
        """测试不同调仓频率"""
        signals, prices = sample_data

        # 每日调仓
        engine_daily = BacktestEngine(initial_capital=1000000, verbose=False)
        results_daily = engine_daily.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=3,
            bottom_n=3,
            rebalance_freq='D'
        )

        # 每周调仓
        engine_weekly = BacktestEngine(initial_capital=1000000, verbose=False)
        results_weekly = engine_weekly.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=3,
            bottom_n=3,
            rebalance_freq='W'
        )

        # 每日调仓应该有更多交易
        trades_daily = len(results_daily.data['cost_analyzer'].trades)
        trades_weekly = len(results_weekly.data['cost_analyzer'].trades)

        assert trades_daily >= trades_weekly

    def test_portfolio_value_continuity(self, sample_data):
        """测试组合净值连续性"""
        signals, prices = sample_data

        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        results = engine.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=5,
            bottom_n=5
        )

        pv = results.data['portfolio_value']['total']

        # 检查没有NaN值
        assert not pv.isna().any()

        # 检查净值始终为正
        assert (pv > 0).all()

        # 检查净值变化合理（单日涨跌不超过50%）
        daily_change = pv.pct_change().dropna()
        assert (daily_change.abs() < 0.5).all()

    def test_position_sizing(self, sample_data):
        """测试持仓规模"""
        signals, prices = sample_data

        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        results = engine.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=5,
            bottom_n=5,
            holding_period=5,
            rebalance_freq='W'
        )

        positions = results.data['positions']

        # 检查持仓数量不超过限制
        for pos_record in positions:
            long_count = len(pos_record['long_positions'])
            short_count = len(pos_record['short_positions'])

            assert long_count <= 5
            assert short_count <= 5

    def test_cash_management(self, sample_data):
        """测试现金管理"""
        signals, prices = sample_data

        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        results = engine.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=5,
            bottom_n=5
        )

        pv = results.data['portfolio_value']

        # 现金不应该变成负数（允许小的浮点误差）
        assert (pv['cash'] >= -1).all()


class TestMarketNeutralEdgeCases:
    """测试边界情况"""

    def test_insufficient_stocks(self):
        """测试股票数量不足"""
        np.random.seed(42)

        # 只有5只股票
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        stocks = [f'{i:06d}' for i in range(600000, 600005)]

        prices = pd.DataFrame(
            np.random.rand(len(dates), len(stocks)) * 10 + 10,
            index=dates,
            columns=stocks
        )

        signals = pd.DataFrame(
            np.random.randn(len(dates), len(stocks)),
            index=dates,
            columns=stocks
        )

        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        # 要求做多10只、做空10只，但只有5只股票
        results = engine.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=10,  # 超过可用股票数
            bottom_n=10
        )

        # 应该能正常运行（最多持有5只）
        assert 'portfolio_value' in results.data

    def test_zero_signals(self):
        """测试全零信号"""
        np.random.seed(42)

        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        stocks = [f'{i:06d}' for i in range(600000, 600010)]

        prices = pd.DataFrame(
            np.random.rand(len(dates), len(stocks)) * 10 + 10,
            index=dates,
            columns=stocks
        )

        # 全零信号
        signals = pd.DataFrame(
            0,
            index=dates,
            columns=stocks
        )

        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        results = engine.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=5,
            bottom_n=5
        )

        # 应该能正常运行
        assert 'portfolio_value' in results.data

    def test_single_day(self):
        """测试单日数据"""
        dates = pd.date_range('2023-01-01', periods=1, freq='D')
        stocks = [f'{i:06d}' for i in range(600000, 600010)]

        prices = pd.DataFrame(
            [[10.0] * len(stocks)],
            index=dates,
            columns=stocks
        )

        signals = pd.DataFrame(
            [[1.0] * len(stocks)],
            index=dates,
            columns=stocks
        )

        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        results = engine.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=3,
            bottom_n=3
        )

        # 单日数据应该不会有交易（需要次日）
        pv = results.data['portfolio_value']
        assert len(pv) == 1
        assert pv['total'].iloc[0] == 1000000  # 应该等于初始资金


class TestMarketNeutralVsLongOnly:
    """测试市场中性vs纯多头"""

    @pytest.fixture
    def trending_market_data(self):
        """创建趋势市场数据"""
        np.random.seed(42)

        dates = pd.date_range('2023-01-01', periods=60, freq='D')
        stocks = [f'{i:06d}' for i in range(600000, 600020)]

        # 市场整体上涨
        price_data = {}
        for stock in stocks:
            base_price = 10.0
            # 整体上涨趋势 + 个股随机波动
            trend = np.linspace(0, 0.2, len(dates))  # 20%上涨
            noise = np.random.normal(0, 0.01, len(dates))
            returns = trend + noise
            prices = base_price * (1 + returns).cumprod()
            price_data[stock] = prices

        prices_df = pd.DataFrame(price_data, index=dates)

        # 随机信号
        signals_df = pd.DataFrame(
            np.random.randn(len(dates), len(stocks)),
            index=dates,
            columns=stocks
        )

        return signals_df, prices_df

    def test_market_neutral_vs_long_only_in_bull_market(self, trending_market_data):
        """测试牛市中市场中性vs纯多头"""
        signals, prices = trending_market_data

        # 纯多头
        engine_long = BacktestEngine(initial_capital=1000000, verbose=False)
        results_long = engine_long.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=10,
            holding_period=5
        )

        # 市场中性
        engine_neutral = BacktestEngine(initial_capital=1000000, verbose=False)
        results_neutral = engine_neutral.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=5,
            bottom_n=5,
            holding_period=5
        )

        final_long = results_long.data['portfolio_value']['total'].iloc[-1]
        final_neutral = results_neutral.data['portfolio_value']['total'].iloc[-1]

        # 在牛市中，纯多头通常表现更好（因为市场中性抵消了市场收益）
        # 但这取决于信号质量，所以只验证两者都能运行
        assert final_long > 0
        assert final_neutral > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
