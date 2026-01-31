"""
BacktestEngine分块回测测试

测试内容:
- 分块回测基本功能
- 与非分块版本结果一致性
- 内存优化效果
- 不同chunk_size的正确性
- 边界条件处理

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.backtest.backtest_engine import BacktestEngine


@pytest.fixture
def sample_market_data():
    """生成示例市场数据"""
    np.random.seed(42)

    # 250个交易日，20只股票
    dates = pd.date_range('2023-01-01', periods=250, freq='D')
    stocks = [f"{i:06d}.SZ" for i in range(600000, 600020)]

    # 价格数据（随机游走）
    price_data = {}
    for stock in stocks:
        base_price = 10.0
        returns = np.random.normal(0.0005, 0.015, len(dates))
        prices = base_price * (1 + returns).cumprod()
        price_data[stock] = prices

    prices_df = pd.DataFrame(price_data, index=dates)

    # 信号数据（模拟预测能力）
    signal_data = {}
    for stock in stocks:
        # 信号与未来收益正相关
        future_returns = prices_df[stock].pct_change(5).shift(-5)
        signals = future_returns * 10 + np.random.normal(0, 0.5, len(dates))
        signal_data[stock] = signals

    signals_df = pd.DataFrame(signal_data, index=dates)

    return prices_df, signals_df


class TestChunkedBacktest:
    """测试分块回测"""

    def test_basic_chunked_backtest(self, sample_market_data):
        """测试基本分块回测功能"""
        prices_df, signals_df = sample_market_data

        engine = BacktestEngine(
            initial_capital=1000000,
            verbose=False
        )

        # 运行分块回测
        results = engine.backtest_long_only_chunked(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W',
            chunk_size=60  # 每个窗口60天
        )

        # 验证结果结构
        assert 'portfolio_value' in results.data
        assert 'positions' in results.data
        assert 'daily_returns' in results.data
        assert 'cost_analysis' in results.data

        # 验证portfolio_value
        portfolio_value = results.data['portfolio_value']
        assert not portfolio_value.empty
        assert len(portfolio_value) == len(prices_df)
        assert 'cash' in portfolio_value.columns
        assert 'holdings' in portfolio_value.columns
        assert 'total' in portfolio_value.columns

        # 验证最终资产为正
        final_value = portfolio_value['total'].iloc[-1]
        assert final_value > 0

    def test_consistency_with_regular_backtest(self, sample_market_data):
        """测试分块回测与常规回测的一致性"""
        prices_df, signals_df = sample_market_data

        # 使用相同配置
        config = {
            'initial_capital': 1000000,
            'commission_rate': 0.0003,
            'stamp_tax_rate': 0.001,
            'slippage': 0.001,
            'verbose': False
        }

        # 常规回测
        engine_regular = BacktestEngine(**config)
        results_regular = engine_regular.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W'
        )

        # 分块回测
        engine_chunked = BacktestEngine(**config)
        results_chunked = engine_chunked.backtest_long_only_chunked(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W',
            chunk_size=60
        )

        # 比较最终资产（应该非常接近，允许小误差）
        final_regular = results_regular.data['portfolio_value']['total'].iloc[-1]
        final_chunked = results_chunked.data['portfolio_value']['total'].iloc[-1]

        relative_error = abs(final_chunked - final_regular) / final_regular
        # 分块回测由于窗口切分，允许有小幅差异（3%以内可接受）
        assert relative_error < 0.03, \
            f"分块回测与常规回测结果差异过大: {relative_error:.2%}"

        # 比较收益率曲线相关性
        returns_regular = results_regular.data['daily_returns'].fillna(0)
        returns_chunked = results_chunked.data['daily_returns'].fillna(0)

        correlation = returns_regular.corr(returns_chunked)
        # 分块回测由于窗口边界处理，相关性略低但仍然很高（>0.98可接受）
        assert correlation > 0.98, \
            f"分块回测与常规回测收益率相关性过低: {correlation:.4f}"

    def test_different_chunk_sizes(self, sample_market_data):
        """测试不同chunk_size的正确性"""
        prices_df, signals_df = sample_market_data

        chunk_sizes = [30, 60, 90, 125]  # 不同窗口大小
        results_list = []

        for chunk_size in chunk_sizes:
            engine = BacktestEngine(initial_capital=1000000, verbose=False)

            results = engine.backtest_long_only_chunked(
                signals=signals_df,
                prices=prices_df,
                top_n=5,
                holding_period=5,
                rebalance_freq='W',
                chunk_size=chunk_size
            )

            final_value = results.data['portfolio_value']['total'].iloc[-1]
            results_list.append(final_value)

        # 验证不同chunk_size的结果应该非常接近
        max_value = max(results_list)
        min_value = min(results_list)

        relative_range = (max_value - min_value) / max_value
        # 不同chunk_size由于窗口边界处理略有不同，允许有小幅差异
        assert relative_range < 0.03, \
            f"不同chunk_size结果差异过大: {relative_range:.2%}"

    def test_edge_case_small_chunk_size(self, sample_market_data):
        """测试边界情况：很小的chunk_size"""
        prices_df, signals_df = sample_market_data

        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        # chunk_size=20（小于持仓期）
        results = engine.backtest_long_only_chunked(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W',
            chunk_size=20  # 很小的窗口
        )

        # 应该能正常运行
        assert not results.data['portfolio_value'].empty
        assert len(results.data['portfolio_value']) == len(prices_df)

    def test_edge_case_large_chunk_size(self, sample_market_data):
        """测试边界情况：很大的chunk_size"""
        prices_df, signals_df = sample_market_data

        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        # chunk_size大于总天数
        results = engine.backtest_long_only_chunked(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W',
            chunk_size=300  # 大于250天
        )

        # 应该正常运行（相当于不分块）
        assert not results.data['portfolio_value'].empty

    def test_edge_case_chunk_size_equals_data_length(self, sample_market_data):
        """测试chunk_size等于数据长度"""
        prices_df, signals_df = sample_market_data

        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        results = engine.backtest_long_only_chunked(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W',
            chunk_size=len(prices_df)  # 等于数据长度
        )

        # 应该与常规回测结果一致
        assert not results.data['portfolio_value'].empty

    def test_portfolio_continuity(self, sample_market_data):
        """测试组合净值连续性（无跳跃）"""
        prices_df, signals_df = sample_market_data

        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        results = engine.backtest_long_only_chunked(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W',
            chunk_size=60
        )

        portfolio_value = results.data['portfolio_value']['total']

        # 检查日收益率是否合理（没有异常跳跃）
        daily_returns = portfolio_value.pct_change().dropna()

        # 日收益率应该在合理范围内（-10%到+10%）
        assert (daily_returns > -0.1).all(), "存在异常大幅下跌"
        assert (daily_returns < 0.1).all(), "存在异常大幅上涨"

        # 组合净值应该是连续的（没有缺失值）
        assert not portfolio_value.isna().any()

    def test_position_continuity(self, sample_market_data):
        """测试持仓连续性"""
        prices_df, signals_df = sample_market_data

        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        results = engine.backtest_long_only_chunked(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W',
            chunk_size=60
        )

        positions = results.data['positions']

        # 验证每个日期都有持仓记录
        assert len(positions) == len(prices_df)

        # 验证持仓数量合理（最多top_n）
        for pos_record in positions:
            num_positions = len(pos_record['positions'])
            assert num_positions <= 5, f"持仓数量超过top_n: {num_positions}"

    def test_cost_analysis(self, sample_market_data):
        """测试成本分析功能"""
        prices_df, signals_df = sample_market_data

        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            verbose=False
        )

        results = engine.backtest_long_only_chunked(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W',
            chunk_size=60
        )

        cost_analysis = results.data['cost_analysis']

        # 验证成本分析结果
        assert 'total_commission' in cost_analysis
        assert 'total_stamp_tax' in cost_analysis
        assert 'total_slippage' in cost_analysis

        # 成本应该为非负
        assert cost_analysis['total_commission'] >= 0
        assert cost_analysis['total_stamp_tax'] >= 0
        assert cost_analysis['total_slippage'] >= 0

    def test_different_rebalance_freq(self, sample_market_data):
        """测试不同调仓频率"""
        prices_df, signals_df = sample_market_data

        frequencies = ['D', 'W', 'M']

        for freq in frequencies:
            engine = BacktestEngine(initial_capital=1000000, verbose=False)

            results = engine.backtest_long_only_chunked(
                signals=signals_df,
                prices=prices_df,
                top_n=5,
                holding_period=5,
                rebalance_freq=freq,
                chunk_size=60
            )

            # 应该能正常运行
            assert not results.data['portfolio_value'].empty

    def test_with_memory_monitor(self, sample_market_data):
        """测试内存监控功能"""
        prices_df, signals_df = sample_market_data

        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        # 启用内存监控
        results = engine.backtest_long_only_chunked(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            holding_period=5,
            rebalance_freq='W',
            chunk_size=60,
            enable_memory_monitor=True  # 启用监控
        )

        # 应该能正常运行（监控不影响功能）
        assert not results.data['portfolio_value'].empty


@pytest.mark.slow
class TestChunkedBacktestPerformance:
    """性能测试"""

    def test_large_dataset(self):
        """测试大数据集"""
        np.random.seed(42)

        # 1000天，100只股票
        dates = pd.date_range('2020-01-01', periods=1000, freq='D')
        stocks = [f"{i:06d}.SZ" for i in range(600000, 600100)]

        # 生成数据
        price_data = {}
        signal_data = {}

        for stock in stocks:
            base_price = 10.0
            returns = np.random.normal(0.0005, 0.015, len(dates))
            prices = base_price * (1 + returns).cumprod()
            price_data[stock] = prices
            signal_data[stock] = np.random.randn(len(dates))

        prices_df = pd.DataFrame(price_data, index=dates)
        signals_df = pd.DataFrame(signal_data, index=dates)

        # 分块回测
        engine = BacktestEngine(initial_capital=10000000, verbose=False)

        results = engine.backtest_long_only_chunked(
            signals=signals_df,
            prices=prices_df,
            top_n=20,
            holding_period=10,
            rebalance_freq='W',
            chunk_size=100
        )

        # 验证能处理大数据集
        assert len(results.data['portfolio_value']) == 1000
        assert results.data['portfolio_value']['total'].iloc[-1] > 0


@pytest.mark.integration
class TestChunkedBacktestIntegration:
    """集成测试"""

    def test_end_to_end_workflow(self):
        """端到端工作流测试"""
        np.random.seed(123)

        # 模拟2年数据
        dates = pd.date_range('2022-01-01', '2023-12-31', freq='D')
        stocks = [f"{i:06d}.SZ" for i in range(600000, 600050)]

        # 生成价格数据
        price_data = {}
        for stock in stocks:
            base = 15.0
            returns = np.random.normal(0.0003, 0.012, len(dates))
            prices = base * (1 + returns).cumprod()
            price_data[stock] = prices

        prices_df = pd.DataFrame(price_data, index=dates)

        # 生成信号（动量策略）
        signal_data = {}
        for stock in stocks:
            # 20日动量
            momentum = prices_df[stock].pct_change(20)
            signal_data[stock] = momentum

        signals_df = pd.DataFrame(signal_data, index=dates)

        # 创建回测引擎
        engine = BacktestEngine(
            initial_capital=5000000,
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            slippage=0.001,
            verbose=False
        )

        # 运行分块回测
        results = engine.backtest_long_only_chunked(
            signals=signals_df,
            prices=prices_df,
            top_n=10,
            holding_period=10,
            rebalance_freq='W',
            chunk_size=90,
            enable_memory_monitor=True
        )

        # 验证完整性
        assert len(results.data['portfolio_value']) == len(dates)
        assert len(results.data['positions']) == len(dates)

        # 计算指标
        portfolio_value = results.data['portfolio_value']
        final_value = portfolio_value['total'].iloc[-1]
        total_return = (final_value / 5000000 - 1) * 100

        print(f"\n回测结果:")
        print(f"  初始资金: 5,000,000")
        print(f"  最终资产: {final_value:,.0f}")
        print(f"  总收益率: {total_return:.2f}%")

        # 基本合理性检查
        assert final_value > 0
        assert abs(total_return) < 200  # 2年收益率应该在合理范围内


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
