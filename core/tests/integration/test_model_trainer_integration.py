"""
Model Trainer 集成测试
测试模型训练器在真实场景下的端到端功能
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil

from core.src.models.model_trainer import (
    TrainingConfig,
    DataSplitConfig,
    ModelTrainer,
    train_stock_model
)


# ==================== Fixtures ====================

@pytest.fixture
def realistic_stock_data():
    """创建更接近真实的股票数据"""
    np.random.seed(42)
    n_samples = 1000
    dates = pd.date_range('2020-01-01', periods=n_samples, freq='D')

    # 模拟技术指标
    df = pd.DataFrame({
        'close': 100 + np.cumsum(np.random.randn(n_samples) * 2),
        'volume': np.random.randint(1000000, 10000000, n_samples),
        'ma_5': np.nan,
        'ma_10': np.nan,
        'rsi': np.random.uniform(20, 80, n_samples),
        'macd': np.random.randn(n_samples),
        'volatility': np.random.uniform(0.01, 0.05, n_samples),
    }, index=dates)

    # 计算移动平均
    df['ma_5'] = df['close'].rolling(5).mean()
    df['ma_10'] = df['close'].rolling(10).mean()

    # 计算收益率特征
    df['return_1d'] = df['close'].pct_change(1)
    df['return_5d'] = df['close'].pct_change(5)
    df['return_10d'] = df['close'].pct_change(10)

    # 目标：未来5日收益率
    df['target'] = df['close'].pct_change(5).shift(-5)

    # 移除 NaN
    df = df.dropna()

    return df


@pytest.fixture
def feature_columns():
    """特征列"""
    return [
        'return_1d', 'return_5d', 'return_10d',
        'ma_5', 'ma_10', 'rsi', 'macd', 'volatility'
    ]


@pytest.fixture
def temp_model_dir():
    """临时模型目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


# ==================== 端到端测试 ====================

class TestEndToEndWorkflow:
    """测试端到端工作流"""

    def test_complete_lightgbm_workflow(
        self,
        realistic_stock_data,
        feature_columns,
        temp_model_dir
    ):
        """测试完整的 LightGBM 工作流"""
        # 1. 配置
        config = TrainingConfig(
            model_type='lightgbm',
            model_params={
                'learning_rate': 0.05,
                'n_estimators': 100,
                'num_leaves': 31,
                'verbose': -1
            },
            output_dir=temp_model_dir,
            early_stopping_rounds=20,
            verbose_eval=100
        )

        # 2. 创建训练器
        trainer = ModelTrainer(config=config)

        # 3. 准备数据
        split_config = DataSplitConfig(train_ratio=0.7, valid_ratio=0.15)
        X_train, y_train, X_valid, y_valid, X_test, y_test = trainer.prepare_data(
            realistic_stock_data,
            feature_columns,
            'target',
            split_config
        )

        # 4. 训练
        trainer.train(X_train, y_train, X_valid, y_valid)

        # 5. 评估
        metrics = trainer.evaluate(X_test, y_test, dataset_name='test', verbose=False)

        # 验证评估指标
        assert 'ic' in metrics
        assert 'rmse' in metrics
        assert 'r2' in metrics
        assert 'long_short_return' in metrics

        # IC 应该在合理范围内
        assert -1 <= metrics['ic'] <= 1

        # 6. 保存模型
        model_path = trainer.save_model('lightgbm_stock_model', save_metrics=True)

        # 验证文件存在
        assert Path(model_path).exists()
        assert Path(temp_model_dir, 'lightgbm_stock_model_meta.json').exists()

        # 7. 加载模型
        new_trainer = ModelTrainer(config=config)
        new_trainer.load_model('lightgbm_stock_model')

        # 8. 验证加载的模型
        new_metrics = new_trainer.evaluate(X_test, y_test, verbose=False)

        # 加载前后的评估结果应该一致
        assert abs(metrics['ic'] - new_metrics['ic']) < 1e-6
        assert abs(metrics['rmse'] - new_metrics['rmse']) < 1e-6

    def test_complete_ridge_workflow(
        self,
        realistic_stock_data,
        feature_columns,
        temp_model_dir
    ):
        """测试完整的 Ridge 工作流"""
        config = TrainingConfig(
            model_type='ridge',
            model_params={'alpha': 1.0},
            output_dir=temp_model_dir
        )

        trainer = ModelTrainer(config=config)

        split_config = DataSplitConfig(train_ratio=0.7, valid_ratio=0.15)
        X_train, y_train, X_valid, y_valid, X_test, y_test = trainer.prepare_data(
            realistic_stock_data,
            feature_columns,
            'target',
            split_config
        )

        trainer.train(X_train, y_train, X_valid, y_valid)
        metrics = trainer.evaluate(X_test, y_test, verbose=False)

        # Ridge 模型评估
        assert 'ic' in metrics
        assert 'r2' in metrics

        # 注意: Ridge 模型目前不支持 save_model
        # 只测试训练和评估功能
        # TODO: 为 Ridge 模型添加 save_model 支持

    def test_convenience_function_workflow(
        self,
        realistic_stock_data,
        feature_columns
    ):
        """测试便捷函数工作流"""
        trainer, metrics = train_stock_model(
            realistic_stock_data,
            feature_columns,
            'target',
            model_type='ridge',
            model_params={'alpha': 0.5},
            train_ratio=0.7,
            valid_ratio=0.15
        )

        # 验证返回值
        assert isinstance(trainer, ModelTrainer)
        assert isinstance(metrics, dict)
        assert trainer.model is not None

        # 验证评估指标
        assert 'ic' in metrics
        assert 'rmse' in metrics


