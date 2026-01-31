#!/usr/bin/env python3
"""
性能基准测试框架

本模块提供性能测试的基础设施,包括:
- 性能阈值定义 (PerformanceThresholds)
- 性能测试基类 (PerformanceBenchmarkBase)
- 性能报告生成器 (PerformanceReporter)
- 测试数据生成器

性能阈值基于REFACTORING_PLAN.md定义:
- 特征计算: Alpha因子<60s, 技术指标<30s, 单因子<0.5s
- 回测: 向量化<3s, 多头<2s, 市场中性<5s
- 数据库: 单查询<10ms, 批量100股<500ms
- 模型: LightGBM<10s, GRU(CPU)<60s, GRU(GPU)<5s

作者: Stock Analysis Team
创建: 2026-01-31
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any
import warnings

import pytest
import pandas as pd
import numpy as np

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

# 抑制警告
warnings.filterwarnings('ignore')


# ==================== 数据生成工具 ====================


def generate_ohlcv_data(n_stocks: int = 100, n_days: int = 250, seed: int = 42) -> pd.DataFrame:
    """
    生成OHLCV测试数据

    Args:
        n_stocks: 股票数量
        n_days: 交易天数
        seed: 随机种子

    Returns:
        包含多只股票OHLCV数据的DataFrame
    """
    np.random.seed(seed)
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')

    all_data = []

    for stock_id in range(n_stocks):
        # 生成价格序列（几何布朗运动）
        returns = np.random.normal(0.0005, 0.02, n_days)
        price = 100 * (1 + returns).cumprod()

        # 生成OHLC
        daily_volatility = np.abs(np.random.normal(0, 0.01, n_days))

        df = pd.DataFrame({
            'stock_code': f'{stock_id:06d}',
            'date': dates,
            'open': price * (1 + np.random.uniform(-0.01, 0.01, n_days)),
            'high': price * (1 + daily_volatility),
            'low': price * (1 - daily_volatility),
            'close': price,
            'vol': np.random.uniform(1e6, 1e7, n_days),
        })

        all_data.append(df)

    return pd.concat(all_data, ignore_index=True)


def generate_single_stock_data(n_days: int = 250, seed: int = 42) -> pd.DataFrame:
    """
    生成单只股票的OHLCV数据

    Args:
        n_days: 交易天数
        seed: 随机种子

    Returns:
        单只股票的DataFrame
    """
    np.random.seed(seed)
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')

    # 生成价格序列
    returns = np.random.normal(0.0005, 0.02, n_days)
    price = 100 * (1 + returns).cumprod()

    daily_volatility = np.abs(np.random.normal(0, 0.01, n_days))

    return pd.DataFrame({
        'open': price * (1 + np.random.uniform(-0.01, 0.01, n_days)),
        'high': price * (1 + daily_volatility),
        'low': price * (1 - daily_volatility),
        'close': price,
        'vol': np.random.uniform(1e6, 1e7, n_days),
    }, index=dates)


def generate_features_data(n_samples: int = 100000, n_features: int = 125, seed: int = 42) -> pd.DataFrame:
    """
    生成特征数据用于模型训练测试

    Args:
        n_samples: 样本数量
        n_features: 特征数量
        seed: 随机种子

    Returns:
        特征DataFrame
    """
    np.random.seed(seed)

    feature_names = [f'feature_{i}' for i in range(n_features)]
    data = np.random.randn(n_samples, n_features)

    return pd.DataFrame(data, columns=feature_names)


def generate_target_data(n_samples: int = 100000, seed: int = 42) -> pd.Series:
    """
    生成目标变量(收益率)

    Args:
        n_samples: 样本数量
        seed: 随机种子

    Returns:
        目标Series
    """
    np.random.seed(seed)
    return pd.Series(np.random.normal(0, 0.02, n_samples), name='target')


# ==================== Pytest Fixtures ====================


@pytest.fixture(scope='session')
def benchmark_data_large():
    """大规模基准测试数据: 1000股×250天"""
    return generate_ohlcv_data(n_stocks=1000, n_days=250)


@pytest.fixture(scope='session')
def benchmark_data_medium():
    """中等规模基准测试数据: 100股×250天"""
    return generate_ohlcv_data(n_stocks=100, n_days=250)


@pytest.fixture(scope='session')
def single_stock_data():
    """单只股票数据: 250天"""
    return generate_single_stock_data(n_days=250)


@pytest.fixture(scope='session')
def single_stock_data_long():
    """单只股票长期数据: 1000天"""
    return generate_single_stock_data(n_days=1000)


@pytest.fixture(scope='session')
def model_training_data():
    """模型训练数据: 10万样本×125特征"""
    X = generate_features_data(n_samples=100000, n_features=125)
    y = generate_target_data(n_samples=100000)
    return X, y


@pytest.fixture(scope='session')
def model_training_data_small():
    """小规模模型训练数据: 1万样本×125特征"""
    X = generate_features_data(n_samples=10000, n_features=125)
    y = generate_target_data(n_samples=10000)
    return X, y


# ==================== 性能阈值配置 ====================


class PerformanceThresholds:
    """性能阈值定义（基于REFACTORING_PLAN.md）"""

    # 特征计算阈值
    ALPHA_FACTORS_ALL = 60.0  # 125个Alpha因子计算 <60秒
    TECHNICAL_INDICATORS_ALL = 30.0  # 60+技术指标 <30秒
    SINGLE_FACTOR_AVG = 0.5  # 单因子平均 <0.5秒

    # 回测阈值
    BACKTEST_VECTORIZED = 3.0  # 向量化回测 <3秒 (1000股×250天)
    BACKTEST_LONG_ONLY = 2.0  # 多头策略 <2秒
    BACKTEST_MARKET_NEUTRAL = 5.0  # 市场中性 <5秒

    # 数据库阈值
    DB_SINGLE_QUERY = 0.01  # 单股票查询 <10ms
    DB_BATCH_QUERY_100 = 0.5  # 批量查询100股 <500ms
    DB_FEATURE_WRITE_1000 = 1.0  # 特征写入1000行 <1秒

    # 模型训练阈值
    LIGHTGBM_TRAIN_100K = 10.0  # LightGBM训练10万样本 <10秒
    GRU_TRAIN_CPU = 60.0  # GRU训练CPU <60秒
    GRU_TRAIN_GPU = 5.0  # GRU训练GPU <5秒


# ==================== 性能测试基类 ====================


class PerformanceBenchmarkBase:
    """性能基准测试基类"""

    def assert_performance(
        self,
        elapsed: float,
        threshold: float,
        operation: str,
        details: Dict[str, Any] = None
    ):
        """
        断言性能满足要求

        Args:
            elapsed: 实际耗时(秒)
            threshold: 阈值(秒)
            operation: 操作描述
            details: 额外信息
        """
        details_str = ""
        if details:
            details_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            details_str = f" ({details_str})"

        message = (
            f"性能回归检测失败: {operation}{details_str}\n"
            f"实际耗时: {elapsed:.3f}s > 阈值: {threshold:.3f}s\n"
            f"性能劣化: {(elapsed/threshold - 1) * 100:.1f}%"
        )

        assert elapsed < threshold, message

        # 输出性能统计
        margin = (1 - elapsed/threshold) * 100
        print(f"✓ {operation}: {elapsed:.3f}s (余量: {margin:.1f}%){details_str}")

    def benchmark_operation(self, operation_func, *args, **kwargs):
        """
        执行操作并测量时间

        Args:
            operation_func: 要测试的函数
            *args, **kwargs: 函数参数

        Returns:
            (result, elapsed_time)
        """
        start = time.time()
        result = operation_func(*args, **kwargs)
        elapsed = time.time() - start
        return result, elapsed


# ==================== 性能报告生成 ====================


class PerformanceReporter:
    """性能测试报告生成器"""

    def __init__(self):
        self.results = []

    def add_result(
        self,
        category: str,
        test_name: str,
        elapsed: float,
        threshold: float,
        passed: bool,
        details: Dict[str, Any] = None
    ):
        """添加测试结果"""
        self.results.append({
            'category': category,
            'test_name': test_name,
            'elapsed': elapsed,
            'threshold': threshold,
            'passed': passed,
            'margin_pct': (1 - elapsed/threshold) * 100 if passed else (elapsed/threshold - 1) * 100,
            'details': details or {}
        })

    def generate_report(self) -> str:
        """生成性能报告"""
        if not self.results:
            return "没有性能测试结果"

        # 按类别分组
        categories = {}
        for result in self.results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)

        # 生成报告
        lines = [
            "=" * 80,
            "性能基准测试报告",
            "=" * 80,
            ""
        ]

        for category, results in categories.items():
            lines.append(f"\n【{category}】")
            lines.append("-" * 80)

            for r in results:
                status = "✓ PASS" if r['passed'] else "✗ FAIL"
                margin_str = f"{r['margin_pct']:+.1f}%" if r['passed'] else f"{r['margin_pct']:+.1f}%"

                lines.append(
                    f"{status} {r['test_name']}: "
                    f"{r['elapsed']:.3f}s / {r['threshold']:.3f}s "
                    f"(余量: {margin_str})"
                )

        # 汇总统计
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0

        lines.extend([
            "",
            "=" * 80,
            f"汇总: 总计 {total} 项, 通过 {passed} 项, 失败 {failed} 项, 通过率 {pass_rate:.1f}%",
            "=" * 80
        ])

        return "\n".join(lines)


# 全局报告器
performance_reporter = PerformanceReporter()


# ==================== 工具函数 ====================


def print_benchmark_header(title: str):
    """打印基准测试标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_benchmark_result(operation: str, elapsed: float, threshold: float):
    """打印基准测试结果"""
    passed = elapsed < threshold
    status = "✓ PASS" if passed else "✗ FAIL"
    margin = (1 - elapsed/threshold) * 100 if passed else (elapsed/threshold - 1) * 100
    margin_str = f"{margin:+.1f}%"

    print(f"{status} {operation}: {elapsed:.3f}s / {threshold:.3f}s (余量: {margin_str})")
