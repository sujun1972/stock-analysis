"""
MLSelector 多因子加权模型使用示例

本文件展示如何使用增强版的多因子加权模型进行股票选择，包括：
1. 基础等权模型
2. 自定义因子权重模型
3. 因子分组加权模型
4. 不同归一化方法对比
5. 完整回测流程

作者: Claude Code
日期: 2026-02-06
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

# 导入核心模块
import sys
sys.path.insert(0, '/Volumes/MacDriver/stock-analysis')

from core.src.strategies.three_layer.selectors.ml_selector import MLSelector
from core.src.strategies.three_layer.entries import ImmediateEntry
from core.src.strategies.three_layer.exits import FixedStopLossExit


def create_sample_data(num_stocks=100, num_days=252):
    """
    创建模拟市场数据

    Args:
        num_stocks: 股票数量
        num_days: 交易日数量

    Returns:
        DataFrame(index=日期, columns=股票代码, values=价格)
    """
    np.random.seed(42)

    # 创建日期索引
    dates = pd.date_range(
        start=datetime.now() - timedelta(days=num_days),
        periods=num_days,
        freq='D'
    )

    # 创建股票代码
    stocks = [f'STOCK_{i:03d}' for i in range(num_stocks)]

    # 生成价格数据（随机游走）
    returns = np.random.normal(0.001, 0.02, (num_days, num_stocks))
    prices = 100 * np.exp(np.cumsum(returns, axis=0))

    df = pd.DataFrame(prices, index=dates, columns=stocks)

    return df


# ============================================
# 示例 1: 基础多因子加权（等权平均）
# ============================================
def example_1_basic_equal_weight():
    """
    示例1：基础多因子加权 - 等权平均

    特点：
    - 所有因子权重相等
    - Z-Score 归一化
    - 适合快速测试
    """
    print("=" * 60)
    print("示例 1: 基础多因子加权（等权平均）")
    print("=" * 60)

    # 创建测试数据
    prices = create_sample_data(num_stocks=50, num_days=120)

    # 创建选股器
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'features': 'momentum_20d,rsi_14d,volatility_20d,ma_cross_20d',
        'normalization_method': 'z_score',
        'top_n': 10
    })

    # 选股
    test_date = prices.index[-1]
    selected_stocks = selector.select(test_date, prices)

    print(f"\n选股日期: {test_date.date()}")
    print(f"候选股票数: {len(prices.columns)}")
    print(f"选中股票数: {len(selected_stocks)}")
    print(f"选中股票: {selected_stocks[:5]}...")  # 显示前5只

    return selected_stocks


# ============================================
# 示例 2: 自定义因子权重
# ============================================
def example_2_custom_factor_weights():
    """
    示例2：自定义因子权重

    特点：
    - 动量因子权重 60%
    - RSI 指标权重 40%
    - 适合强调特定因子
    """
    print("\n" + "=" * 60)
    print("示例 2: 自定义因子权重")
    print("=" * 60)

    # 创建测试数据
    prices = create_sample_data(num_stocks=50, num_days=120)

    # 配置因子权重（动量权重更高）
    factor_weights = json.dumps({
        "momentum_20d": 0.6,  # 60% 权重
        "rsi_14d": 0.4        # 40% 权重
    })

    # 创建选股器
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'features': 'momentum_20d,rsi_14d',
        'factor_weights': factor_weights,
        'normalization_method': 'z_score',
        'top_n': 10
    })

    # 选股
    test_date = prices.index[-1]
    selected_stocks = selector.select(test_date, prices)

    print(f"\n因子权重配置:")
    print(f"  - momentum_20d: 60%")
    print(f"  - rsi_14d: 40%")
    print(f"\n选股日期: {test_date.date()}")
    print(f"选中股票数: {len(selected_stocks)}")
    print(f"选中股票: {selected_stocks[:5]}...")

    return selected_stocks


# ============================================
# 示例 3: 因子分组加权
# ============================================
def example_3_factor_groups():
    """
    示例3：因子分组加权

    特点：
    - 将因子分为3组：动量、技术、波动率
    - 组内等权，组间加权
    - 动量组 50%，技术组 30%，波动率组 20%
    """
    print("\n" + "=" * 60)
    print("示例 3: 因子分组加权")
    print("=" * 60)

    # 创建测试数据
    prices = create_sample_data(num_stocks=50, num_days=120)

    # 配置因子分组
    factor_groups = json.dumps({
        "momentum": ["momentum_5d", "momentum_20d", "momentum_60d"],
        "technical": ["rsi_14d", "rsi_28d", "ma_cross_20d"],
        "volatility": ["volatility_20d", "atr_14d"]
    })

    # 配置分组权重
    group_weights = json.dumps({
        "momentum": 0.5,    # 50% 权重
        "technical": 0.3,   # 30% 权重
        "volatility": 0.2   # 20% 权重
    })

    # 创建选股器
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'features': 'momentum_5d,momentum_20d,momentum_60d,rsi_14d,rsi_28d,ma_cross_20d,volatility_20d,atr_14d',
        'factor_groups': factor_groups,
        'group_weights': group_weights,
        'normalization_method': 'z_score',
        'top_n': 10
    })

    # 选股
    test_date = prices.index[-1]
    selected_stocks = selector.select(test_date, prices)

    print(f"\n因子分组配置:")
    print(f"  - 动量组 (50%): momentum_5d, momentum_20d, momentum_60d")
    print(f"  - 技术组 (30%): rsi_14d, rsi_28d, ma_cross_20d")
    print(f"  - 波动率组 (20%): volatility_20d, atr_14d")
    print(f"\n选股日期: {test_date.date()}")
    print(f"选中股票数: {len(selected_stocks)}")
    print(f"选中股票: {selected_stocks[:5]}...")

    return selected_stocks


# ============================================
# 示例 4: 不同归一化方法对比
# ============================================
def example_4_normalization_methods():
    """
    示例4：不同归一化方法对比

    对比4种归一化方法的选股结果：
    - z_score: Z-Score 标准化
    - min_max: Min-Max 归一化
    - rank: 排名归一化
    - none: 不归一化
    """
    print("\n" + "=" * 60)
    print("示例 4: 不同归一化方法对比")
    print("=" * 60)

    # 创建测试数据
    prices = create_sample_data(num_stocks=50, num_days=120)
    test_date = prices.index[-1]

    methods = ['z_score', 'min_max', 'rank', 'none']
    results = {}

    for method in methods:
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'features': 'momentum_20d,rsi_14d,volatility_20d',
            'normalization_method': method,
            'top_n': 10
        })

        selected_stocks = selector.select(test_date, prices)
        results[method] = selected_stocks

        print(f"\n{method.upper()} 归一化:")
        print(f"  选中股票: {selected_stocks[:3]}...")

    # 计算不同方法的重叠度
    print("\n不同方法的股票重叠分析:")
    for i, method1 in enumerate(methods):
        for method2 in methods[i+1:]:
            overlap = set(results[method1]) & set(results[method2])
            overlap_pct = len(overlap) / 10 * 100
            print(f"  {method1} vs {method2}: {len(overlap)}/10 ({overlap_pct:.0f}% 重叠)")

    return results


# ============================================
# 示例 5: 价格过滤 + 多因子加权
# ============================================
def example_5_with_price_filters():
    """
    示例5：价格过滤 + 多因子加权

    特点：
    - 过滤价格 < 5 元的股票
    - 过滤价格 > 200 元的股票
    - 然后进行多因子选股
    """
    print("\n" + "=" * 60)
    print("示例 5: 价格过滤 + 多因子加权")
    print("=" * 60)

    # 创建测试数据
    prices = create_sample_data(num_stocks=50, num_days=120)

    # 创建选股器（带价格过滤）
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'features': 'momentum_20d,rsi_14d,volatility_20d',
        'normalization_method': 'z_score',
        'filter_min_price': 50,   # 最低价格 50 元
        'filter_max_price': 150,  # 最高价格 150 元
        'top_n': 10
    })

    # 选股
    test_date = prices.index[-1]
    current_prices = prices.loc[test_date]

    print(f"\n价格过滤条件:")
    print(f"  - 最低价格: 50 元")
    print(f"  - 最高价格: 150 元")
    print(f"\n市场价格分布:")
    print(f"  - 平均价格: {current_prices.mean():.2f} 元")
    print(f"  - 价格范围: [{current_prices.min():.2f}, {current_prices.max():.2f}]")

    selected_stocks = selector.select(test_date, prices)

    print(f"\n选中股票数: {len(selected_stocks)}")
    if selected_stocks:
        selected_prices = current_prices[selected_stocks]
        print(f"选中股票价格范围: [{selected_prices.min():.2f}, {selected_prices.max():.2f}]")
        print(f"选中股票: {selected_stocks[:5]}...")

    return selected_stocks


# ============================================
# 示例 6: 完整回测流程
# ============================================
def example_6_complete_backtest():
    """
    示例6：完整回测流程

    展示如何将 MLSelector 集成到三层架构回测中
    """
    print("\n" + "=" * 60)
    print("示例 6: 完整回测流程（简化版）")
    print("=" * 60)

    # 创建测试数据
    prices = create_sample_data(num_stocks=50, num_days=252)

    # 配置多因子选股器
    factor_weights = json.dumps({
        "momentum_20d": 0.4,
        "rsi_14d": 0.3,
        "volatility_20d": 0.3
    })

    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'features': 'momentum_20d,rsi_14d,volatility_20d',
        'factor_weights': factor_weights,
        'normalization_method': 'z_score',
        'top_n': 10
    })

    # 模拟周度选股
    print("\n模拟周度选股:")
    rebalance_dates = prices.index[-60::5]  # 最近60天，每5天选一次

    all_selections = {}
    for date in rebalance_dates:
        selected = selector.select(date, prices)
        all_selections[date] = selected
        print(f"  {date.date()}: 选出 {len(selected)} 只股票")

    # 统计选股频率
    stock_counts = {}
    for selected in all_selections.values():
        for stock in selected:
            stock_counts[stock] = stock_counts.get(stock, 0) + 1

    # 最常被选中的股票
    top_stocks = sorted(stock_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"\n最常被选中的股票（前5名）:")
    for stock, count in top_stocks:
        print(f"  {stock}: 被选中 {count}/{len(rebalance_dates)} 次 ({count/len(rebalance_dates)*100:.1f}%)")

    return all_selections


# ============================================
# 示例 7: 高级配置 - 多策略组合
# ============================================
def example_7_multi_strategy_combination():
    """
    示例7：多策略组合

    创建3个不同配置的选股器，对比效果
    """
    print("\n" + "=" * 60)
    print("示例 7: 多策略组合")
    print("=" * 60)

    # 创建测试数据
    prices = create_sample_data(num_stocks=50, num_days=120)
    test_date = prices.index[-1]

    # 策略1: 动量导向（强调动量）
    selector_momentum = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'features': 'momentum_5d,momentum_20d,momentum_60d',
        'normalization_method': 'z_score',
        'top_n': 10
    })

    # 策略2: 技术指标导向
    selector_technical = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'features': 'rsi_14d,rsi_28d,ma_cross_20d',
        'normalization_method': 'min_max',
        'top_n': 10
    })

    # 策略3: 均衡配置
    groups = json.dumps({
        "momentum": ["momentum_20d"],
        "technical": ["rsi_14d"],
        "volatility": ["volatility_20d"]
    })
    weights = json.dumps({
        "momentum": 0.33,
        "technical": 0.33,
        "volatility": 0.34
    })

    selector_balanced = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'features': 'momentum_20d,rsi_14d,volatility_20d',
        'factor_groups': groups,
        'group_weights': weights,
        'normalization_method': 'rank',
        'top_n': 10
    })

    # 执行选股
    selected_momentum = selector_momentum.select(test_date, prices)
    selected_technical = selector_technical.select(test_date, prices)
    selected_balanced = selector_balanced.select(test_date, prices)

    print(f"\n策略1（动量导向）:")
    print(f"  选中股票: {selected_momentum[:3]}...")

    print(f"\n策略2（技术指标导向）:")
    print(f"  选中股票: {selected_technical[:3]}...")

    print(f"\n策略3（均衡配置）:")
    print(f"  选中股票: {selected_balanced[:3]}...")

    # 计算策略间重叠
    overlap_12 = set(selected_momentum) & set(selected_technical)
    overlap_13 = set(selected_momentum) & set(selected_balanced)
    overlap_23 = set(selected_technical) & set(selected_balanced)

    print(f"\n策略重叠分析:")
    print(f"  动量 ∩ 技术: {len(overlap_12)}/10 只")
    print(f"  动量 ∩ 均衡: {len(overlap_13)}/10 只")
    print(f"  技术 ∩ 均衡: {len(overlap_23)}/10 只")

    # 三策略共同选中的股票（高确定性）
    common = set(selected_momentum) & set(selected_technical) & set(selected_balanced)
    if common:
        print(f"\n三策略共同选中（高确定性）: {list(common)}")

    return {
        'momentum': selected_momentum,
        'technical': selected_technical,
        'balanced': selected_balanced
    }


# ============================================
# 示例 8: 参数敏感性分析
# ============================================
def example_8_parameter_sensitivity():
    """
    示例8：参数敏感性分析

    测试 top_n 参数对选股结果的影响
    """
    print("\n" + "=" * 60)
    print("示例 8: 参数敏感性分析")
    print("=" * 60)

    # 创建测试数据
    prices = create_sample_data(num_stocks=50, num_days=120)
    test_date = prices.index[-1]

    # 测试不同的 top_n 值
    top_n_values = [5, 10, 20, 30]
    results = {}

    for top_n in top_n_values:
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'features': 'momentum_20d,rsi_14d,volatility_20d',
            'normalization_method': 'z_score',
            'top_n': top_n
        })

        selected = selector.select(test_date, prices)
        results[top_n] = selected

        print(f"\ntop_n = {top_n}:")
        print(f"  选中股票数: {len(selected)}")
        print(f"  前3只: {selected[:3]}")

    # 分析稳定性（前10名在不同 top_n 下的稳定性）
    print("\n稳定性分析（前10名）:")
    top_10_base = set(results[10])
    for top_n in [5, 20, 30]:
        overlap = set(results[top_n][:10]) & top_10_base
        print(f"  top_n={top_n} 与 top_n=10 的重叠: {len(overlap)}/10")

    return results


# ============================================
# 主函数 - 运行所有示例
# ============================================
def main():
    """运行所有示例"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "MLSelector 多因子加权模型使用示例" + " " * 14 + "║")
    print("╚" + "=" * 58 + "╝")

    try:
        # 运行示例
        example_1_basic_equal_weight()
        example_2_custom_factor_weights()
        example_3_factor_groups()
        example_4_normalization_methods()
        example_5_with_price_filters()
        example_6_complete_backtest()
        example_7_multi_strategy_combination()
        example_8_parameter_sensitivity()

        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
