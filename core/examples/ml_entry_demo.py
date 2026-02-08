"""
MLEntry 使用示例

演示如何使用 MLEntry 生成交易信号:
1. 加载训练好的模型
2. 生成做多/做空信号
3. 获取Top股票列表
4. 自定义参数配置

版本: v1.0.0
创建时间: 2026-02-08
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.ml import MLEntry, TrainedModel, TrainingConfig, FeatureEngine, LabelGenerator
from src.models.lightgbm_model import LightGBMStockModel


def create_sample_data():
    """创建示例市场数据"""
    print("创建示例市场数据...")

    dates = pd.date_range('2023-01-01', '2024-01-31', freq='D')
    stocks = [
        '600000.SH', '600036.SH', '600519.SH', '601318.SH', '600887.SH',
        '000001.SZ', '000002.SZ', '000858.SZ', '002594.SZ', '300750.SZ'
    ]

    data = []
    np.random.seed(42)

    for stock in stocks:
        base_price = np.random.uniform(10, 100)
        prices = []

        for i, date in enumerate(dates):
            # 生成价格走势
            if i == 0:
                price = base_price
            else:
                change = np.random.normal(0.001, 0.02)  # 日均涨跌0.1%, 波动率2%
                price = prices[-1] * (1 + change)

            prices.append(price)

            data.append({
                'stock_code': stock,
                'date': date,
                'open': price * (1 + np.random.uniform(-0.01, 0.01)),
                'high': price * (1 + np.random.uniform(0, 0.02)),
                'low': price * (1 - np.random.uniform(0, 0.02)),
                'close': price,
                'volume': np.random.randint(1000000, 10000000)
            })

    df = pd.DataFrame(data)
    print(f"✅ 已创建 {len(stocks)} 只股票, {len(dates)} 个交易日的数据")
    return df


def create_and_save_model(market_data: pd.DataFrame, model_path: str):
    """创建并保存训练好的模型"""
    print("\n" + "=" * 60)
    print("步骤 1: 创建并保存训练好的模型")
    print("=" * 60)

    # 1. 创建特征引擎
    print("\n1.1 创建特征引擎...")
    feature_engine = FeatureEngine(
        feature_groups=['technical'],
        lookback_window=60,
        cache_enabled=True
    )

    # 2. 准备训练数据
    print("1.2 准备训练数据...")
    train_stocks = market_data['stock_code'].unique()[:8]  # 用8只股票训练
    train_dates = market_data['date'].unique()[60:250]  # 用中间的数据训练

    X_list = []
    y_list = []

    label_generator = LabelGenerator(forward_window=5, label_type='return')

    for date in train_dates[::10]:  # 每10天采样一次
        date_str = pd.Timestamp(date).strftime('%Y-%m-%d')

        # 计算特征
        features = feature_engine.calculate_features(
            train_stocks, market_data, date_str
        )

        # 生成标签
        labels = label_generator.generate_labels(
            train_stocks, market_data, date_str
        )

        # 对齐索引
        common_idx = features.index.intersection(labels.index)
        if len(common_idx) > 0:
            X_list.append(features.loc[common_idx])
            y_list.append(labels.loc[common_idx])

    X_train = pd.concat(X_list, axis=0)
    y_train = pd.concat(y_list, axis=0)

    print(f"   训练样本数: {len(X_train)}")
    print(f"   特征数量: {X_train.shape[1]}")

    # 3. 训练模型
    print("1.3 训练模型...")
    model = LightGBMStockModel()

    # 准备数据
    X_clean = X_train.fillna(0).replace([np.inf, -np.inf], 0)

    # 训练模型 (不使用早停和verbose)
    model.train(
        X_train=X_clean,
        y_train=y_train,
        early_stopping_rounds=0,
        verbose_eval=0
    )

    # 4. 封装为 TrainedModel
    print("1.4 封装为 TrainedModel...")
    config = TrainingConfig(
        model_type='lightgbm',
        train_start_date='2023-03-01',
        train_end_date='2023-09-30',
        forward_window=5,
        feature_groups=['technical']
    )

    trained_model = TrainedModel(
        model=model,
        feature_engine=feature_engine,
        config=config,
        metrics={'ic': 0.08, 'rank_ic': 0.12, 'sharpe': 1.5}
    )

    # 设置特征列
    trained_model.set_feature_columns(X_train.columns.tolist())

    # 5. 保存模型
    print(f"1.5 保存模型到 {model_path}...")
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    trained_model.save(model_path)

    print("✅ 模型创建并保存成功!")
    return model_path


def example_1_basic_usage(model_path: str, market_data: pd.DataFrame):
    """示例1: 基本使用"""
    print("\n" + "=" * 60)
    print("示例 1: 基本使用 - 生成做多信号")
    print("=" * 60)

    # 创建 MLEntry 策略
    strategy = MLEntry(
        model_path=model_path,
        confidence_threshold=0.6,
        top_long=5,
        enable_short=False
    )

    print(f"\n策略配置:")
    print(f"  置信度阈值: {strategy.confidence_threshold}")
    print(f"  做多数量: {strategy.top_long}")
    print(f"  做空数量: {strategy.top_short}")
    print(f"  启用做空: {strategy.enable_short}")

    # 生成信号
    stock_pool = market_data['stock_code'].unique().tolist()
    test_date = '2024-01-15'

    print(f"\n生成 {test_date} 的交易信号...")
    signals = strategy.generate_signals(
        stock_pool=stock_pool,
        market_data=market_data,
        date=test_date
    )

    # 显示结果
    print(f"\n✅ 生成了 {len(signals)} 个交易信号:")
    print("-" * 80)
    print(f"{'股票代码':<15} {'方向':<10} {'权重':<10} {'预期收益':<12} {'置信度':<10}")
    print("-" * 80)

    for stock, info in sorted(signals.items(), key=lambda x: x[1]['weight'], reverse=True):
        print(f"{stock:<15} {info['action']:<10} {info['weight']:.4f}    "
              f"{info['expected_return']:>10.4f}  {info['confidence']:>8.2f}")

    print("-" * 80)
    total_weight = sum(s['weight'] for s in signals.values())
    print(f"总权重: {total_weight:.4f}")


def example_2_long_short(model_path: str, market_data: pd.DataFrame):
    """示例2: 做多做空策略"""
    print("\n" + "=" * 60)
    print("示例 2: 做多做空策略")
    print("=" * 60)

    # 创建支持做空的策略
    strategy = MLEntry(
        model_path=model_path,
        confidence_threshold=0.65,
        top_long=3,
        top_short=2,
        enable_short=True
    )

    print(f"\n策略配置:")
    print(f"  做多数量: {strategy.top_long}")
    print(f"  做空数量: {strategy.top_short}")
    print(f"  启用做空: {strategy.enable_short}")

    # 生成信号
    stock_pool = market_data['stock_code'].unique().tolist()
    test_date = '2024-01-20'

    signals = strategy.generate_signals(
        stock_pool=stock_pool,
        market_data=market_data,
        date=test_date
    )

    # 分组显示
    long_signals = {k: v for k, v in signals.items() if v['action'] == 'long'}
    short_signals = {k: v for k, v in signals.items() if v['action'] == 'short'}

    print(f"\n✅ 做多信号 ({len(long_signals)} 个):")
    print("-" * 80)
    for stock, info in sorted(long_signals.items(), key=lambda x: x[1]['weight'], reverse=True):
        print(f"  {stock:<15} 权重: {info['weight']:.4f}  预期收益: {info['expected_return']:>7.4f}")

    print(f"\n✅ 做空信号 ({len(short_signals)} 个):")
    print("-" * 80)
    for stock, info in sorted(short_signals.items(), key=lambda x: x[1]['weight'], reverse=True):
        print(f"  {stock:<15} 权重: {info['weight']:.4f}  预期收益: {info['expected_return']:>7.4f}")


def example_3_top_stocks(model_path: str, market_data: pd.DataFrame):
    """示例3: 获取Top股票"""
    print("\n" + "=" * 60)
    print("示例 3: 获取Top N股票列表")
    print("=" * 60)

    strategy = MLEntry(
        model_path=model_path,
        confidence_threshold=0.7,
        top_long=10
    )

    stock_pool = market_data['stock_code'].unique().tolist()
    test_date = '2024-01-25'

    # 获取Top 5 做多股票
    print(f"\n获取 {test_date} 的 Top 5 做多股票...")
    top_long_stocks = strategy.get_top_stocks(
        stock_pool=stock_pool,
        market_data=market_data,
        date=test_date,
        top_n=5,
        action='long'
    )

    print("\n✅ Top 5 做多股票:")
    for i, stock in enumerate(top_long_stocks, 1):
        print(f"  {i}. {stock}")


def example_4_custom_params(model_path: str, market_data: pd.DataFrame):
    """示例4: 自定义参数"""
    print("\n" + "=" * 60)
    print("示例 4: 自定义参数配置")
    print("=" * 60)

    # 保守策略 (高置信度阈值)
    conservative_strategy = MLEntry(
        model_path=model_path,
        confidence_threshold=0.8,  # 高置信度
        top_long=3,                # 少量持仓
        min_expected_return=0.01   # 最小预期收益1%
    )

    # 激进策略 (低置信度阈值)
    aggressive_strategy = MLEntry(
        model_path=model_path,
        confidence_threshold=0.5,  # 低置信度
        top_long=10,               # 大量持仓
        min_expected_return=0.0
    )

    stock_pool = market_data['stock_code'].unique().tolist()
    test_date = '2024-01-28'

    print("\n保守策略:")
    print(conservative_strategy)
    conservative_signals = conservative_strategy.generate_signals(
        stock_pool, market_data, test_date
    )
    print(f"  生成信号数: {len(conservative_signals)}")

    print("\n激进策略:")
    print(aggressive_strategy)
    aggressive_signals = aggressive_strategy.generate_signals(
        stock_pool, market_data, test_date
    )
    print(f"  生成信号数: {len(aggressive_signals)}")


def main():
    """主函数"""
    print("=" * 60)
    print("MLEntry 使用示例")
    print("=" * 60)

    # 1. 创建示例数据
    market_data = create_sample_data()

    # 2. 创建并保存模型
    model_path = 'models/ml_entry_demo_model.pkl'
    create_and_save_model(market_data, model_path)

    # 3. 运行示例
    example_1_basic_usage(model_path, market_data)
    example_2_long_short(model_path, market_data)
    example_3_top_stocks(model_path, market_data)
    example_4_custom_params(model_path, market_data)

    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
