"""
完整的策略使用示例

演示从数据加载到回测的完整工作流程
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from loguru import logger

# 导入策略
from src.strategies import (
    MomentumStrategy,
    MeanReversionStrategy,
    MultiFactorStrategy,
    StrategyCombiner
)

# 导入回测引擎
from src.backtest.backtest_engine import BacktestEngine
from src.backtest.performance_analyzer import PerformanceAnalyzer

# 导入特征工程
from src.features.alpha_factors import AlphaFactors


def create_sample_data(n_days=252, n_stocks=20):
    """
    创建示例数据

    Args:
        n_days: 交易天数
        n_stocks: 股票数量

    Returns:
        prices_df, volumes_df
    """
    logger.info(f"\n创建示例数据: {n_days}天 × {n_stocks}只股票")

    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    stocks = [f'{i:06d}' for i in range(600000, 600000 + n_stocks)]

    # 模拟价格数据（带不同趋势）
    price_data = {}
    volume_data = {}

    for i, stock in enumerate(stocks):
        # 不同股票有不同的特征
        trend = np.random.choice([0.0005, 0.001, 0.0015, -0.0005, 0.0])
        volatility = np.random.choice([0.01, 0.02, 0.03])

        returns = trend + np.random.normal(0, volatility, n_days)
        prices = 10.0 * (1 + returns).cumprod()

        # 添加一些异常值（模拟涨停）
        if i < 3:
            prices[20:25] *= 1.1  # 连续上涨
        if i >= n_stocks - 3:
            prices[30:35] *= 0.9  # 连续下跌

        price_data[stock] = prices
        volume_data[stock] = np.random.uniform(1000000, 50000000, n_days)

    prices_df = pd.DataFrame(price_data, index=dates)
    volumes_df = pd.DataFrame(volume_data, index=dates)

    return prices_df, volumes_df


def calculate_features(prices_df, volumes_df):
    """
    计算Alpha因子

    Args:
        prices_df: 价格DataFrame
        volumes_df: 成交量DataFrame

    Returns:
        features_df: 因子DataFrame
    """
    logger.info("\n计算Alpha因子...")

    all_features = {}

    for stock in prices_df.columns:
        # 构造单只股票的OHLCV数据
        stock_df = pd.DataFrame({
            'close': prices_df[stock],
            'open': prices_df[stock] * (1 + np.random.uniform(-0.01, 0.01, len(prices_df))),
            'high': prices_df[stock] * (1 + np.random.uniform(0, 0.02, len(prices_df))),
            'low': prices_df[stock] * (1 + np.random.uniform(-0.02, 0, len(prices_df))),
            'vol': volumes_df[stock]
        }, index=prices_df.index)

        # 计算因子
        af = AlphaFactors(stock_df, inplace=False)
        features = af.add_all_alpha_factors(show_cache_stats=False)

        # 提取几个关键因子
        key_factors = ['MOM20', 'REV5', 'VOLATILITY20', 'VOLUME_RATIO5', 'TREND20']
        for factor in key_factors:
            if factor in features.columns:
                if factor not in all_features:
                    all_features[factor] = {}
                all_features[factor][stock] = features[factor]

    # 转换为多列格式
    features_dict = {}
    for factor, stock_data in all_features.items():
        for stock, values in stock_data.items():
            col_name = f"{factor}_{stock}"
            features_dict[col_name] = values

    features_df = pd.DataFrame(features_dict, index=prices_df.index)

    logger.success(f"✓ 因子计算完成: {features_df.shape[1]} 个因子")

    return features_df


def example_1_momentum_strategy():
    """示例1: 动量策略"""
    logger.info("\n" + "=" * 70)
    logger.info("示例1: 动量策略")
    logger.info("=" * 70)

    # 1. 创建数据
    prices, volumes = create_sample_data(n_days=100, n_stocks=10)

    # 2. 创建策略
    config = {
        'lookback_period': 20,
        'top_n': 3,
        'holding_period': 5,
        'filter_negative': True
    }
    strategy = MomentumStrategy('MOM20', config)

    # 3. 生成信号
    signals = strategy.generate_signals(prices, volumes=volumes)

    # 4. 回测
    engine = BacktestEngine(
        initial_capital=1000000,
        commission_rate=0.0003,
        verbose=True
    )

    results = strategy.backtest(engine, prices)

    # 5. 分析结果
    portfolio_value = results['portfolio_value']
    logger.info(f"\n回测结果:")
    logger.info(f"  初始资金: ¥{engine.initial_capital:,.0f}")
    logger.info(f"  最终资金: ¥{portfolio_value['total'].iloc[-1]:,.0f}")
    logger.info(f"  总收益率: {(portfolio_value['total'].iloc[-1] / engine.initial_capital - 1) * 100:.2f}%")

    return results


def example_2_mean_reversion_strategy():
    """示例2: 均值回归策略"""
    logger.info("\n" + "=" * 70)
    logger.info("示例2: 均值回归策略")
    logger.info("=" * 70)

    # 创建震荡市场数据
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    stocks = [f'{i:06d}' for i in range(600000, 600005)]

    price_data = {}
    for stock in stocks:
        t = np.arange(len(dates))
        # 震荡模式
        trend = 10 + 2 * np.sin(t * 2 * np.pi / 20)
        noise = np.random.normal(0, 0.3, len(dates))
        prices = trend + noise
        price_data[stock] = prices

    prices_df = pd.DataFrame(price_data, index=dates)

    # 创建策略
    config = {
        'lookback_period': 10,
        'z_score_threshold': -1.5,
        'top_n': 2,
        'holding_period': 3
    }
    strategy = MeanReversionStrategy('MR10', config)

    # 回测
    engine = BacktestEngine(initial_capital=500000, verbose=False)
    results = strategy.backtest(engine, prices_df)

    portfolio_value = results['portfolio_value']
    logger.info(f"\n回测结果:")
    logger.info(f"  总收益率: {(portfolio_value['total'].iloc[-1] / engine.initial_capital - 1) * 100:.2f}%")

    return results


def example_3_strategy_combination():
    """示例3: 策略组合"""
    logger.info("\n" + "=" * 70)
    logger.info("示例3: 策略组合（动量 + 均值回归）")
    logger.info("=" * 70)

    # 创建数据
    prices, volumes = create_sample_data(n_days=100, n_stocks=10)

    # 创建多个策略
    mom_strategy = MomentumStrategy('MOM20', {
        'lookback_period': 20,
        'top_n': 5,
        'holding_period': 5
    })

    mr_strategy = MeanReversionStrategy('MR15', {
        'lookback_period': 15,
        'z_score_threshold': -1.5,
        'top_n': 5,
        'holding_period': 5
    })

    # 组合策略
    combiner = StrategyCombiner(
        strategies=[mom_strategy, mr_strategy],
        weights=[0.6, 0.4]  # 动量策略权重更高
    )

    # 生成组合信号
    combined_signals = combiner.combine(
        prices=prices,
        volumes=volumes,
        method='weighted'
    )

    # 回测组合策略
    engine = BacktestEngine(initial_capital=1000000, verbose=False)
    results = engine.backtest_long_only(
        signals=combined_signals,
        prices=prices,
        top_n=5,
        holding_period=5
    )

    portfolio_value = results['portfolio_value']
    logger.info(f"\n组合策略回测结果:")
    logger.info(f"  总收益率: {(portfolio_value['total'].iloc[-1] / engine.initial_capital - 1) * 100:.2f}%")

    # 分析策略一致性
    signals_list = combiner.generate_individual_signals(prices, volumes=volumes)
    analysis = combiner.analyze_agreement(signals_list)
    logger.info(f"\n策略一致性分析:")
    logger.info(f"  各策略买入信号数: {analysis['buy_counts']}")
    logger.info(f"  平均相关性: {analysis['avg_correlation']:.3f}")

    return results


def main():
    """主函数"""
    logger.info("\n" + "=" * 70)
    logger.info("策略模块完整使用示例")
    logger.info("=" * 70)

    try:
        # 示例1: 动量策略
        example_1_momentum_strategy()

        # 示例2: 均值回归策略
        example_2_mean_reversion_strategy()

        # 示例3: 策略组合
        example_3_strategy_combination()

        logger.success("\n" + "=" * 70)
        logger.success("✓ 所有示例运行完成")
        logger.success("=" * 70)

    except Exception as e:
        logger.error(f"\n示例运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
