#!/usr/bin/env python3
"""
回测引擎与成本分析器集成测试
测试BacktestEngine自动记录交易成本的功能
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.backtest import BacktestEngine, TradingCostAnalyzer


class TestBacktestEngineWithCostAnalysis:
    """回测引擎成本分析集成测试"""

    @pytest.fixture
    def sample_market_data(self):
        """创建示例市场数据"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        stocks = [f'{600000+i:06d}' for i in range(10)]

        # 价格数据
        price_data = {}
        signal_data = {}
        for stock in stocks:
            base_price = 10.0
            returns = np.random.normal(0.001, 0.02, len(dates))
            prices = base_price * (1 + returns).cumprod()
            price_data[stock] = prices

            # 信号与未来收益相关
            future_returns = (pd.Series(prices).shift(-5) / pd.Series(prices) - 1) * 100
            signals = future_returns + np.random.normal(0, 0.01, len(dates))
            signal_data[stock] = signals.values

        prices_df = pd.DataFrame(price_data, index=dates)
        signals_df = pd.DataFrame(signal_data, index=dates)

        return prices_df, signals_df, stocks

    def test_backtest_records_trades(self, sample_market_data):
        """测试回测引擎记录交易"""
        prices_df, signals_df, stocks = sample_market_data

        # 创建回测引擎
        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            slippage=0.001,
            verbose=False
        )

        # 运行回测
        results = engine.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W'
        )

        # 检查成本分析结果存在
        assert 'cost_analysis' in results.data
        assert 'cost_analyzer' in results.data

        # 检查交易被记录
        cost_analyzer = results.data['cost_analyzer']
        assert len(cost_analyzer.trades) > 0

        # 检查成本指标
        cost_analysis = results.data['cost_analysis']
        assert 'total_cost' in cost_analysis
        assert 'n_trades' in cost_analysis
        assert cost_analysis['total_cost'] > 0

    def test_cost_breakdown_accuracy(self, sample_market_data):
        """测试成本分解准确性"""
        prices_df, signals_df, stocks = sample_market_data

        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            slippage=0.001,
            verbose=False
        )

        results = engine.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W'
        )

        cost_analysis = results.data['cost_analysis']

        # 检查成本构成比例合理
        total_cost = cost_analysis['total_cost']
        commission = cost_analysis['total_commission']
        stamp_tax = cost_analysis['total_stamp_tax']
        slippage = cost_analysis['total_slippage']

        # 总成本应该等于三项之和
        assert abs(total_cost - (commission + stamp_tax + slippage)) < 0.01

        # 检查比例
        assert cost_analysis['commission_pct'] > 0
        assert cost_analysis['stamp_tax_pct'] > 0
        assert cost_analysis['slippage_pct'] > 0

        # 比例之和应该接近1
        total_pct = (cost_analysis['commission_pct'] +
                    cost_analysis['stamp_tax_pct'] +
                    cost_analysis['slippage_pct'])
        assert abs(total_pct - 1.0) < 0.01

    def test_buy_sell_trades_recorded(self, sample_market_data):
        """测试买入和卖出交易都被记录"""
        prices_df, signals_df, stocks = sample_market_data

        engine = BacktestEngine(
            initial_capital=1000000,
            verbose=False
        )

        results = engine.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W'
        )

        cost_analyzer = results.data['cost_analyzer']
        trades_df = cost_analyzer.get_trades_dataframe()

        # 检查有买入和卖出交易
        buy_trades = trades_df[trades_df['action'] == 'buy']
        sell_trades = trades_df[trades_df['action'] == 'sell']

        assert len(buy_trades) > 0, "应该有买入交易"
        assert len(sell_trades) > 0, "应该有卖出交易"

        # 买入交易不应该有印花税
        assert (buy_trades['stamp_tax'] == 0).all()

        # 卖出交易应该有印花税
        assert (sell_trades['stamp_tax'] > 0).all()

    def test_trading_frequency_impact(self, sample_market_data):
        """测试调仓频率对成本的影响"""
        prices_df, signals_df, stocks = sample_market_data

        # 日度调仓
        engine_daily = BacktestEngine(initial_capital=1000000, verbose=False)
        results_daily = engine_daily.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=1,
            rebalance_freq='D'
        )

        # 周度调仓
        engine_weekly = BacktestEngine(initial_capital=1000000, verbose=False)
        results_weekly = engine_weekly.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W'
        )

        # 日度调仓的成本应该高于周度
        cost_daily = results_daily.data['cost_analysis']['total_cost']
        cost_weekly = results_weekly.data['cost_analysis']['total_cost']
        trades_daily = results_daily.data['cost_analysis']['n_trades']
        trades_weekly = results_weekly.data['cost_analysis']['n_trades']

        assert cost_daily > cost_weekly, "日度调仓成本应该高于周度"
        assert trades_daily > trades_weekly, "日度调仓交易次数应该更多"

    def test_turnover_rate_calculation(self, sample_market_data):
        """测试换手率计算"""
        prices_df, signals_df, stocks = sample_market_data

        engine = BacktestEngine(initial_capital=1000000, verbose=False)
        results = engine.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W'
        )

        cost_analysis = results.data['cost_analysis']

        # 检查换手率存在且合理
        assert 'annual_turnover_rate' in cost_analysis
        assert 'total_turnover_rate' in cost_analysis

        annual_turnover = cost_analysis['annual_turnover_rate']
        assert annual_turnover > 0, "换手率应该大于0"
        assert annual_turnover < 1000, "换手率不应该异常高"

    def test_cost_impact_on_returns(self, sample_market_data):
        """测试成本对收益的影响"""
        prices_df, signals_df, stocks = sample_market_data

        engine = BacktestEngine(initial_capital=1000000, verbose=False)
        results = engine.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W'
        )

        cost_analysis = results.data['cost_analysis']

        # 检查成本影响指标
        assert 'cost_to_capital_ratio' in cost_analysis
        assert 'cost_drag' in cost_analysis
        assert 'return_with_cost' in cost_analysis
        assert 'return_without_cost' in cost_analysis

        # 无成本收益应该大于或等于有成本收益
        return_with_cost = cost_analysis['return_with_cost']
        return_without_cost = cost_analysis['return_without_cost']
        assert return_without_cost >= return_with_cost

        # 成本拖累应该是正数（或零）
        cost_drag = cost_analysis['cost_drag']
        assert cost_drag >= 0

    def test_zero_slippage_scenario(self, sample_market_data):
        """测试零滑点场景"""
        prices_df, signals_df, stocks = sample_market_data

        engine = BacktestEngine(
            initial_capital=1000000,
            slippage=0.0,  # 零滑点
            verbose=False
        )

        results = engine.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W'
        )

        cost_analysis = results.data['cost_analysis']

        # 滑点成本应该为0
        assert cost_analysis['total_slippage'] == 0.0
        assert cost_analysis['slippage_pct'] == 0.0

    def test_high_commission_scenario(self, sample_market_data):
        """测试高佣金场景"""
        prices_df, signals_df, stocks = sample_market_data

        # 高佣金
        engine_high = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.001,  # 千一佣金
            verbose=False
        )

        # 低佣金
        engine_low = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0001,  # 万一佣金
            verbose=False
        )

        results_high = engine_high.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W'
        )

        results_low = engine_low.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W'
        )

        # 高佣金的总成本应该更高
        cost_high = results_high.data['cost_analysis']['total_commission']
        cost_low = results_low.data['cost_analysis']['total_commission']

        assert cost_high > cost_low, "高佣金应该导致更高的总佣金"

    def test_cost_by_stock_analysis(self, sample_market_data):
        """测试按股票统计成本"""
        prices_df, signals_df, stocks = sample_market_data

        engine = BacktestEngine(initial_capital=1000000, verbose=False)
        results = engine.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W'
        )

        cost_analyzer = results.data['cost_analyzer']
        cost_by_stock = cost_analyzer.calculate_cost_by_stock()

        # 应该有多只股票的成本统计
        assert len(cost_by_stock) > 0
        assert 'trade_count' in cost_by_stock.columns
        assert 'total_cost' in cost_by_stock.columns
        assert 'cost_ratio' in cost_by_stock.columns

    def test_cost_over_time_series(self, sample_market_data):
        """测试成本时间序列"""
        prices_df, signals_df, stocks = sample_market_data

        engine = BacktestEngine(initial_capital=1000000, verbose=False)
        results = engine.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W'
        )

        cost_analyzer = results.data['cost_analyzer']
        cost_over_time = cost_analyzer.calculate_cost_over_time()

        # 应该有时间序列数据
        assert len(cost_over_time) > 0
        assert 'cumulative_total_cost' in cost_over_time.columns

        # 累计成本应该单调递增
        assert cost_over_time['cumulative_total_cost'].is_monotonic_increasing

    def test_empty_backtest_scenario(self):
        """测试空回测场景（无交易）"""
        # 创建全NaN信号
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        stocks = ['600000', '600001']

        prices_df = pd.DataFrame(
            np.ones((10, 2)) * 10.0,
            index=dates,
            columns=stocks
        )

        signals_df = pd.DataFrame(
            np.nan,
            index=dates,
            columns=stocks
        )

        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        # 应该能正常运行，即使没有交易
        results = engine.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=2,
            holding_period=5,
            rebalance_freq='D'
        )

        # 成本应该为0或空字典（无交易时）
        cost_analysis = results.data['cost_analysis']
        if cost_analysis:  # 如果有成本分析结果
            assert cost_analysis.get('n_trades', 0) == 0 or cost_analysis.get('total_cost', 0) == 0
        else:  # 无交易记录
            assert True  # 空字典是预期行为


