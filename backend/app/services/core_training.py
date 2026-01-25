"""
统一的核心训练模块
提供可复用的训练流程，供手动训练和自动实验服务调用
消除代码重复，确保训练逻辑的一致性
"""

import asyncio
import pickle
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

import pandas as pd
from loguru import logger

import sys
sys.path.insert(0, '/app/src')

from src.data_pipeline import DataPipeline, get_full_training_data
from src.models.model_trainer import ModelTrainer


class CoreTrainingService:
    """
    核心训练服务

    提供统一的训练流程，包括：
    1. 数据准备
    2. 模型训练
    3. 模型评估
    4. 模型保存
    5. 元数据保存
    """

    def __init__(self, models_dir: str = '/data/models/ml_models'):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    async def train_model(
        self,
        config: Dict[str, Any],
        model_id: Optional[str] = None,
        save_features: bool = True,
        save_training_history: bool = True,
        evaluate_on: str = 'test',  # 'train', 'valid', 'test'
        use_async: bool = True  # 是否使用异步训练
    ) -> Dict[str, Any]:
        """
        统一的训练流程

        Args:
            config: 训练配置字典
                - symbol: 股票代码
                - model_type: 模型类型 ('lightgbm', 'gru')
                - start_date: 开始日期
                - end_date: 结束日期
                - target_period: 预测周期
                - train_ratio: 训练集比例
                - valid_ratio: 验证集比例
                - scale_features: 是否缩放特征
                - balance_samples: 是否平衡样本
                - scaler_type: 缩放器类型
                - model_params: 模型参数
                - selected_features: 特征选择（可选）
                - early_stopping_rounds: 早停轮数（LightGBM）
                - seq_length: 序列长度（GRU）
                - batch_size: 批次大小（GRU）
                - epochs: 训练轮数（GRU）

            model_id: 模型ID（如果未提供则自动生成）
            save_features: 是否保存完整特征数据（用于特征快照）
            save_training_history: 是否保存训练历史（GRU损失曲线）
            evaluate_on: 在哪个数据集上评估 ('train', 'valid', 'test')
            use_async: 是否使用异步训练（手动训练=True，自动实验=False）

        Returns:
            训练结果字典:
                - model_id: 模型ID
                - model_name: 模型名称（同model_id，兼容性）
                - model_path: 模型文件路径
                - scaler_path: Scaler文件路径
                - features_path: 特征数据路径（如果save_features=True）
                - metrics: 评估指标
                - feature_importance: 特征重要性（LightGBM）
                - training_history: 训练历史（GRU）
                - train_duration: 训练耗时（秒）
                - train_samples: 训练集样本数
                - valid_samples: 验证集样本数
                - test_samples: 测试集样本数
                - feature_count: 特征数量
                - trained_at: 训练完成时间
        """

        start_time = datetime.now()

        try:
            # ======== 步骤1: 数据准备 ========
            logger.info(f"[CoreTraining] 获取训练数据...")

            # 使用统一的数据获取接口
            if use_async:
                result = await asyncio.to_thread(
                    get_full_training_data,
                    symbol=config['symbol'],
                    start_date=config['start_date'],
                    end_date=config['end_date'],
                    target_period=config.get('target_period', 5),
                    train_ratio=config.get('train_ratio', 0.7),
                    valid_ratio=config.get('valid_ratio', 0.15),
                    scale_features=config.get('scale_features', True),
                    balance_samples=config.get('balance_samples', False),
                    scaler_type=config.get('scaler_type', 'robust')
                )
            else:
                result = get_full_training_data(
                    symbol=config['symbol'],
                    start_date=config['start_date'],
                    end_date=config['end_date'],
                    target_period=config.get('target_period', 5),
                    train_ratio=config.get('train_ratio', 0.7),
                    valid_ratio=config.get('valid_ratio', 0.15),
                    scale_features=config.get('scale_features', True),
                    balance_samples=config.get('balance_samples', False),
                    scaler_type=config.get('scaler_type', 'robust')
                )

            X_train, y_train, X_valid, y_valid, X_test, y_test, pipeline = result

            logger.info(f"[CoreTraining] 数据准备完成: train={len(X_train)}, valid={len(X_valid)}, test={len(X_test)}")

            # 特征选择（如果指定）
            if config.get('selected_features'):
                selected = config['selected_features']
                X_train = X_train[selected]
                X_valid = X_valid[selected]
                X_test = X_test[selected]
                logger.info(f"[CoreTraining] 使用指定特征: {len(selected)} 个")

            # ======== 步骤2: 创建训练器 ========
            trainer = ModelTrainer(
                model_type=config['model_type'],
                model_params=config.get('model_params', {}),
                output_dir=str(self.models_dir)
            )

            # ======== 步骤3: 训练模型 ========
            logger.info(f"[CoreTraining] 开始训练 {config['model_type']} 模型...")

            if use_async:
                # 异步训练（手动训练服务）
                if config['model_type'] == 'lightgbm':
                    await asyncio.to_thread(
                        trainer.train,
                        X_train, y_train,
                        X_valid, y_valid,
                        early_stopping_rounds=config.get('early_stopping_rounds', 50),
                        verbose_eval=50
                    )
                elif config['model_type'] == 'gru':
                    await asyncio.to_thread(
                        trainer.train,
                        X_train, y_train,
                        X_valid, y_valid,
                        seq_length=config.get('seq_length', 20),
                        batch_size=config.get('batch_size', 64),
                        epochs=config.get('epochs', 100),
                        early_stopping_patience=10
                    )
                else:
                    raise ValueError(f"不支持的模型类型: {config['model_type']}")
            else:
                # 同步训练（自动实验服务）
                if config['model_type'] == 'lightgbm':
                    trainer.train_lightgbm(
                        X_train=X_train,
                        y_train=y_train,
                        X_valid=X_valid,
                        y_valid=y_valid
                    )
                elif config['model_type'] == 'gru':
                    trainer.train_gru(
                        X_train=X_train,
                        y_train=y_train,
                        X_valid=X_valid,
                        y_valid=y_valid
                    )
                else:
                    raise ValueError(f"不支持的模型类型: {config['model_type']}")

            # ======== 步骤4: 评估模型 ========
            logger.info(f"[CoreTraining] 评估模型（数据集: {evaluate_on}）...")

            # 选择评估数据集
            if evaluate_on == 'train':
                X_eval, y_eval = X_train, y_train
            elif evaluate_on == 'valid':
                X_eval, y_eval = X_valid, y_valid
            else:
                X_eval, y_eval = X_test, y_test

            if use_async:
                metrics = await asyncio.to_thread(
                    trainer.evaluate,
                    X_eval, y_eval,
                    dataset_name=evaluate_on,
                    verbose=False
                )
            else:
                metrics = trainer.evaluate(
                    X_eval, y_eval,
                    dataset_name=evaluate_on,
                    verbose=False
                )

            # ======== 步骤5: 生成模型ID ========
            if model_id is None:
                model_id = self._generate_model_id(config)

            # ======== 步骤6: 保存模型 ========
            logger.info(f"[CoreTraining] 保存模型: {model_id}")

            if use_async:
                await asyncio.to_thread(
                    trainer.save_model,
                    model_id,
                    save_metrics=True
                )
            else:
                trainer.save_model(
                    model_name=model_id,
                    save_metrics=True
                )

            # 确定模型文件路径
            if config['model_type'] == 'lightgbm':
                model_path = self.models_dir / f"{model_id}.txt"
            else:
                model_path = self.models_dir / f"{model_id}.pth"

            # ======== 步骤7: 保存Scaler ========
            scaler_path = self.models_dir / f"{model_id}_scaler.pkl"
            with open(scaler_path, 'wb') as f:
                pickle.dump(pipeline.get_scaler(), f)
            logger.info(f"[CoreTraining] ✅ Scaler已保存: {scaler_path}")

            # ======== 步骤8: 保存特征数据（可选） ========
            features_path = None
            if save_features:
                # 合并所有数据集
                X_all = pd.concat([X_train, X_valid, X_test]).sort_index()
                y_all = pd.concat([y_train, y_valid, y_test]).sort_index()

                features_path = self.models_dir / f"{model_id}_features.pkl"
                with open(features_path, 'wb') as f:
                    pickle.dump({'X': X_all, 'y': y_all}, f)
                logger.info(f"[CoreTraining] ✅ 特征数据已保存: {len(X_all)} 条记录")

            # ======== 步骤9: 提取可视化数据 ========
            feature_importance = None
            training_history = None

            if config['model_type'] == 'lightgbm' and hasattr(trainer.model, 'get_feature_importance'):
                # LightGBM: 特征重要性
                try:
                    importance_df = trainer.model.get_feature_importance('gain', top_n=20)
                    if importance_df is not None and not importance_df.empty:
                        feature_importance = dict(zip(
                            importance_df['feature'].tolist(),
                            importance_df['gain'].tolist()
                        ))
                except Exception as e:
                    logger.warning(f"[CoreTraining] 获取特征重要性失败: {e}")

            if config['model_type'] == 'gru' and save_training_history:
                # GRU: 训练历史
                history = trainer.training_history
                if history and 'train_loss' in history:
                    training_history = {
                        'train_loss': [float(loss) for loss in history['train_loss']],
                        'valid_loss': [float(loss) for loss in history.get('valid_loss', [])]
                    }

            # ======== 步骤10: 计算训练耗时 ========
            end_time = datetime.now()
            train_duration = (end_time - start_time).total_seconds()

            # ======== 返回结果 ========
            result = {
                'model_id': model_id,
                'model_name': model_id,  # 兼容旧接口
                'model_path': str(model_path),
                'scaler_path': str(scaler_path),
                'features_path': str(features_path) if features_path else None,
                'metrics': metrics,
                'feature_importance': feature_importance,
                'training_history': training_history,
                'train_duration': int(train_duration),
                'train_samples': len(X_train),
                'valid_samples': len(X_valid),
                'test_samples': len(X_test),
                'feature_count': len(X_train.columns),
                'trained_at': end_time.isoformat()
            }

            logger.info(f"[CoreTraining] ✅ 训练完成! IC={metrics.get('ic', 0):.4f}, 耗时={train_duration:.1f}秒")

            return result

        except Exception as e:
            logger.error(f"[CoreTraining] ❌ 训练失败: {e}", exc_info=True)
            raise

    def _generate_model_id(self, config: Dict) -> str:
        """
        生成模型ID

        格式: {symbol}_{model_type}_T{target_period}_{scaler_type}_{timestamp}
        """
        symbol = config['symbol']
        model_type = config['model_type']
        target_period = config.get('target_period', 5)
        scaler_type = config.get('scaler_type', 'robust')
        timestamp = int(time.time() * 1000)  # 毫秒级时间戳

        return f"{symbol}_{model_type}_T{target_period}_{scaler_type}_{timestamp}"
