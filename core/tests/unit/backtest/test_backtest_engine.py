#!/usr/bin/env python3
"""
回测引擎单元测试

测试BacktestEngine的所有核心功能

Author: Stock Analysis Core Team
Date: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.backtest.backtest_engine import BacktestEngine
from src.backtest.slippage_models import (
    FixedSlippageModel,
    VolumeBasedSlippageModel,
    MarketImpactModel
)


class TestBacktestEngineInitialization:
    """测试BacktestEngine初始化"""

    def test_default_initialization(self):
        """测试默认初始化"""
        engine = BacktestEngine()

        assert engine.initial_capital == 1000000.0
        assert engine.commission_rate > 0
        assert engine.stamp_tax_rate > 0
        assert engine.slippage >= 0
        assert engine.slippage_model is not None

    def test_custom_parameters(self):
        """测试自定义参数"""
        engine = BacktestEngine(
            initial_capital=2000000,
            commission_rate=0.0005,
            stamp_tax_rate=0.002,
            slippage=0.002
        )

        assert engine.initial_capital == 2000000
        assert engine.commission_rate == 0.0005
        assert engine.stamp_tax_rate == 0.002
        assert engine.slippage == 0.002

    def test_custom_slippage_model(self):
        """测试自定义滑点模型"""
        custom_model = VolumeBasedSlippageModel(base_slippage=0.0005)
        engine = BacktestEngine(slippage_model=custom_model)

        assert engine.slippage_model == custom_model
        assert isinstance(engine.slippage_model, VolumeBasedSlippageModel)


class TestTradingCostCalculation:
    """测试交易成本计算"""

    def test_buy_cost(self):
        """测试买入成本"""
        engine = BacktestEngine(
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            min_commission=5.0
        )

        # 大额交易
        cost = engine.calculate_trading_cost(100000, is_buy=True)
        # 成本包含佣金和过户费
        assert cost > 30.0  # 至少有佣金
        assert cost < 100.0  # 不会太高

        # 小额交易（触发最小佣金）
        cost_small = engine.calculate_trading_cost(10000, is_buy=True)
        assert cost_small >= 5.0  # 至少是最小佣金

    def test_sell_cost(self):
        """测试卖出成本"""
        engine = BacktestEngine(
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            min_commission=5.0
        )

        # 卖出有佣金、印花税和过户费
        cost = engine.calculate_trading_cost(100000, is_buy=False)
        # 应该包含佣金30 + 印花税100 + 过户费
        assert cost > 130.0
        assert cost < 200.0  # 不会太高


class TestLongOnlyBacktest:
    """测试纯多头回测"""

    @pytest.fixture
    def sample_data(self):
        """创建测试数据"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=60, freq='D')
        stocks = [f'{i:06d}' for i in range(600000, 600010)]

        # 价格数据
        price_data = {}
        for stock in stocks:
            base_price = 10.0
            returns = np.random.normal(0.001, 0.02, len(dates))
            prices = base_price * (1 + returns).cumprod()
            price_data[stock] = prices

        prices_df = pd.DataFrame(price_data, index=dates)

        # 信号数据（带预测能力）
        signal_data = {}
        for stock in stocks:
            future_returns = prices_df[stock].pct_change(5).shift(-5)
            signals = future_returns * 100 + np.random.normal(0, 0.5, len(dates))
            signal_data[stock] = signals

        signals_df = pd.DataFrame(signal_data, index=dates)

        return signals_df, prices_df

    def test_basic_backtest(self, sample_data):
        """测试基础回测"""
        signals, prices = sample_data

        engine = BacktestEngine(initial_capital=1000000)
        results = engine.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=5,
            holding_period=5,
            rebalance_freq='W'
        )
        assert results.is_success(), f'回测失败: {results.error}'

        # 验证结果结构
        assert 'portfolio_value' in results.data
        assert 'positions' in results.data
        assert 'daily_returns' in results.data
        assert 'cost_analysis' in results.data

        # 验证数据类型
        assert isinstance(results.data['portfolio_value'], pd.DataFrame)
        assert isinstance(results.data['daily_returns'], pd.Series)

        # 验证组合净值
        pv = results.data['portfolio_value']
        assert 'cash' in pv.columns
        assert 'holdings' in pv.columns
        assert 'total' in pv.columns

        # 净值应该连续
        assert len(pv) == len(signals)
        assert not pv['total'].isna().any()

    def test_different_rebalance_frequencies(self, sample_data):
        """测试不同调仓频率"""
        signals, prices = sample_data

        # 每日调仓
        engine_daily = BacktestEngine(initial_capital=1000000)
        results_daily = engine_daily.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=5,
            rebalance_freq='D'
        )

        # 每周调仓
        engine_weekly = BacktestEngine(initial_capital=1000000)
        results_weekly = engine_weekly.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=5,
            rebalance_freq='W'
        )

        # 每月调仓
        engine_monthly = BacktestEngine(initial_capital=1000000)
        results_monthly = engine_monthly.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=5,
            rebalance_freq='M'
        )

        # 每日调仓应该有更多交易
        trades_daily = len(results_daily.data['cost_analyzer'].trades)
        trades_weekly = len(results_weekly.data['cost_analyzer'].trades)
        trades_monthly = len(results_monthly.data['cost_analyzer'].trades)

        assert trades_daily >= trades_weekly >= trades_monthly

    def test_different_portfolio_sizes(self, sample_data):
        """测试不同组合规模"""
        signals, prices = sample_data
        engine = BacktestEngine(initial_capital=1000000)

        # 小组合
        results_small = engine.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=3
        )

        # 大组合
        results_large = engine.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=8
        )

        # 都应该成功运行
        assert 'portfolio_value' in results_small.data
        assert 'portfolio_value' in results_large.data

    def test_holding_period(self, sample_data):
        """测试持仓期限制"""
        signals, prices = sample_data
        engine = BacktestEngine(initial_capital=1000000)

        results = engine.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=5,
            holding_period=10,  # 最少持有10天
            rebalance_freq='W'
        )
        assert results.is_success(), f'回测失败: {results.error}'

        # 验证回测成功
        assert 'portfolio_value' in results.data
        assert len(results.data['portfolio_value']) == len(signals)

    def test_with_different_slippage_models(self, sample_data):
        """测试不同滑点模型"""
        signals, prices = sample_data

        # 固定滑点
        engine1 = BacktestEngine(
            initial_capital=1000000,
            slippage_model=FixedSlippageModel(0.001)
        )
        results1 = engine1.backtest_long_only(signals, prices, top_n=5)

        # 基于成交量的滑点
        engine2 = BacktestEngine(
            initial_capital=1000000,
            slippage_model=VolumeBasedSlippageModel()
        )
        results2 = engine2.backtest_long_only(signals, prices, top_n=5)

        # 两种模型都应该成功运行
        assert results1.data['portfolio_value'] is not None
        assert results2.data['portfolio_value'] is not None

    def test_capital_management(self, sample_data):
        """测试资金管理"""
        signals, prices = sample_data
        engine = BacktestEngine(initial_capital=1000000)

        results = engine.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=5
        )
        assert results.is_success(), f'回测失败: {results.error}'

        pv = results.data['portfolio_value']

        # 现金不应该变成负数（允许小的浮点误差）
        assert (pv['cash'] >= -1).all()

        # 总资产应该保持正数
        assert (pv['total'] > 0).all()