# ==================== 多模型对比测试 ====================

class TestModelComparison:
    """测试多模型对比"""

    def test_compare_lightgbm_and_ridge(
        self,
        realistic_stock_data,
        feature_columns,
        temp_model_dir
    ):
        """对比 LightGBM 和 Ridge 模型"""
        split_config = DataSplitConfig(train_ratio=0.7, valid_ratio=0.15)

        # LightGBM
        lgb_config = TrainingConfig(
            model_type='lightgbm',
            model_params={'n_estimators': 50, 'verbose': -1},
            output_dir=temp_model_dir
        )
        lgb_trainer = ModelTrainer(config=lgb_config)
        X_train, y_train, X_valid, y_valid, X_test, y_test = lgb_trainer.prepare_data(
            realistic_stock_data, feature_columns, 'target', split_config
        )
        lgb_trainer.train(X_train, y_train, X_valid, y_valid)
        lgb_metrics = lgb_trainer.evaluate(X_test, y_test, verbose=False)

        # Ridge
        ridge_config = TrainingConfig(
            model_type='ridge',
            model_params={'alpha': 1.0},
            output_dir=temp_model_dir
        )
        ridge_trainer = ModelTrainer(config=ridge_config)
        ridge_trainer.train(X_train, y_train, X_valid, y_valid)
        ridge_metrics = ridge_trainer.evaluate(X_test, y_test, verbose=False)

        # 两个模型都应该有合理的结果
        assert 'ic' in lgb_metrics
        assert 'ic' in ridge_metrics

        # IC 应该在 [-1, 1] 范围内
        assert -1 <= lgb_metrics['ic'] <= 1
        assert -1 <= ridge_metrics['ic'] <= 1

        print(f"\nLightGBM IC: {lgb_metrics['ic']:.4f}")
        print(f"Ridge IC: {ridge_metrics['ic']:.4f}")


# ==================== 参数调优测试 ====================

class TestParameterTuning:
    """测试参数调优"""

    def test_lightgbm_learning_rate_impact(
        self,
        realistic_stock_data,
        feature_columns,
        temp_model_dir
    ):
        """测试 LightGBM 学习率的影响"""
        split_config = DataSplitConfig(train_ratio=0.7, valid_ratio=0.15)

        learning_rates = [0.01, 0.05, 0.1]
        results = []

        for lr in learning_rates:
            config = TrainingConfig(
                model_type='lightgbm',
                model_params={
                    'learning_rate': lr,
                    'n_estimators': 50,
                    'verbose': -1
                },
                output_dir=temp_model_dir
            )

            trainer = ModelTrainer(config=config)
            X_train, y_train, X_valid, y_valid, X_test, y_test = trainer.prepare_data(
                realistic_stock_data, feature_columns, 'target', split_config
            )

            trainer.train(X_train, y_train, X_valid, y_valid)
            metrics = trainer.evaluate(X_test, y_test, verbose=False)

            results.append({
                'learning_rate': lr,
                'ic': metrics['ic'],
                'rmse': metrics['rmse']
            })

        # 验证所有学习率都产生了结果
        assert len(results) == len(learning_rates)

        # 打印结果
        print("\n学习率影响:")
        for result in results:
            print(f"  LR={result['learning_rate']}: IC={result['ic']:.4f}, RMSE={result['rmse']:.4f}")

    def test_ridge_alpha_impact(
        self,
        realistic_stock_data,
        feature_columns,
        temp_model_dir
    ):
        """测试 Ridge alpha 的影响"""
        split_config = DataSplitConfig(train_ratio=0.7, valid_ratio=0.15)

        alphas = [0.1, 1.0, 10.0]
        results = []

        for alpha in alphas:
            config = TrainingConfig(
                model_type='ridge',
                model_params={'alpha': alpha},
                output_dir=temp_model_dir
            )

            trainer = ModelTrainer(config=config)
            X_train, y_train, X_valid, y_valid, X_test, y_test = trainer.prepare_data(
                realistic_stock_data, feature_columns, 'target', split_config
            )

            trainer.train(X_train, y_train, X_valid, y_valid)
            metrics = trainer.evaluate(X_test, y_test, verbose=False)

            results.append({
                'alpha': alpha,
                'ic': metrics['ic'],
                'r2': metrics['r2']
            })

        # 验证所有 alpha 都产生了结果
        assert len(results) == len(alphas)

        # 打印结果
        print("\nAlpha 影响:")
        for result in results:
            print(f"  Alpha={result['alpha']}: IC={result['ic']:.4f}, R²={result['r2']:.4f}")


