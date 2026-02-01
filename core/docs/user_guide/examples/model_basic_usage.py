"""
模型基础使用示例

演示如何使用 Core 模块中的三种基础模型：
1. Ridge 回归模型
2. LightGBM 模型
3. GRU 深度学习模型

适用场景：
- 初次使用模型的用户
- 了解各模型的基本用法
- 快速训练和预测
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
    GRUStockModel,
    GRU_AVAILABLE
)


def generate_sample_data(n_samples=1000, n_features=30):
    """
    生成示例数据

    参数:
        n_samples: 样本数量
        n_features: 特征数量

    返回:
        X: 特征DataFrame
        y: 目标Series
    """
    np.random.seed(42)

    # 生成特征
    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )

    # 生成目标（模拟收益率）
    # y = 0.1 * feature_0 + 0.05 * feature_1 + noise
    y = pd.Series(
        0.1 * X['feature_0'] + 0.05 * X['feature_1'] + np.random.randn(n_samples) * 0.01,
        name='returns'
    )

    return X, y


def example_ridge_model():
    """示例1: Ridge 回归模型"""
    logger.info("=" * 60)
    logger.info("示例1: Ridge 回归模型")
    logger.info("=" * 60)

    # 1. 生成数据
    X, y = generate_sample_data(n_samples=1000, n_features=30)

    # 分割数据
    train_size = 600
    valid_size = 800

    X_train, y_train = X[:train_size], y[:train_size]
    X_valid, y_valid = X[train_size:valid_size], y[train_size:valid_size]
    X_test, y_test = X[valid_size:], y[valid_size:]

    logger.info(f"训练集: {len(X_train)} 样本")
    logger.info(f"验证集: {len(X_valid)} 样本")
    logger.info(f"测试集: {len(X_test)} 样本")

    # 2. 创建模型
    model = RidgeStockModel(alpha=1.0)
    logger.info(f"创建模型: {model}")

    # 3. 训练模型
    logger.info("开始训练...")
    model.train(X_train, y_train)
    logger.info("训练完成!")

    # 4. 预测
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    # 5. 评估
    train_ic = np.corrcoef(y_train, y_pred_train)[0, 1]
    test_ic = np.corrcoef(y_test, y_pred_test)[0, 1]

    logger.info(f"训练集 IC: {train_ic:.6f}")
    logger.info(f"测试集 IC: {test_ic:.6f}")

    # 6. 保存模型
    save_path = project_root / 'examples' / 'saved_models' / 'ridge_model.pkl'
    save_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(save_path))
    logger.info(f"模型已保存到: {save_path}")

    # 7. 加载模型
    loaded_model = RidgeStockModel.load(str(save_path))
    y_pred_loaded = loaded_model.predict(X_test)

    # 验证加载的模型
    assert np.allclose(y_pred_test, y_pred_loaded), "加载的模型预测结果不一致"
    logger.info("✓ 模型加载验证成功")

    return model, test_ic


def example_lightgbm_model():
    """示例2: LightGBM 模型"""
    logger.info("\n" + "=" * 60)
    logger.info("示例2: LightGBM 模型")
    logger.info("=" * 60)

    # 1. 生成数据
    X, y = generate_sample_data(n_samples=1000, n_features=30)

    # 分割数据
    train_size = 600
    valid_size = 800

    X_train, y_train = X[:train_size], y[:train_size]
    X_valid, y_valid = X[train_size:valid_size], y[train_size:valid_size]
    X_test, y_test = X[valid_size:], y[valid_size:]

    # 2. 创建模型（自定义参数）
    model = LightGBMStockModel(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=5,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    logger.info(f"创建模型: LightGBM")
    logger.info(f"参数: n_estimators={model.n_estimators}, lr={model.learning_rate}")

    # 3. 训练模型（带验证集）
    logger.info("开始训练...")
    model.train(
        X_train, y_train,
        X_valid, y_valid,
        early_stopping_rounds=10,
        verbose=False
    )
    logger.info("训练完成!")

    # 4. 预测
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    # 5. 评估
    train_ic = np.corrcoef(y_train, y_pred_train)[0, 1]
    test_ic = np.corrcoef(y_test, y_pred_test)[0, 1]

    logger.info(f"训练集 IC: {train_ic:.6f}")
    logger.info(f"测试集 IC: {test_ic:.6f}")

    # 6. 查看特征重要性
    if hasattr(model, 'get_feature_importance'):
        importance = model.get_feature_importance(top_n=10)
        logger.info("\n前10个重要特征:")
        for feature, score in importance.items():
            logger.info(f"  {feature}: {score:.4f}")

    # 7. 保存模型
    save_path = project_root / 'examples' / 'saved_models' / 'lightgbm_model.pkl'
    model.save(str(save_path))
    logger.info(f"模型已保存到: {save_path}")

    return model, test_ic


def example_gru_model():
    """示例3: GRU 深度学习模型"""
    logger.info("\n" + "=" * 60)
    logger.info("示例3: GRU 深度学习模型")
    logger.info("=" * 60)

    if not GRU_AVAILABLE:
        logger.warning("PyTorch 未安装，跳过 GRU 模型示例")
        return None, None

    # 1. 生成时序数据
    n_samples = 1000
    n_features = 20
    sequence_length = 10

    # 生成序列数据 (n_samples, sequence_length, n_features)
    np.random.seed(42)
    sequences = np.random.randn(n_samples, sequence_length, n_features)

    # 生成目标
    targets = np.random.randn(n_samples) * 0.01

    # 转换为 DataFrame 和 Series
    # 注意：GRU 需要特殊的数据格式
    X = pd.DataFrame(sequences.reshape(n_samples, -1))
    y = pd.Series(targets, name='returns')

    # 分割数据
    train_size = 600
    valid_size = 800

    X_train, y_train = X[:train_size], y[:train_size]
    X_valid, y_valid = X[train_size:valid_size], y[train_size:valid_size]
    X_test, y_test = X[valid_size:], y[valid_size:]

    # 2. 创建模型
    trainer = GRUStockModel(
        input_size=n_features,
        hidden_size=64,
        num_layers=2,
        dropout=0.2,
        sequence_length=sequence_length
    )
    logger.info("创建 GRU 模型")
    logger.info(f"参数: hidden_size=64, num_layers=2, sequence_length={sequence_length}")

    # 3. 训练模型
    logger.info("开始训练...")
    try:
        trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            epochs=20,
            batch_size=32,
            learning_rate=0.001,
            verbose=True
        )
        logger.info("训练完成!")

        # 4. 预测
        y_pred_test = trainer.predict(X_test)

        # 5. 评估
        test_ic = np.corrcoef(y_test, y_pred_test)[0, 1]
        logger.info(f"测试集 IC: {test_ic:.6f}")

        # 6. 保存模型
        save_path = project_root / 'examples' / 'saved_models' / 'gru_model.pkl'
        trainer.save(str(save_path))
        logger.info(f"模型已保存到: {save_path}")

        return trainer, test_ic

    except Exception as e:
        logger.error(f"GRU 训练出错: {e}")
        return None, None


def main():
    """主函数"""
    logger.info("开始模型基础使用示例")
    logger.info("本示例将演示三种模型的基本用法\n")

    results = {}

    # 示例1: Ridge
    try:
        _, ic = example_ridge_model()
        results['Ridge'] = ic
    except Exception as e:
        logger.error(f"Ridge 示例出错: {e}")
        results['Ridge'] = None

    # 示例2: LightGBM
    try:
        _, ic = example_lightgbm_model()
        results['LightGBM'] = ic
    except Exception as e:
        logger.error(f"LightGBM 示例出错: {e}")
        results['LightGBM'] = None

    # 示例3: GRU
    try:
        _, ic = example_gru_model()
        results['GRU'] = ic
    except Exception as e:
        logger.error(f"GRU 示例出错: {e}")
        results['GRU'] = None

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("示例运行完成！")
    logger.info("=" * 60)
    logger.info("\n测试集 IC 对比:")
    for model_name, ic in results.items():
        if ic is not None:
            logger.info(f"  {model_name:12s}: {ic:.6f}")
        else:
            logger.info(f"  {model_name:12s}: N/A (未运行)")

    logger.info("\n模型文件已保存到: saved_models/")
    logger.info("\n下一步:")
    logger.info("  1. 查看 ensemble_example.py 学习模型集成")
    logger.info("  2. 查看 model_training_pipeline.py 学习完整训练流程")
    logger.info("  3. 查看 model_comparison_demo.py 学习模型对比")


if __name__ == '__main__':
    main()
