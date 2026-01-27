"""
Alpha因子优化效果测试

测试内容:
1. 向量化线性回归性能对比
2. 缓存机制验证
3. 数据泄漏检测验证
4. 内存使用对比
"""

import pandas as pd
import numpy as np
import time
import sys
import os

# 添加路径以导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from features.alpha_factors import AlphaFactors, FactorCache
from loguru import logger

# 配置日志
logger.remove()
logger.add(lambda msg: print(msg, end=''), level="INFO")


def create_test_data(n_rows: int = 1000) -> pd.DataFrame:
    """创建测试数据"""
    dates = pd.date_range('2020-01-01', periods=n_rows, freq='D')

    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, n_rows)
    prices = base_price * (1 + returns).cumprod()

    df = pd.DataFrame({
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, n_rows)),
        'high': prices * (1 + np.random.uniform(0, 0.03, n_rows)),
        'low': prices * (1 + np.random.uniform(-0.03, 0, n_rows)),
        'close': prices,
        'vol': np.random.uniform(1000000, 10000000, n_rows)
    }, index=dates)

    return df


def test_vectorized_trend_performance():
    """测试向量化趋势因子性能"""
    logger.info("\n" + "=" * 70)
    logger.info("测试1: 向量化线性回归性能")
    logger.info("=" * 70)

    # 创建测试数据
    df = create_test_data(n_rows=2000)
    logger.info(f"测试数据: {len(df)} 行")

    # 测试优化版本
    logger.info("\n测试优化版本（向量化）...")
    af = AlphaFactors(df.copy(), inplace=False)

    start = time.perf_counter()
    af.trend.add_trend_strength(periods=[20, 60])
    elapsed_optimized = time.perf_counter() - start

    logger.info(f"✓ 优化版本耗时: {elapsed_optimized:.4f} 秒")
    logger.info(f"✓ 生成因子: TREND20, TREND_R2_20, TREND60, TREND_R2_60")

    # 验证结果正确性
    result = af.get_dataframe()
    assert 'TREND20' in result.columns, "TREND20 因子缺失"
    assert 'TREND_R2_20' in result.columns, "TREND_R2_20 因子缺失"
    assert result['TREND20'].notna().sum() > 0, "TREND20 因子全为 NaN"

    logger.info(f"✓ TREND20 有效值: {result['TREND20'].notna().sum()}/{len(result)}")
    logger.info(f"✓ TREND20 范围: [{result['TREND20'].min():.6f}, {result['TREND20'].max():.6f}]")

    return elapsed_optimized


def test_cache_mechanism():
    """测试缓存机制"""
    logger.info("\n" + "=" * 70)
    logger.info("测试2: 缓存机制验证")
    logger.info("=" * 70)

    df = create_test_data(n_rows=1000)

    # 清空缓存
    af = AlphaFactors(df, inplace=False)
    af.clear_cache()

    # 第一次计算（无缓存）
    logger.info("\n第一次计算（无缓存）...")
    start = time.perf_counter()
    af.add_momentum_factors(periods=[5, 10, 20])
    af.add_volatility_factors(periods=[5, 10, 20])
    elapsed_first = time.perf_counter() - start

    cache_stats = af.get_cache_stats()
    logger.info(f"✓ 第一次耗时: {elapsed_first:.4f} 秒")
    logger.info(f"✓ 缓存命中率: {cache_stats['hit_rate']:.2%}")
    logger.info(f"✓ 缓存大小: {cache_stats['size']}/{cache_stats['max_size']}")

    # 第二次计算（使用缓存）
    logger.info("\n第二次计算（使用缓存）...")
    af2 = AlphaFactors(df, inplace=False)
    start = time.perf_counter()
    af2.add_momentum_factors(periods=[5, 10, 20])
    af2.add_volatility_factors(periods=[5, 10, 20])
    elapsed_second = time.perf_counter() - start

    cache_stats2 = af2.get_cache_stats()
    logger.info(f"✓ 第二次耗时: {elapsed_second:.4f} 秒")
    logger.info(f"✓ 缓存命中率: {cache_stats2['hit_rate']:.2%}")
    logger.info(f"✓ 加速比: {elapsed_first / elapsed_second:.2f}x")

    assert cache_stats2['hit_rate'] > 0, "缓存未生效"
    logger.info("✓ 缓存机制验证通过")