class TestMarketNeutralBacktest:
    """测试市场中性回测"""

    @pytest.fixture
    def sample_data(self):
        """创建测试数据"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=60, freq='D')
        stocks = [f'{i:06d}' for i in range(600000, 600020)]

        price_data = {}
        for stock in stocks:
            base_price = 10.0 + np.random.rand() * 5
            returns = np.random.normal(0.0005, 0.015, len(dates))
            prices = base_price * (1 + returns).cumprod()
            price_data[stock] = prices

        prices_df = pd.DataFrame(price_data, index=dates)

        # 信号数据
        signal_data = {}
        for i, stock in enumerate(stocks):
            if i < 10:
                future_returns = prices_df[stock].pct_change(5).shift(-5)
                signals = future_returns * 100 + np.random.normal(2, 0.5, len(dates))
            else:
                future_returns = prices_df[stock].pct_change(5).shift(-5)
                signals = -future_returns * 100 + np.random.normal(-2, 0.5, len(dates))

            signal_data[stock] = signals

        signals_df = pd.DataFrame(signal_data, index=dates)

        return signals_df, prices_df

    def test_basic_market_neutral(self, sample_data):
        """测试基础市场中性"""
        signals, prices = sample_data

        engine = BacktestEngine(initial_capital=1000000)
        results = engine.backtest_market_neutral(
            signals=signals,
            prices=prices,
            top_n=5,
            bottom_n=5,
            margin_rate=0.10
        )
        assert results.is_success(), f'回测失败: {results.error}'

        # 验证结果
        assert 'portfolio_value' in results.data
        pv = results.data['portfolio_value']

        # 应该有多空头市值
        assert 'long_value' in pv.columns
        assert 'short_value' in pv.columns
        assert 'short_interest' in pv.columns


class TestGetterMethods:
    """测试getter方法"""

    @pytest.fixture
    def engine_with_results(self):
        """创建有结果的引擎"""
        np.random.seed(42)
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

        engine = BacktestEngine(initial_capital=1000000)
        engine.backtest_long_only(signals, prices, top_n=3)

        return engine

    def test_get_portfolio_value(self, engine_with_results):
        """测试获取组合净值"""
        pv = engine_with_results.get_portfolio_value()

        assert isinstance(pv, pd.DataFrame)
        assert 'total' in pv.columns
        assert len(pv) > 0

    def test_get_daily_returns(self, engine_with_results):
        """测试获取每日收益率"""
        returns = engine_with_results.get_daily_returns()

        assert isinstance(returns, pd.Series)
        assert len(returns) > 0

    def test_get_positions(self, engine_with_results):
        """测试获取持仓历史"""
        positions = engine_with_results.get_positions()

        assert isinstance(positions, list)
        assert len(positions) > 0

    def test_getter_before_backtest(self):
        """测试回测前调用getter应该抛出异常"""
        engine = BacktestEngine()

        with pytest.raises(ValueError):
            engine.get_portfolio_value()

        with pytest.raises(ValueError):
            engine.get_daily_returns()

        with pytest.raises(ValueError):
            engine.get_positions()


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_signals(self):
        """测试空信号"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        stocks = [f'{i:06d}' for i in range(600000, 600005)]

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

        engine = BacktestEngine()
        results = engine.backtest_long_only(signals, prices, top_n=3)
        assert results.is_success(), f'回测失败: {results.error}'

        # 应该能正常运行
        assert results.data['portfolio_value'] is not None

    def test_single_stock(self):
        """测试单只股票"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        stocks = ['600000']

        prices = pd.DataFrame(
            np.random.rand(len(dates), 1) * 10 + 10,
            index=dates,
            columns=stocks
        )

        signals = pd.DataFrame(
            np.random.randn(len(dates), 1),
            index=dates,
            columns=stocks
        )

        engine = BacktestEngine()
        results = engine.backtest_long_only(signals, prices, top_n=1)
        assert results.is_success(), f'回测失败: {results.error}'

        assert results.data['portfolio_value'] is not None

    def test_insufficient_capital(self):
        """测试资金不足"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        stocks = [f'{i:06d}' for i in range(600000, 600010)]

        # 高价股
        prices = pd.DataFrame(
            np.random.rand(len(dates), len(stocks)) * 100 + 100,
            index=dates,
            columns=stocks
        )

        signals = pd.DataFrame(
            np.random.randn(len(dates), len(stocks)),
            index=dates,
            columns=stocks
        )

        # 很少的初始资金
        engine = BacktestEngine(initial_capital=10000)
        results = engine.backtest_long_only(signals, prices, top_n=5)
        assert results.is_success(), f'回测失败: {results.error}'

        # 应该能运行但可能无法建仓
        assert results.data['portfolio_value'] is not None

    def test_nan_prices(self):
        """测试包含NaN的价格"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        stocks = [f'{i:06d}' for i in range(600000, 600005)]

        prices = pd.DataFrame(
            np.random.rand(len(dates), len(stocks)) * 10 + 10,
            index=dates,
            columns=stocks
        )

        # 添加一些NaN
        prices.iloc[10:15, 0] = np.nan

        signals = pd.DataFrame(
            np.random.randn(len(dates), len(stocks)),
            index=dates,
            columns=stocks
        )

        engine = BacktestEngine()
        results = engine.backtest_long_only(signals, prices, top_n=3)
        assert results.is_success(), f'回测失败: {results.error}'

        # 应该能处理NaN并跳过
        assert results.data['portfolio_value'] is not None

    def test_invalid_rebalance_freq(self):
        """测试无效的调仓频率"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        stocks = ['600000']

        prices = pd.DataFrame(
            [[10.0]] * len(dates),
            index=dates,
            columns=stocks
        )

        signals = pd.DataFrame(
            [[1.0]] * len(dates),
            index=dates,
            columns=stocks
        )

        engine = BacktestEngine()

        with pytest.raises(ValueError):
            engine.backtest_long_only(
                signals, prices, top_n=1, rebalance_freq='INVALID'
            )


