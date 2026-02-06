"""
ML-3 LightGBM 排序模型完整使用示例

本示例演示如何：
1. 准备训练数据
2. 训练 LightGBM 排序模型
3. 在 MLSelector 中使用训练好的模型
4. 进行回测验证

作者: Core MLSelector Team
日期: 2026-02-06
版本: v1.0
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


# ============================================================================
# 示例 1: 训练 LightGBM 模型（完整流程）
# ============================================================================
def example_1_train_lightgbm_model():
    """
    示例 1: 训练 LightGBM 排序模型

    步骤：
    1. 加载历史价格数据
    2. 准备训练数据（特征 + 标签）
    3. 训练模型
    4. 评估模型
    5. 保存模型
    """
    print("\n" + "=" * 60)
    print("示例 1: 训练 LightGBM 排序模型")
    print("=" * 60)

    try:
        import lightgbm
    except ImportError:
        print("错误: 需要安装 lightgbm")
        print("安装命令: pip install lightgbm")
        return

    from tools.train_stock_ranker_lgbm import StockRankerTrainer

    # 步骤 1: 创建模拟数据（实际使用时替换为真实数据）
    print("\n步骤 1: 加载数据")
    dates = pd.date_range('2020-01-01', periods=800, freq='D')
    stocks = [f'STOCK_{i:03d}' for i in range(100)]

    np.random.seed(42)
    # 创建带趋势的价格数据
    base_price = 100
    trends = np.random.randn(100) * 0.0005
    noise = np.random.randn(800, 100) * 0.02

    prices_data = base_price * np.exp(
        np.cumsum(trends + noise, axis=0)
    )
    prices = pd.DataFrame(prices_data, index=dates, columns=stocks)

    print(f"数据形状: {prices.shape}")
    print(f"日期范围: {prices.index[0]} ~ {prices.index[-1]}")

    # 步骤 2: 创建训练器
    print("\n步骤 2: 创建训练器")
    trainer = StockRankerTrainer(
        label_forward_days=5,      # 预测未来5日收益
        label_threshold=0.02        # 收益率阈值 2%
    )

    print(f"特征数量: {len(trainer.feature_names)}")
    print(f"特征列表: {trainer.feature_names}")

    # 步骤 3: 准备训练数据
    print("\n步骤 3: 准备训练数据")
    X_train, y_train, groups_train = trainer.prepare_training_data(
        prices=prices,
        start_date='2020-02-01',
        end_date='2021-12-31',
        sample_freq='W'  # 周频采样
    )

    print(f"训练样本数: {len(X_train)}")
    print(f"训练日期数: {len(groups_train)}")
    print(f"标签分布:")
    print(y_train.value_counts().sort_index())

    # 步骤 4: 准备测试数据
    print("\n步骤 4: 准备测试数据")
    X_test, y_test, groups_test = trainer.prepare_training_data(
        prices=prices,
        start_date='2022-01-01',
        end_date='2022-06-30',
        sample_freq='W'
    )

    print(f"测试样本数: {len(X_test)}")

    # 步骤 5: 训练模型
    print("\n步骤 5: 训练模型")
    model = trainer.train_model(
        X_train=X_train,
        y_train=y_train,
        groups_train=groups_train,
        model_params={
            'n_estimators': 100,
            'learning_rate': 0.05,
            'max_depth': 6,
            'num_leaves': 31,
            'verbose': 10
        }
    )

    print("模型训练完成！")

    # 步骤 6: 评估模型
    print("\n步骤 6: 评估模型")
    metrics = trainer.evaluate_model(
        model=model,
        X_test=X_test,
        y_test=y_test,
        groups_test=groups_test
    )

    print(f"模型评估结果: {metrics}")

    # 步骤 7: 保存模型
    print("\n步骤 7: 保存模型")
    model_path = project_root / 'models' / 'stock_ranker_lgbm.pkl'
    model_path.parent.mkdir(parents=True, exist_ok=True)

    trainer.save_model(model, str(model_path))
    print(f"模型已保存: {model_path}")

    print("\n训练完成！")

    return str(model_path)


# ============================================================================
# 示例 2: 使用训练好的 LightGBM 模型进行选股
# ============================================================================
def example_2_use_lightgbm_selector(model_path: str):
    """
    示例 2: 使用 LightGBM 模型进行选股

    步骤：
    1. 加载训练好的模型
    2. 创建 MLSelector（lightgbm_ranker 模式）
    3. 执行选股
    """
    print("\n" + "=" * 60)
    print("示例 2: 使用 LightGBM 模型进行选股")
    print("=" * 60)

    try:
        import lightgbm
    except ImportError:
        print("错误: 需要安装 lightgbm")
        return

    from src.strategies.three_layer.selectors.ml_selector import MLSelector

    # 准备测试数据
    dates = pd.date_range('2022-01-01', periods=200, freq='D')
    stocks = [f'STOCK_{i:03d}' for i in range(100)]

    np.random.seed(42)
    prices_data = 100 + np.cumsum(
        np.random.randn(200, 100) * 0.02, axis=0
    )
    prices = pd.DataFrame(prices_data, index=dates, columns=stocks)

    # 创建 MLSelector，使用 LightGBM 模型
    print("\n创建 MLSelector（LightGBM 模式）")
    selector = MLSelector(params={
        'mode': 'lightgbm_ranker',
        'model_path': model_path,
        'top_n': 30,
        'filter_min_price': 10,
        'filter_max_price': 500
    })

    print(f"模型加载状态: {selector.model is not None}")
    print(f"选股模式: {selector.mode}")

    # 执行选股
    print("\n执行选股")
    test_dates = pd.date_range('2022-03-01', '2022-06-30', freq='M')

    for test_date in test_dates:
        selected_stocks = selector.select(test_date, prices)

        print(f"\n日期: {test_date.date()}")
        print(f"选出股票数: {len(selected_stocks)}")
        print(f"前10只股票: {selected_stocks[:10]}")


# ============================================================================
# 示例 3: 对比多因子加权 vs LightGBM
# ============================================================================
def example_3_compare_methods(model_path: str):
    """
    示例 3: 对比多因子加权和 LightGBM 两种方法

    步骤：
    1. 创建两个 MLSelector（不同模式）
    2. 在相同日期选股
    3. 对比结果
    """
    print("\n" + "=" * 60)
    print("示例 3: 对比多因子加权 vs LightGBM")
    print("=" * 60)

    try:
        import lightgbm
    except ImportError:
        print("错误: 需要安装 lightgbm")
        return

    from src.strategies.three_layer.selectors.ml_selector import MLSelector

    # 准备数据
    dates = pd.date_range('2022-01-01', periods=200, freq='D')
    stocks = [f'STOCK_{i:03d}' for i in range(100)]

    np.random.seed(42)
    prices_data = 100 + np.cumsum(
        np.random.randn(200, 100) * 0.02, axis=0
    )
    prices = pd.DataFrame(prices_data, index=dates, columns=stocks)

    # 创建两个选股器
    print("\n创建两个选股器")

    # 方法 1: 多因子加权
    selector_weighted = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'top_n': 30,
        'features': 'momentum_20d,rsi_14d,volatility_20d,ma_cross_20d',
        'normalization_method': 'z_score'
    })

    # 方法 2: LightGBM
    selector_lgbm = MLSelector(params={
        'mode': 'lightgbm_ranker',
        'model_path': model_path,
        'top_n': 30
    })

    # 执行选股
    test_date = pd.Timestamp('2022-05-01')

    print(f"\n选股日期: {test_date.date()}")

    stocks_weighted = selector_weighted.select(test_date, prices)
    stocks_lgbm = selector_lgbm.select(test_date, prices)

    # 对比结果
    print(f"\n多因子加权: {len(stocks_weighted)} 只股票")
    print(f"LightGBM: {len(stocks_lgbm)} 只股票")

    overlap = set(stocks_weighted) & set(stocks_lgbm)
    overlap_ratio = len(overlap) / max(len(stocks_weighted), len(stocks_lgbm))

    print(f"\n重叠股票数: {len(overlap)}")
    print(f"重叠率: {overlap_ratio:.2%}")

    print(f"\n只在多因子加权中: {set(stocks_weighted) - set(stocks_lgbm)}")
    print(f"只在LightGBM中: {set(stocks_lgbm) - set(stocks_weighted)}")


# ============================================================================
# 示例 4: LightGBM 选股器回测
# ============================================================================
def example_4_backtest_with_lightgbm(model_path: str):
    """
    示例 4: 使用 LightGBM 选股器进行完整回测

    步骤：
    1. 创建三层策略（MLSelector + Entry + Exit）
    2. 执行回测
    3. 分析结果
    """
    print("\n" + "=" * 60)
    print("示例 4: LightGBM 选股器回测")
    print("=" * 60)

    try:
        import lightgbm
    except ImportError:
        print("错误: 需要安装 lightgbm")
        return

    from src.strategies.three_layer.selectors.ml_selector import MLSelector
    from src.strategies.three_layer.entries import ImmediateEntry
    from src.strategies.three_layer.exits import FixedHoldingPeriodExit
    from src.strategies.three_layer.base import StrategyComposer

    # 准备回测数据
    dates = pd.date_range('2022-01-01', periods=250, freq='D')
    stocks = [f'STOCK_{i:03d}' for i in range(100)]

    np.random.seed(42)
    prices_data = 100 + np.cumsum(
        np.random.randn(250, 100) * 0.02, axis=0
    )
    prices = pd.DataFrame(prices_data, index=dates, columns=stocks)

    # 创建三层策略
    print("\n创建三层策略")

    selector = MLSelector(params={
        'mode': 'lightgbm_ranker',
        'model_path': model_path,
        'top_n': 20
    })

    entry = ImmediateEntry()

    exit_strategy = FixedHoldingPeriodExit(params={
        'holding_period': 10
    })

    composer = StrategyComposer(
        selector=selector,
        entry=entry,
        exit_strategy=exit_strategy,
        rebalance_freq='M'  # 月度调仓
    )

    print("策略组合创建完成")
    print(f"选股器: {composer.selector.name}")
    print(f"入场策略: {composer.entry.name}")
    print(f"退出策略: {composer.exit.name}")
    print(f"调仓频率: {composer.rebalance_freq}")

    # 模拟回测
    print("\n开始回测（简化版）")
    rebalance_dates = pd.date_range('2022-01-31', '2022-09-30', freq='M')

    backtest_results = []

    for date in rebalance_dates:
        # 选股
        selected = selector.select(date, prices)

        # 记录结果
        backtest_results.append({
            'date': date,
            'selected_stocks': selected,
            'count': len(selected)
        })

        print(f"日期: {date.date()}, 选股数: {len(selected)}")

    print(f"\n回测完成，共 {len(backtest_results)} 个调仓周期")

    # 统计选股稳定性
    all_stocks = set()
    for result in backtest_results:
        all_stocks.update(result['selected_stocks'])

    print(f"\n总共选中过: {len(all_stocks)} 只不同股票")
    print(f"平均每期选股: {np.mean([r['count'] for r in backtest_results]):.1f} 只")


# ============================================================================
# 示例 5: 超参数调优
# ============================================================================
def example_5_hyperparameter_tuning():
    """
    示例 5: LightGBM 超参数调优

    演示如何使用不同参数训练多个模型并对比
    """
    print("\n" + "=" * 60)
    print("示例 5: LightGBM 超参数调优")
    print("=" * 60)

    try:
        import lightgbm
    except ImportError:
        print("错误: 需要安装 lightgbm")
        return

    from tools.train_stock_ranker_lgbm import StockRankerTrainer

    # 创建数据
    dates = pd.date_range('2020-01-01', periods=500, freq='D')
    stocks = [f'STOCK_{i:03d}' for i in range(80)]

    np.random.seed(42)
    prices_data = 100 + np.cumsum(
        np.random.randn(500, 80) * 0.02, axis=0
    )
    prices = pd.DataFrame(prices_data, index=dates, columns=stocks)

    # 创建训练器
    trainer = StockRankerTrainer()

    # 准备数据
    X_train, y_train, groups_train = trainer.prepare_training_data(
        prices=prices,
        start_date='2020-02-01',
        end_date='2021-06-30',
        sample_freq='W'
    )

    X_test, y_test, groups_test = trainer.prepare_training_data(
        prices=prices,
        start_date='2021-07-01',
        end_date='2021-12-31',
        sample_freq='W'
    )

    # 定义多组超参数
    param_configs = [
        {
            'name': '默认参数',
            'params': {
                'n_estimators': 100,
                'learning_rate': 0.05,
                'max_depth': 6
            }
        },
        {
            'name': '深层模型',
            'params': {
                'n_estimators': 150,
                'learning_rate': 0.03,
                'max_depth': 8
            }
        },
        {
            'name': '快速模型',
            'params': {
                'n_estimators': 50,
                'learning_rate': 0.1,
                'max_depth': 4
            }
        }
    ]

    # 训练和评估
    print("\n开始超参数调优")
    results = []

    for config in param_configs:
        print(f"\n训练配置: {config['name']}")
        print(f"参数: {config['params']}")

        # 训练
        model = trainer.train_model(
            X_train=X_train,
            y_train=y_train,
            groups_train=groups_train,
            model_params={**config['params'], 'verbose': -1}
        )

        # 评估
        metrics = trainer.evaluate_model(
            model=model,
            X_test=X_test,
            y_test=y_test,
            groups_test=groups_test
        )

        results.append({
            'name': config['name'],
            'params': config['params'],
            'metrics': metrics
        })

        print(f"测试集性能: {metrics}")

    # 总结
    print("\n" + "=" * 60)
    print("超参数调优总结")
    print("=" * 60)

    for result in results:
        print(f"\n配置: {result['name']}")
        print(f"参数: {result['params']}")
        print(f"性能: {result['metrics']}")


# ============================================================================
# 主函数
# ============================================================================
def main():
    """
    主函数：依次运行所有示例

    使用方法：
        python ml3_lightgbm_ranker_example.py
    """
    # 配置日志
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<level>{message}</level>",
        level="INFO"
    )

    print("\n" + "=" * 60)
    print("ML-3 LightGBM 排序模型完整使用示例")
    print("=" * 60)

    # 示例 1: 训练模型
    model_path = example_1_train_lightgbm_model()

    if model_path:
        # 示例 2: 使用模型选股
        example_2_use_lightgbm_selector(model_path)

        # 示例 3: 对比方法
        example_3_compare_methods(model_path)

        # 示例 4: 回测
        example_4_backtest_with_lightgbm(model_path)

    # 示例 5: 超参数调优
    example_5_hyperparameter_tuning()

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
