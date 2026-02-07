"""
MLSelector 使用示例

演示如何使用机器学习选股器（MLSelector）进行股票选择
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 导入 MLSelector
from src.strategies.three_layer.selectors import MLSelector


def generate_sample_data(num_stocks=20, num_days=252):
    """生成模拟市场数据"""
    dates = pd.date_range(start='2023-01-01', periods=num_days, freq='D')

    np.random.seed(42)
    stocks = {}

    for i in range(num_stocks):
        # 随机游走模拟股价
        returns = np.random.normal(0.0005, 0.02, num_days)
        prices = 100 * np.exp(np.cumsum(returns))
        stocks[f"STOCK_{i:02d}"] = prices

    return pd.DataFrame(stocks, index=dates)


def example_1_basic_usage():
    """示例1: 基础用法 - 多因子加权选股"""
    print("=" * 60)
    print("示例1: 基础用法 - 多因子加权选股")
    print("=" * 60)

    # 生成测试数据
    prices = generate_sample_data(num_stocks=20, num_days=252)
    test_date = prices.index[-1]

    # 创建 MLSelector
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 10,
        'features': 'momentum_20d,rsi_14d,volatility_20d'
    })

    # 选股
    selected_stocks = selector.select(test_date, prices)

    print(f"\n选股日期: {test_date.date()}")
    print(f"选股模式: 多因子加权")
    print(f"使用特征: momentum_20d, rsi_14d, volatility_20d")
    print(f"选出股票数: {len(selected_stocks)}")
    print(f"选中股票: {', '.join(selected_stocks)}")
    print()


def example_2_custom_features():
    """示例2: 自定义特征集"""
    print("=" * 60)
    print("示例2: 自定义特征集")
    print("=" * 60)

    prices = generate_sample_data(num_stocks=15, num_days=180)
    test_date = prices.index[-1]

    # 使用更多特征
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 8,
        'features': 'momentum_5d,momentum_10d,momentum_20d,momentum_60d,rsi_14d,rsi_28d,volatility_20d,ma_cross_20d'
    })

    selected_stocks = selector.select(test_date, prices)

    print(f"\n选股日期: {test_date.date()}")
    print(f"使用特征数量: 8")
    print(f"选出股票数: {len(selected_stocks)}")
    print(f"选中股票: {', '.join(selected_stocks)}")
    print()


def example_3_price_filtering():
    """示例3: 价格过滤"""
    print("=" * 60)
    print("示例3: 价格过滤")
    print("=" * 60)

    # 生成不同价格区间的股票
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')

    prices = pd.DataFrame({
        'LOW_STOCK_01': np.linspace(5, 8, 100),      # 低价股
        'LOW_STOCK_02': np.linspace(6, 9, 100),
        'MID_STOCK_01': np.linspace(50, 60, 100),    # 中价股
        'MID_STOCK_02': np.linspace(45, 55, 100),
        'HIGH_STOCK_01': np.linspace(200, 220, 100), # 高价股
        'HIGH_STOCK_02': np.linspace(180, 210, 100),
    }, index=dates)

    test_date = dates[-1]

    # 只选择中价股 (10-100元)
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 10,
        'features': 'momentum_20d,rsi_14d',
        'filter_min_price': 10,    # 最低10元
        'filter_max_price': 100,   # 最高100元
    })

    selected_stocks = selector.select(test_date, prices)

    print(f"\n选股日期: {test_date.date()}")
    print(f"价格过滤: 10元 - 100元")
    print(f"选出股票数: {len(selected_stocks)}")
    print(f"选中股票: {', '.join(selected_stocks)}")
    print("\n价格检查:")
    for stock in selected_stocks:
        price = prices.loc[test_date, stock]
        print(f"  {stock}: {price:.2f}元")
    print()


def example_4_default_features():
    """示例4: 使用默认特征集"""
    print("=" * 60)
    print("示例4: 使用默认特征集")
    print("=" * 60)

    prices = generate_sample_data(num_stocks=25, num_days=150)
    test_date = prices.index[-1]

    # 不指定features参数，使用默认特征集
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 12,
        'features': ''  # 空字符串表示使用默认特征
    })

    selected_stocks = selector.select(test_date, prices)

    print(f"\n选股日期: {test_date.date()}")
    print(f"使用默认特征集（11个特征）:")
    print(f"  - 动量: momentum_5d, momentum_10d, momentum_20d, momentum_60d")
    print(f"  - RSI: rsi_14d, rsi_28d")
    print(f"  - 波动率: volatility_20d, volatility_60d")
    print(f"  - 均线: ma_cross_20d, ma_cross_60d")
    print(f"  - ATR: atr_14d")
    print(f"\n选出股票数: {len(selected_stocks)}")
    print(f"选中股票: {', '.join(selected_stocks)}")
    print()


def example_5_comparison_different_periods():
    """示例5: 比较不同时期的选股结果"""
    print("=" * 60)
    print("示例5: 比较不同时期的选股结果")
    print("=" * 60)

    prices = generate_sample_data(num_stocks=30, num_days=252)

    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 5,
        'features': 'momentum_20d,rsi_14d,volatility_20d'
    })

    # 选择不同日期
    dates_to_test = [
        prices.index[60],   # 第60天
        prices.index[120],  # 第120天
        prices.index[180],  # 第180天
        prices.index[-1],   # 最后一天
    ]

    print("\n不同时期选股结果对比:")
    for date in dates_to_test:
        selected = selector.select(date, prices)
        print(f"\n{date.date()}: {', '.join(selected[:3])}... (共{len(selected)}只)")
    print()


def example_6_feature_exploration():
    """示例6: 探索单一特征的选股效果"""
    print("=" * 60)
    print("示例6: 探索单一特征的选股效果")
    print("=" * 60)

    prices = generate_sample_data(num_stocks=20, num_days=120)
    test_date = prices.index[-1]

    # 测试不同单一特征
    features_to_test = [
        'momentum_20d',
        'rsi_14d',
        'volatility_20d',
        'ma_cross_20d',
    ]

    print(f"\n选股日期: {test_date.date()}")
    print(f"Top N: 5\n")

    for feature in features_to_test:
        selector = MLSelector(params={
            'top_n': 5,
            'features': feature
        })

        selected = selector.select(test_date, prices)
        print(f"{feature:20s}: {', '.join(selected)}")
    print()


def example_7_lightgbm_mode_without_model():
    """示例7: LightGBM模式（无模型，自动回退）"""
    print("=" * 60)
    print("示例7: LightGBM模式（无模型，自动回退）")
    print("=" * 60)

    prices = generate_sample_data(num_stocks=15, num_days=100)
    test_date = prices.index[-1]

    # 尝试使用LightGBM模式，但不提供模型路径
    # 会自动回退到多因子加权模式
    selector = MLSelector(params={
        'mode': 'lightgbm_ranker',
        'model_path': '',  # 未提供模型
        'top_n': 8,
        'features': 'momentum_20d,rsi_14d'
    })

    selected_stocks = selector.select(test_date, prices)

    print(f"\n选股日期: {test_date.date()}")
    print(f"尝试模式: lightgbm_ranker")
    print(f"实际模式: multi_factor_weighted (自动回退)")
    print(f"选出股票数: {len(selected_stocks)}")
    print(f"选中股票: {', '.join(selected_stocks)}")
    print()


def example_8_integration_with_strategy():
    """示例8: 与三层架构策略集成"""
    print("=" * 60)
    print("示例8: 与三层架构策略集成")
    print("=" * 60)

    from src.strategies.three_layer.entries import ImmediateEntry
    from src.strategies.three_layer.exits import FixedStopLossExit
    from src.strategies.three_layer.base import StrategyComposer

    prices = generate_sample_data(num_stocks=30, num_days=252)

    # 组合策略
    composer = StrategyComposer(
        selector=MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 15,
            'features': 'momentum_20d,rsi_14d,volatility_20d,ma_cross_20d'
        }),
        entry=ImmediateEntry(),
        exit_strategy=FixedStopLossExit(params={'stop_loss_pct': -5.0}),
        rebalance_freq='W'  # 周频调仓
    )

    print("\n三层架构策略配置:")
    print(f"  选股器: MLSelector (多因子加权)")
    print(f"  入场策略: ImmediateEntry (立即入场)")
    print(f"  退出策略: FixedStopLossExit (止损-5%)")
    print(f"  调仓频率: 每周")
    print(f"\n选股器配置:")
    print(f"  Top N: 15")
    print(f"  特征: 4个 (momentum_20d, rsi_14d, volatility_20d, ma_cross_20d)")

    # 演示选股
    test_date = prices.index[-1]
    selected = composer.selector.select(test_date, prices)
    print(f"\n当前选中股票: {len(selected)}只")
    print(f"示例: {', '.join(selected[:5])}...")
    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("MLSelector 使用示例集合")
    print("=" * 60 + "\n")

    # 运行所有示例
    example_1_basic_usage()
    example_2_custom_features()
    example_3_price_filtering()
    example_4_default_features()
    example_5_comparison_different_periods()
    example_6_feature_exploration()
    example_7_lightgbm_mode_without_model()
    example_8_integration_with_strategy()

    print("=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
