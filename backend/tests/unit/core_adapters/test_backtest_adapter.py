"""
BacktestAdapter 单元测试

测试回测引擎适配器的所有功能。

作者: Backend Team
创建日期: 2026-02-01
更新日期: 2026-02-09
版本: 2.0.0 (补充完整测试用例)
"""

import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

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
        stamp_tax_rate=0.001,
        min_commission=5.0,
        slippage=0.0
    )


@pytest.fixture
def sample_portfolio_value():
    """创建示例投资组合价值序列"""
    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    values = 1000000 + np.cumsum(np.random.randn(100) * 10000)
    return pd.Series(values, index=dates)


@pytest.fixture
def sample_portfolio_df():
    """创建示例投资组合 DataFrame"""
    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    return pd.DataFrame({
        'cash': [500000] * 10,
        'holdings': [500000] * 10,
        'total': [1000000] * 10
    }, index=dates)


@pytest.fixture
def sample_trades():
    """创建示例交易记录"""
    return pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=10, freq="10D"),
        "code": ["000001"] * 10,
        "action": ["buy", "sell"] * 5,
        "buy_price": [100.0, 102.0, 104.0, 106.0, 108.0] * 2,
        "sell_price": [102.0, 104.0, 106.0, 108.0, 110.0] * 2,
        "quantity": [100] * 10,
        "price": [100.0, 102.0, 104.0, 106.0, 108.0, 102.0, 104.0, 106.0, 108.0, 110.0],
    })


@pytest.fixture
def sample_prices_df():
    """创建示例价格数据"""
    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    return pd.DataFrame({
        'open': [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0],
        'high': [102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0],
        'low': [99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0],
        'close': [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0],
        'volume': [1000000] * 10
    }, index=dates)


@pytest.fixture
def mock_backtest_success_response():
    """模拟成功的回测响应"""
    mock_response = Mock()
    mock_response.is_success.return_value = True
    mock_response.data = {
        'portfolio_value': pd.DataFrame({
            'cash': [500000] * 10,
            'holdings': [500000] * 10,
            'total': [1000000] * 10
        }, index=pd.date_range("2023-01-01", periods=10, freq="D")),
        'positions': [],
        'trades': [],
        'daily_returns': pd.Series([0.01] * 10),
        'cost_metrics': {'total_commission': 300.0}
    }
    return mock_response


@pytest.fixture
def mock_backtest_failure_response():
    """模拟失败的回测响应"""
    mock_response = Mock()
    mock_response.is_success.return_value = False
    mock_response.message = "回测失败"
    return mock_response


class TestBacktestAdapterInit:
    """测试 BacktestAdapter 初始化"""

    def test_init_default_params(self):
        """测试使用默认参数初始化"""
        adapter = BacktestAdapter()
        assert adapter.initial_capital == 1000000.0
        assert adapter.commission_rate == 0.0003
        assert adapter.stamp_tax_rate == 0.001
        assert adapter.min_commission == 5.0
        assert adapter.slippage == 0.0
        assert adapter.verbose is True
        assert adapter.engine is not None

    def test_init_custom_params(self):
        """测试使用自定义参数初始化"""
        adapter = BacktestAdapter(
            initial_capital=2000000.0,
            commission_rate=0.0005,
            stamp_tax_rate=0.002,
            min_commission=10.0,
            slippage=0.01,
            verbose=False
        )
        assert adapter.initial_capital == 2000000.0
        assert adapter.commission_rate == 0.0005
        assert adapter.stamp_tax_rate == 0.002
        assert adapter.min_commission == 10.0
        assert adapter.slippage == 0.01
        assert adapter.verbose is False