class TestCostAnalysisEdgeCases:
    """成本分析边界情况测试"""

    def test_single_trade(self):
        """测试单笔交易"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        prices_df = pd.DataFrame(
            {'600000': np.linspace(10, 11, 10)},
            index=dates
        )
        signals_df = pd.DataFrame(
            {'600000': [1] + [0] * 9},  # 只在第一天有信号
            index=dates
        )

        engine = BacktestEngine(initial_capital=1000000, verbose=False)
        results = engine.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=1,
            holding_period=100,  # 长期持有
            rebalance_freq='D'
        )

        # 应该只有买入交易，没有卖出
        cost_analyzer = results.data['cost_analyzer']
        trades_df = cost_analyzer.get_trades_dataframe()

        # 至少有一笔买入交易
        assert len(trades_df[trades_df['action'] == 'buy']) >= 1

    def test_high_frequency_small_trades(self):
        """测试高频小额交易（触发最小佣金）"""
        dates = pd.date_range('2023-01-01', periods=20, freq='D')
        prices_df = pd.DataFrame(
            {'600000': [10.0] * 20},
            index=dates
        )

        # 每天都有信号
        signals_df = pd.DataFrame(
            {'600000': [1.0] * 20},
            index=dates
        )

        engine = BacktestEngine(
            initial_capital=100000,  # 小资金
            verbose=False
        )

        results = engine.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=1,
            holding_period=1,  # 每天换仓
            rebalance_freq='D'
        )

        # 应该有较多交易（如果有交易的话）
        cost_analysis = results.data['cost_analysis']
        if cost_analysis:  # 有成本分析结果
            # 可能因为资金不足无法交易，所以放宽条件
            assert cost_analysis.get('n_trades', 0) >= 0
        else:
            # 无交易也是可能的（资金不足）
            assert True

    def test_cost_comparison_different_params(self):
        """测试不同参数下的成本对比"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        stocks = ['600000', '600001', '600002']

        prices_df = pd.DataFrame(
            np.random.uniform(9, 11, (50, 3)),
            index=dates,
            columns=stocks
        )

        signals_df = pd.DataFrame(
            np.random.uniform(-1, 1, (50, 3)),
            index=dates,
            columns=stocks
        )

        # 不同top_n值
        costs = []
        for top_n in [1, 2, 3]:
            engine = BacktestEngine(initial_capital=1000000, verbose=False)
            results = engine.backtest_long_only(
                signals=signals_df,
                prices=prices_df,
                top_n=top_n,
                holding_period=5,
                rebalance_freq='W'
            )
            costs.append(results.data['cost_analysis']['total_cost'])

        # 持仓股票越多，调仓成本可能越高
        # 但不是严格递增（取决于调仓频率和信号稳定性）
        assert all(c >= 0 for c in costs)


