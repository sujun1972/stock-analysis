#!/usr/bin/env python3
"""
使用DataPipeline进行端到端模型训练
演示从数据库读取到模型训练的完整流程
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_pipeline import DataPipeline, get_full_training_data, PipelineConfig, DEFAULT_CONFIG
from models.model_trainer import ModelTrainer
import warnings

warnings.filterwarnings('ignore')


def train_lightgbm_example():
    """示例1: 使用LightGBM训练股票预测模型"""
    print("\n" + "="*80)
    print("示例1: LightGBM股票预测模型")
    print("="*80)

    # 1. 创建数据流水线
    pipeline = DataPipeline(
        target_periods=5,        # 预测未来5日收益率
        scaler_type='robust',    # 使用鲁棒缩放（对异常值不敏感）
        cache_features=True,     # 缓存特征以加速后续运行
        verbose=True
    )

    # 2. 获取训练数据
    print("\n[阶段1] 获取训练数据...")
    config = PipelineConfig(
        target_period=5,
        train_ratio=0.7,
        valid_ratio=0.15,
        scale_features=True,
        balance_samples=False,     # LightGBM对不平衡样本较鲁棒，可不平衡
        use_cache=True,
        force_refresh=False,       # 使用缓存（第二次运行会很快）
        scaler_type='robust'
    )
    X, y = pipeline.get_training_data(
        symbol='000001',           # 平安银行
        start_date='20200101',
        end_date='20231231',
        config=config
    )

    # 3. 准备模型数据
    print("\n[阶段2] 准备模型数据...")
    X_train, y_train, X_valid, y_valid, X_test, y_test = pipeline.prepare_for_model(
        X, y,
        config=config,
        fit_scaler=True
    )

    # 4. 创建模型训练器
    print("\n[阶段3] 训练LightGBM模型...")
    trainer = ModelTrainer(
        model_type='lightgbm',
        model_params={
            'learning_rate': 0.05,
            'n_estimators': 500,
            'num_leaves': 31,
            'max_depth': 6,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 0.1
        },
        output_dir='data/models/saved'
    )

    # 5. 训练模型
    trainer.train(
        X_train, y_train,
        X_valid, y_valid,
        early_stopping_rounds=50,
        verbose_eval=50
    )

    # 6. 评估模型
    print("\n[阶段4] 评估模型性能...")

    print("\n训练集评估:")
    train_metrics = trainer.evaluate(X_train, y_train, dataset_name='train', verbose=True)

    print("\n验证集评估:")
    valid_metrics = trainer.evaluate(X_valid, y_valid, dataset_name='valid', verbose=True)

    print("\n测试集评估:")
    test_metrics = trainer.evaluate(X_test, y_test, dataset_name='test', verbose=True)

    # 7. 特征重要性
    print("\n[阶段5] 分析特征重要性...")
    if hasattr(trainer.model, 'get_feature_importance'):
        importance_df = trainer.model.get_feature_importance('gain', top_n=20)
        print("\nTop 20 重要特征:")
        print(importance_df.to_string(index=False))

    # 8. 保存模型
    print("\n[阶段6] 保存模型...")
    model_name = '000001_lgb_5d_return'
    trainer.save_model(model_name, save_metrics=True)

    # 保存scaler（用于推理）
    import pickle
    scaler_path = f'data/models/saved/{model_name}_scaler.pkl'
    with open(scaler_path, 'wb') as f:
        pickle.dump(pipeline.get_scaler(), f)
    print(f"✓ Scaler已保存至: {scaler_path}")

    print("\n" + "="*80)
    print("✓ LightGBM训练完成")
    print("="*80)

    return trainer, pipeline, test_metrics


def train_gru_example():
    """示例2: 使用GRU训练时序预测模型"""
    print("\n" + "="*80)
    print("示例2: GRU时序预测模型")
    print("="*80)

    try:
        import torch
    except ImportError:
        print("PyTorch未安装，跳过GRU示例")
        print("安装命令: pip install torch")
        return

    # 1. 一键获取数据（使用便捷函数）
    print("\n[阶段1] 一键获取训练数据...")
    config = PipelineConfig(
        target_period=10,          # 预测未来10日收益率
        train_ratio=0.7,
        valid_ratio=0.15,
        scale_features=True,       # GRU必须缩放特征！
        balance_samples=True,      # 样本平衡
        scaler_type='standard'     # GRU通常用标准化
    )
    X_train, y_train, X_valid, y_valid, X_test, y_test, pipeline = get_full_training_data(
        symbol='600519',           # 贵州茅台
        start_date='20200101',
        end_date='20231231',
        config=config
    )

    # 2. 创建GRU训练器
    print("\n[阶段2] 训练GRU模型...")
    trainer = ModelTrainer(
        model_type='gru',
        model_params={
            'hidden_size': 64,
            'num_layers': 2,
            'dropout': 0.2,
            'bidirectional': False,
            'learning_rate': 0.001
        },
        output_dir='data/models/saved'
    )

    # 3. 训练模型
    trainer.train(
        X_train, y_train,
        X_valid, y_valid,
        seq_length=20,             # 时序长度
        batch_size=64,
        epochs=100,
        early_stopping_patience=10
    )

    # 4. 评估模型
    print("\n[阶段3] 评估模型性能...")
    test_metrics = trainer.evaluate(X_test, y_test, dataset_name='test', verbose=True)

    # 5. 保存模型
    print("\n[阶段4] 保存模型...")
    model_name = '600519_gru_10d_return'
    trainer.save_model(model_name, save_metrics=True)

    # 保存scaler
    import pickle
    scaler_path = f'data/models/saved/{model_name}_scaler.pkl'
    with open(scaler_path, 'wb') as f:
        pickle.dump(pipeline.get_scaler(), f)
    print(f"✓ Scaler已保存至: {scaler_path}")

    print("\n" + "="*80)
    print("✓ GRU训练完成")
    print("="*80)

    return trainer, pipeline, test_metrics


def compare_models():
    """示例3: 对比不同模型和预测周期"""
    print("\n" + "="*80)
    print("示例3: 多模型对比实验")
    print("="*80)

    symbol = '000001'
    start_date = '20200101'
    end_date = '20231231'

    results = []

    # 测试不同预测周期
    for target_period in [5, 10, 20]:
        print(f"\n{'='*60}")
        print(f"预测周期: {target_period}日")
        print(f"{'='*60}")

        # 获取数据
        pipeline = DataPipeline(
            target_periods=target_period,
            scaler_type='robust',
            verbose=False  # 减少输出
        )

        config = PipelineConfig(
            target_period=target_period,
            train_ratio=0.7,
            valid_ratio=0.15,
            scale_features=True
        )
        X, y = pipeline.get_training_data(symbol, start_date, end_date, config)

        X_train, y_train, X_valid, y_valid, X_test, y_test = pipeline.prepare_for_model(
            X, y,
            config=config
        )

        # 训练LightGBM
        print(f"\n训练LightGBM (T={target_period})...")
        trainer_lgb = ModelTrainer(model_type='lightgbm', model_params={'verbose': -1})
        trainer_lgb.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)
        metrics_lgb = trainer_lgb.evaluate(X_test, y_test, dataset_name='test', verbose=False)

        results.append({
            'model': 'LightGBM',
            'target_period': target_period,
            'rmse': metrics_lgb['rmse'],
            'r2': metrics_lgb['r2'],
            'ic': metrics_lgb['ic'],
            'rank_ic': metrics_lgb['rank_ic']
        })

    # 打印对比结果
    print("\n" + "="*80)
    print("模型对比结果")
    print("="*80)

    import pandas as pd
    results_df = pd.DataFrame(results)
    print("\n" + results_df.to_string(index=False))

    print("\n最佳配置:")
    best_by_ic = results_df.loc[results_df['ic'].idxmax()]
    print(f"  最佳IC: {best_by_ic['model']} (T={best_by_ic['target_period']}, IC={best_by_ic['ic']:.4f})")

    best_by_r2 = results_df.loc[results_df['r2'].idxmax()]
    print(f"  最佳R²: {best_by_r2['model']} (T={best_by_r2['target_period']}, R²={best_by_r2['r2']:.4f})")


def batch_train_stocks():
    """示例4: 批量训练多只股票"""
    print("\n" + "="*80)
    print("示例4: 批量训练多只股票")
    print("="*80)

    # 股票列表（示例）
    stocks = ['000001', '600519', '000858']  # 平安银行、贵州茅台、五粮液
    target_period = 5

    for symbol in stocks:
        try:
            print(f"\n{'='*60}")
            print(f"训练股票: {symbol}")
            print(f"{'='*60}")

            # 获取数据
            config = PipelineConfig(
                target_period=target_period,
                scale_features=True,
                balance_samples=False
            )
            X_train, y_train, X_valid, y_valid, X_test, y_test, pipeline = get_full_training_data(
                symbol=symbol,
                start_date='20210101',
                end_date='20231231',
                config=config
            )

            # 训练模型
            trainer = ModelTrainer(
                model_type='lightgbm',
                model_params={'verbose': -1}
            )

            trainer.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)

            # 评估
            metrics = trainer.evaluate(X_test, y_test, dataset_name='test', verbose=False)

            print(f"\n{symbol} 测试集指标:")
            print(f"  RMSE: {metrics['rmse']:.4f}")
            print(f"  R²: {metrics['r2']:.4f}")
            print(f"  IC: {metrics['ic']:.4f}")
            print(f"  Rank IC: {metrics['rank_ic']:.4f}")

            # 保存模型
            model_name = f'{symbol}_lgb_{target_period}d'
            trainer.save_model(model_name, save_metrics=True)

        except Exception as e:
            print(f"✗ {symbol} 训练失败: {e}")
            continue

    print("\n" + "="*80)
    print("✓ 批量训练完成")
    print("="*80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='使用DataPipeline训练股票预测模型')
    parser.add_argument('--example', type=str, default='1',
                       choices=['1', '2', '3', '4', 'all'],
                       help='示例编号 (1=LightGBM, 2=GRU, 3=模型对比, 4=批量训练, all=运行所有)')

    args = parser.parse_args()

    print("\n" + "="*80)
    print("使用DataPipeline进行端到端模型训练")
    print("="*80)

    if args.example == '1' or args.example == 'all':
        train_lightgbm_example()

    if args.example == '2' or args.example == 'all':
        train_gru_example()

    if args.example == '3' or args.example == 'all':
        compare_models()

    if args.example == '4' or args.example == 'all':
        batch_train_stocks()

    print("\n" + "="*80)
    print("✓ 所有训练任务完成")
    print("="*80)
    print("\n使用方法:")
    print("  python train_model_with_pipeline.py --example 1  # 运行LightGBM示例")
    print("  python train_model_with_pipeline.py --example 2  # 运行GRU示例")
    print("  python train_model_with_pipeline.py --example 3  # 运行模型对比")
    print("  python train_model_with_pipeline.py --example 4  # 运行批量训练")
    print("  python train_model_with_pipeline.py --example all  # 运行所有示例")