class TestBacktestAdapterRunBacktest:
    """测试回测执行功能"""

    @pytest.mark.asyncio
    async def test_run_backtest_success(self, backtest_adapter, mock_backtest_success_response, sample_prices_df):
        """测试成功运行回测"""
        with patch.object(backtest_adapter.engine, 'backtest_long_only', return_value=mock_backtest_success_response):
            with patch('src.data_pipeline.data_loader.DataLoader') as mock_loader_class:
                mock_loader = Mock()
                mock_loader.load_data.return_value = sample_prices_df
                mock_loader_class.return_value = mock_loader

                result = await backtest_adapter.run_backtest(
                    stock_codes=['000001'],
                    strategy_params={'strategy_name': '测试策略', 'top_n': 10},
                    start_date=date(2023, 1, 1),
                    end_date=date(2023, 1, 10)
                )

                assert isinstance(result, dict)
                assert 'metrics' in result
                assert 'equity_curve' in result
                assert result['symbol'] == '000001'

    @pytest.mark.asyncio
    async def test_run_backtest_empty_stock_codes(self, backtest_adapter):
        """测试空股票代码列表"""
        result = await backtest_adapter.run_backtest(
            stock_codes=[],
            strategy_params={},
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31)
        )

        assert 'error' in result

    @pytest.mark.asyncio
    async def test_run_backtest_no_data_available(self, backtest_adapter):
        """测试市场数据不可用"""
        with patch('src.data_pipeline.data_loader.DataLoader') as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load_data.return_value = pd.DataFrame()  # 空数据
            mock_loader_class.return_value = mock_loader

            result = await backtest_adapter.run_backtest(
                stock_codes=['000001'],
                strategy_params={},
                start_date=date(2023, 1, 1),
                end_date=date(2023, 1, 10)
            )

            # 空数据会导致缺少 'close' 列的错误
            assert 'error' in result or 'message' in result

    @pytest.mark.asyncio
    async def test_run_backtest_engine_failure(self, backtest_adapter, mock_backtest_failure_response, sample_prices_df):
        """测试回测引擎执行失败"""
        with patch.object(backtest_adapter.engine, 'backtest_long_only', return_value=mock_backtest_failure_response):
            with patch('src.data_pipeline.data_loader.DataLoader') as mock_loader_class:
                mock_loader = Mock()
                mock_loader.load_data.return_value = sample_prices_df
                mock_loader_class.return_value = mock_loader

                result = await backtest_adapter.run_backtest(
                    stock_codes=['000001'],
                    strategy_params={},
                    start_date=date(2023, 1, 1),
                    end_date=date(2023, 1, 10)
                )

                assert 'error' in result

    @pytest.mark.asyncio
    async def test_run_backtest_data_loader_exception(self, backtest_adapter):
        """测试数据加载器异常"""
        with patch('src.data_pipeline.data_loader.DataLoader') as mock_loader_class:
            mock_loader_class.side_effect = Exception("数据加载失败")

            result = await backtest_adapter.run_backtest(
                stock_codes=['000001'],
                strategy_params={},
                start_date=date(2023, 1, 1),
                end_date=date(2023, 1, 10)
            )

            assert 'error' in result

    @pytest.mark.asyncio
    async def test_run_backtest_missing_close_column(self, backtest_adapter):
        """测试缺少收盘价列"""
        with patch('src.data_pipeline.data_loader.DataLoader') as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load_data.return_value = pd.DataFrame({'open': [100, 101]})  # 缺少 close 列
            mock_loader_class.return_value = mock_loader

            result = await backtest_adapter.run_backtest(
                stock_codes=['000001'],
                strategy_params={},
                start_date=date(2023, 1, 1),
                end_date=date(2023, 1, 10)
            )

            assert 'error' in result

    @pytest.mark.asyncio
    async def test_run_backtest_with_exchange_suffix(self, backtest_adapter, mock_backtest_success_response, sample_prices_df):
        """测试股票代码包含交易所后缀"""
        with patch.object(backtest_adapter.engine, 'backtest_long_only', return_value=mock_backtest_success_response):
            with patch('src.data_pipeline.data_loader.DataLoader') as mock_loader_class:
                mock_loader = Mock()
                mock_loader.load_data.return_value = sample_prices_df
                mock_loader_class.return_value = mock_loader

                result = await backtest_adapter.run_backtest(
                    stock_codes=['000001.SZ'],  # 带交易所后缀
                    strategy_params={},
                    start_date=date(2023, 1, 1),
                    end_date=date(2023, 1, 10)
                )

                # 验证调用时移除了后缀
                mock_loader.load_data.assert_called_once()
                call_args = mock_loader.load_data.call_args
                assert call_args[1]['symbol'] == '000001'  # 后缀已移除

                # 验证返回结果包含原始代码
                assert result['symbol'] == '000001.SZ'


