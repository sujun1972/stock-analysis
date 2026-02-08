"""
ML策略回测示例

演示如何使用MLEntry策略进行完整的回测工作流:
1. 训练ML模型
2. 创建ML入场策略
3. 执行回测
4. 分析结果

版本: v1.0.0
创建时间: 2026-02-08
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ml.feature_engine import FeatureEngine
from src.ml.label_generator import LabelGenerator
from src.ml.trained_model import TrainedModel, TrainingConfig
from src.ml.ml_entry import MLEntry
from src.backtest.backtest_engine import BacktestEngine


def generate_sample_data(n_stocks=10, n_days=500):
    """
    生成模拟市场数据

    Args:
        n_stocks: 股票数量
        n_days: 天数

    Returns:
        pd.DataFrame: OHLCV数据
    """
    np.random.seed(42)

    stocks = [f'60000{i}.SH' for i in range(n_stocks)]
    # 使用固定的历史日期范围，避免日期问题
    start_date = datetime(2023, 1, 1)
    dates = pd.date_range(start_date, periods=n_days, freq='D')

    data_list = []

    for stock in stocks:
        # 生成价格走势
        base_price = 10.0 + np.random.rand() * 20
        prices = [base_price]

        for _ in range(len(dates) - 1):
            # 加入趋势和随机性
            trend = np.random.randn() * 0.001
            noise = np.random.randn() * 0.02
            change = trend + noise
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 1.0))

        for i, date in enumerate(dates):
            price = prices[i]
            data_list.append({
                'date': date,
                'stock_code': stock,
                'open': price * (1 + np.random.randn() * 0.01),
                'high': price * (1 + abs(np.random.randn()) * 0.02),
                'low': price * (1 - abs(np.random.randn()) * 0.02),
                'close': price,
                'volume': int(1000000 + np.random.rand() * 2000000)
            })

    df = pd.DataFrame(data_list)
    df['date'] = pd.to_datetime(df['date'])
    return df


def train_sample_model(market_data, stock_pool, train_date):
    """
    训练一个简单的ML模型

    Args:
        market_data: 市场数据
        stock_pool: 股票池
        train_date: 训练日期

    Returns:
        TrainedModel: 训练好的模型
    """
    print("\n=== 步骤1: 训练ML模型 ===")

    # 1. 特征工程
    print("1.1 初始化特征引擎...")
    feature_engine = FeatureEngine(
        feature_groups=['technical'],
        lookback_window=60
    )

    print("1.2 计算特征...")
    features = feature_engine.calculate_features(
        stock_codes=stock_pool,
        market_data=market_data,
        date=train_date
    )
    print(f"✓ 特征计算完成: {features.shape}")

    # 2. 标签生成
    print("1.3 生成标签...")
    label_generator = LabelGenerator(
        forward_window=5,
        label_type='return'
    )
    labels = label_generator.generate_labels(
        stock_codes=stock_pool,
        market_data=market_data,
        date=train_date
    )
    print(f"✓ 标签生成完成: {len(labels)}个")

    # 3. 数据预处理
    print("1.4 数据预处理...")
    X = features.fillna(0).replace([np.inf, -np.inf], 0)
    y = labels

    # 4. 训练模型
    print("1.5 训练模型...")
    from sklearn.ensemble import RandomForestRegressor

    model = RandomForestRegressor(
        n_estimators=50,
        max_depth=5,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X.values, y.values)
    print(f"✓ 模型训练完成")

    # 5. 封装模型
    print("1.6 封装模型...")
    config = TrainingConfig(
        model_type='random_forest',
        train_start_date='2023-01-01',
        train_end_date=train_date,
        forward_window=5,
        feature_groups=['technical']
    )

    trained_model = TrainedModel(
        model=model,
        feature_engine=feature_engine,
        config=config,
        metrics={'ic': 0.08, 'rank_ic': 0.12}
    )
    trained_model.set_feature_columns(X.columns.tolist())
    print(f"✓ 模型封装完成")

    return trained_model


def example_1_basic_ml_backtest():
    """
    示例1: 基本ML策略回测

    展示最简单的ML策略回测流程
    """
    print("\n" + "="*60)
    print("示例1: 基本ML策略回测")
    print("="*60)

    # 1. 生成数据
    print("\n=== 准备数据 ===")
    market_data = generate_sample_data(n_stocks=10, n_days=500)
    stock_pool = market_data['stock_code'].unique().tolist()
    print(f"✓ 生成数据: {len(stock_pool)}只股票, {len(market_data['date'].unique())}天")

    # 2. 训练模型
    train_date = (market_data['date'].max() - timedelta(days=200)).strftime('%Y-%m-%d')
    trained_model = train_sample_model(market_data, stock_pool[:5], train_date)

    # 3. 保存模型
    print("\n=== 步骤2: 保存模型 ===")
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as f:
        model_path = f.name
    trained_model.save(model_path)
    print(f"✓ 模型已保存: {model_path}")

    try:
        # 4. 创建ML策略
        print("\n=== 步骤3: 创建ML策略 ===")
        ml_entry = MLEntry(
            model_path=model_path,
            confidence_threshold=0.6,
            top_long=5,
            enable_short=False
        )
        print(f"✓ ML策略创建完成")
        print(f"  - 置信度阈值: 0.6")
        print(f"  - 做多数量: 5只")
        print(f"  - 做空: 禁用")

        # 5. 创建回测引擎
        print("\n=== 步骤4: 执行回测 ===")
        engine = BacktestEngine(
            initial_capital=1000000.0,
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            slippage=0.001
        )

        # 6. 执行回测
        backtest_start = (market_data['date'].max() - timedelta(days=150)).strftime('%Y-%m-%d')
        backtest_end = market_data['date'].max().strftime('%Y-%m-%d')

        result = engine.backtest_ml_strategy(
            ml_entry=ml_entry,
            stock_pool=stock_pool,
            market_data=market_data,
            start_date=backtest_start,
            end_date=backtest_end,
            rebalance_freq='W'  # 周度调仓
        )

        # 7. 分析结果
        print("\n=== 步骤5: 分析结果 ===")
        if result.success:
            metrics = result.data['metrics']
            portfolio_value = result.data['portfolio_value']

            print(f"\n回测绩效:")
            print(f"  - 回测天数: {metrics['n_days']}天")
            print(f"  - 总收益率: {metrics['total_return']:.2%}")
            print(f"  - 年化收益: {metrics['annual_return']:.2%}")
            print(f"  - 波动率: {metrics['volatility']:.2%}")
            print(f"  - 夏普比率: {metrics['sharpe_ratio']:.2f}")
            print(f"  - 最大回撤: {metrics['max_drawdown']:.2%}")
            print(f"  - 胜率: {metrics['win_rate']:.2%}")

            print(f"\n资金变化:")
            print(f"  - 初始资金: {result.metadata.get('initial_capital', 1000000):,.0f}")
            print(f"  - 最终资金: {result.metadata.get('final_value', 0):,.0f}")
            initial = result.metadata.get('initial_capital', 1000000)
            final = result.metadata.get('final_value', 0)
            print(f"  - 盈亏: {final - initial:,.0f}")

            # 成本分析
            if 'cost_analysis' in result.data:
                cost = result.data['cost_analysis']
                print(f"\n成本分析:")
                print(f"  - 总佣金: {cost.get('total_commission', 0):,.2f}")
                print(f"  - 总滑点: {cost.get('total_slippage', 0):,.2f}")

            print(f"\n✓ 示例1完成!")
        else:
            print(f"✗ 回测失败: {result.message}")

    finally:
        # 清理临时文件
        if os.path.exists(model_path):
            os.remove(model_path)


def example_2_long_short_strategy():
    """
    示例2: 多空策略回测

    展示支持做空的ML策略
    """
    print("\n" + "="*60)
    print("示例2: 多空策略回测")
    print("="*60)

    # 1. 生成数据
    print("\n=== 准备数据 ===")
    market_data = generate_sample_data(n_stocks=15, n_days=500)
    stock_pool = market_data['stock_code'].unique().tolist()
    print(f"✓ 生成数据: {len(stock_pool)}只股票")

    # 2. 训练模型
    train_date = (market_data['date'].max() - timedelta(days=200)).strftime('%Y-%m-%d')
    trained_model = train_sample_model(market_data, stock_pool[:8], train_date)

    # 3. 保存模型
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as f:
        model_path = f.name
    trained_model.save(model_path)

    try:
        # 4. 创建多空策略
        print("\n=== 创建多空策略 ===")
        ml_entry = MLEntry(
            model_path=model_path,
            confidence_threshold=0.6,
            top_long=5,
            top_short=3,
            enable_short=True  # 启用做空
        )
        print(f"✓ 多空策略创建完成")
        print(f"  - 做多: 5只")
        print(f"  - 做空: 3只")

        # 5. 执行回测
        print("\n=== 执行回测 ===")
        engine = BacktestEngine(initial_capital=1000000.0)

        backtest_start = (market_data['date'].max() - timedelta(days=150)).strftime('%Y-%m-%d')
        backtest_end = market_data['date'].max().strftime('%Y-%m-%d')

        result = engine.backtest_ml_strategy(
            ml_entry=ml_entry,
            stock_pool=stock_pool,
            market_data=market_data,
            start_date=backtest_start,
            end_date=backtest_end,
            rebalance_freq='W'
        )

        # 6. 分析结果
        print("\n=== 分析结果 ===")
        if result.success:
            metrics = result.data['metrics']
            portfolio_value = result.data['portfolio_value']

            print(f"\n多空策略绩效:")
            print(f"  - 总收益率: {metrics['total_return']:.2%}")
            print(f"  - 年化收益: {metrics['annual_return']:.2%}")
            print(f"  - 夏普比率: {metrics['sharpe_ratio']:.2f}")
            print(f"  - 最大回撤: {metrics['max_drawdown']:.2%}")

            print(f"\n持仓分析:")
            print(f"  - 最终多头价值: {portfolio_value['long_value'].iloc[-1]:,.0f}")
            print(f"  - 最终空头价值: {portfolio_value['short_value'].iloc[-1]:,.0f}")
            print(f"  - 空头盈亏: {portfolio_value['short_pnl'].iloc[-1]:,.0f}")

            print(f"\n✓ 示例2完成!")

    finally:
        if os.path.exists(model_path):
            os.remove(model_path)


def example_3_parameter_comparison():
    """
    示例3: 参数对比

    对比不同参数设置的回测结果
    """
    print("\n" + "="*60)
    print("示例3: 参数对比 - 不同调仓频率")
    print("="*60)

    # 1. 准备数据
    print("\n=== 准备数据 ===")
    market_data = generate_sample_data(n_stocks=10, n_days=500)
    stock_pool = market_data['stock_code'].unique().tolist()

    # 2. 训练模型
    train_date = (market_data['date'].max() - timedelta(days=200)).strftime('%Y-%m-%d')
    trained_model = train_sample_model(market_data, stock_pool[:5], train_date)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as f:
        model_path = f.name
    trained_model.save(model_path)

    try:
        ml_entry = MLEntry(
            model_path=model_path,
            confidence_threshold=0.6,
            top_long=5
        )

        backtest_start = (market_data['date'].max() - timedelta(days=120)).strftime('%Y-%m-%d')
        backtest_end = market_data['date'].max().strftime('%Y-%m-%d')

        # 3. 测试不同调仓频率
        frequencies = ['D', 'W', 'M']
        results = {}

        print("\n=== 回测不同调仓频率 ===")
        for freq in frequencies:
            engine = BacktestEngine(initial_capital=1000000.0)

            result = engine.backtest_ml_strategy(
                ml_entry=ml_entry,
                stock_pool=stock_pool,
                market_data=market_data,
                start_date=backtest_start,
                end_date=backtest_end,
                rebalance_freq=freq
            )

            if result.success:
                results[freq] = result.data['metrics']

        # 4. 对比结果
        print("\n=== 参数对比结果 ===")
        print(f"{'频率':<8} {'总收益率':<12} {'年化收益':<12} {'夏普比率':<10} {'最大回撤':<10}")
        print("-" * 60)

        freq_names = {'D': '日度', 'W': '周度', 'M': '月度'}
        for freq in frequencies:
            if freq in results:
                m = results[freq]
                print(f"{freq_names[freq]:<8} "
                      f"{m['total_return']:>10.2%}  "
                      f"{m['annual_return']:>10.2%}  "
                      f"{m['sharpe_ratio']:>8.2f}  "
                      f"{m['max_drawdown']:>8.2%}")

        print(f"\n✓ 示例3完成!")

    finally:
        if os.path.exists(model_path):
            os.remove(model_path)


def main():
    """运行所有示例"""
    print("\n" + "="*60)
    print("ML策略回测示例集")
    print("="*60)

    # 运行示例
    example_1_basic_ml_backtest()
    example_2_long_short_strategy()
    example_3_parameter_comparison()

    print("\n" + "="*60)
    print("所有示例运行完成!")
    print("="*60)


if __name__ == '__main__':
    main()
