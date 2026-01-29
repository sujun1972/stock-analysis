"""
模型对比示例

演示如何系统性地对比多个模型的性能：
1. 使用 ComparisonEvaluator 对比模型
2. 生成详细的对比报告
3. 可视化性能差异
4. 识别最佳模型

适用场景：
- 选择最佳模型
- 理解模型差异
- 生成评估报告
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

import pandas as pd
import numpy as np
from loguru import logger
from typing import Dict, List
import json

from models import (
    RidgeStockModel,
    LightGBMStockModel,
    ModelTrainer,
    ComparisonEvaluator,
    WeightedAverageEnsemble
)


def generate_sample_data(n_samples=1500, n_features=40):
    """生成示例数据"""
    np.random.seed(42)

    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )

    # 生成目标（更复杂的关系）
    y = pd.Series(
        0.15 * X['feature_0'] +
        0.10 * X['feature_1'] +
        0.05 * X['feature_2'] * X['feature_3'] +  # 交互项
        np.random.randn(n_samples) * 0.015,
        name='returns'
    )

    return X, y


def prepare_data():
    """准备训练、验证、测试数据"""
    logger.info("=" * 60)
    logger.info("准备数据")
    logger.info("=" * 60)

    X, y = generate_sample_data(n_samples=1500, n_features=40)

    # 分割数据
    train_size = 900
    valid_size = 1200

    X_train, y_train = X[:train_size], y[:train_size]
    X_valid, y_valid = X[train_size:valid_size], y[train_size:valid_size]
    X_test, y_test = X[valid_size:], y[valid_size:]

    logger.info(f"训练集: {len(X_train)} 样本")
    logger.info(f"验证集: {len(X_valid)} 样本")
    logger.info(f"测试集: {len(X_test)} 样本")

    return (X_train, y_train), (X_valid, y_valid), (X_test, y_test)


def example_basic_comparison():
    """示例1: 基础模型对比"""
    logger.info("\n" + "=" * 60)
    logger.info("示例1: 基础模型对比")
    logger.info("=" * 60)

    # 准备数据
    (X_train, y_train), (X_valid, y_valid), (X_test, y_test) = prepare_data()

    # 创建模型配置
    models_config = {
        'Ridge (α=0.1)': {
            'type': 'ridge',
            'params': {'alpha': 0.1}
        },
        'Ridge (α=1.0)': {
            'type': 'ridge',
            'params': {'alpha': 1.0}
        },
        'Ridge (α=10.0)': {
            'type': 'ridge',
            'params': {'alpha': 10.0}
        },
        'LightGBM (浅层)': {
            'type': 'lightgbm',
            'params': {
                'n_estimators': 50,
                'learning_rate': 0.1,
                'max_depth': 3,
                'num_leaves': 15
            }
        },
        'LightGBM (中层)': {
            'type': 'lightgbm',
            'params': {
                'n_estimators': 100,
                'learning_rate': 0.05,
                'max_depth': 5,
                'num_leaves': 31
            }
        },
        'LightGBM (深层)': {
            'type': 'lightgbm',
            'params': {
                'n_estimators': 200,
                'learning_rate': 0.03,
                'max_depth': 7,
                'num_leaves': 63
            }
        }
    }

    # 训练所有模型
    logger.info(f"\n训练 {len(models_config)} 个模型...")
    models = {}

    for name, config in models_config.items():
        logger.info(f"  训练 {name}...")

        if config['type'] == 'ridge':
            model = RidgeStockModel(**config['params'])
            model.train(X_train, y_train)

        elif config['type'] == 'lightgbm':
            model = LightGBMStockModel(**config['params'], random_state=42)
            model.train(X_train, y_train, X_valid, y_valid, verbose=False)

        models[name] = model

    logger.info("✓ 所有模型训练完成")

    # 评估所有模型
    logger.info("\n评估模型性能...")
    results = {}

    for name, model in models.items():
        # 预测
        y_pred_train = model.predict(X_train)
        y_pred_valid = model.predict(X_valid)
        y_pred_test = model.predict(X_test)

        # 计算指标
        train_ic = np.corrcoef(y_train, y_pred_train)[0, 1]
        valid_ic = np.corrcoef(y_valid, y_pred_valid)[0, 1]
        test_ic = np.corrcoef(y_test, y_pred_test)[0, 1]

        # Rank IC
        test_rank_ic = pd.Series(y_test.values).corr(
            pd.Series(y_pred_test), method='spearman'
        )

        # MSE
        test_mse = np.mean((y_test - y_pred_test) ** 2)

        results[name] = {
            'Train IC': train_ic,
            'Valid IC': valid_ic,
            'Test IC': test_ic,
            'Test Rank IC': test_rank_ic,
            'Test MSE': test_mse
        }

    # 生成对比报告
    results_df = pd.DataFrame(results).T
    results_df = results_df.sort_values('Test IC', ascending=False)

    logger.info("\n" + "=" * 80)
    logger.info("模型性能对比")
    logger.info("=" * 80)
    print(results_df.to_string())

    # 识别最佳模型
    best_model_name = results_df.index[0]
    logger.info(f"\n✓ 最佳模型: {best_model_name}")
    logger.info(f"  测试集 IC: {results_df.loc[best_model_name, 'Test IC']:.6f}")

    # 保存结果
    output_dir = Path('core/examples/comparison_outputs')
    output_dir.mkdir(parents=True, exist_ok=True)

    results_df.to_csv(output_dir / 'model_comparison.csv')
    logger.info(f"\n✓ 结果已保存到: {output_dir / 'model_comparison.csv'}")

    return models, results_df


def example_detailed_analysis():
    """示例2: 详细分析（包含统计检验）"""
    logger.info("\n" + "=" * 60)
    logger.info("示例2: 详细模型分析")
    logger.info("=" * 60)

    # 准备数据
    (X_train, y_train), (X_valid, y_valid), (X_test, y_test) = prepare_data()

    # 训练两个主要模型
    logger.info("训练主要模型...")

    ridge = RidgeStockModel(alpha=1.0)
    ridge.train(X_train, y_train)

    lgb = LightGBMStockModel(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=5,
        num_leaves=31,
        random_state=42
    )
    lgb.train(X_train, y_train, X_valid, y_valid, verbose=False)

    models = {'Ridge': ridge, 'LightGBM': lgb}

    # 详细分析
    logger.info("\n详细性能分析:")

    for name, model in models.items():
        logger.info(f"\n{name}:")

        # 预测
        y_pred_test = model.predict(X_test)

        # 1. 基本统计
        logger.info("  基本统计:")
        logger.info(f"    预测均值: {y_pred_test.mean():.6f}")
        logger.info(f"    预测标准差: {y_pred_test.std():.6f}")
        logger.info(f"    预测范围: [{y_pred_test.min():.6f}, {y_pred_test.max():.6f}]")

        # 2. 相关性
        ic = np.corrcoef(y_pred_test, y_test)[0, 1]
        rank_ic = pd.Series(y_test.values).corr(pd.Series(y_pred_test), method='spearman')

        logger.info("  相关性:")
        logger.info(f"    IC (Pearson):  {ic:.6f}")
        logger.info(f"    Rank IC (Spearman): {rank_ic:.6f}")

        # 3. 误差分析
        errors = y_test - y_pred_test
        mae = np.abs(errors).mean()
        mse = (errors ** 2).mean()
        rmse = np.sqrt(mse)

        logger.info("  误差分析:")
        logger.info(f"    MAE:  {mae:.6f}")
        logger.info(f"    MSE:  {mse:.6f}")
        logger.info(f"    RMSE: {rmse:.6f}")

        # 4. 分位数分析
        logger.info("  预测分位数分析:")
        y_pred_series = pd.Series(y_pred_test)

        for q in [0.1, 0.25, 0.5, 0.75, 0.9]:
            threshold = y_pred_series.quantile(q)
            top_mask = y_pred_test >= threshold
            top_actual_return = y_test[top_mask].mean()

            logger.info(f"    Top {(1-q)*100:.0f}% 预测 → 实际平均收益: {top_actual_return:.6f}")

    # 模型差异分析
    logger.info("\n模型预测差异:")
    pred_ridge = ridge.predict(X_test)
    pred_lgb = lgb.predict(X_test)

    pred_corr = np.corrcoef(pred_ridge, pred_lgb)[0, 1]
    pred_diff = np.abs(pred_ridge - pred_lgb).mean()

    logger.info(f"  预测相关性: {pred_corr:.6f}")
    logger.info(f"  预测平均差异: {pred_diff:.6f}")

    if pred_corr < 0.8:
        logger.info("  → 模型预测差异较大，适合集成")
    else:
        logger.info("  → 模型预测相似，集成收益可能有限")


def example_ensemble_comparison():
    """示例3: 集成模型对比"""
    logger.info("\n" + "=" * 60)
    logger.info("示例3: 单模型 vs 集成模型对比")
    logger.info("=" * 60)

    # 准备数据
    (X_train, y_train), (X_valid, y_valid), (X_test, y_test) = prepare_data()

    # 训练基础模型
    logger.info("训练基础模型...")

    ridge = RidgeStockModel(alpha=1.0)
    ridge.train(X_train, y_train)

    lgb1 = LightGBMStockModel(
        n_estimators=100, learning_rate=0.05,
        max_depth=5, num_leaves=31, random_state=42
    )
    lgb1.train(X_train, y_train, X_valid, y_valid, verbose=False)

    lgb2 = LightGBMStockModel(
        n_estimators=150, learning_rate=0.03,
        max_depth=7, num_leaves=63, random_state=43
    )
    lgb2.train(X_train, y_train, X_valid, y_valid, verbose=False)

    # 创建集成
    logger.info("创建集成模型...")

    ensemble_equal = WeightedAverageEnsemble(
        [ridge, lgb1, lgb2],
        model_names=['Ridge', 'LGB-1', 'LGB-2']
    )

    ensemble_optimized = WeightedAverageEnsemble(
        [ridge, lgb1, lgb2],
        model_names=['Ridge', 'LGB-1', 'LGB-2']
    )
    ensemble_optimized.optimize_weights(X_valid, y_valid, metric='ic')

    # 评估所有模型
    all_models = {
        'Ridge (单模型)': ridge,
        'LightGBM-1 (单模型)': lgb1,
        'LightGBM-2 (单模型)': lgb2,
        '集成-等权重': ensemble_equal,
        '集成-优化权重': ensemble_optimized
    }

    results = {}
    for name, model in all_models.items():
        y_pred = model.predict(X_test)
        ic = np.corrcoef(y_pred, y_test)[0, 1]
        rank_ic = pd.Series(y_test.values).corr(pd.Series(y_pred), method='spearman')

        results[name] = {
            'Test IC': ic,
            'Test Rank IC': rank_ic
        }

    # 显示结果
    results_df = pd.DataFrame(results).T
    results_df = results_df.sort_values('Test IC', ascending=False)

    logger.info("\n" + "=" * 60)
    logger.info("单模型 vs 集成模型性能对比")
    logger.info("=" * 60)
    print(results_df.to_string())

    # 计算提升
    best_single_ic = results_df.loc[
        [name for name in results_df.index if '单模型' in name],
        'Test IC'
    ].max()

    ensemble_ic = results_df.loc['集成-优化权重', 'Test IC']
    improvement = (ensemble_ic / best_single_ic - 1) * 100

    logger.info(f"\n✓ 集成模型相比最佳单模型提升: {improvement:+.2f}%")
    logger.info(f"  优化权重: {dict(zip(['Ridge', 'LGB-1', 'LGB-2'], ensemble_optimized.weights))}")


def generate_summary_report():
    """示例4: 生成汇总报告"""
    logger.info("\n" + "=" * 60)
    logger.info("示例4: 生成汇总报告")
    logger.info("=" * 60)

    # 准备数据
    (X_train, y_train), (X_valid, y_valid), (X_test, y_test) = prepare_data()

    # 训练多个模型
    models_to_test = [
        ('Ridge (α=1)', RidgeStockModel(alpha=1.0)),
        ('LightGBM', LightGBMStockModel(
            n_estimators=100, learning_rate=0.05,
            max_depth=5, num_leaves=31, random_state=42
        ))
    ]

    report = {
        'metadata': {
            'n_train': len(X_train),
            'n_valid': len(X_valid),
            'n_test': len(X_test),
            'n_features': X_train.shape[1]
        },
        'models': {}
    }

    # 训练和评估
    for name, model in models_to_test:
        logger.info(f"评估 {name}...")

        # 训练
        if 'LightGBM' in name:
            model.train(X_train, y_train, X_valid, y_valid, verbose=False)
        else:
            model.train(X_train, y_train)

        # 评估
        y_pred_test = model.predict(X_test)
        ic = np.corrcoef(y_pred_test, y_test)[0, 1]
        rank_ic = pd.Series(y_test.values).corr(pd.Series(y_pred_test), method='spearman')

        report['models'][name] = {
            'test_ic': float(ic),
            'test_rank_ic': float(rank_ic),
            'test_mse': float(np.mean((y_test - y_pred_test) ** 2))
        }

    # 保存报告
    output_dir = Path('core/examples/comparison_outputs')
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / 'summary_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    logger.info(f"\n✓ 汇总报告已保存到: {report_path}")

    # 显示报告
    logger.info("\n汇总报告:")
    logger.info(json.dumps(report, indent=2))


def main():
    """主函数"""
    logger.info("开始模型对比示例")
    logger.info("本示例将演示如何系统性地对比模型性能\n")

    # 示例1: 基础对比
    try:
        logger.info("\n运行示例1: 基础模型对比")
        example_basic_comparison()
    except Exception as e:
        logger.error(f"示例1 出错: {e}")

    # 示例2: 详细分析
    try:
        logger.info("\n运行示例2: 详细分析")
        example_detailed_analysis()
    except Exception as e:
        logger.error(f"示例2 出错: {e}")

    # 示例3: 集成对比
    try:
        logger.info("\n运行示例3: 集成模型对比")
        example_ensemble_comparison()
    except Exception as e:
        logger.error(f"示例3 出错: {e}")

    # 示例4: 汇总报告
    try:
        logger.info("\n运行示例4: 生成汇总报告")
        generate_summary_report()
    except Exception as e:
        logger.error(f"示例4 出错: {e}")

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("所有示例运行完成！")
    logger.info("=" * 60)

    logger.info("\n关键要点:")
    logger.info("  1. 使用多个指标评估模型（IC、Rank IC、MSE）")
    logger.info("  2. 对比单模型和集成模型")
    logger.info("  3. 分析预测分位数性能")
    logger.info("  4. 生成可复现的评估报告")

    logger.info("\n输出目录: core/examples/comparison_outputs/")
    logger.info("  - model_comparison.csv : 详细对比结果")
    logger.info("  - summary_report.json  : 汇总报告")


if __name__ == '__main__':
    main()
