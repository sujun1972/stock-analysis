"""
独立的测试运行脚本
避免导入冲突问题
"""
import sys
from pathlib import Path

# 添加正确的路径
core_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(core_dir / 'src'))

import unittest
import numpy as np

# 导入测试模块
from models.model_evaluator import (
    ModelEvaluator,
    MetricsCalculator,
    ResultFormatter,
    EvaluationConfig,
    evaluate_model,
    InvalidInputError,
    InsufficientDataError,
    filter_valid_pairs
)

print("="*70)
print("模型评估器测试套件")
print("="*70)
print(f"测试路径: {core_dir}")
print()

# 快速功能测试
def quick_functional_test():
    """快速功能测试"""
    print("执行快速功能测试...")

    # 生成测试数据
    np.random.seed(42)
    n_samples = 1000
    true_signal = np.random.randn(n_samples)
    predictions = true_signal + np.random.randn(n_samples) * 0.5
    actual_returns = true_signal * 0.02 + np.random.randn(n_samples) * 0.01

    # 测试评估器
    evaluator = ModelEvaluator()
    metrics = evaluator.evaluate_regression(predictions, actual_returns, verbose=False)

    print(f"✓ 回归评估成功 - 计算了 {len(metrics)} 个指标")
    print(f"  IC: {metrics['ic']:.4f}")
    print(f"  Rank IC: {metrics['rank_ic']:.4f}")
    print(f"  Long-Short Return: {metrics['long_short_return']:.4f}")

    # 测试时间序列评估
    predictions_by_date = {}
    actuals_by_date = {}
    for i in range(20):
        date = f"2024-01-{i+1:02d}"
        np.random.seed(i)
        n = 100
        signal = np.random.randn(n)
        predictions_by_date[date] = signal + np.random.randn(n) * 0.3
        actuals_by_date[date] = signal * 0.015 + np.random.randn(n) * 0.01

    ts_metrics = evaluator.evaluate_timeseries(
        predictions_by_date, actuals_by_date, verbose=False
    )
    print(f"✓ 时间序列评估成功 - IC均值: {ts_metrics['ic_mean']:.4f}, IC IR: {ts_metrics['ic_ir']:.2f}")

    # 测试异常处理
    try:
        evaluator.evaluate_regression(None, actual_returns)
        print("✗ 异常处理测试失败 - 应该抛出 InvalidInputError")
    except InvalidInputError:
        print("✓ 异常处理测试成功 - 正确抛出 InvalidInputError")

    # 测试配置
    config = EvaluationConfig(n_groups=10, top_pct=0.1)
    evaluator_custom = ModelEvaluator(config=config)
    custom_metrics = evaluator_custom.evaluate_regression(predictions, actual_returns, verbose=False)
    group_count = sum(1 for k in custom_metrics.keys() if k.startswith('group_'))
    print(f"✓ 自定义配置测试成功 - 使用了 {group_count} 个分组")

    # 测试向后兼容性
    static_ic = ModelEvaluator.calculate_ic(predictions, actual_returns)
    print(f"✓ 向后兼容性测试成功 - 静态方法 IC: {static_ic:.4f}")

    print()
    return True


# 性能测试
def performance_test():
    """性能测试"""
    print("执行性能测试...")
    import time

    # 大数据集测试
    np.random.seed(42)
    n_large = 100000
    predictions = np.random.randn(n_large)
    actual_returns = predictions * 0.02 + np.random.randn(n_large) * 0.01

    evaluator = ModelEvaluator()
    start_time = time.time()
    metrics = evaluator.evaluate_regression(predictions, actual_returns, verbose=False)
    elapsed = time.time() - start_time

    print(f"✓ 大数据集测试 ({n_large:,} 样本) - 用时: {elapsed:.2f}秒")

    # 时间序列性能测试
    predictions_by_date = {}
    actuals_by_date = {}
    for i in range(100):
        date = f"2024-{(i//30)+1:02d}-{(i%30)+1:02d}"
        np.random.seed(i)
        predictions_by_date[date] = np.random.randn(1000)
        actuals_by_date[date] = np.random.randn(1000) * 0.01

    start_time = time.time()
    ts_metrics = evaluator.evaluate_timeseries(
        predictions_by_date, actuals_by_date, verbose=False
    )
    elapsed = time.time() - start_time

    print(f"✓ 时间序列测试 (100天 x 1000股票) - 用时: {elapsed:.2f}秒")
    print()
    return True


