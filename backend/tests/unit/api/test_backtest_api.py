"""
Backtest API 单元测试

测试所有 Backtest API 端点的功能。

作者: Backend Team
创建日期: 2026-02-02
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# 添加项目路径
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.api.endpoints.backtest import (
    BacktestRequest,
    OptimizeParamsRequest,
    ParallelBacktestRequest,
    analyze_trading_costs,
    calculate_metrics,
    calculate_risk_metrics,
    get_trade_statistics,
    optimize_strategy_params,
    run_backtest,
    run_parallel_backtest,
)


@pytest.fixture
def mock_backtest_adapter():
    """创建模拟的 BacktestAdapter"""
    with patch("app.api.endpoints.backtest.backtest_adapter") as mock:
        yield mock


@pytest.fixture
def mock_data_adapter():
    """创建模拟的 DataAdapter"""
    with patch("app.api.endpoints.backtest.data_adapter") as mock:
        yield mock


@pytest.fixture
def sample_backtest_request():
    """创建示例回测请求"""
    return BacktestRequest(
        stock_codes=["000001", "000002"],
        start_date="2023-01-01",
        end_date="2023-12-31",
        strategy_params={"type": "ma_cross", "short_window": 5, "long_window": 20},
        initial_capital=1000000.0,
        commission_rate=0.0003,
        stamp_tax_rate=0.001,
        min_commission=5.0,
        slippage=0.0,
    )


@pytest.fixture
def sample_backtest_result():
    """创建示例回测结果"""
    return {
        "portfolio_value": [1000000, 1020000, 1015000],
        "positions": [{"code": "000001", "quantity": 100}],
        "trades": [{"code": "000001", "action": "buy", "price": 10.0}],
        "metrics": {
            "total_return": 0.015,
            "annual_return": 0.15,
            "sharpe_ratio": 1.5,
            "max_drawdown": -0.05,
            "win_rate": 0.65,
        },
    }


class TestRunBacktest:
    """测试运行回测端点"""

    @pytest.mark.asyncio
    async def test_run_backtest_success(self, sample_backtest_request, sample_backtest_result):
        """测试成功运行回测"""
        # Arrange
        with patch("app.api.endpoints.backtest.BacktestAdapter") as MockAdapter:
            mock_instance = MockAdapter.return_value
            mock_instance.run_backtest = AsyncMock(return_value=sample_backtest_result)

            # Act
            result = await run_backtest(sample_backtest_request)

            # Assert
            assert result["code"] == 200
            assert result["message"] == "回测完成"
            assert result["data"] == sample_backtest_result
            mock_instance.run_backtest.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_backtest_invalid_date_range(self):
        """测试无效日期范围"""
        # Arrange
        invalid_request = BacktestRequest(
            stock_codes=["000001"],
            start_date="2023-12-31",  # 开始日期晚于结束日期
            end_date="2023-01-01",
            strategy_params={},
            initial_capital=1000000.0,
        )

        # Act
        result = await run_backtest(invalid_request)

        # Assert
        assert result["code"] == 400
        assert "开始日期必须小于结束日期" in result["message"]

    @pytest.mark.asyncio
    async def test_run_backtest_invalid_date_format(self):
        """测试无效日期格式"""
        # Arrange
        invalid_request = BacktestRequest(
            stock_codes=["000001"],
            start_date="2023/01/01",  # 错误的日期格式
            end_date="2023-12-31",
            strategy_params={},
            initial_capital=1000000.0,
        )

        # Act
        result = await run_backtest(invalid_request)

        # Assert
        assert result["code"] == 400
        assert "参数错误" in result["message"]

    @pytest.mark.asyncio
    async def test_run_backtest_adapter_error(self, sample_backtest_request):
        """测试适配器执行错误"""
        # Arrange
        with patch("app.api.endpoints.backtest.BacktestAdapter") as MockAdapter:
            mock_instance = MockAdapter.return_value
            mock_instance.run_backtest = AsyncMock(side_effect=Exception("回测引擎错误"))

            # Act
            result = await run_backtest(sample_backtest_request)

            # Assert
            assert result["code"] == 500
            assert "回测执行失败" in result["message"]


class TestCalculateMetrics:
    """测试计算指标端点"""

    @pytest.mark.asyncio
    async def test_calculate_metrics_success(self, mock_backtest_adapter):
        """测试成功计算指标"""
        # Arrange
        portfolio_value = [1000000, 1020000, 1015000]
        dates = ["2023-01-01", "2023-01-02", "2023-01-03"]
        trades = [{"code": "000001", "action": "buy"}]
        positions = [{"code": "000001", "quantity": 100}]

        expected_metrics = {"total_return": 0.015, "sharpe_ratio": 1.5, "max_drawdown": -0.05}
        mock_backtest_adapter.calculate_metrics = AsyncMock(return_value=expected_metrics)

        # Act
        result = await calculate_metrics(
            portfolio_value=portfolio_value, dates=dates, trades=trades, positions=positions
        )

        # Assert
        assert result["code"] == 200
        assert result["message"] == "指标计算完成"
        assert result["data"] == expected_metrics
        mock_backtest_adapter.calculate_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_metrics_empty_data(self, mock_backtest_adapter):
        """测试空数据"""
        # Arrange
        portfolio_value = []
        dates = []

        # Act
        result = await calculate_metrics(portfolio_value=portfolio_value, dates=dates)

        # Assert
        # 空数据应该导致错误
        assert result["code"] in [400, 500]


class TestRunParallelBacktest:
    """测试并行回测端点"""

    @pytest.mark.asyncio
    async def test_parallel_backtest_success(self, mock_backtest_adapter):
        """测试成功并行回测"""
        # Arrange
        request = ParallelBacktestRequest(
            stock_codes=["000001"],
            strategy_params_list=[
                {"short_window": 5, "long_window": 20},
                {"short_window": 10, "long_window": 40},
            ],
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=1000000.0,
            n_processes=2,
        )

        mock_results = [
            {"params": {"short_window": 5}, "metrics": {"sharpe_ratio": 1.5}},
            {"params": {"short_window": 10}, "metrics": {"sharpe_ratio": 1.8}},
        ]
        mock_backtest_adapter.run_parallel_backtest = AsyncMock(return_value=mock_results)

        # Act
        result = await run_parallel_backtest(request)

        # Assert
        assert result["code"] == 200
        assert "并行回测完成" in result["message"]
        assert result["data"]["total_runs"] == 2
        assert result["data"]["successful_runs"] == 2
        assert result["data"]["best_result"] is not None

    @pytest.mark.asyncio
    async def test_parallel_backtest_with_failures(self, mock_backtest_adapter):
        """测试部分失败的并行回测"""
        # Arrange
        request = ParallelBacktestRequest(
            stock_codes=["000001"],
            strategy_params_list=[
                {"short_window": 5, "long_window": 20},
                {"short_window": 10, "long_window": 40},
            ],
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=1000000.0,
        )

        mock_results = [
            {"params": {"short_window": 5}, "metrics": {"sharpe_ratio": 1.5}},
            {"params": {"short_window": 10}, "error": "数据不足"},
        ]
        mock_backtest_adapter.run_parallel_backtest = AsyncMock(return_value=mock_results)

        # Act
        result = await run_parallel_backtest(request)

        # Assert
        assert result["code"] == 200
        assert result["data"]["successful_runs"] == 1
        assert result["data"]["failed_runs"] == 1


class TestOptimizeStrategyParams:
    """测试参数优化端点"""

    @pytest.mark.asyncio
    async def test_optimize_params_success(self):
        """测试成功优化参数"""
        # Arrange
        request = OptimizeParamsRequest(
            stock_codes=["000001"],
            param_grid={"short_window": [5, 10], "long_window": [20, 40]},
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=1000000.0,
            metric="sharpe_ratio",
        )

        expected_result = {
            "best_params": {"short_window": 10, "long_window": 40},
            "best_metric_value": 1.85,
            "metric": "sharpe_ratio",
            "total_combinations": 4,
        }

        with patch("app.api.endpoints.backtest.BacktestAdapter") as MockAdapter:
            mock_instance = MockAdapter.return_value
            mock_instance.optimize_strategy_params = AsyncMock(return_value=expected_result)

            # Act
            result = await optimize_strategy_params(request)

            # Assert
            assert result["code"] == 200
            assert result["message"] == "参数优化完成"
            assert result["data"]["best_params"]["short_window"] == 10

    @pytest.mark.asyncio
    async def test_optimize_params_empty_grid(self):
        """测试空参数网格"""
        # Arrange
        request = OptimizeParamsRequest(
            stock_codes=["000001"],
            param_grid={},  # 空参数网格
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=1000000.0,
        )

        with patch("app.api.endpoints.backtest.BacktestAdapter") as MockAdapter:
            mock_instance = MockAdapter.return_value
            mock_instance.optimize_strategy_params = AsyncMock(
                side_effect=ValueError("参数网格不能为空")
            )

            # Act
            result = await optimize_strategy_params(request)

            # Assert
            assert result["code"] == 400


class TestAnalyzeTradingCosts:
    """测试交易成本分析端点"""

    @pytest.mark.asyncio
    async def test_analyze_costs_success(self, mock_backtest_adapter):
        """测试成功分析成本"""
        # Arrange
        trades = [
            {"code": "000001", "action": "buy", "price": 10.0, "quantity": 100},
            {"code": "000001", "action": "sell", "price": 11.0, "quantity": 100},
        ]

        expected_analysis = {
            "total_commission": 15.0,
            "total_stamp_tax": 11.0,
            "total_cost": 26.0,
            "cost_ratio": 0.0026,
        }
        mock_backtest_adapter.analyze_trading_costs = AsyncMock(return_value=expected_analysis)

        # Act
        from app.api.endpoints.backtest import CostAnalysisRequest
        request = CostAnalysisRequest(trades=trades)
        result = await analyze_trading_costs(request)

        # Assert
        assert result["code"] == 200
        assert result["message"] == "成本分析完成"
        assert result["data"]["total_cost"] == 26.0

    @pytest.mark.asyncio
    async def test_analyze_costs_empty_trades(self):
        """测试空交易记录"""
        # Act
        from app.api.endpoints.backtest import CostAnalysisRequest
        request = CostAnalysisRequest(trades=[])
        result = await analyze_trading_costs(request)

        # Assert
        assert result["code"] == 400
        assert "不能为空" in result["message"]


class TestCalculateRiskMetrics:
    """测试风险指标端点"""

    @pytest.mark.asyncio
    async def test_calculate_risk_metrics_success(self, mock_backtest_adapter):
        """测试成功计算风险指标"""
        # Arrange
        returns = [0.01, -0.005, 0.015, -0.01]
        dates = ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"]
        positions = []

        expected_metrics = {"volatility": 0.18, "var_95": -0.025, "cvar_95": -0.035}
        mock_backtest_adapter.calculate_risk_metrics = AsyncMock(return_value=expected_metrics)

        # Act
        result = await calculate_risk_metrics(returns=returns, dates=dates, positions=positions)

        # Assert
        assert result["code"] == 200
        assert result["message"] == "风险指标计算完成"
        assert "volatility" in result["data"]


class TestGetTradeStatistics:
    """测试交易统计端点"""

    @pytest.mark.asyncio
    async def test_get_trade_statistics_success(self, mock_backtest_adapter):
        """测试成功获取交易统计"""
        # Arrange
        trades = [
            {"code": "000001", "buy_price": 10.0, "sell_price": 11.0},
            {"code": "000002", "buy_price": 20.0, "sell_price": 19.0},
        ]

        expected_stats = {
            "total_trades": 2,
            "winning_trades": 1,
            "losing_trades": 1,
            "win_rate": 0.5,
            "profit_factor": 1.0,
        }
        mock_backtest_adapter.get_trade_statistics = AsyncMock(return_value=expected_stats)

        # Act
        from app.api.endpoints.backtest import TradeStatisticsRequest
        request = TradeStatisticsRequest(trades=trades)
        result = await get_trade_statistics(request)

        # Assert
        assert result["code"] == 200
        assert result["message"] == "交易统计完成"
        assert result["data"]["total_trades"] == 2
        assert result["data"]["win_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_get_trade_statistics_empty(self, mock_backtest_adapter):
        """测试空交易统计"""
        # Arrange
        expected_stats = {"total_trades": 0, "win_rate": 0.0}
        mock_backtest_adapter.get_trade_statistics = AsyncMock(return_value=expected_stats)

        # Act
        from app.api.endpoints.backtest import TradeStatisticsRequest
        request = TradeStatisticsRequest(trades=[])
        result = await get_trade_statistics(request)

        # Assert
        assert result["code"] == 200
        assert result["data"]["total_trades"] == 0


class TestBacktestRequestValidation:
    """测试请求模型验证"""

    def test_backtest_request_valid(self):
        """测试有效请求"""
        # Act
        request = BacktestRequest(
            stock_codes=["000001"],
            start_date="2023-01-01",
            end_date="2023-12-31",
            strategy_params={},
            initial_capital=1000000.0,
        )

        # Assert
        assert request.stock_codes == ["000001"]
        assert request.initial_capital == 1000000.0

    def test_backtest_request_invalid_capital(self):
        """测试无效资金"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            BacktestRequest(
                stock_codes=["000001"],
                start_date="2023-01-01",
                end_date="2023-12-31",
                strategy_params={},
                initial_capital=-1000.0,  # 负数资金
            )

    def test_backtest_request_empty_stock_codes(self):
        """测试空股票代码"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            BacktestRequest(
                stock_codes=[],  # 空列表
                start_date="2023-01-01",
                end_date="2023-12-31",
                strategy_params={},
                initial_capital=1000000.0,
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
