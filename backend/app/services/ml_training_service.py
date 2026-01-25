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
import numpy as np

from loguru import logger

# 导入core模块
import sys
sys.path.insert(0, '/app/src')

from src.data_pipeline import DataPipeline, get_full_training_data
from src.models.model_trainer import ModelTrainer


def sanitize_float_values(data: Any) -> Any:
    """
    递归清理数据中的无效浮点数值（NaN, Inf, -Inf）
    将无效值转换为 None 以便 JSON 序列化

    此函数用于处理机器学习模型输出中可能出现的特殊浮点值，
    这些值无法被 JSON 序列化，会导致 API 响应失败。

    参数:
        data: 待清理的数据，支持 dict, list, float, int, numpy类型等

    返回:
        清理后的数据，无效浮点数被替换为 None
    """
    if isinstance(data, dict):
        return {k: sanitize_float_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_float_values(item) for item in data]
    elif isinstance(data, float):
        if np.isnan(data) or np.isinf(data):
            return None
        return data
    elif isinstance(data, (np.floating, np.integer)):
        value = float(data)
        if np.isnan(value) or np.isinf(value):
            return None
        return value
    else:
        return data


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

        # 数据库连接
        from database.db_manager import DatabaseManager
        self.db = DatabaseManager()

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

            # 保存完整特征数据用于特征快照查看器
            # 合并训练集、验证集、测试集以覆盖所有历史日期
            X_all = pd.concat([X_train, X_valid, X_test]).sort_index()
            y_all = pd.concat([y_train, y_valid, y_test]).sort_index()

            features_path = self.models_dir / f"{model_name}_features.pkl"
            with open(features_path, 'wb') as f:
                pickle.dump({'X': X_all, 'y': y_all}, f)

            logger.info(f"[{task_id}] 特征数据已保存: {len(X_all)} 条记录")

            # 获取模型特定的可视化数据
            feature_importance = None
            training_history = None

            if config['model_type'] == 'lightgbm' and hasattr(trainer.model, 'get_feature_importance'):
                # LightGBM: 获取特征重要性
                importance_df = trainer.model.get_feature_importance('gain', top_n=20)
                feature_importance = dict(zip(
                    importance_df['feature'].tolist(),
                    importance_df['gain'].tolist()
                ))
            elif config['model_type'] == 'gru':
                # GRU: 保存训练历史（损失曲线）
                history = trainer.training_history
                if history and 'train_loss' in history:
                    training_history = {
                        'train_loss': [float(loss) for loss in history['train_loss']],
                        'valid_loss': [float(loss) for loss in history.get('valid_loss', [])]
                    }

            # ======== 完成 ========
            # ======== 任务完成 ========
            task['status'] = 'completed'
            task['progress'] = 100.0
            task['current_step'] = 'Finished'
            completed_at = datetime.now()
            task['completed_at'] = completed_at.isoformat()
            # 清理指标和特征重要性中的 NaN/Inf 值，避免 JSON 序列化错误
            task['metrics'] = sanitize_float_values(metrics)
            task['feature_importance'] = sanitize_float_values(feature_importance)
            task['training_history'] = sanitize_float_values(training_history)
            task['model_name'] = model_name  # 保存模型名称用于特征快照功能
            task['model_path'] = str(self.models_dir / f"{model_name}.txt" if config['model_type'] == 'lightgbm' else self.models_dir / f"{model_name}.pth")

            self._save_metadata()

            # 将模型信息写入数据库的 experiments 表
            await self._save_to_database(task_id, model_name, metrics, feature_importance, completed_at)

            logger.info(f"[{task_id}] 训练完成! IC={metrics.get('ic', 0):.4f}")

        except Exception as e:
            logger.error(f"[{task_id}] 训练失败: {e}", exc_info=True)

            task['status'] = 'failed'
            task['current_step'] = 'Failed'
            task['completed_at'] = datetime.now().isoformat()
            task['error_message'] = str(e)

            self._save_metadata()

    async def _save_to_database(
        self,
        task_id: str,
        model_name: str,
        metrics: Dict,
        feature_importance: Dict,
        completed_at: datetime
    ):
        """
        将手动训练的模型保存到数据库的 experiments 表

        参数:
            task_id: 任务ID
            model_name: 模型名称
            metrics: 训练指标
            feature_importance: 特征重要性
            completed_at: 完成时间
        """
        try:
            task = self.tasks[task_id]
            config = task['config']

            # 准备插入数据
            experiment_name = f"手动训练_{model_name}"
            experiment_hash = f"manual_{task_id}"

            # 构建config JSON
            config_json = json.dumps({
                'symbol': config['symbol'],
                'model_type': config['model_type'],
                'target_period': config.get('target_period', 5),
                'start_date': config['start_date'],
                'end_date': config['end_date'],
                'test_size': config.get('test_size', 0.2),
                'feature_config': config.get('feature_config', {}),
                'model_params': config.get('model_params', {})
            })

            # 构建train_metrics JSON
            train_metrics_json = json.dumps(sanitize_float_values(metrics))

            # 构建feature_importance JSON（可选）
            feature_importance_json = json.dumps(sanitize_float_values(feature_importance)) if feature_importance else None

            model_path = task['model_path']
            started_at = datetime.fromisoformat(task['started_at'])
            train_duration = int((completed_at - started_at).total_seconds())

            # 插入到数据库
            query = """
                INSERT INTO experiments (
                    batch_id, experiment_name, experiment_hash, config,
                    model_id, model_path, train_metrics, feature_importance,
                    status, train_started_at, train_completed_at, train_duration_seconds,
                    created_at
                )
                VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s)
                ON CONFLICT (experiment_hash) DO UPDATE SET
                    train_metrics = EXCLUDED.train_metrics,
                    feature_importance = EXCLUDED.feature_importance,
                    train_completed_at = EXCLUDED.train_completed_at,
                    train_duration_seconds = EXCLUDED.train_duration_seconds,
                    status = EXCLUDED.status
            """

            params = (
                None,  # batch_id (手动训练为 NULL)
                experiment_name,
                experiment_hash,
                config_json,
                model_name,
                model_path,
                train_metrics_json,
                feature_importance_json,
                'completed',
                started_at,
                completed_at,
                train_duration,
                started_at
            )

            await asyncio.to_thread(self.db._execute_update, query, params)
            logger.info(f"✅ 模型已保存到数据库: {model_name}")

        except Exception as e:
            logger.error(f"保存模型到数据库失败: {e}", exc_info=True)
            # 不抛出异常，避免影响训练流程

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
        # 从训练配置恢复模型参数（GRU需要input_size等参数才能初始化）
        model_params = config.get('model_params') or {}

        # 对于GRU模型，确保包含input_size
        if config['model_type'] == 'gru':
            if 'input_size' not in model_params:
                model_params['input_size'] = len(X.columns)

        trainer = ModelTrainer(
            model_type=config['model_type'],
            model_params=model_params,
            output_dir=str(self.models_dir)
        )

        model_name = Path(task['model_path']).stem
        await asyncio.to_thread(
            trainer.load_model,
            model_name
        )

        # 预测（GRU模型需要seq_length参数）
        if config['model_type'] == 'gru':
            seq_length = config.get('seq_length', 20)
            predictions = await asyncio.to_thread(
                trainer.model.predict,
                X_scaled,
                seq_length=seq_length
            )
            # GRU预测会损失前seq_length个样本，需要对齐
            y = y.iloc[seq_length:]
            X = X.iloc[seq_length:]
        else:
            predictions = await asyncio.to_thread(
                trainer.model.predict,
                X_scaled
            )

        # 组装预测结果
        results = []
        for date, pred, actual in zip(X.index, predictions, y.values):
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
            'metrics': sanitize_float_values(metrics)
        }

    async def predict_from_experiment(
        self,
        experiment_id: int,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        使用实验表中的模型进行预测（新版API）

        参数:
            experiment_id: 实验ID（experiments表主键）
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        返回:
            预测结果
        """
        import sys
        sys.path.insert(0, '/app/src')
        from database.db_manager import DatabaseManager

        # 查询实验信息
        db = DatabaseManager()
        query = """
            SELECT id, model_id, config, model_path, status
            FROM experiments
            WHERE id = %s
        """

        results = await asyncio.to_thread(db._execute_query, query, (experiment_id,))

        if not results or len(results) == 0:
            raise ValueError(f"实验不存在: {experiment_id}")

        exp_id, model_id, config, model_path, status = results[0]

        if status != 'completed':
            raise ValueError(f"实验未完成训练: {experiment_id} (状态: {status})")

        if not model_path:
            raise ValueError(f"实验缺少模型文件路径: {experiment_id}")

        # 加载模型
        logger.info(f"使用实验 {experiment_id} 的模型 {model_id} 进行预测...")

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
        scaler_path = Path(model_path).with_name(
            Path(model_path).stem + '_scaler.pkl'
        )
        scaler = None
        if scaler_path.exists():
            with open(scaler_path, 'rb') as f:
                scaler = pickle.load(f)

            # 检查加载的scaler是否有效（旧模型可能保存了None）
            if scaler is not None:
                pipeline.set_scaler(scaler)
                logger.info(f"✅ 已加载scaler: {scaler_path}")
            else:
                logger.warning(f"⚠️ Scaler文件损坏（内容为None）: {scaler_path}")

        # 如果scaler无效或不存在，使用当前数据重新fit
        if scaler is None:
            logger.warning(f"⚠️ 使用当前数据重新fit scaler（这可能导致预测不准确）")
            from sklearn.preprocessing import RobustScaler
            scaler = RobustScaler()
            scaler.fit(X)
            logger.warning(f"⚠️ 建议重新训练模型以获得准确的scaler")

        # 缩放特征（使用保存的scaler）
        X_scaled = await asyncio.to_thread(
            scaler.transform,
            X
        )

        import pandas as pd
        X_scaled = pd.DataFrame(X_scaled, columns=X.columns, index=X.index)

        # 加载模型并预测
        # 从训练配置恢复模型参数（GRU需要input_size等参数才能初始化）
        model_params = config.get('model_params') or {}

        # 对于GRU模型，确保包含input_size
        if config['model_type'] == 'gru':
            if 'input_size' not in model_params:
                model_params['input_size'] = len(X.columns)

        trainer = ModelTrainer(
            model_type=config['model_type'],
            model_params=model_params,
            output_dir=str(self.models_dir)
        )

        model_name = Path(model_path).stem
        await asyncio.to_thread(
            trainer.load_model,
            model_name
        )

        # 预测（GRU模型需要seq_length参数）
        if config['model_type'] == 'gru':
            seq_length = config.get('seq_length', 20)
            predictions = await asyncio.to_thread(
                trainer.model.predict,
                X_scaled,
                seq_length=seq_length
            )
            # GRU预测会损失前seq_length个样本，需要对齐
            y = y.iloc[seq_length:]
            X = X.iloc[seq_length:]
        else:
            predictions = await asyncio.to_thread(
                trainer.model.predict,
                X_scaled
            )

        # 组装预测结果
        results = []
        for date, pred, actual in zip(X.index, predictions, y.values):
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
            'metrics': sanitize_float_values(metrics)
        }
