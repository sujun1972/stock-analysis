#!/usr/bin/env python3
"""
Phase 3 AI模型测试脚本
测试LightGBM、GRU模型、评估器和训练器功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.lightgbm_model import LightGBMStockModel
from src.models.model_evaluator import ModelEvaluator
from src.models.model_trainer import ModelTrainer

import pandas as pd
import numpy as np
from typing import Tuple


def create_test_data(n_samples: int = 1000, n_features: int = 20) -> Tuple:
    """创建测试数据"""
    np.random.seed(42)

    dates = pd.date_range('2020-01-01', periods=n_samples, freq='D')

    # 模拟特征
    features = {}
    for i in range(n_features):
        features[f'feature_{i}'] = np.random.randn(n_samples)

    # 模拟目标（带真实信号的收益率）
    true_signal = (
        features['feature_0'] * 0.5 +
        features['feature_1'] * 0.3 +
        features['feature_2'] * -0.2
    )
    target = true_signal * 0.02 + np.random.randn(n_samples) * 0.01

    df = pd.DataFrame(features, index=dates)
    df['target'] = target

    return df, [f'feature_{i}' for i in range(n_features)]


def test_lightgbm_model():
    """测试LightGBM模型"""
    print("\n" + "="*60)
    print("测试1: LightGBM模型")
    print("="*60)

    # 创建数据
    df, feature_cols = create_test_data(1000, 20)

    print(f"\n1.1 数据准备:")
    print(f"  样本数: {len(df)}")
    print(f"  特征数: {len(feature_cols)}")

    # 分割数据
    split_idx = int(len(df) * 0.8)
    train_df = df[:split_idx]
    test_df = df[split_idx:]

    X_train, y_train = train_df[feature_cols], train_df['target']
    X_test, y_test = test_df[feature_cols], test_df['target']

    print(f"  训练集: {len(X_train)} 样本")
    print(f"  测试集: {len(X_test)} 样本")

    # 训练模型
    print("\n1.2 训练模型")
    model = LightGBMStockModel(
        objective='regression',
        learning_rate=0.1,
        n_estimators=100,
        num_leaves=31,
        verbose=-1
    )

    history = model.train(
        X_train, y_train,
        X_test, y_test,
        early_stopping_rounds=10,
        verbose_eval=0
    )

    print(f"  ✓ 训练完成，最佳迭代: {history['best_iteration']}")

    # 预测
    print("\n1.3 预测")
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    print(f"  训练集预测数量: {len(y_pred_train)}")
    print(f"  测试集预测数量: {len(y_pred_test)}")

    # 计算指标
    from sklearn.metrics import mean_squared_error, r2_score

    train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    train_r2 = r2_score(y_train, y_pred_train)
    test_r2 = r2_score(y_test, y_pred_test)

    print(f"\n1.4 性能指标:")
    print(f"  训练集 RMSE: {train_rmse:.6f}, R²: {train_r2:.4f}")
    print(f"  测试集 RMSE: {test_rmse:.6f}, R²: {test_r2:.4f}")

    # 特征重要性
    print("\n1.5 特征重要性 (Top 5):")
    importance_df = model.get_feature_importance('gain', top_n=5)
    print(importance_df)

    # 保存和加载
    print("\n1.6 保存和加载模型")
    save_path = project_root / 'data' / 'test_models' / 'test_lgb.txt'
    save_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(save_path))

    new_model = LightGBMStockModel()
    new_model.load_model(str(save_path))

    y_pred_new = new_model.predict(X_test)
    assert np.allclose(y_pred_test, y_pred_new), "加载后预测不一致"
    print("  ✓ 模型保存和加载成功")

    print("\n✅ 测试1通过")
    return model, X_test, y_test


def test_model_evaluator():
    """测试模型评估器"""
    print("\n" + "="*60)
    print("测试2: 模型评估器")
    print("="*60)

    # 创建测试数据
    np.random.seed(42)
    n_samples = 1000

    # 模拟预测值和实际收益率（有相关性）
    true_signal = np.random.randn(n_samples)
    predictions = true_signal + np.random.randn(n_samples) * 0.5
    actual_returns = true_signal * 0.02 + np.random.randn(n_samples) * 0.01

    print(f"\n2.1 数据准备:")
    print(f"  样本数: {n_samples}")

    # 创建评估器
    evaluator = ModelEvaluator()

    # 测试IC计算
    print("\n2.2 IC指标:")
    ic = evaluator.calculate_ic(predictions, actual_returns, method='pearson')
    rank_ic = evaluator.calculate_rank_ic(predictions, actual_returns)

    print(f"  IC: {ic:.4f}")
    print(f"  Rank IC: {rank_ic:.4f}")

    assert -1 <= ic <= 1, "IC值超出范围"
    assert -1 <= rank_ic <= 1, "Rank IC值超出范围"

    # 测试分组收益
    print("\n2.3 分组收益:")
    group_returns = evaluator.calculate_group_returns(predictions, actual_returns, n_groups=5)
    for group, ret in sorted(group_returns.items()):
        print(f"  Group {group}: {ret:.6f}")

    # 测试多空收益
    print("\n2.4 多空收益:")
    long_short = evaluator.calculate_long_short_return(predictions, actual_returns)
    print(f"  Long: {long_short['long']:.6f}")
    print(f"  Short: {long_short['short']:.6f}")
    print(f"  Long-Short: {long_short['long_short']:.6f}")

    # 测试Sharpe比率
    print("\n2.5 Sharpe比率:")
    sharpe = evaluator.calculate_sharpe_ratio(actual_returns)
    print(f"  Sharpe Ratio: {sharpe:.4f}")

    # 测试最大回撤
    print("\n2.6 最大回撤:")
    max_dd = evaluator.calculate_max_drawdown(actual_returns)
    print(f"  Max Drawdown: {max_dd:.4%}")

    # 测试胜率
    print("\n2.7 胜率:")
    win_rate = evaluator.calculate_win_rate(actual_returns)
    print(f"  Win Rate: {win_rate:.4%}")

    # 全面评估
    print("\n2.8 全面评估:")
    metrics = evaluator.evaluate_regression(predictions, actual_returns, verbose=False)

    print(f"  评估指标数量: {len(metrics)}")
    assert 'ic' in metrics, "缺少IC指标"
    assert 'rank_ic' in metrics, "缺少Rank IC指标"
    assert 'long_short_return' in metrics, "缺少多空收益指标"

    print("\n✅ 测试2通过")
    return evaluator


def test_model_trainer():
    """测试模型训练器"""
    print("\n" + "="*60)
    print("测试3: 模型训练器")
    print("="*60)

    # 创建数据
    df, feature_cols = create_test_data(1000, 20)

    print(f"\n3.1 数据准备:")
    print(f"  样本数: {len(df)}")
    print(f"  特征数: {len(feature_cols)}")

    # 创建训练器
    print("\n3.2 创建LightGBM训练器")
    trainer = ModelTrainer(
        model_type='lightgbm',
        model_params={
            'learning_rate': 0.1,
            'n_estimators': 100,
            'num_leaves': 31
        },
        output_dir=str(project_root / 'data' / 'test_models')
    )

    # 准备数据
    print("\n3.3 数据分割")
    X_train, y_train, X_valid, y_valid, X_test, y_test = trainer.prepare_data(
        df, feature_cols, 'target',
        train_ratio=0.7,
        valid_ratio=0.15
    )

    # 训练
    print("\n3.4 训练模型")
    trainer.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)
    print("  ✓ 训练完成")

    # 评估
    print("\n3.5 评估模型")
    test_metrics = trainer.evaluate(X_test, y_test, dataset_name='test', verbose=False)

    print(f"  测试集指标:")
    print(f"    RMSE: {test_metrics['rmse']:.6f}")
    print(f"    R²: {test_metrics['r2']:.4f}")
    print(f"    IC: {test_metrics['ic']:.4f}")
    print(f"    Rank IC: {test_metrics['rank_ic']:.4f}")
    print(f"    Long-Short Return: {test_metrics['long_short_return']:.6f}")

    # 保存模型
    print("\n3.6 保存模型")
    trainer.save_model('trainer_test_model')
    print("  ✓ 模型已保存")

    # 加载模型
    print("\n3.7 加载模型")
    new_trainer = ModelTrainer(
        output_dir=str(project_root / 'data' / 'test_models')
    )
    new_trainer.load_model('trainer_test_model')
    print("  ✓ 模型已加载")

    # 验证加载后的模型
    new_metrics = new_trainer.evaluate(X_test, y_test, dataset_name='test', verbose=False)
    assert abs(new_metrics['rmse'] - test_metrics['rmse']) < 1e-6, "加载后RMSE不一致"
    print("  ✓ 加载后模型预测一致")

    print("\n✅ 测试3通过")
    return trainer


def test_integrated_workflow():
    """测试完整工作流"""
    print("\n" + "="*60)
    print("测试4: 完整工作流")
    print("="*60)

    # 创建数据
    df, feature_cols = create_test_data(1000, 20)

    print(f"\n4.1 数据准备:")
    print(f"  样本数: {len(df)}")

    # 使用便捷函数训练模型
    print("\n4.2 使用便捷函数训练模型")
    from src.models.model_trainer import train_stock_model

    trainer, test_metrics = train_stock_model(
        df=df,
        feature_cols=feature_cols,
        target_col='target',
        model_type='lightgbm',
        model_params={
            'learning_rate': 0.1,
            'n_estimators': 50
        },
        train_ratio=0.7,
        valid_ratio=0.15,
        save_path=None
    )

    print(f"\n4.3 模型性能:")
    print(f"  RMSE: {test_metrics['rmse']:.6f}")
    print(f"  IC: {test_metrics['ic']:.4f}")
    print(f"  Rank IC: {test_metrics['rank_ic']:.4f}")
    print(f"  Long-Short Return: {test_metrics['long_short_return']:.6f}")

    # 验证关键指标
    assert test_metrics['rmse'] < 0.1, "RMSE过高"
    assert abs(test_metrics['ic']) > 0.1, "IC相关性过低"

    print("\n✅ 测试4通过")


def main():
    """运行所有测试"""
    print("\n" + "🤖"*30)
    print("Phase 3: AI模型测试")
    print("🤖"*30)

    try:
        # 导入必要的类型
        from typing import Tuple

        # 运行各项测试
        test_lightgbm_model()
        test_model_evaluator()
        test_model_trainer()
        test_integrated_workflow()

        print("\n" + "="*60)
        print("✅ 所有测试通过！Phase 3 AI模型运行正常")
        print("="*60 + "\n")

        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