class TestBacktestAdapterCalculateMetrics:
    """测试绩效指标计算"""

    @pytest.mark.asyncio
    async def test_calculate_metrics_success(self, backtest_adapter, sample_portfolio_value, sample_trades):
        """测试成功计算绩效指标"""
        positions = pd.DataFrame({
            "date": pd.date_range("2023-01-01", periods=100, freq="D"),
            "position": np.random.randint(0, 1000, 100),
        })

        with patch('app.core_adapters.backtest_adapter.PerformanceAnalyzer') as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_result = Mock()
            mock_result.data = {
                'total_return': 0.25,
                'sharpe_ratio': 1.5,
                'max_drawdown': -0.15
            }
            mock_analyzer.calculate_all_metrics.return_value = mock_result
            mock_analyzer_class.return_value = mock_analyzer

            result = await backtest_adapter.calculate_metrics(
                sample_portfolio_value, positions, sample_trades
            )

            assert isinstance(result, dict)
            assert 'total_return' in result
            assert 'sharpe_ratio' in result

    @pytest.mark.asyncio
    async def test_calculate_metrics_with_dataframe(self, backtest_adapter, sample_trades):
        """测试使用 DataFrame 格式的 portfolio_value"""
        portfolio_df = pd.DataFrame({
            'value': [1000000, 1010000, 1020000],
            'cash': [500000, 505000, 510000]
        }, index=pd.date_range("2023-01-01", periods=3, freq="D"))

        positions = pd.DataFrame()

        with patch('app.core_adapters.backtest_adapter.PerformanceAnalyzer') as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_result = Mock()
            mock_result.data = {'total_return': 0.02}
            mock_analyzer.calculate_all_metrics.return_value = mock_result
            mock_analyzer_class.return_value = mock_analyzer

            result = await backtest_adapter.calculate_metrics(
                portfolio_df, positions, sample_trades
            )

            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_calculate_metrics_analyzer_returns_dict(self, backtest_adapter, sample_portfolio_value, sample_trades):
        """测试 PerformanceAnalyzer 直接返回字典"""
        positions = pd.DataFrame()

        with patch('app.core_adapters.backtest_adapter.PerformanceAnalyzer') as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer.calculate_all_metrics.return_value = {
                'total_return': 0.15,
                'sharpe_ratio': 1.2
            }
            mock_analyzer_class.return_value = mock_analyzer

            result = await backtest_adapter.calculate_metrics(
                sample_portfolio_value, positions, sample_trades
            )

            assert isinstance(result, dict)
            assert 'total_return' in result


class TestBacktestAdapterTradingCosts:
    """测试交易成本分析"""

    @pytest.mark.asyncio
    async def test_analyze_trading_costs_with_dataframe(self, backtest_adapter, sample_trades):
        """测试使用 DataFrame 分析交易成本"""
        with patch('app.core_adapters.backtest_adapter.TradingCostAnalyzer') as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer.trades = [1, 2, 3]
            mock_analyzer.calculate_total_costs.return_value = {
                'total_commission': 300.0,
                'total_stamp_tax': 1000.0,
                'total_slippage': 0.0
            }
            mock_analyzer_class.return_value = mock_analyzer

            result = await backtest_adapter.analyze_trading_costs(sample_trades)

            assert isinstance(result, dict)
            assert 'total_commission' in result
            assert 'trade_count' in result
            assert result['trade_count'] == 3

    @pytest.mark.asyncio
    async def test_analyze_trading_costs_with_list(self, backtest_adapter):
        """测试使用列表分析交易成本"""
        trades_list = [
            {'date': '2023-01-01', 'code': '000001', 'action': 'buy', 'price': 100.0, 'quantity': 100},
            {'date': '2023-01-02', 'code': '000001', 'action': 'sell', 'price': 105.0, 'quantity': 100},
        ]

        with patch('app.core_adapters.backtest_adapter.TradingCostAnalyzer') as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer.trades = trades_list
            mock_analyzer.calculate_total_costs.return_value = {
                'total_commission': 30.0,
                'total_stamp_tax': 105.0
            }
            mock_analyzer_class.return_value = mock_analyzer

            result = await backtest_adapter.analyze_trading_costs(trades_list)

            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_analyze_trading_costs_empty_trades(self, backtest_adapter):
        """测试空交易记录"""
        with patch('app.core_adapters.backtest_adapter.TradingCostAnalyzer') as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer.trades = []
            mock_analyzer.calculate_total_costs.return_value = {
                'total_commission': 0.0,
                'total_stamp_tax': 0.0
            }
            mock_analyzer_class.return_value = mock_analyzer

            result = await backtest_adapter.analyze_trading_costs(pd.DataFrame())

            assert result['trade_count'] == 0