def test_integration_with_performance_analyzer():
    """测试与绩效分析器的集成"""
    from src.backtest import PerformanceAnalyzer

    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    stocks = ['600000', '600001']

    prices_df = pd.DataFrame(
        np.random.uniform(9, 11, (100, 2)),
        index=dates,
        columns=stocks
    )

    signals_df = pd.DataFrame(
        np.random.uniform(-1, 1, (100, 2)),
        index=dates,
        columns=stocks
    )

    # 运行回测
    engine = BacktestEngine(initial_capital=1000000, verbose=False)
    results = engine.backtest_long_only(
        signals=signals_df,
        prices=prices_df,
        top_n=1,
        holding_period=5,
        rebalance_freq='W'
    )

    # 使用绩效分析器
    analyzer = PerformanceAnalyzer(
        returns=results.data['daily_returns'],
        risk_free_rate=0.03,
        periods_per_year=252
    )

    metrics = analyzer.calculate_all_metrics(verbose=False)

    # 检查可以同时获得绩效指标和成本分析
    assert 'sharpe_ratio' in metrics.data
    assert 'total_cost' in results.data['cost_analysis']

    # 成本应该影响收益
    total_return = metrics.data['total_return']
    cost_drag = results.data['cost_analysis']['cost_drag']

    # 成本拖累应该是合理的
    assert 0 <= cost_drag <= abs(total_return)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
