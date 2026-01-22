"""
机器学习训练服务
管理训练任务的生命周期
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import json
import pickle
import pandas as pd

from loguru import logger

# 导入core模块
import sys
sys.path.insert(0, '/app/src')

from src.data_pipeline import DataPipeline, get_full_training_data
from src.models.model_trainer import ModelTrainer


class MLTrainingService:
    """机器学习训练服务"""

    def __init__(self):
        """初始化服务"""
        self.tasks: Dict[str, Dict[str, Any]] = {}  # 内存中的任务状态
        self.models_dir = Path('/data/models/ml_models')
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # 任务元数据存储
        self.metadata_file = self.models_dir / 'tasks_metadata.json'
        self._load_metadata()

    def _load_metadata(self):
        """加载任务元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    self.tasks = json.load(f)
                logger.info(f"加载了 {len(self.tasks)} 个历史任务")
            except Exception as e:
                logger.error(f"加载元数据失败: {e}")
                self.tasks = {}

    def _save_metadata(self):
        """保存任务元数据"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.tasks, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存元数据失败: {e}")

    async def create_task(self, config: Dict[str, Any]) -> str:
        """
        创建训练任务

        参数:
            config: 训练配置

        返回:
            task_id: 任务ID
        """
        task_id = str(uuid.uuid4())

        task = {
            'task_id': task_id,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'config': config,
            'progress': 0.0,
            'current_step': 'Created',
            'metrics': None,
            'model_path': None,
            'feature_importance': None,
            'error_message': None
        }

        self.tasks[task_id] = task
        self._save_metadata()

        logger.info(f"创建训练任务: {task_id}")

        return task_id

    async def start_training(self, task_id: str):
        """
        开始训练任务（异步执行）

        参数:
            task_id: 任务ID
        """
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在: {task_id}")

        task = self.tasks[task_id]

        if task['status'] == 'running':
            raise ValueError(f"任务已在运行: {task_id}")

        # 更新状态
        task['status'] = 'running'
        task['started_at'] = datetime.now().isoformat()
        task['progress'] = 0.0
        task['current_step'] = 'Initializing'
        self._save_metadata()

        # 异步执行训练
        asyncio.create_task(self._run_training(task_id))

        logger.info(f"开始训练任务: {task_id}")

    async def _run_training(self, task_id: str):
        """
        执行训练（内部方法）

        参数:
            task_id: 任务ID
        """
        task = self.tasks[task_id]
        config = task['config']

        try:
            # ======== 步骤1: 获取数据 ========
            task['current_step'] = 'Fetching Data'
            task['progress'] = 10.0
            self._save_metadata()

            logger.info(f"[{task_id}] 获取数据...")

            # 使用DataPipeline获取数据
            result = await asyncio.to_thread(
                get_full_training_data,
                symbol=config['symbol'],
                start_date=config['start_date'],
                end_date=config['end_date'],
                target_period=config.get('target_period', 5),
                train_ratio=config.get('train_ratio', 0.7),
                valid_ratio=config.get('valid_ratio', 0.15),
                scale_features=True,
                balance_samples=config.get('balance_samples', False),
                scaler_type=config.get('scaler_type', 'robust')
            )

            X_train, y_train, X_valid, y_valid, X_test, y_test, pipeline = result

            logger.info(f"[{task_id}] 数据获取完成: train={len(X_train)}, valid={len(X_valid)}, test={len(X_test)}")

            # ======== 步骤2: 计算特征 ========
            task['current_step'] = 'Calculating Features'
            task['progress'] = 30.0
            self._save_metadata()

            # 如果指定了特征列表，则筛选
            if config.get('selected_features'):
                selected = config['selected_features']
                X_train = X_train[selected]
                X_valid = X_valid[selected]
                X_test = X_test[selected]
                logger.info(f"[{task_id}] 使用指定特征: {len(selected)} 个")

            # ======== 步骤3: 训练模型 ========
            task['current_step'] = 'Training Model'
            task['progress'] = 50.0
            self._save_metadata()

            logger.info(f"[{task_id}] 开始训练 {config['model_type']} 模型...")

            # 创建训练器
            model_params = config.get('model_params', {})
            trainer = ModelTrainer(
                model_type=config['model_type'],
                model_params=model_params,
                output_dir=str(self.models_dir)
            )

            # 训练
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

            # ======== 步骤4: 评估模型 ========
            task['current_step'] = 'Evaluating Model'
            task['progress'] = 80.0
            self._save_metadata()

            logger.info(f"[{task_id}] 评估模型...")

            metrics = await asyncio.to_thread(
                trainer.evaluate,
                X_test, y_test,
                dataset_name='test',
                verbose=False
            )

            # ======== 步骤5: 保存模型 ========
            task['current_step'] = 'Saving Model'
            task['progress'] = 90.0
            self._save_metadata()

            logger.info(f"[{task_id}] 保存模型...")

            model_name = f"{config['symbol']}_{config['model_type']}_{task_id[:8]}"
            await asyncio.to_thread(
                trainer.save_model,
                model_name,
                save_metrics=True
            )

            # 保存scaler
            scaler_path = self.models_dir / f"{model_name}_scaler.pkl"
            with open(scaler_path, 'wb') as f:
                pickle.dump(pipeline.get_scaler(), f)

            # 保存特征数据（用于特征快照查看器）
            # 合并训练、验证、测试集以包含所有日期的数据
            X_all = pd.concat([X_train, X_valid, X_test]).sort_index()
            y_all = pd.concat([y_train, y_valid, y_test]).sort_index()

            features_path = self.models_dir / f"{model_name}_features.pkl"
            with open(features_path, 'wb') as f:
                pickle.dump({'X': X_all, 'y': y_all}, f)

            logger.info(f"[{task_id}] 保存特征数据: {len(X_all)} 条记录")

            # 获取特征重要性（仅LightGBM）
            feature_importance = None
            if config['model_type'] == 'lightgbm' and hasattr(trainer.model, 'get_feature_importance'):
                importance_df = trainer.model.get_feature_importance('gain', top_n=20)
                feature_importance = dict(zip(
                    importance_df['feature'].tolist(),
                    importance_df['gain'].tolist()
                ))

            # ======== 完成 ========
            task['status'] = 'completed'
            task['progress'] = 100.0
            task['current_step'] = 'Finished'
            task['completed_at'] = datetime.now().isoformat()
            task['metrics'] = metrics
            task['model_name'] = model_name  # 保存模型名称用于特征快照
            task['model_path'] = str(self.models_dir / f"{model_name}.txt" if config['model_type'] == 'lightgbm' else self.models_dir / f"{model_name}.pth")
            task['feature_importance'] = feature_importance

            self._save_metadata()

            logger.info(f"[{task_id}] 训练完成! IC={metrics.get('ic', 0):.4f}")

        except Exception as e:
            logger.error(f"[{task_id}] 训练失败: {e}", exc_info=True)

            task['status'] = 'failed'
            task['current_step'] = 'Failed'
            task['completed_at'] = datetime.now().isoformat()
            task['error_message'] = str(e)

            self._save_metadata()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> list[Dict[str, Any]]:
        """
        列出任务

        参数:
            status: 状态过滤
            limit: 返回数量限制

        返回:
            任务列表
        """
        tasks = list(self.tasks.values())

        # 状态过滤
        if status:
            tasks = [t for t in tasks if t['status'] == status]

        # 按创建时间倒序
        tasks.sort(key=lambda t: t['created_at'], reverse=True)

        return tasks[:limit]

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_metadata()
            logger.info(f"删除任务: {task_id}")
            return True
        return False

    async def predict(
        self,
        model_id: str,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        使用训练好的模型进行预测

        参数:
            model_id: 模型ID（即task_id）
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        返回:
            预测结果
        """
        # 获取任务信息
        task = self.get_task(model_id)
        if not task or task['status'] != 'completed':
            raise ValueError(f"模型不存在或未完成训练: {model_id}")

        config = task['config']

        # 加载模型
        logger.info(f"使用模型 {model_id} 进行预测...")

        # 获取数据（使用相同的Pipeline配置）
        pipeline = DataPipeline(
            target_periods=config.get('target_period', 5),
            scaler_type=config.get('scaler_type', 'robust'),
            cache_features=False,
            verbose=False
        )

        X, y = await asyncio.to_thread(
            pipeline.get_training_data,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            use_cache=False
        )

        # 加载scaler
        scaler_path = Path(task['model_path']).with_name(
            Path(task['model_path']).stem + '_scaler.pkl'
        )
        if scaler_path.exists():
            with open(scaler_path, 'rb') as f:
                scaler = pickle.load(f)
            pipeline.set_scaler(scaler)

        # 缩放特征（使用保存的scaler）
        X_scaled = await asyncio.to_thread(
            scaler.transform,
            X
        )

        import pandas as pd
        X_scaled = pd.DataFrame(X_scaled, columns=X.columns, index=X.index)

        # 加载模型并预测
        trainer = ModelTrainer(
            model_type=config['model_type'],
            output_dir=str(self.models_dir)
        )

        model_name = Path(task['model_path']).stem
        await asyncio.to_thread(
            trainer.load_model,
            model_name
        )

        # 预测
        predictions = await asyncio.to_thread(
            trainer.model.predict,
            X_scaled
        )

        # 组装结果
        results = []
        for idx, (date, pred, actual) in enumerate(zip(X.index, predictions, y.values)):
            results.append({
                'date': date.strftime('%Y-%m-%d'),
                'prediction': float(pred),
                'actual': float(actual)
            })

        # 计算预测指标
        from sklearn.metrics import mean_squared_error, r2_score
        import numpy as np

        rmse = np.sqrt(mean_squared_error(y.values, predictions))
        r2 = r2_score(y.values, predictions)

        # 计算IC
        from scipy.stats import pearsonr, spearmanr
        ic, _ = pearsonr(predictions, y.values)
        rank_ic, _ = spearmanr(predictions, y.values)

        metrics = {
            'rmse': float(rmse),
            'r2': float(r2),
            'ic': float(ic),
            'rank_ic': float(rank_ic),
            'samples': len(predictions)
        }

        return {
            'predictions': results,
            'metrics': metrics
        }