class TestBacktestAdapterRiskMetrics:
    """测试风险指标计算"""

    @pytest.mark.asyncio
    async def test_calculate_risk_metrics_success(self, backtest_adapter):
        """测试成功计算风险指标"""
        returns = pd.Series(np.random.randn(100) * 0.01)
        positions = pd.DataFrame({
            "date": pd.date_range("2023-01-01", periods=100, freq="D"),
            "position": np.random.randint(0, 1000, 100),
        })

        result = await backtest_adapter.calculate_risk_metrics(returns, positions)

        assert isinstance(result, dict)
        assert 'volatility' in result
        assert 'var_95' in result
        assert 'cvar_95' in result
        assert 'downside_volatility' in result
        assert isinstance(result['volatility'], (int, float))

    @pytest.mark.asyncio
    async def test_calculate_risk_metrics_no_negative_returns(self, backtest_adapter):
        """测试没有负收益率的情况"""
        returns = pd.Series(np.abs(np.random.randn(100) * 0.01))  # 全部正收益
        positions = pd.DataFrame()

        result = await backtest_adapter.calculate_risk_metrics(returns, positions)

        assert isinstance(result, dict)
        assert 'downside_volatility' in result


class TestBacktestAdapterTradeStatistics:
    """测试交易统计"""

    @pytest.mark.asyncio
    async def test_get_trade_statistics_with_trades(self, backtest_adapter, sample_trades):
        """测试获取交易统计（有交易）"""
        result = await backtest_adapter.get_trade_statistics(sample_trades)

        assert isinstance(result, dict)
        assert result["total_trades"] == 10
        assert "winning_trades" in result
        assert "losing_trades" in result
        assert "win_rate" in result
        assert "profit_factor" in result

    @pytest.mark.asyncio
    async def test_get_trade_statistics_empty(self, backtest_adapter):
        """测试获取交易统计（无交易）"""
        empty_trades = pd.DataFrame()

        result = await backtest_adapter.get_trade_statistics(empty_trades)

        assert isinstance(result, dict)
        assert result["total_trades"] == 0
        assert result["win_rate"] == 0.0
        assert result["profit_factor"] == 0.0

    @pytest.mark.asyncio
    async def test_get_trade_statistics_all_winning(self, backtest_adapter):
        """测试全部盈利交易"""
        trades = pd.DataFrame({
            'buy_price': [100.0, 105.0, 110.0],
            'sell_price': [105.0, 110.0, 115.0],
        })

        result = await backtest_adapter.get_trade_statistics(trades)

        assert result["winning_trades"] == 3
        assert result["losing_trades"] == 0
        assert result["win_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_get_trade_statistics_all_losing(self, backtest_adapter):
        """测试全部亏损交易"""
        trades = pd.DataFrame({
            'buy_price': [105.0, 110.0, 115.0],
            'sell_price': [100.0, 105.0, 110.0],
        })

        result = await backtest_adapter.get_trade_statistics(trades)

        assert result["winning_trades"] == 0
        assert result["losing_trades"] == 3
        assert result["win_rate"] == 0.0
        assert result["profit_factor"] == 0.0


class TestBacktestAdapterHelperMethods:
    """测试辅助方法"""

    def test_convert_equity_curve(self, backtest_adapter, sample_portfolio_df):
        """测试转换资产曲线"""
        result = backtest_adapter._convert_equity_curve(sample_portfolio_df)

        assert isinstance(result, list)
        assert len(result) == 10
        assert all('date' in item for item in result)
        assert all('value' in item for item in result)
        assert all('cash' in item for item in result)

    def test_convert_equity_curve_empty(self, backtest_adapter):
        """测试转换空资产曲线"""
        result = backtest_adapter._convert_equity_curve(pd.DataFrame())

        assert isinstance(result, list)
        assert len(result) == 0

    def test_generate_kline_data(self, backtest_adapter, sample_prices_df):
        """测试生成K线数据"""
        result = backtest_adapter._generate_kline_data(sample_prices_df)

        assert isinstance(result, list)
        assert len(result) == 10
        assert all('date' in item for item in result)
        assert all('close' in item for item in result)
        assert all('open' in item for item in result)

    def test_generate_kline_data_minimal(self, backtest_adapter):
        """测试生成最小K线数据（仅收盘价）"""
        prices_df = pd.DataFrame({
            'close': [100.0, 101.0, 102.0]
        }, index=pd.date_range("2023-01-01", periods=3, freq="D"))

        result = backtest_adapter._generate_kline_data(prices_df)

        assert len(result) == 3
        assert all('close' in item for item in result)

    def test_extract_signal_points_from_trades(self, backtest_adapter, sample_trades, sample_prices_df):
        """测试从交易记录提取信号点"""
        result = backtest_adapter._extract_signal_points(
            trades=[{'date': '2023-01-01', 'action': 'buy', 'price': 100.0}],
            positions=[],
            prices_df=sample_prices_df
        )

        assert 'buy' in result
        assert 'sell' in result
        assert len(result['buy']) == 1

    def test_extract_signal_points_from_positions(self, backtest_adapter, sample_prices_df):
        """测试从持仓记录提取信号点"""
        positions = [
            {'date': '2023-01-01', 'positions': {'000001': {'entry_price': 100.0}}},
            {'date': '2023-01-02', 'positions': {}},
        ]

        result = backtest_adapter._extract_signal_points(
            trades=[],
            positions=positions,
            prices_df=sample_prices_df
        )

        assert isinstance(result, dict)
        assert 'buy' in result
        assert 'sell' in result

    def test_normalize_date(self, backtest_adapter):
        """测试标准化日期"""
        # 测试 datetime 对象
        dt = datetime(2023, 1, 1)
        assert backtest_adapter._normalize_date(dt) == "2023-01-01"

        # 测试字符串
        assert backtest_adapter._normalize_date("2023-01-01") == "2023-01-01"
        assert backtest_adapter._normalize_date("2023-01-01T10:30:00") == "2023-01-01"

        # 测试无效输入
        assert backtest_adapter._normalize_date(None) == ""

    def test_get_close_price(self, backtest_adapter, sample_prices_df):
        """测试获取收盘价"""
        price = backtest_adapter._get_close_price("2023-01-01", sample_prices_df)

        assert price is not None
        assert isinstance(price, float)

    def test_get_close_price_invalid_date(self, backtest_adapter, sample_prices_df):
        """测试获取不存在日期的收盘价"""
        price = backtest_adapter._get_close_price("2099-01-01", sample_prices_df)

        assert price is None

    def test_calculate_metrics_helper(self, backtest_adapter, sample_portfolio_df):
        """测试计算指标辅助方法"""
        daily_returns = pd.Series([0.01, 0.02, -0.01, 0.015])
        equity_curve = backtest_adapter._convert_equity_curve(sample_portfolio_df)
        cost_metrics = {'total_commission': 300.0}

        with patch('app.core_adapters.backtest_adapter.PerformanceAnalyzer') as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_result = Mock()
            mock_result.data = {'total_return': 0.035}
            mock_analyzer.calculate_all_metrics.return_value = mock_result
            mock_analyzer_class.return_value = mock_analyzer

            result = backtest_adapter._calculate_metrics(daily_returns, equity_curve, cost_metrics)

            assert isinstance(result, dict)

    def test_calculate_metrics_helper_fallback(self, backtest_adapter, sample_portfolio_df):
        """测试计算指标辅助方法（使用备用计算）"""
        daily_returns = pd.Series([0.01, 0.02])
        equity_curve = backtest_adapter._convert_equity_curve(sample_portfolio_df)
        cost_metrics = {}

        with patch('app.core_adapters.backtest_adapter.PerformanceAnalyzer') as mock_analyzer_class:
            mock_analyzer_class.side_effect = Exception("计算失败")

            result = backtest_adapter._calculate_metrics(daily_returns, equity_curve, cost_metrics)

            assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
