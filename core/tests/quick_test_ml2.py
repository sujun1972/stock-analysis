"""
快速测试 ML-2 多因子加权模型增强功能

运行此脚本验证新功能是否正常工作
"""

import sys
sys.path.insert(0, '/Volumes/MacDriver/stock-analysis')

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

from core.src.strategies.three_layer.selectors.ml_selector import MLSelector


def test_normalization_methods():
    """测试归一化方法"""
    print("\n" + "="*60)
    print("测试 1: 归一化方法")
    print("="*60)

    # 创建测试数据
    dates = pd.date_range(start="2023-01-01", periods=60, freq="D")
    prices_df = pd.DataFrame({
        'A': np.linspace(100, 130, 60),
        'B': 100 + np.sin(np.linspace(0, 4 * np.pi, 60)) * 10,
        'C': np.linspace(120, 100, 60)
    }, index=dates)

    methods = ['z_score', 'min_max', 'rank', 'none']

    for method in methods:
        selector = MLSelector(params={
            'features': 'momentum_20d,rsi_14d',
            'normalization_method': method,
            'top_n': 2
        })

        try:
            selected = selector.select(dates[-1], prices_df)
            print(f"  ✅ {method:10s}: 选出 {len(selected)} 只股票")
        except Exception as e:
            print(f"  ❌ {method:10s}: 失败 - {e}")


def test_factor_weights():
    """测试因子权重"""
    print("\n" + "="*60)
    print("测试 2: 因子权重")
    print("="*60)

    # 创建测试数据
    dates = pd.date_range(start="2023-01-01", periods=60, freq="D")
    prices_df = pd.DataFrame({
        'A': np.linspace(100, 130, 60),
        'B': 100 + np.sin(np.linspace(0, 4 * np.pi, 60)) * 10,
        'C': np.linspace(120, 100, 60)
    }, index=dates)

    # 配置因子权重
    weights_config = json.dumps({
        "momentum_20d": 0.6,
        "rsi_14d": 0.4
    })

    try:
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'features': 'momentum_20d,rsi_14d',
            'factor_weights': weights_config,
            'top_n': 2
        })

        selected = selector.select(dates[-1], prices_df)

        print(f"  ✅ 因子权重解析: {selector.factor_weights}")
        print(f"  ✅ 选出股票: {selected}")

    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_factor_groups():
    """测试因子分组"""
    print("\n" + "="*60)
    print("测试 3: 因子分组")
    print("="*60)

    # 创建测试数据
    dates = pd.date_range(start="2023-01-01", periods=60, freq="D")
    prices_df = pd.DataFrame({
        'A': np.linspace(100, 130, 60),
        'B': 100 + np.sin(np.linspace(0, 4 * np.pi, 60)) * 10,
        'C': np.linspace(120, 100, 60)
    }, index=dates)

    # 配置因子分组
    groups_config = json.dumps({
        "momentum": ["momentum_5d", "momentum_20d"],
        "technical": ["rsi_14d"]
    })

    weights_config = json.dumps({
        "momentum": 0.6,
        "technical": 0.4
    })

    try:
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'features': 'momentum_5d,momentum_20d,rsi_14d',
            'factor_groups': groups_config,
            'group_weights': weights_config,
            'top_n': 2
        })

        selected = selector.select(dates[-1], prices_df)

        print(f"  ✅ 因子分组: {list(selector.factor_groups.keys())}")
        print(f"  ✅ 分组权重: {selector.group_weights}")
        print(f"  ✅ 选出股票: {selected}")

    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_parameter_count():
    """测试参数数量"""
    print("\n" + "="*60)
    print("测试 4: 参数数量")
    print("="*60)

    params = MLSelector.get_parameters()
    param_names = [p.name for p in params]

    print(f"  总参数数: {len(params)}")
    print(f"  参数列表:")
    for i, name in enumerate(param_names, 1):
        print(f"    {i:2d}. {name}")

    # 验证新增参数
    new_params = ['factor_weights', 'normalization_method', 'factor_groups', 'group_weights']
    missing = [p for p in new_params if p not in param_names]

    if not missing:
        print(f"  ✅ 所有新增参数都存在")
    else:
        print(f"  ❌ 缺少参数: {missing}")


def test_integration():
    """集成测试"""
    print("\n" + "="*60)
    print("测试 5: 集成测试（完整流程）")
    print("="*60)

    # 创建更大的测试数据集
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=120, freq="D")
    num_stocks = 20

    stocks = [f'STOCK_{i:02d}' for i in range(num_stocks)]
    returns = np.random.normal(0.001, 0.02, (120, num_stocks))
    prices = 100 * np.exp(np.cumsum(returns, axis=0))
    prices_df = pd.DataFrame(prices, index=dates, columns=stocks)

    # 配置复杂的因子分组
    groups_config = json.dumps({
        "momentum": ["momentum_5d", "momentum_20d", "momentum_60d"],
        "technical": ["rsi_14d", "rsi_28d"],
        "volatility": ["volatility_20d"]
    })

    weights_config = json.dumps({
        "momentum": 0.5,
        "technical": 0.3,
        "volatility": 0.2
    })

    try:
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'features': 'momentum_5d,momentum_20d,momentum_60d,rsi_14d,rsi_28d,volatility_20d',
            'factor_groups': groups_config,
            'group_weights': weights_config,
            'normalization_method': 'z_score',
            'filter_min_price': 50,
            'filter_max_price': 200,
            'top_n': 5
        })

        selected = selector.select(dates[-1], prices_df)

        print(f"  ✅ 候选股票数: {len(stocks)}")
        print(f"  ✅ 选出股票数: {len(selected)}")
        print(f"  ✅ 选出股票: {selected}")

        # 验证选出的股票价格在范围内
        current_prices = prices_df.loc[dates[-1]]
        selected_prices = current_prices[selected]
        print(f"  ✅ 选出股票价格范围: [{selected_prices.min():.2f}, {selected_prices.max():.2f}]")

    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """运行所有测试"""
    print("\n╔" + "="*58 + "╗")
    print("║" + " "*15 + "ML-2 多因子加权模型快速测试" + " "*15 + "║")
    print("╚" + "="*58 + "╝")

    try:
        test_parameter_count()
        test_normalization_methods()
        test_factor_weights()
        test_factor_groups()
        test_integration()

        print("\n" + "="*60)
        print("✅ 所有测试完成！")
        print("="*60)
        print("\n建议: 运行完整单元测试以验证所有功能")
        print("  cd core && python3 -m pytest tests/unit/strategies/three_layer/selectors/test_ml_selector.py -v")

    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
