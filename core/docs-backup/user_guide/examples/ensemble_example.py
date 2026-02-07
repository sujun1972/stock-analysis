"""
模型集成示例

演示如何使用三种集成方法：
1. 加权平均集成 (Weighted Average)
2. 投票法集成 (Voting)
3. Stacking 集成

适用场景：
- 提升模型性能（通常提升 5-15% IC）
- 降低单模型风险
- 融合不同模型优势
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

import pandas as pd
import numpy as np
from loguru import logger

from models import (
    RidgeStockModel,
    LightGBMStockModel,
    WeightedAverageEnsemble,
    VotingEnsemble,
    StackingEnsemble,
    create_ensemble
)


def generate_sample_data(n_samples=1000, n_features=30):
    """生成示例数据"""
    np.random.seed(42)

    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )

    # 生成目标（模拟收益率）
    y = pd.Series(
        0.1 * X['feature_0'] + 0.05 * X['feature_1'] + np.random.randn(n_samples) * 0.01,
        name='returns'
    )

    return X, y


def train_base_models(X_train, y_train, X_valid, y_valid):
    """
    训练基础模型

    返回:
        models: 模型字典
    """
    logger.info("训练基础模型...")

    models = {}

    # 1. Ridge 模型
    logger.info("  训练 Ridge 模型...")
    ridge = RidgeStockModel(alpha=1.0)
    ridge.train(X_train, y_train)
    models['Ridge'] = ridge

    # 2. LightGBM 模型 (参数1)
    logger.info("  训练 LightGBM-1 模型...")
    lgb1 = LightGBMStockModel(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=5,
        num_leaves=31,
        random_state=42
    )
    lgb1.train(X_train, y_train, X_valid, y_valid, verbose=False)
    models['LightGBM-1'] = lgb1

    # 3. LightGBM 模型 (参数2 - 更深)
    logger.info("  训练 LightGBM-2 模型...")
    lgb2 = LightGBMStockModel(
        n_estimators=150,
        learning_rate=0.03,
        max_depth=7,
        num_leaves=63,
        random_state=43
    )
    lgb2.train(X_train, y_train, X_valid, y_valid, verbose=False)
    models['LightGBM-2'] = lgb2

    logger.info(f"✓ 完成训练 {len(models)} 个基础模型")

    return models


def evaluate_models(models, X_test, y_test):
    """
    评估所有模型

    参数:
        models: 模型字典
        X_test: 测试特征
        y_test: 测试目标

    返回:
        results: 评估结果字典
    """
    results = {}

    for name, model in models.items():
        y_pred = model.predict(X_test)
        ic = np.corrcoef(y_pred, y_test)[0, 1]
        results[name] = ic

    return results


def example_weighted_average():
    """示例1: 加权平均集成"""
    logger.info("\n" + "=" * 60)
    logger.info("示例1: 加权平均集成 (Weighted Average)")
    logger.info("=" * 60)

    # 1. 准备数据
    X, y = generate_sample_data(n_samples=1000, n_features=30)

    train_size = 600
    valid_size = 800

    X_train, y_train = X[:train_size], y[:train_size]
    X_valid, y_valid = X[train_size:valid_size], y[train_size:valid_size]
    X_test, y_test = X[valid_size:], y[valid_size:]

    # 2. 训练基础模型
    models = train_base_models(X_train, y_train, X_valid, y_valid)

    # 3. 评估单模型性能
    logger.info("\n单模型性能:")
    single_results = evaluate_models(models, X_test, y_test)
    for name, ic in single_results.items():
        logger.info(f"  {name:15s}: IC = {ic:.6f}")

    # 4. 方法1: 等权重集成
    logger.info("\n方法1: 等权重集成")
    ensemble_equal = WeightedAverageEnsemble(
        models=list(models.values()),
        model_names=list(models.keys())
    )

    y_pred_equal = ensemble_equal.predict(X_test)
    ic_equal = np.corrcoef(y_pred_equal, y_test)[0, 1]
    logger.info(f"  等权重集成 IC: {ic_equal:.6f}")
    logger.info(f"  权重: {ensemble_equal.weights}")

    # 5. 方法2: 自定义权重（根据单模型性能）
    logger.info("\n方法2: 自定义权重")
    custom_weights = [0.3, 0.4, 0.3]  # Ridge=0.3, LGB-1=0.4, LGB-2=0.3

    ensemble_custom = WeightedAverageEnsemble(
        models=list(models.values()),
        weights=custom_weights,
        model_names=list(models.keys())
    )

    y_pred_custom = ensemble_custom.predict(X_test)
    ic_custom = np.corrcoef(y_pred_custom, y_test)[0, 1]
    logger.info(f"  自定义权重 IC: {ic_custom:.6f}")
    logger.info(f"  权重: {ensemble_custom.weights}")

    # 6. 方法3: 自动优化权重
    logger.info("\n方法3: 自动优化权重")
    ensemble_optimized = WeightedAverageEnsemble(
        models=list(models.values()),
        model_names=list(models.keys())
    )

    # 在验证集上优化权重
    optimized_weights = ensemble_optimized.optimize_weights(
        X_valid, y_valid,
        metric='ic'
    )

    y_pred_optimized = ensemble_optimized.predict(X_test)
    ic_optimized = np.corrcoef(y_pred_optimized, y_test)[0, 1]
    logger.info(f"  优化权重 IC: {ic_optimized:.6f}")
    logger.info(f"  优化后权重: {optimized_weights}")

    # 7. 总结
    logger.info("\n加权平均集成总结:")
    logger.info(f"  最佳单模型: {max(single_results, key=single_results.get)} "
                f"(IC={max(single_results.values()):.6f})")
    logger.info(f"  等权重集成: IC={ic_equal:.6f} "
                f"(提升 {(ic_equal/max(single_results.values())-1)*100:+.2f}%)")
    logger.info(f"  优化权重集成: IC={ic_optimized:.6f} "
                f"(提升 {(ic_optimized/max(single_results.values())-1)*100:+.2f}%)")

    return ensemble_optimized, ic_optimized


def example_voting():
    """示例2: 投票法集成"""
    logger.info("\n" + "=" * 60)
    logger.info("示例2: 投票法集成 (Voting)")
    logger.info("=" * 60)
    logger.info("适用场景: 选股策略（选择 Top N 股票）")

    # 1. 准备数据
    X, y = generate_sample_data(n_samples=1000, n_features=30)

    train_size = 600
    valid_size = 800

    X_train, y_train = X[:train_size], y[:train_size]
    X_valid, y_valid = X[train_size:valid_size], y[train_size:valid_size]
    X_test, y_test = X[valid_size:], y[valid_size:]

    # 2. 训练基础模型
    models = train_base_models(X_train, y_train, X_valid, y_valid)

    # 3. 创建投票集成
    ensemble = VotingEnsemble(
        models=list(models.values()),
        model_names=list(models.keys()),
        voting_weights=[1.0, 1.5, 1.0]  # LightGBM-1 权重更高
    )

    # 4. 方法1: 获取投票分数
    logger.info("\n方法1: 获取投票分数")
    scores = ensemble.predict(X_test)
    logger.info(f"  投票分数范围: [{scores.min():.4f}, {scores.max():.4f}]")

    # 评估投票分数
    ic_voting = np.corrcoef(scores, y_test)[0, 1]
    logger.info(f"  投票分数 IC: {ic_voting:.6f}")

    # 5. 方法2: 选择 Top N 股票
    logger.info("\n方法2: 选择 Top 50 股票")
    top_n = 50
    top_indices = ensemble.select_top_n(X_test, top_n=top_n)

    logger.info(f"  选出 {len(top_indices)} 只股票")
    logger.info(f"  股票索引: {top_indices[:10]}... (前10个)")

    # 计算选中股票的平均收益
    selected_returns = y_test.iloc[top_indices]
    avg_return = selected_returns.mean()
    logger.info(f"  选中股票平均收益: {avg_return:.6f}")
    logger.info(f"  全部股票平均收益: {y_test.mean():.6f}")
    logger.info(f"  超额收益: {avg_return - y_test.mean():.6f}")

    # 6. 方法3: 获取 Top N 及其分数
    logger.info("\n方法3: 获取 Top N 及其分数")
    top_indices, top_scores = ensemble.select_top_n(
        X_test, top_n=top_n, return_scores=True
    )

    logger.info(f"  Top 10 股票:")
    for i, (idx, score) in enumerate(zip(top_indices[:10], top_scores[:10])):
        logger.info(f"    #{i+1}: 索引={idx}, 分数={score:.4f}, 实际收益={y_test.iloc[idx]:.6f}")

    return ensemble, ic_voting


def example_stacking():
    """示例3: Stacking 集成"""
    logger.info("\n" + "=" * 60)
    logger.info("示例3: Stacking 集成")
    logger.info("=" * 60)
    logger.info("两层结构: 基础模型 → 元学习器")

    # 1. 准备数据（Stacking 需要三个数据集）
    X, y = generate_sample_data(n_samples=1000, n_features=30)

    train_size = 600
    valid_size = 800

    X_train, y_train = X[:train_size], y[:train_size]
    X_valid, y_valid = X[train_size:valid_size], y[train_size:valid_size]
    X_test, y_test = X[valid_size:], y[valid_size:]

    logger.info(f"数据分割: 训练={train_size}, 验证={valid_size-train_size}, 测试={len(X)-valid_size}")

    # 2. 训练基础模型
    models = train_base_models(X_train, y_train, X_valid, y_valid)

    # 3. 方法1: 仅使用基础模型预测
    logger.info("\n方法1: 基础 Stacking（仅使用基础模型预测）")

    ensemble_basic = StackingEnsemble(
        base_models=list(models.values()),
        meta_learner=RidgeStockModel(alpha=0.5),
        model_names=list(models.keys()),
        use_original_features=False
    )

    # 训练元学习器（在验证集上）
    logger.info("  训练元学习器...")
    ensemble_basic.train_meta_learner(X_train, y_train, X_valid, y_valid)

    # 预测
    y_pred_basic = ensemble_basic.predict(X_test)
    ic_basic = np.corrcoef(y_pred_basic, y_test)[0, 1]
    logger.info(f"  基础 Stacking IC: {ic_basic:.6f}")

    # 4. 方法2: 结合原始特征
    logger.info("\n方法2: 完整 Stacking（结合原始特征）")

    ensemble_full = StackingEnsemble(
        base_models=list(models.values()),
        meta_learner=RidgeStockModel(alpha=0.5),
        model_names=list(models.keys()),
        use_original_features=True  # 使用原始特征
    )

    # 训练元学习器
    logger.info("  训练元学习器...")
    ensemble_full.train_meta_learner(X_train, y_train, X_valid, y_valid)

    # 预测
    y_pred_full = ensemble_full.predict(X_test)
    ic_full = np.corrcoef(y_pred_full, y_test)[0, 1]
    logger.info(f"  完整 Stacking IC: {ic_full:.6f}")

    # 5. 方法3: 使用 LightGBM 作为元学习器
    logger.info("\n方法3: 使用 LightGBM 元学习器")

    meta_lgb = LightGBMStockModel(
        n_estimators=50,
        learning_rate=0.05,
        max_depth=3,
        num_leaves=15
    )

    ensemble_lgb_meta = StackingEnsemble(
        base_models=list(models.values()),
        meta_learner=meta_lgb,
        model_names=list(models.keys()),
        use_original_features=False
    )

    # 训练元学习器
    logger.info("  训练元学习器...")
    ensemble_lgb_meta.train_meta_learner(X_train, y_train, X_valid, y_valid)

    # 预测
    y_pred_lgb = ensemble_lgb_meta.predict(X_test)
    ic_lgb = np.corrcoef(y_pred_lgb, y_test)[0, 1]
    logger.info(f"  LightGBM 元学习器 IC: {ic_lgb:.6f}")

    # 6. 总结
    logger.info("\nStacking 集成总结:")
    logger.info(f"  基础 Stacking:   IC={ic_basic:.6f}")
    logger.info(f"  完整 Stacking:   IC={ic_full:.6f}")
    logger.info(f"  LightGBM 元学习: IC={ic_lgb:.6f}")

    return ensemble_full, ic_full


def example_create_ensemble():
    """示例4: 使用便捷函数创建集成"""
    logger.info("\n" + "=" * 60)
    logger.info("示例4: 使用便捷函数快速创建集成")
    logger.info("=" * 60)

    # 1. 准备数据
    X, y = generate_sample_data(n_samples=1000, n_features=30)

    train_size = 600
    valid_size = 800

    X_train, y_train = X[:train_size], y[:train_size]
    X_valid, y_valid = X[train_size:valid_size], y[train_size:valid_size]
    X_test, y_test = X[valid_size:], y[valid_size:]

    # 2. 训练基础模型
    models = train_base_models(X_train, y_train, X_valid, y_valid)
    model_list = list(models.values())

    # 3. 快速创建不同类型的集成
    results = {}

    # 加权平均
    logger.info("\n创建加权平均集成...")
    ensemble_wa = create_ensemble(
        model_list,
        method='weighted_average',
        weights=[0.3, 0.4, 0.3]
    )
    ic_wa = np.corrcoef(ensemble_wa.predict(X_test), y_test)[0, 1]
    results['WeightedAverage'] = ic_wa
    logger.info(f"  IC = {ic_wa:.6f}")

    # 投票法
    logger.info("\n创建投票法集成...")
    ensemble_vote = create_ensemble(
        model_list,
        method='voting'
    )
    ic_vote = np.corrcoef(ensemble_vote.predict(X_test), y_test)[0, 1]
    results['Voting'] = ic_vote
    logger.info(f"  IC = {ic_vote:.6f}")

    # Stacking
    logger.info("\n创建 Stacking 集成...")
    ensemble_stack = create_ensemble(
        model_list,
        method='stacking',
        meta_learner=RidgeStockModel()
    )
    ensemble_stack.train_meta_learner(X_train, y_train, X_valid, y_valid)
    ic_stack = np.corrcoef(ensemble_stack.predict(X_test), y_test)[0, 1]
    results['Stacking'] = ic_stack
    logger.info(f"  IC = {ic_stack:.6f}")

    # 总结
    logger.info("\n便捷函数创建结果:")
    for method, ic in results.items():
        logger.info(f"  {method:20s}: IC = {ic:.6f}")

    return results


def main():
    """主函数"""
    logger.info("开始模型集成示例")
    logger.info("本示例将演示三种集成方法的使用\n")

    all_results = {}

    # 示例1: 加权平均
    try:
        _, ic = example_weighted_average()
        all_results['Weighted Average (Optimized)'] = ic
    except Exception as e:
        logger.error(f"加权平均示例出错: {e}")

    # 示例2: 投票法
    try:
        _, ic = example_voting()
        all_results['Voting'] = ic
    except Exception as e:
        logger.error(f"投票法示例出错: {e}")

    # 示例3: Stacking
    try:
        _, ic = example_stacking()
        all_results['Stacking (Full)'] = ic
    except Exception as e:
        logger.error(f"Stacking 示例出错: {e}")

    # 示例4: 便捷函数
    try:
        example_create_ensemble()
    except Exception as e:
        logger.error(f"便捷函数示例出错: {e}")

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("示例运行完成！")
    logger.info("=" * 60)
    logger.info("\n所有集成方法 IC 对比:")
    for method, ic in all_results.items():
        logger.info(f"  {method:30s}: {ic:.6f}")

    logger.info("\n关键要点:")
    logger.info("  1. 加权平均：简单有效，支持权重优化")
    logger.info("  2. 投票法：适合选股策略（Top N）")
    logger.info("  3. Stacking：性能最优，需要独立验证集")
    logger.info("  4. 使用 create_ensemble() 快速创建")

    logger.info("\n详细文档: docs/ENSEMBLE_GUIDE.md")


if __name__ == '__main__':
    main()