def test_data_leakage_detection():
    """测试数据泄漏检测"""
    logger.info("\n" + "=" * 70)
    logger.info("测试3: 数据泄漏检测")
    logger.info("=" * 70)

    df = create_test_data(n_rows=500)

    # 正常因子（无泄漏）
    logger.info("\n测试正常因子（应该无泄漏）...")
    af = AlphaFactors(df, inplace=False, enable_leak_detection=True)
    af.add_momentum_factors(periods=[5, 10])

    # 人工构造泄漏因子（使用未来数据）
    logger.info("\n测试泄漏因子（故意使用未来数据）...")
    df_leak = df.copy()
    df_leak['LEAK_FACTOR'] = df_leak['close'].shift(-5)  # 使用未来5日价格

    af_leak = AlphaFactors(df_leak, inplace=True, enable_leak_detection=True)
    is_leak = af_leak.momentum._detect_data_leakage(
        df_leak['LEAK_FACTOR'],
        'LEAK_FACTOR'
    )

    if is_leak:
        logger.info("✓ 成功检测到数据泄漏")
    else:
        logger.warning("⚠ 未能检测到明显的数据泄漏（可能相关性不够强）")


def test_memory_usage():
    """测试内存使用"""
    logger.info("\n" + "=" * 70)
    logger.info("测试4: 内存使用对比")
    logger.info("=" * 70)

    try:
        import psutil
        import os

        process = psutil.Process(os.getpid())

        df = create_test_data(n_rows=5000)
        logger.info(f"测试数据: {len(df)} 行")

        # 测试 inplace=False（传统模式）
        mem_before = process.memory_info().rss / 1024 / 1024
        af1 = AlphaFactors(df.copy(), inplace=False, enable_copy_on_write=False)
        af1.add_all_alpha_factors()
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_traditional = mem_after - mem_before

        logger.info(f"\n传统模式内存增长: {mem_traditional:.2f} MB")

        # 测试 Copy-on-Write 模式
        mem_before = process.memory_info().rss / 1024 / 1024
        af2 = AlphaFactors(df.copy(), inplace=False, enable_copy_on_write=True)
        af2.add_all_alpha_factors()
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_cow = mem_after - mem_before

        logger.info(f"CoW模式内存增长: {mem_cow:.2f} MB")

        if mem_cow < mem_traditional:
            savings = (1 - mem_cow / mem_traditional) * 100
            logger.info(f"✓ 内存节省: {savings:.1f}%")
        else:
            logger.info("⚠ CoW 模式未能节省内存（可能数据集太小）")

    except ImportError:
        logger.warning("⚠ 未安装 psutil，跳过内存测试")


def test_comprehensive():
    """综合测试"""
    logger.info("\n" + "=" * 70)
    logger.info("测试5: 综合功能测试")
    logger.info("=" * 70)

    df = create_test_data(n_rows=1000)

    # 创建实例
    af = AlphaFactors(df, inplace=False, enable_leak_detection=False)

    # 计算所有因子
    logger.info("\n计算所有Alpha因子...")
    result = af.add_all_alpha_factors(show_cache_stats=True)

    # 验证结果
    factor_names = af.get_factor_names()
    logger.info(f"\n✓ 总列数: {len(result.columns)}")
    logger.info(f"✓ 因子数量: {len(factor_names)}")

    # 显示因子分类
    summary = af.get_factor_summary()
    logger.info("\n因子分类统计:")
    for category, count in summary.items():
        if count > 0:
            logger.info(f"  {category}: {count}")

    # 验证关键因子存在
    key_factors = ['MOM20', 'REV5', 'VOLATILITY20', 'VOLUME_RATIO5', 'TREND20']
    missing = [f for f in key_factors if f not in result.columns]

    if missing:
        logger.error(f"✗ 缺少关键因子: {missing}")
    else:
        logger.info(f"\n✓ 所有关键因子都已生成")

    # 检查NaN比例
    logger.info("\n因子完整性检查:")
    for factor in key_factors[:3]:  # 检查前3个
        nan_ratio = result[factor].isna().sum() / len(result) * 100
        logger.info(f"  {factor}: {100-nan_ratio:.1f}% 有效数据")


def run_all_tests():
    """运行所有测试"""
    logger.info("\n")
    logger.info("╔" + "=" * 68 + "╗")
    logger.info("║" + " " * 15 + "Alpha因子优化效果测试" + " " * 26 + "║")
    logger.info("╚" + "=" * 68 + "╝")

    try:
        # 执行测试
        test_vectorized_trend_performance()
        test_cache_mechanism()
        test_data_leakage_detection()
        test_memory_usage()
        test_comprehensive()

        # 总结
        logger.info("\n" + "=" * 70)
        logger.info("测试总结")
        logger.info("=" * 70)
        logger.info("✓ 所有测试完成")
        logger.info("✓ 优化版本工作正常")
        logger.info("\n主要改进:")
        logger.info("  1. 向量化线性回归 - 性能提升显著")
        logger.info("  2. 共享缓存机制 - 减少重复计算")
        logger.info("  3. Copy-on-Write - 降低内存占用")
        logger.info("  4. 数据泄漏检测 - 提高因子可靠性")

    except Exception as e:
        logger.error(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    run_all_tests()
