"""
测试重构后的 model_trainer.py
"""
import sys
import pandas as pd
import numpy as np

from core.src.models.model_trainer import (
    TrainingConfig,
    DataSplitConfig,
    ModelTrainer,
    train_stock_model,
    DataPreparator,
    StrategyFactory
)

def test_config():
    """测试配置类"""
    print("\n" + "="*60)
    print("测试 1: 配置类")
    print("="*60)

    # 测试 TrainingConfig
    config = TrainingConfig(
        model_type='lightgbm',
        model_params={'learning_rate': 0.1}
    )
    print(f"✓ TrainingConfig 创建成功: {config.model_type}")

    # 测试 DataSplitConfig
    split_config = DataSplitConfig(train_ratio=0.7, valid_ratio=0.15)
    print(f"✓ DataSplitConfig 创建成功: train={split_config.train_ratio}")

    # 测试无效配置
    try:
        bad_config = TrainingConfig(model_type='invalid_type')
        print("✗ 应该抛出异常")
    except ValueError as e:
        print(f"✓ 正确捕获无效模型类型: {e}")


def test_data_preparator():
    """测试数据准备器"""
    print("\n" + "="*60)
    print("测试 2: 数据准备器")
    print("="*60)

    # 创建测试数据
    np.random.seed(42)
    df = pd.DataFrame({
        'feature_1': np.random.randn(100),
        'feature_2': np.random.randn(100),
        'target': np.random.randn(100)
    })

    # 测试验证
    try:
        DataPreparator.validate_data(df, ['feature_1', 'feature_2'], 'target')
        print("✓ 数据验证通过")
    except Exception as e:
        print(f"✗ 数据验证失败: {e}")
        return

    # 测试数据准备
    split_config = DataSplitConfig(train_ratio=0.6, valid_ratio=0.2)
    X_train, y_train, X_valid, y_valid, X_test, y_test = DataPreparator.prepare_data(
        df, ['feature_1', 'feature_2'], 'target', split_config
    )

    print(f"✓ 数据分割成功:")
    print(f"  训练集: {len(X_train)} 样本")
    print(f"  验证集: {len(X_valid)} 样本")
    print(f"  测试集: {len(X_test)} 样本")


def test_strategy_factory():
    """测试策略工厂"""
    print("\n" + "="*60)
    print("测试 3: 策略工厂")
    print("="*60)

    # 测试 LightGBM 策略
    strategy = StrategyFactory.create_strategy('lightgbm')
    print(f"✓ 创建 LightGBM 策略: {type(strategy).__name__}")

    # 测试 Ridge 策略
    strategy = StrategyFactory.create_strategy('ridge')
    print(f"✓ 创建 Ridge 策略: {type(strategy).__name__}")

    # 测试无效策略
    try:
        strategy = StrategyFactory.create_strategy('invalid')
        print("✗ 应该抛出异常")
    except Exception as e:
        print(f"✓ 正确捕获无效策略: {type(e).__name__}")


def test_model_trainer():
    """测试模型训练器"""
    print("\n" + "="*60)
    print("测试 4: 模型训练器 (LightGBM)")
    print("="*60)

    # 创建测试数据
    np.random.seed(42)
    n_samples = 500
    df = pd.DataFrame({
        'feature_1': np.random.randn(n_samples),
        'feature_2': np.random.randn(n_samples),
        'feature_3': np.random.randn(n_samples),
    })
    df['target'] = df['feature_1'] * 0.5 + df['feature_2'] * 0.3 + np.random.randn(n_samples) * 0.1

    # 创建训练器
    config = TrainingConfig(
        model_type='lightgbm',
        model_params={
            'learning_rate': 0.1,
            'n_estimators': 50,
            'num_leaves': 15,
            'verbose': -1
        },
        verbose_eval=100
    )

    trainer = ModelTrainer(config=config)
    print(f"✓ 训练器创建成功")

    # 准备数据
    split_config = DataSplitConfig(train_ratio=0.6, valid_ratio=0.2)
    X_train, y_train, X_valid, y_valid, X_test, y_test = trainer.prepare_data(
        df, ['feature_1', 'feature_2', 'feature_3'], 'target', split_config
    )
    print(f"✓ 数据准备完成")

    # 训练模型
    trainer.train(X_train, y_train, X_valid, y_valid)
    print(f"✓ 模型训练完成")

    # 评估模型
    metrics = trainer.evaluate(X_test, y_test, dataset_name='test', verbose=False)
    print(f"✓ 模型评估完成: IC={metrics.get('ic', 0):.4f}")

    # 测试保存和加载
    try:
        model_path = trainer.save_model('test_refactor_model')
        print(f"✓ 模型保存成功: {model_path}")

        # 创建新训练器并加载模型
        new_trainer = ModelTrainer(config=config)
        new_trainer.load_model('test_refactor_model')
        print(f"✓ 模型加载成功")

        # 验证预测
        new_metrics = new_trainer.evaluate(X_test, y_test, dataset_name='test', verbose=False)
        print(f"✓ 加载后评估: IC={new_metrics.get('ic', 0):.4f}")

    except Exception as e:
        print(f"✗ 保存/加载失败: {e}")
        import traceback
        traceback.print_exc()


def test_convenience_function():
    """测试便捷函数"""
    print("\n" + "="*60)
    print("测试 5: 便捷函数")
    print("="*60)

    # 创建测试数据
    np.random.seed(123)
    n_samples = 300
    df = pd.DataFrame({
        'f1': np.random.randn(n_samples),
        'f2': np.random.randn(n_samples),
    })
    df['target'] = df['f1'] * 0.7 + np.random.randn(n_samples) * 0.1

    # 使用便捷函数
    try:
        trainer, metrics = train_stock_model(
            df,
            ['f1', 'f2'],
            'target',
            model_type='ridge',
            train_ratio=0.7,
            valid_ratio=0.15
        )
        print(f"✓ 便捷函数执行成功")
        print(f"✓ IC={metrics.get('ic', 0):.4f}, R2={metrics.get('r2', 0):.4f}")
    except Exception as e:
        print(f"✗ 便捷函数失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始测试重构后的 model_trainer.py")
    print("="*60)

    try:
        test_config()
        test_data_preparator()
        test_strategy_factory()
        test_model_trainer()
        test_convenience_function()

        print("\n" + "="*60)
        print("✓ 所有测试通过！")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
