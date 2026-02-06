"""
ML-4 因子库集成使用示例

展示如何使用 MLSelector 的完整特征库功能（125+ 因子）
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.strategies.three_layer.selectors.ml_selector import MLSelector
from loguru import logger


def generate_sample_data():
    """生成示例数据"""
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    stocks = [f'stock_{i:03d}' for i in range(50)]

    np.random.seed(42)
    prices_data = {}
    for stock in stocks:
        base_price = 100
        returns = np.random.randn(200) * 0.02
        prices = base_price * (1 + returns).cumprod()
        prices_data[stock] = prices

    prices = pd.DataFrame(prices_data, index=dates)
    return prices, dates


def example_1_basic_usage():
    """示例1: 基础用法 - 使用完整特征库"""
    logger.info("\n" + "=" * 60)
    logger.info("示例1: 基础用法")
    logger.info("=" * 60)

    prices, dates = generate_sample_data()

    # 创建MLSelector（完整特征库模式）
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 10,
        'use_feature_engine': True,  # 使用完整特征库
        'features': 'momentum_20d,rsi_14d,volatility_20d'
    })

    # 执行选股
    select_date = dates[150]
    selected_stocks = selector.select(select_date, prices)

    logger.info(f"选股日期: {select_date.date()}")
    logger.info(f"选出股票: {len(selected_stocks)} 只")
    logger.info(f"股票列表: {selected_stocks[:5]}...")


def example_2_wildcard_all_alpha():
    """示例2: 使用通配符 - 所有Alpha因子"""
    logger.info("\n" + "=" * 60)
    logger.info("示例2: 使用所有Alpha因子")
    logger.info("=" * 60)

    prices, dates = generate_sample_data()

    # 使用 alpha:* 通配符选择所有Alpha因子
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 10,
        'use_feature_engine': True,
        'features': 'alpha:*'  # 所有Alpha因子
    })

    logger.info(f"解析的特征数量: {len(selector.features)}")
    logger.info(f"特征列表: {selector.features}")

    # 执行选股
    select_date = dates[150]
    selected_stocks = selector.select(select_date, prices)

    logger.info(f"选出股票: {len(selected_stocks)} 只")


def example_3_wildcard_all_tech():
    """示例3: 使用通配符 - 所有技术指标"""
    logger.info("\n" + "=" * 60)
    logger.info("示例3: 使用所有技术指标")
    logger.info("=" * 60)

    prices, dates = generate_sample_data()

    # 使用 tech:* 通配符选择所有技术指标
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 10,
        'use_feature_engine': True,
        'features': 'tech:*'  # 所有技术指标
    })

    logger.info(f"解析的特征数量: {len(selector.features)}")
    logger.info(f"特征列表: {selector.features}")

    # 执行选股
    select_date = dates[150]
    selected_stocks = selector.select(select_date, prices)

    logger.info(f"选出股票: {len(selected_stocks)} 只")


def example_4_category_selection():
    """示例4: 类别选择 - 指定因子类别"""
    logger.info("\n" + "=" * 60)
    logger.info("示例4: 类别选择")
    logger.info("=" * 60)

    prices, dates = generate_sample_data()

    # 使用 alpha:momentum 和 tech:rsi 指定类别
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 10,
        'use_feature_engine': True,
        'features': 'alpha:momentum,alpha:reversal,tech:rsi,tech:macd'
    })

    logger.info(f"解析的特征数量: {len(selector.features)}")
    logger.info(f"特征列表: {selector.features}")

    # 执行选股
    select_date = dates[150]
    selected_stocks = selector.select(select_date, prices)

    logger.info(f"选出股票: {len(selected_stocks)} 只")
    logger.info(f"Top 5: {selected_stocks[:5]}")


def example_5_mixed_format():
    """示例5: 混合格式 - 通配符 + 具体特征"""
    logger.info("\n" + "=" * 60)
    logger.info("示例5: 混合格式")
    logger.info("=" * 60)

    prices, dates = generate_sample_data()

    # 混合使用：具体特征 + 类别通配符
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 10,
        'use_feature_engine': True,
        'features': 'momentum_20d,alpha:reversal,tech:ma'  # 混合格式
    })

    logger.info(f"解析的特征数量: {len(selector.features)}")
    logger.info(f"特征列表: {selector.features}")

    # 执行选股
    select_date = dates[150]
    selected_stocks = selector.select(select_date, prices)

    logger.info(f"选出股票: {len(selected_stocks)} 只")


def example_6_fast_vs_full():
    """示例6: 性能对比 - 快速模式 vs 完整特征库"""
    logger.info("\n" + "=" * 60)
    logger.info("示例6: 性能对比")
    logger.info("=" * 60)

    import time

    prices, dates = generate_sample_data()
    select_date = dates[150]

    # 快速模式
    logger.info("\n快速模式（简化特征）:")
    selector_fast = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 10,
        'use_feature_engine': False,  # 快速模式
        'features': 'momentum_20d,rsi_14d,volatility_20d'
    })

    start_time = time.time()
    selected_fast = selector_fast.select(select_date, prices)
    time_fast = time.time() - start_time

    logger.info(f"  耗时: {time_fast:.4f} 秒")
    logger.info(f"  选出: {len(selected_fast)} 只股票")

    # 完整特征库模式
    logger.info("\n完整特征库模式:")
    selector_full = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 10,
        'use_feature_engine': True,  # 完整特征库
        'features': 'momentum_20d,rsi_14d,volatility_20d'
    })

    start_time = time.time()
    selected_full = selector_full.select(select_date, prices)
    time_full = time.time() - start_time

    logger.info(f"  耗时: {time_full:.4f} 秒")
    logger.info(f"  选出: {len(selected_full)} 只股票")

    # 对比
    logger.info(f"\n性能对比:")
    logger.info(f"  快速模式: {time_fast:.4f} 秒")
    logger.info(f"  完整模式: {time_full:.4f} 秒")
    if time_fast > 0:
        logger.info(f"  速度比: {time_full / time_fast:.1f}x")


def example_7_with_factor_weights():
    """示例7: 自定义因子权重"""
    logger.info("\n" + "=" * 60)
    logger.info("示例7: 自定义因子权重")
    logger.info("=" * 60)

    import json

    prices, dates = generate_sample_data()

    # 设置因子权重
    factor_weights = json.dumps({
        "momentum_20d": 0.5,
        "rsi_14d": 0.3,
        "volatility_20d": 0.2
    })

    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 10,
        'use_feature_engine': True,
        'features': 'momentum_20d,rsi_14d,volatility_20d',
        'factor_weights': factor_weights,
        'normalization_method': 'z_score'
    })

    logger.info(f"因子权重: {factor_weights}")

    # 执行选股
    select_date = dates[150]
    selected_stocks = selector.select(select_date, prices)

    logger.info(f"选出股票: {len(selected_stocks)} 只")
    logger.info(f"Top 5: {selected_stocks[:5]}")


def example_8_feature_categories():
    """示例8: 查看可用的特征分类"""
    logger.info("\n" + "=" * 60)
    logger.info("示例8: 可用特征分类")
    logger.info("=" * 60)

    selector = MLSelector(params={})

    # Alpha因子分类
    logger.info("\nAlpha因子分类:")
    for category in ['momentum', 'reversal', 'volatility', 'volume', 'trend']:
        factors = selector._get_alpha_factors_by_category(category)
        logger.info(f"  {category:12s}: {len(factors):2d} 个因子 - {factors[:2]}...")

    # 技术指标分类
    logger.info("\n技术指标分类:")
    for category in ['ma', 'ema', 'rsi', 'macd', 'bb', 'atr', 'cci']:
        indicators = selector._get_tech_indicators_by_category(category)
        logger.info(f"  {category:12s}: {len(indicators):2d} 个指标 - {indicators[:2]}...")

    # 所有可用特征
    all_alpha = selector._get_all_alpha_factors()
    all_tech = selector._get_all_technical_indicators()

    logger.info(f"\n总计:")
    logger.info(f"  Alpha因子: {len(all_alpha)} 个")
    logger.info(f"  技术指标: {len(all_tech)} 个")
    logger.info(f"  合计: {len(all_alpha) + len(all_tech)} 个特征")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("ML-4 因子库集成使用示例")
    logger.info("=" * 60)

    try:
        # 运行所有示例
        example_1_basic_usage()
        example_2_wildcard_all_alpha()
        example_3_wildcard_all_tech()
        example_4_category_selection()
        example_5_mixed_format()
        example_6_fast_vs_full()
        example_7_with_factor_weights()
        example_8_feature_categories()

        # 总结
        logger.info("\n" + "=" * 60)
        logger.success("✅ 所有示例运行成功！")
        logger.info("=" * 60)

        logger.info("\n使用建议:")
        logger.info("  1. 快速开发: use_feature_engine=False")
        logger.info("  2. 生产环境: use_feature_engine=True")
        logger.info("  3. 探索特征: 使用 'alpha:*' 或 'tech:*'")
        logger.info("  4. 精确控制: 指定具体特征列表")
        logger.info("  5. 混合使用: 结合通配符和具体特征")

    except Exception as e:
        logger.error(f"❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