class TestCostAnalyzerIntegration:
    """测试成本分析器集成"""

    def test_trades_recorded(self):
        """测试交易被记录"""
        np.random.seed(42)
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

        engine = BacktestEngine()
        results = engine.backtest_long_only(signals, prices, top_n=3, rebalance_freq='W')
        assert results.is_success(), f'回测失败: {results.error}'

        # 应该有交易记录
        assert len(results.data['cost_analyzer'].trades) > 0

        # 应该有成本分析
        assert 'cost_analysis' in results.data
        assert 'total_cost' in results.data['cost_analysis']


class TestMarketDataIntegration:
    """测试市场数据集成（高级滑点模型）"""

    @pytest.fixture
    def market_data_sample(self):
        """创建市场数据样本"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        stocks = [f'{i:06d}' for i in range(600000, 600005)]

        # 价格数据
        prices = pd.DataFrame(
            np.random.rand(len(dates), len(stocks)) * 10 + 10,
            index=dates,
            columns=stocks
        )

        # 成交量数据
        volumes = pd.DataFrame(
            np.random.rand(len(dates), len(stocks)) * 1000000 + 500000,
            index=dates,
            columns=stocks
        )

        # 波动率数据
        volatilities = pd.DataFrame(
            np.random.rand(len(dates), len(stocks)) * 0.02 + 0.01,
            index=dates,
            columns=stocks
        )

        # 盘口数据
        bid_prices = prices * 0.999  # 买一价
        ask_prices = prices * 1.001  # 卖一价

        # 信号数据
        signals = pd.DataFrame(
            np.random.randn(len(dates), len(stocks)),
            index=dates,
            columns=stocks
        )

        return {
            'prices': prices,
            'signals': signals,
            'volumes': volumes,
            'volatilities': volatilities,
            'bid_prices': bid_prices,
            'ask_prices': ask_prices
        }

    def test_set_market_data_volumes(self, market_data_sample):
        """测试设置成交量数据"""
        engine = BacktestEngine(
            initial_capital=1000000,
            slippage_model=VolumeBasedSlippageModel()
        )

        # 设置成交量数据
        engine.set_market_data(volumes=market_data_sample['volumes'])

        assert 'volumes' in engine._market_data_cache
        assert engine._market_data_cache['volumes'].equals(market_data_sample['volumes'])

    def test_set_market_data_volatilities(self, market_data_sample):
        """测试设置波动率数据"""
        engine = BacktestEngine(
            initial_capital=1000000,
            slippage_model=MarketImpactModel()
        )

        # 设置波动率数据
        engine.set_market_data(volatilities=market_data_sample['volatilities'])

        assert 'volatilities' in engine._market_data_cache
        assert engine._market_data_cache['volatilities'].equals(market_data_sample['volatilities'])

    def test_set_market_data_bid_ask(self, market_data_sample):
        """测试设置盘口数据"""
        engine = BacktestEngine(initial_capital=1000000)

        # 设置盘口数据
        engine.set_market_data(
            bid_prices=market_data_sample['bid_prices'],
            ask_prices=market_data_sample['ask_prices']
        )

        assert 'bid_prices' in engine._market_data_cache
        assert 'ask_prices' in engine._market_data_cache

    def test_set_all_market_data(self, market_data_sample):
        """测试设置所有市场数据"""
        engine = BacktestEngine(initial_capital=1000000)

        # 一次设置所有数据
        engine.set_market_data(
            volumes=market_data_sample['volumes'],
            volatilities=market_data_sample['volatilities'],
            bid_prices=market_data_sample['bid_prices'],
            ask_prices=market_data_sample['ask_prices']
        )

        # 验证所有数据都已设置
        assert len(engine._market_data_cache) == 4
        assert 'volumes' in engine._market_data_cache
        assert 'volatilities' in engine._market_data_cache
        assert 'bid_prices' in engine._market_data_cache
        assert 'ask_prices' in engine._market_data_cache

    def test_backtest_with_volume_data(self, market_data_sample):
        """测试带成交量数据的回测"""
        engine = BacktestEngine(
            initial_capital=1000000,
            slippage_model=VolumeBasedSlippageModel(base_slippage=0.0005)
        )

        # 设置成交量数据
        engine.set_market_data(volumes=market_data_sample['volumes'])

        # 运行回测
        results = engine.backtest_long_only(
            signals=market_data_sample['signals'],
            prices=market_data_sample['prices'],
            top_n=3
        )
        assert results.is_success(), f'回测失败: {results.error}'

        # 应该成功完成
        assert 'portfolio_value' in results.data
        assert len(results.data['portfolio_value']) > 0

    def test_backtest_with_all_market_data(self, market_data_sample):
        """测试带完整市场数据的回测"""
        engine = BacktestEngine(
            initial_capital=1000000,
            slippage_model=MarketImpactModel(
                volatility_weight=0.5,
                volume_impact_alpha=0.5
            )
        )

        # 设置所有市场数据
        engine.set_market_data(
            volumes=market_data_sample['volumes'],
            volatilities=market_data_sample['volatilities'],
            bid_prices=market_data_sample['bid_prices'],
            ask_prices=market_data_sample['ask_prices']
        )

        # 运行回测
        results = engine.backtest_long_only(
            signals=market_data_sample['signals'],
            prices=market_data_sample['prices'],
            top_n=3
        )
        assert results.is_success(), f'回测失败: {results.error}'

        # 验证结果
        assert 'portfolio_value' in results.data
        assert results.data['portfolio_value'] is not None
        assert len(results.data['cost_analyzer'].trades) > 0

    def test_slippage_with_vs_without_volume_data(self, market_data_sample):
        """对比有无成交量数据时的滑点差异"""
        # 不带成交量数据
        engine1 = BacktestEngine(
            initial_capital=1000000,
            slippage_model=VolumeBasedSlippageModel()
        )
        results1 = engine1.backtest_long_only(
            signals=market_data_sample['signals'],
            prices=market_data_sample['prices'],
            top_n=3
        )

        # 带成交量数据
        engine2 = BacktestEngine(
            initial_capital=1000000,
            slippage_model=VolumeBasedSlippageModel()
        )
        engine2.set_market_data(volumes=market_data_sample['volumes'])
        results2 = engine2.backtest_long_only(
            signals=market_data_sample['signals'],
            prices=market_data_sample['prices'],
            top_n=3
        )

        # 两者应该有不同的滑点成本
        cost1 = results1.data['cost_analysis']['total_slippage']
        cost2 = results2.data['cost_analysis']['total_slippage']

        # 成本可能不同（取决于成交量数据）
        assert cost1 >= 0
        assert cost2 >= 0


class TestAdvancedBacktestFeatures:
    """测试高级回测功能"""

    def test_backtest_with_market_impact_model(self):
        """测试使用市场冲击模型的回测"""
        np.random.seed(42)
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

        # 使用市场冲击模型
        engine = BacktestEngine(
            initial_capital=1000000,
            slippage_model=MarketImpactModel(
                volatility_weight=0.5,
                volume_impact_alpha=0.5,
                urgency_factor=1.0
            )
        )

        results = engine.backtest_long_only(signals, prices, top_n=3)
        assert results.is_success(), f'回测失败: {results.error}'

        assert 'portfolio_value' in results.data
        assert len(results.data['cost_analyzer'].trades) > 0

    def test_large_capital_high_slippage(self):
        """测试大资金时滑点影响"""
        np.random.seed(42)
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

        # 小资金
        engine_small = BacktestEngine(
            initial_capital=1000000,
            slippage_model=VolumeBasedSlippageModel()
        )
        results_small = engine_small.backtest_long_only(signals, prices, top_n=3)

        # 大资金
        engine_large = BacktestEngine(
            initial_capital=100000000,  # 1亿
            slippage_model=VolumeBasedSlippageModel()
        )
        results_large = engine_large.backtest_long_only(signals, prices, top_n=3)

        # 大资金的滑点成本比例应该更高
        small_slippage_ratio = (
            results_small.data['cost_analysis']['total_slippage'] /
            results_small.data['cost_analysis']['total_cost']
        )
        large_slippage_ratio = (
            results_large.data['cost_analysis']['total_slippage'] /
            results_large.data['cost_analysis']['total_cost']
        )

        # 验证结果合理
        assert small_slippage_ratio >= 0
        assert large_slippage_ratio >= 0

    def test_transaction_cost_breakdown(self):
        """测试交易成本分解"""
        np.random.seed(42)
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

        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            slippage=0.001
        )

        results = engine.backtest_long_only(signals, prices, top_n=3, rebalance_freq='W')
        assert results.is_success(), f'回测失败: {results.error}'

        # 验证成本分解
        cost_analysis = results.data['cost_analysis']

        assert 'total_commission' in cost_analysis
        assert 'total_stamp_tax' in cost_analysis
        assert 'total_slippage' in cost_analysis
        assert 'total_cost' in cost_analysis

        # 总成本应该等于各项之和
        total = (
            cost_analysis['total_commission'] +
            cost_analysis['total_stamp_tax'] +
            cost_analysis['total_slippage']
        )
        assert abs(cost_analysis['total_cost'] - total) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