# 边界测试
def boundary_test():
    """边界测试"""
    print("执行边界测试...")

    # NaN 处理
    predictions = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
    actual_returns = np.array([0.01, 0.02, 0.03, np.nan, 0.05])
    valid_preds, valid_returns = filter_valid_pairs(predictions, actual_returns)
    assert len(valid_preds) == 3, "NaN 过滤失败"
    print("✓ NaN 处理测试成功")

    # Inf 处理
    predictions = np.array([1.0, np.inf, 3.0, -np.inf, 5.0])
    actual_returns = np.array([0.01, 0.02, np.inf, 0.04, 0.05])
    valid_preds, valid_returns = filter_valid_pairs(predictions, actual_returns)
    assert len(valid_preds) == 2, "Inf 过滤失败"
    print("✓ Inf 处理测试成功")

    # 空数据处理
    try:
        filter_valid_pairs(np.array([]), np.array([]))
        print("✗ 空数据处理失败 - 应该抛出异常")
    except InsufficientDataError:
        print("✓ 空数据处理测试成功")

    # 数据不足处理
    try:
        filter_valid_pairs(np.array([1.0]), np.array([0.01]), min_samples=2)
        print("✗ 数据不足处理失败 - 应该抛出异常")
    except InsufficientDataError:
        print("✓ 数据不足处理测试成功")

    print()
    return True


# 指标准确性测试
def accuracy_test():
    """指标准确性测试"""
    print("执行指标准确性测试...")

    # 完美相关测试
    np.random.seed(42)
    n = 1000
    true_signal = np.random.randn(n)
    predictions = true_signal
    actual_returns = true_signal * 0.02

    ic = MetricsCalculator.calculate_ic(predictions, actual_returns)
    assert ic > 0.99, f"完美相关 IC 应该接近 1.0，实际: {ic:.4f}"
    print(f"✓ 完美相关测试成功 - IC: {ic:.4f}")

    # 无相关测试
    np.random.seed(42)
    predictions = np.random.randn(n)
    actual_returns = np.random.randn(n) * 0.01

    ic = MetricsCalculator.calculate_ic(predictions, actual_returns)
    assert abs(ic) < 0.2, f"无相关 IC 应该接近 0，实际: {ic:.4f}"
    print(f"✓ 无相关测试成功 - IC: {ic:.4f}")

    # 负相关测试
    np.random.seed(42)
    predictions = np.random.randn(n)
    actual_returns = -predictions * 0.02 + np.random.randn(n) * 0.01

    ic = MetricsCalculator.calculate_ic(predictions, actual_returns)
    assert ic < -0.5, f"负相关 IC 应该为负，实际: {ic:.4f}"
    print(f"✓ 负相关测试成功 - IC: {ic:.4f}")

    # Sharpe 比率测试
    returns = np.random.randn(252) * 0.01 + 0.002
    sharpe = MetricsCalculator.calculate_sharpe_ratio(returns)
    assert sharpe > 0, "正收益应该有正的 Sharpe 比率"
    print(f"✓ Sharpe 比率测试成功 - Sharpe: {sharpe:.2f}")

    # 最大回撤测试
    returns = np.array([0.01] * 10)
    max_dd = MetricsCalculator.calculate_max_drawdown(returns)
    assert max_dd < 0.01, "持续上涨应该几乎没有回撤"
    print(f"✓ 最大回撤测试成功 - MaxDD: {max_dd:.4f}")

    print()
    return True


# 运行所有测试
def run_all_tests():
    """运行所有测试"""
    all_passed = True

    try:
        all_passed &= quick_functional_test()
    except Exception as e:
        print(f"✗ 功能测试失败: {e}")
        all_passed = False

    try:
        all_passed &= performance_test()
    except Exception as e:
        print(f"✗ 性能测试失败: {e}")
        all_passed = False

    try:
        all_passed &= boundary_test()
    except Exception as e:
        print(f"✗ 边界测试失败: {e}")
        all_passed = False

    try:
        all_passed &= accuracy_test()
    except Exception as e:
        print(f"✗ 准确性测试失败: {e}")
        all_passed = False

    print("="*70)
    if all_passed:
        print("✓ 所有测试通过!")
    else:
        print("✗ 部分测试失败")
    print("="*70)

    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
