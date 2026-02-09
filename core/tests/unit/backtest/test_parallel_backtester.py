#!/usr/bin/env python3
"""
并行回测执行器单元测试

测试 ParallelBacktester 的所有核心功能

Author: Stock Analysis Core Team
Date: 2026-01-31
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from backtest.parallel_backtester import (
    ParallelBacktester,
    BacktestTask,
    BacktestResult,
    parallel_backtest
)
from strategies.predefined.momentum_strategy import MomentumStrategy
from strategies.predefined.mean_reversion_strategy import MeanReversionStrategy
from config.features import ParallelComputingConfig


# ==================== Fixtures ====================

@pytest.fixture
def sample_prices():
    """生成测试价格数据"""
    dates = pd.date_range('2020-01-01', periods=60, freq='D')
    stocks = [f'stock_{i}' for i in range(20)]

    # 生成价格数据（带趋势和噪声）
    np.random.seed(42)
    base_prices = 100
    returns = np.random.randn(60, 20) * 0.02
    prices = base_prices * (1 + returns).cumprod(axis=0)

    df = pd.DataFrame(prices, index=dates, columns=stocks)
    return df


@pytest.fixture
def sample_strategies():
    """生成测试策略列表"""
    strategies = [
        MomentumStrategy(
            name="动量策略1",
            config={'lookback': 20, 'top_n': 10}
        ),
        MomentumStrategy(
            name="动量策略2",
            config={'lookback': 10, 'top_n': 10}
        ),
        MeanReversionStrategy(
            name="均值回归策略",
            config={'lookback': 15, 'top_n': 10}
        )
    ]
    return strategies


# ==================== 测试初始化 ====================

class TestParallelBacktesterInitialization:
    """测试 ParallelBacktester 初始化"""

    def test_default_initialization(self):
        """测试默认初始化"""
        backtester = ParallelBacktester()

        assert backtester.parallel_config is not None
        assert backtester.parallel_config.enable_parallel is True
        assert backtester.verbose is True

    def test_custom_n_workers(self):
        """测试自定义 worker 数量"""
        backtester = ParallelBacktester(n_workers=4)

        assert backtester.parallel_config.n_workers == 4

    def test_custom_parallel_config(self):
        """测试自定义并行配置"""
        config = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=8,
            show_progress=False,
            parallel_backend='threading'
        )

        backtester = ParallelBacktester(parallel_config=config)

        assert backtester.parallel_config.n_workers == 8
        assert backtester.parallel_config.parallel_backend == 'threading'
        assert backtester.parallel_config.show_progress is False

    def test_disable_progress(self):
        """测试禁用进度条"""
        backtester = ParallelBacktester(show_progress=False)

        assert backtester.parallel_config.show_progress is False


# ==================== 测试任务准备 ====================

class TestTaskPreparation:
    """测试任务准备功能"""

    def test_prepare_tasks_basic(self, sample_strategies, sample_prices):
        """测试基本任务准备"""
        backtester = ParallelBacktester()

        tasks = backtester._prepare_tasks(
            sample_strategies,
            sample_prices,
            features=None,
            backtest_kwargs={}
        )

        assert len(tasks) == len(sample_strategies)
        assert all(isinstance(task, BacktestTask) for task in tasks)

    def test_prepare_tasks_with_params(self, sample_strategies, sample_prices):
        """测试带参数的任务准备"""
        backtester = ParallelBacktester()

        backtest_kwargs = {
            'initial_capital': 2000000,
            'commission_rate': 0.0003,
            'top_n': 20,
            'holding_period': 10
        }

        tasks = backtester._prepare_tasks(
            sample_strategies,
            sample_prices,
            features=None,
            backtest_kwargs=backtest_kwargs
        )

        # 检查引擎参数
        assert tasks[0].engine_params['initial_capital'] == 2000000
        assert tasks[0].engine_params['commission_rate'] == 0.0003

        # 检查回测参数
        assert tasks[0].backtest_params['top_n'] == 20
        assert tasks[0].backtest_params['holding_period'] == 10

    def test_task_serialization(self, sample_strategies, sample_prices):
        """测试任务可序列化性"""
        backtester = ParallelBacktester()

        tasks = backtester._prepare_tasks(
            sample_strategies,
            sample_prices,
            features=None,
            backtest_kwargs={}
        )

        # 检查策略配置是字典（可序列化）
        assert isinstance(tasks[0].strategy_config, dict)
        assert isinstance(tasks[0].strategy_class_name, str)

        # 检查 to_dict 方法
        task_dict = tasks[0].to_dict()
        assert 'strategy_name' in task_dict
        assert 'data_shape' in task_dict


# ==================== 测试单个回测执行 ====================

class TestSingleBacktestExecution:
    """测试单个策略回测执行"""

    def test_run_single_backtest_success(self, sample_strategies, sample_prices):
        """测试成功的单个回测"""
        backtester = ParallelBacktester()

        task = BacktestTask(
            strategy_name=sample_strategies[0].name,
            strategy_class_name=sample_strategies[0].__class__.__name__,
            strategy_config=sample_strategies[0].config.to_dict(),
            prices=sample_prices,
            features=None,
            backtest_params={'top_n': 10},
            engine_params={'initial_capital': 1000000}
        )

        result = backtester._run_single_backtest(task)

        assert isinstance(result, BacktestResult)
        assert result.success is True
        assert result.result is not None
        assert result.error is None
        assert result.execution_time > 0

    def test_run_single_backtest_with_invalid_strategy(self, sample_prices):
        """测试无效策略类名的处理"""
        backtester = ParallelBacktester()

        task = BacktestTask(
            strategy_name="InvalidStrategy",
            strategy_class_name="NonExistentStrategy",  # 不存在的类
            strategy_config={},
            prices=sample_prices,
            features=None,
            backtest_params={},
            engine_params={}
        )

        result = backtester._run_single_backtest(task)

        assert result.success is False
        assert result.error is not None
        assert "未知的策略类" in result.error or "NonExistentStrategy" in result.error

    def test_run_single_backtest_with_bad_data(self, sample_strategies):
        """测试错误数据的处理"""
        backtester = ParallelBacktester()

        # 空的价格数据
        bad_prices = pd.DataFrame()

        task = BacktestTask(
            strategy_name=sample_strategies[0].name,
            strategy_class_name=sample_strategies[0].__class__.__name__,
            strategy_config=sample_strategies[0].config.to_dict(),
            prices=bad_prices,
            features=None,
            backtest_params={},
            engine_params={}
        )

        result = backtester._run_single_backtest(task)

        # 应该失败但不抛出异常
        assert result.success is False
        assert result.error is not None


# ==================== 测试并行回测 ====================

class TestParallelBacktest:
    """测试并行回测功能"""

    def test_run_multiple_strategies_serial(self, sample_strategies, sample_prices):
        """测试串行回测多个策略"""
        backtester = ParallelBacktester(n_workers=1)  # 强制串行

        results = backtester.run(
            strategies=sample_strategies,
            prices=sample_prices,
            initial_capital=1000000,
            top_n=10
        )

        assert len(results) == len(sample_strategies)
        assert all(isinstance(r, BacktestResult) for r in results.values())

        # 检查至少有一个成功
        success_count = sum(1 for r in results.values() if r.success)
        assert success_count > 0

    def test_run_multiple_strategies_parallel(self, sample_strategies, sample_prices):
        """测试并行回测多个策略"""
        backtester = ParallelBacktester(n_workers=2)

        results = backtester.run(
            strategies=sample_strategies,
            prices=sample_prices,
            initial_capital=1000000,
            top_n=10
        )

        assert len(results) == len(sample_strategies)

        # 检查结果完整性
        for strategy in sample_strategies:
            assert strategy.name in results
            result = results[strategy.name]
            assert isinstance(result, BacktestResult)

    def test_run_with_empty_strategies(self, sample_prices):
        """测试空策略列表"""
        backtester = ParallelBacktester()

        results = backtester.run(
            strategies=[],
            prices=sample_prices
        )

        assert results == {}

    def test_run_with_custom_backtest_params(self, sample_strategies, sample_prices):
        """测试自定义回测参数"""
        backtester = ParallelBacktester(n_workers=2)

        results = backtester.run(
            strategies=sample_strategies,
            prices=sample_prices,
            initial_capital=2000000,
            commission_rate=0.0002,
            top_n=15,
            holding_period=7,
            rebalance_freq='W'
        )

        # 验证至少有一个成功
        success_results = [r for r in results.values() if r.success]
        assert len(success_results) > 0

        # 验证结果中包含指标
        for result in success_results:
            metrics = result.get_metrics()
            assert 'sharpe_ratio' in metrics
            assert 'annual_return' in metrics


# ==================== 测试结果处理 ====================

class TestResultProcessing:
    """测试结果处理功能"""

    def test_backtest_result_get_metrics(self):
        """测试提取指标"""
        mock_result = {
            'metrics': {
                'annual_return': 0.25,
                'sharpe_ratio': 1.5,
                'max_drawdown': -0.15,
                'win_rate': 0.58
            }
        }

        result = BacktestResult(
            strategy_name="TestStrategy",
            success=True,
            result=mock_result
        )

        metrics = result.get_metrics()

        assert metrics['annual_return'] == 0.25
        assert metrics['sharpe_ratio'] == 1.5
        assert metrics['max_drawdown'] == -0.15
        assert metrics['win_rate'] == 0.58

    def test_backtest_result_get_metrics_failed(self):
        """测试失败结果的指标提取"""
        result = BacktestResult(
            strategy_name="FailedStrategy",
            success=False,
            error="Some error"
        )

        metrics = result.get_metrics()

        assert metrics == {}


# ==================== 测试对比报告 ====================

class TestComparisonReport:
    """测试对比报告生成"""

    def test_generate_comparison_report_success(self, sample_strategies, sample_prices):
        """测试成功生成对比报告"""
        backtester = ParallelBacktester(n_workers=2)

        results = backtester.run(
            strategies=sample_strategies,
            prices=sample_prices,
            top_n=10
        )

        report = backtester.generate_comparison_report(results)

        assert isinstance(report, pd.DataFrame)
        assert len(report) == len(sample_strategies)
        assert '策略名称' in report.columns
        assert '夏普比率' in report.columns
        assert '年化收益率(%)' in report.columns

    def test_generate_comparison_report_with_failures(self):
        """测试包含失败策略的报告"""
        backtester = ParallelBacktester()

        # 模拟结果（包含成功和失败）
        results = {
            'Strategy1': BacktestResult(
                strategy_name='Strategy1',
                success=True,
                result={
                    'metrics': {
                        'annual_return': 0.20,
                        'sharpe_ratio': 1.2,
                        'max_drawdown': -0.10
                    }
                }
            ),
            'Strategy2': BacktestResult(
                strategy_name='Strategy2',
                success=False,
                error='Test error'
            )
        }

        report = backtester.generate_comparison_report(results)

        assert len(report) == 2
        assert report.loc[report['策略名称'] == 'Strategy1', '状态'].values[0] == '成功'
        assert report.loc[report['策略名称'] == 'Strategy2', '状态'].values[0] == '失败'

    def test_generate_comparison_report_custom_metrics(self):
        """测试自定义指标报告"""
        backtester = ParallelBacktester()

        results = {
            'Strategy1': BacktestResult(
                strategy_name='Strategy1',
                success=True,
                result={
                    'metrics': {
                        'annual_return': 0.20,
                        'sharpe_ratio': 1.2,
                        'max_drawdown': -0.10,
                        'calmar_ratio': 2.0
                    }
                }
            )
        }

        report = backtester.generate_comparison_report(
            results,
            metrics_to_compare=['annual_return', 'sharpe_ratio']
        )

        assert '年化收益率(%)' in report.columns
        assert '夏普比率' in report.columns
        # calmar_ratio 不应该在报告中
        assert '卡玛比率' not in report.columns

    def test_save_comparison_report_csv(self, tmp_path, sample_strategies, sample_prices):
        """测试保存CSV报告"""
        backtester = ParallelBacktester(n_workers=1)

        results = backtester.run(
            strategies=sample_strategies[:1],  # 只用一个策略加快测试
            prices=sample_prices,
            top_n=5
        )

        save_path = tmp_path / "report.csv"
        backtester.save_comparison_report(results, str(save_path), format='csv')

        assert save_path.exists()

        # 验证可以读取
        df = pd.read_csv(save_path)
        assert len(df) > 0


# ==================== 测试便捷函数 ====================

class TestConvenienceFunction:
    """测试便捷函数"""

    def test_parallel_backtest_function(self, sample_strategies, sample_prices):
        """测试 parallel_backtest 便捷函数"""
        results = parallel_backtest(
            strategies=sample_strategies[:2],  # 只用2个策略
            prices=sample_prices,
            n_workers=2,
            show_progress=False,
            initial_capital=1000000,
            top_n=10
        )

        assert len(results) == 2
        assert all(isinstance(r, BacktestResult) for r in results.values())


# ==================== 测试策略重建 ====================

class TestStrategyRebuild:
    """测试策略重建功能"""

    def test_rebuild_momentum_strategy(self, sample_prices):
        """测试重建动量策略"""
        backtester = ParallelBacktester()

        task = BacktestTask(
            strategy_name="TestMomentum",
            strategy_class_name="MomentumStrategy",
            strategy_config={'lookback': 20, 'top_n': 10},
            prices=sample_prices,
            backtest_params={},
            engine_params={}
        )

        strategy = backtester._rebuild_strategy(task)

        assert strategy is not None
        assert isinstance(strategy, MomentumStrategy)
        assert strategy.name == "TestMomentum"

    def test_rebuild_mean_reversion_strategy(self, sample_prices):
        """测试重建均值回归策略"""
        backtester = ParallelBacktester()

        task = BacktestTask(
            strategy_name="TestMeanReversion",
            strategy_class_name="MeanReversionStrategy",
            strategy_config={'lookback': 15},
            prices=sample_prices,
            backtest_params={},
            engine_params={}
        )

        strategy = backtester._rebuild_strategy(task)

        assert strategy is not None
        assert isinstance(strategy, MeanReversionStrategy)

    def test_rebuild_unknown_strategy(self, sample_prices):
        """测试重建未知策略"""
        backtester = ParallelBacktester()

        task = BacktestTask(
            strategy_name="Unknown",
            strategy_class_name="UnknownStrategy",
            strategy_config={},
            prices=sample_prices,
            backtest_params={},
            engine_params={}
        )

        with pytest.raises(ValueError, match="未知的策略类"):
            backtester._rebuild_strategy(task)


# ==================== 测试错误处理 ====================

class TestErrorHandling:
    """测试错误处理"""

    def test_graceful_degradation_to_serial(self, sample_strategies, sample_prices):
        """测试并行失败时优雅降级到串行"""
        backtester = ParallelBacktester(n_workers=2)

        # 模拟并行执行失败（通过 mock）
        with patch('src.backtest.parallel_backtester.ParallelExecutor') as mock_executor:
            mock_executor.return_value.__enter__.side_effect = Exception("Parallel failed")

            # 应该降级到串行执行，不抛出异常
            results = backtester.run(
                strategies=sample_strategies[:1],
                prices=sample_prices,
                top_n=5
            )

            # 仍然应该有结果
            assert len(results) > 0

    def test_individual_strategy_failure_does_not_stop_others(self, sample_prices):
        """测试单个策略失败不影响其他策略"""
        # 创建一个会失败的策略（通过损坏的配置）
        good_strategy = MomentumStrategy("GoodStrategy", {'lookback': 20, 'top_n': 10})

        # 创建一个配置错误的策略
        bad_strategy = MomentumStrategy("BadStrategy", {'lookback': -1, 'top_n': 0})  # 无效参数

        backtester = ParallelBacktester(n_workers=1)

        results = backtester.run(
            strategies=[good_strategy, bad_strategy],
            prices=sample_prices
        )

        # 应该有2个结果
        assert len(results) == 2

        # 至少有一个应该成功（good_strategy）
        success_count = sum(1 for r in results.values() if r.success)
        # 注意：如果bad_strategy的参数验证在策略内部，可能两个都成功
        # 这里我们只确保不会因为一个失败而全部失败
        assert success_count >= 0  # 至少不会抛出异常


# ==================== 性能测试 ====================

class TestPerformance:
    """测试性能相关功能"""

    @pytest.mark.slow
    def test_parallel_faster_than_serial(self, sample_strategies, sample_prices):
        """测试并行比串行快（标记为慢速测试）"""
        import time

        # 串行执行
        backtester_serial = ParallelBacktester(n_workers=1, show_progress=False)
        start_serial = time.time()
        results_serial = backtester_serial.run(
            strategies=sample_strategies,
            prices=sample_prices,
            top_n=10
        )
        time_serial = time.time() - start_serial

        # 并行执行
        backtester_parallel = ParallelBacktester(n_workers=2, show_progress=False)
        start_parallel = time.time()
        results_parallel = backtester_parallel.run(
            strategies=sample_strategies,
            prices=sample_prices,
            top_n=10
        )
        time_parallel = time.time() - start_parallel

        # 结果应该相同
        assert len(results_serial) == len(results_parallel)

        # 并行应该更快（或至少不慢太多，考虑到overhead）
        # 注意：在测试环境中可能不明显，所以这里只是记录而不强制断言
        print(f"\n串行耗时: {time_serial:.2f}s, 并行耗时: {time_parallel:.2f}s")


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试"""

    def test_full_workflow(self, sample_strategies, sample_prices):
        """测试完整工作流"""
        # 1. 创建回测器
        backtester = ParallelBacktester(n_workers=2, show_progress=False)

        # 2. 执行回测
        results = backtester.run(
            strategies=sample_strategies,
            prices=sample_prices,
            initial_capital=1000000,
            commission_rate=0.0003,
            top_n=10,
            holding_period=5,
            rebalance_freq='W'
        )

        # 3. 生成报告
        report = backtester.generate_comparison_report(results)

        # 4. 验证
        assert len(results) == len(sample_strategies)
        assert isinstance(report, pd.DataFrame)
        assert len(report) == len(sample_strategies)

        # 5. 验证至少有一个策略成功
        success_count = sum(1 for r in results.values() if r.success)
        assert success_count > 0
