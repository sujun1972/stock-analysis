"""
FeatureEngine使用示例

演示如何使用FeatureEngine计算股票特征

作者: Stock Analysis Team
创建时间: 2026-02-08
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.ml.feature_engine import FeatureEngine


def create_sample_data(n_stocks=5, n_days=100):
    """创建示例市场数据"""
    print("📊 创建示例数据...")

    stocks = [f'{i:06d}.SH' for i in range(600000, 600000 + n_stocks)]
    dates = pd.date_range('2024-01-01', periods=n_days, freq='D')

    data_list = []
    for stock in stocks:
        np.random.seed(hash(stock) % 2**32)
        base_price = 10.0
        prices = base_price + np.cumsum(np.random.randn(len(dates)) * 0.02)
        prices = np.maximum(prices, 1.0)

        for i, date in enumerate(dates):
            data_list.append({
                'date': date,
                'stock_code': stock,
                'open': prices[i] * (1 + np.random.randn() * 0.01),
                'high': prices[i] * (1 + abs(np.random.randn()) * 0.02),
                'low': prices[i] * (1 - abs(np.random.randn()) * 0.02),
                'close': prices[i],
                'volume': np.random.randint(1000000, 10000000)
            })

    df = pd.DataFrame(data_list)
    print(f"   ✓ 创建了 {n_stocks} 只股票, {n_days} 天的数据")
    return df, stocks


def example_basic_usage():
    """示例1: 基本使用"""
    print("\n" + "="*60)
    print("示例1: FeatureEngine基本使用")
    print("="*60)

    # 创建数据
    market_data, stocks = create_sample_data(n_stocks=3, n_days=100)

    # 创建FeatureEngine
    print("\n🔧 初始化FeatureEngine...")
    engine = FeatureEngine(
        feature_groups=['all'],  # 计算所有特征
        lookback_window=60,
        cache_enabled=True
    )
    print(f"   {engine}")

    # 计算特征
    print("\n⚙️  计算特征...")
    target_date = '2024-03-01'
    features = engine.calculate_features(
        stock_codes=stocks,
        market_data=market_data,
        date=target_date
    )

    print(f"\n✅ 计算完成!")
    print(f"   - 股票数量: {len(features)}")
    print(f"   - 特征数量: {len(features.columns)}")
    print(f"\n前5个特征:")
    print(features.iloc[:, :5])

    return engine, features


def example_specific_groups():
    """示例2: 指定特征组"""
    print("\n" + "="*60)
    print("示例2: 指定计算特定特征组")
    print("="*60)

    market_data, stocks = create_sample_data(n_stocks=2, n_days=100)

    # 只计算Alpha因子
    print("\n🔧 只计算Alpha因子...")
    engine_alpha = FeatureEngine(feature_groups=['alpha'])
    features_alpha = engine_alpha.calculate_features(
        stocks, market_data, '2024-03-01'
    )
    print(f"   Alpha特征数: {len(features_alpha.columns)}")

    # 只计算技术指标
    print("\n🔧 只计算技术指标...")
    engine_tech = FeatureEngine(feature_groups=['technical'])
    features_tech = engine_tech.calculate_features(
        stocks, market_data, '2024-03-01'
    )
    print(f"   技术指标数: {len(features_tech.columns)}")

    # 计算Alpha + 成交量特征
    print("\n🔧 计算Alpha + 成交量特征...")
    engine_mixed = FeatureEngine(feature_groups=['alpha', 'volume'])
    features_mixed = engine_mixed.calculate_features(
        stocks, market_data, '2024-03-01'
    )
    print(f"   混合特征数: {len(features_mixed.columns)}")


def example_cache_performance():
    """示例3: 缓存性能对比"""
    print("\n" + "="*60)
    print("示例3: 缓存性能对比")
    print("="*60)

    market_data, stocks = create_sample_data(n_stocks=5, n_days=100)

    # 使用缓存
    print("\n🚀 启用缓存...")
    engine_cached = FeatureEngine(cache_enabled=True)

    import time
    start = time.time()
    features1 = engine_cached.calculate_features(stocks, market_data, '2024-03-01')
    time1 = time.time() - start
    print(f"   首次计算: {time1:.3f}秒")

    start = time.time()
    features2 = engine_cached.calculate_features(stocks, market_data, '2024-03-01')
    time2 = time.time() - start
    print(f"   缓存读取: {time2:.3f}秒")
    print(f"   加速比: {time1/time2:.1f}x")

    # 不使用缓存
    print("\n🐌 不使用缓存...")
    engine_no_cache = FeatureEngine(cache_enabled=False)

    start = time.time()
    features3 = engine_no_cache.calculate_features(stocks, market_data, '2024-03-01')
    time3 = time.time() - start
    print(f"   计算时间: {time3:.3f}秒")


def example_batch_calculation():
    """示例4: 批量计算多个日期"""
    print("\n" + "="*60)
    print("示例4: 批量计算多个日期的特征")
    print("="*60)

    market_data, stocks = create_sample_data(n_stocks=3, n_days=100)

    engine = FeatureEngine(cache_enabled=True)

    # 计算多个日期
    dates = ['2024-02-15', '2024-03-01', '2024-03-15']

    print("\n⚙️  批量计算...")
    all_features = {}
    for date in dates:
        features = engine.calculate_features(stocks, market_data, date)
        all_features[date] = features
        print(f"   ✓ {date}: {len(features)} 股票 × {len(features.columns)} 特征")

    print(f"\n✅ 批量计算完成! 缓存条目: {len(engine._cache)}")


def example_feature_inspection():
    """示例5: 特征检查"""
    print("\n" + "="*60)
    print("示例5: 特征检查与分析")
    print("="*60)

    market_data, stocks = create_sample_data(n_stocks=3, n_days=100)

    engine = FeatureEngine()
    features = engine.calculate_features(stocks, market_data, '2024-03-01')

    print("\n📋 特征统计:")
    print(f"   - 特征总数: {len(features.columns)}")
    print(f"   - 缺失值数: {features.isna().sum().sum()}")
    print(f"   - 无穷值数: {np.isinf(features.select_dtypes(include=[np.number])).sum().sum()}")

    print("\n📊 特征分布:")
    print(features.describe().iloc[:3])  # 只显示count, mean, std

    print("\n🏷️  特征列名示例 (前10个):")
    feature_names = engine.get_feature_names()
    for i, name in enumerate(feature_names[:10], 1):
        print(f"   {i}. {name}")

    if len(feature_names) > 10:
        print(f"   ... (共 {len(feature_names)} 个特征)")


def main():
    """主函数"""
    print("\n" + "🎯 " + "="*58)
    print("🎯  FeatureEngine 使用示例")
    print("🎯 " + "="*58)

    try:
        # 运行所有示例
        example_basic_usage()
        example_specific_groups()
        example_cache_performance()
        example_batch_calculation()
        example_feature_inspection()

        print("\n" + "="*60)
        print("✅ 所有示例运行成功!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