# ==================== 数据分割测试 ====================

class TestDataSplitting:
    """测试不同的数据分割策略"""

    def test_different_split_ratios(
        self,
        realistic_stock_data,
        feature_columns,
        temp_model_dir
    ):
        """测试不同的数据分割比例"""
        split_configs = [
            DataSplitConfig(train_ratio=0.6, valid_ratio=0.2),
            DataSplitConfig(train_ratio=0.7, valid_ratio=0.15),
            DataSplitConfig(train_ratio=0.8, valid_ratio=0.1),
        ]

        config = TrainingConfig(
            model_type='ridge',
            output_dir=temp_model_dir
        )

        for split_config in split_configs:
            trainer = ModelTrainer(config=config)

            X_train, y_train, X_valid, y_valid, X_test, y_test = trainer.prepare_data(
                realistic_stock_data,
                feature_columns,
                'target',
                split_config
            )

            # 验证分割比例
            total_samples = len(X_train) + len(X_valid) + len(X_test)
            train_pct = len(X_train) / total_samples
            valid_pct = len(X_valid) / total_samples

            # 允许小的误差
            assert abs(train_pct - split_config.train_ratio) < 0.02
            assert abs(valid_pct - split_config.valid_ratio) < 0.02

            print(f"\n分割比例 {split_config.train_ratio}/{split_config.valid_ratio}:")
            print(f"  训练集: {len(X_train)} ({train_pct:.2%})")
            print(f"  验证集: {len(X_valid)} ({valid_pct:.2%})")
            print(f"  测试集: {len(X_test)} ({1-train_pct-valid_pct:.2%})")


# ==================== 错误恢复测试 ====================

class TestErrorRecovery:
    """测试错误恢复"""

    def test_training_with_partial_nan(
        self,
        realistic_stock_data,
        feature_columns,
        temp_model_dir
    ):
        """测试包含部分 NaN 的训练"""
        # 添加一些 NaN
        df = realistic_stock_data.copy()
        df.loc[df.index[:50], 'return_1d'] = np.nan

        config = TrainingConfig(
            model_type='ridge',
            output_dir=temp_model_dir
        )

        trainer = ModelTrainer(config=config)

        # 数据准备应该能处理 NaN
        split_config = DataSplitConfig(remove_nan=True)
        X_train, y_train, X_valid, y_valid, X_test, y_test = trainer.prepare_data(
            df, feature_columns, 'target', split_config
        )

        # 训练应该成功
        trainer.train(X_train, y_train, X_valid, y_valid)
        metrics = trainer.evaluate(X_test, y_test, verbose=False)

        assert 'ic' in metrics

    def test_save_and_load_with_different_config(
        self,
        realistic_stock_data,
        feature_columns,
        temp_model_dir
    ):
        """测试使用不同配置加载模型"""
        # 训练并保存
        config1 = TrainingConfig(
            model_type='lightgbm',
            model_params={'n_estimators': 50, 'verbose': -1},
            output_dir=temp_model_dir
        )

        trainer1 = ModelTrainer(config=config1)

        split_config = DataSplitConfig()
        X_train, y_train, X_valid, y_valid, X_test, y_test = trainer1.prepare_data(
            realistic_stock_data, feature_columns, 'target', split_config
        )

        trainer1.train(X_train, y_train, X_valid, y_valid)
        trainer1.save_model('test_model')

        # 使用不同的配置加载
        config2 = TrainingConfig(
            model_type='lightgbm',  # 类型应该从元数据中加载
            output_dir=temp_model_dir
        )

        trainer2 = ModelTrainer(config=config2)
        trainer2.load_model('test_model')

        # 应该能正常评估
        metrics = trainer2.evaluate(X_test, y_test, verbose=False)
        assert 'ic' in metrics


# ==================== 性能测试 ====================

class TestPerformance:
    """测试性能"""

    def test_training_speed(
        self,
        realistic_stock_data,
        feature_columns,
        temp_model_dir
    ):
        """测试训练速度"""
        import time

        config = TrainingConfig(
            model_type='lightgbm',
            model_params={'n_estimators': 100, 'verbose': -1},
            output_dir=temp_model_dir
        )

        trainer = ModelTrainer(config=config)

        split_config = DataSplitConfig()
        X_train, y_train, X_valid, y_valid, X_test, y_test = trainer.prepare_data(
            realistic_stock_data, feature_columns, 'target', split_config
        )

        # 测量训练时间
        start_time = time.time()
        trainer.train(X_train, y_train, X_valid, y_valid)
        training_time = time.time() - start_time

        # 测量评估时间
        start_time = time.time()
        metrics = trainer.evaluate(X_test, y_test, verbose=False)
        eval_time = time.time() - start_time

        print(f"\n性能测试:")
        print(f"  训练时间: {training_time:.2f} 秒")
        print(f"  评估时间: {eval_time:.2f} 秒")
        print(f"  IC: {metrics['ic']:.4f}")

        # 训练时间应该在合理范围内（对于小数据集）
        assert training_time < 30  # 30秒内完成


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s', '--tb=short'])
