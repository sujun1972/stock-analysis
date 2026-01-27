"""
模型预测服务
负责使用训练好的模型进行预测
"""

import asyncio
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, Union
from loguru import logger
import pandas as pd
import numpy as np

from src.data_pipeline import DataPipeline
from src.models.model_trainer import ModelTrainer
from src.database.db_manager import DatabaseManager
from app.utils.data_cleaning import sanitize_float_values


class ModelPredictor:
    """
    模型预测服务

    职责：
    - 加载训练好的模型
    - 执行预测
    - 处理预测结果
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化预测服务

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        self.db = db or DatabaseManager()

    async def predict(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        model_source: Optional[Union[str, int]] = None,
        task_id: Optional[str] = None,
        experiment_id: Optional[int] = None,
        model_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        统一的预测方法

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            model_source: 模型来源（自动检测：task_id 字符串或 experiment_id 整数）
            task_id: 任务ID（优先级：高）
            experiment_id: 实验ID（优先级：中）
            model_path: 模型路径（优先级：低）
            config: 配置信息（如果提供 model_path，必须提供）

        Returns:
            预测结果

        Raises:
            ValueError: 参数错误或模型不存在
        """
        # 参数优先级处理
        if model_source is not None:
            if isinstance(model_source, int):
                experiment_id = model_source
            elif isinstance(model_source, str):
                # 尝试解析为整数（实验ID）
                try:
                    experiment_id = int(model_source)
                except ValueError:
                    task_id = model_source

        # 根据来源类型获取模型信息
        if task_id:
            return await self._predict_from_task(task_id, symbol, start_date, end_date)
        elif experiment_id is not None:
            return await self._predict_from_experiment(experiment_id, symbol, start_date, end_date)
        elif model_path and config:
            return await self._predict_from_path(model_path, config, symbol, start_date, end_date)
        else:
            raise ValueError(
                "必须提供以下之一: model_source, task_id, experiment_id, 或 (model_path + config)"
            )

    async def _predict_from_task(
        self,
        task_id: str,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        从任务信息进行预测

        Args:
            task_id: 任务ID
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            预测结果
        """
        # 从 TrainingTaskManager 获取任务信息
        from app.services.training_task_manager import TrainingTaskManager
        task_manager = TrainingTaskManager()
        task_info = task_manager.get_task(task_id)

        if not task_info:
            raise ValueError(f"任务不存在: {task_id}")

        if task_info['status'] != 'completed':
            raise ValueError(f"任务未完成: {task_id} (状态: {task_info['status']})")

        config = task_info['config']
        model_path = task_info.get('model_path')

        if not model_path or not Path(model_path).exists():
            raise ValueError(f"模型文件不存在: {model_path}")

        logger.info(f"使用任务 {task_id} 的模型进行预测")

        # 执行预测
        result = await self._execute_prediction(
            model_path=model_path,
            config=config,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

        # 添加任务信息
        result['task_id'] = task_id
        result['model_id'] = task_id

        return result

    async def _predict_from_experiment(
        self,
        experiment_id: int,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        从实验信息进行预测

        Args:
            experiment_id: 实验ID
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            预测结果
        """
        # 查询实验信息
        query = """
            SELECT id, model_id, config, model_path, status
            FROM experiments
            WHERE id = %s
        """

        results = await asyncio.to_thread(self.db._execute_query, query, (experiment_id,))

        if not results or len(results) == 0:
            raise ValueError(f"实验不存在: {experiment_id}")

        exp_id, model_id, config, model_path, status = results[0]

        if status != 'completed':
            raise ValueError(f"实验未完成训练: {experiment_id} (状态: {status})")

        if not model_path or not Path(model_path).exists():
            raise ValueError(f"模型文件不存在: {model_path}")

        logger.info(f"使用实验 {experiment_id} 的模型 {model_id} 进行预测")

        # 执行预测
        result = await self._execute_prediction(
            model_path=model_path,
            config=config,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

        # 添加实验信息
        result['experiment_id'] = experiment_id
        result['model_id'] = model_id

        return result

    async def _predict_from_path(
        self,
        model_path: str,
        config: Dict[str, Any],
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        从模型路径进行预测

        Args:
            model_path: 模型路径
            config: 配置信息
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            预测结果
        """
        if not Path(model_path).exists():
            raise ValueError(f"模型文件不存在: {model_path}")

        logger.info(f"使用模型文件进行预测: {model_path}")

        return await self._execute_prediction(
            model_path=model_path,
            config=config,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

    async def _execute_prediction(
        self,
        model_path: str,
        config: Dict[str, Any],
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        执行预测的核心逻辑

        Args:
            model_path: 模型路径
            config: 配置信息
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            预测结果
        """
        # 获取数据
        X, y, dates = await self._prepare_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            config=config
        )

        # 加载模型和scaler
        model, scaler = await self._load_model_and_scaler(model_path)

        # 特征缩放
        if scaler is not None:
            X_scaled = scaler.transform(X)
        else:
            logger.warning("⚠️ Scaler 不存在，使用原始特征")
            X_scaled = X.values if hasattr(X, 'values') else X

        # 确保 X_scaled 是 numpy array（LightGBM Booster 要求）
        # scaler.transform() 通常返回 numpy array，但为了兼容性统一处理
        if hasattr(X_scaled, 'values'):
            X_scaled = X_scaled.values

        # 执行预测（使用 asyncio.to_thread 避免阻塞事件循环）
        predictions = await asyncio.to_thread(model.predict, X_scaled)

        # 将预测值转换为列表
        pred_list = predictions.tolist() if hasattr(predictions, 'tolist') else predictions

        # 将真实值转换为列表
        y_list = y.tolist() if hasattr(y, 'tolist') else (y if isinstance(y, list) else [])

        # 构建预测结果列表（每个元素包含日期、预测值、真实值）
        predictions_formatted = []
        for i, date in enumerate(dates):
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            pred_value = float(pred_list[i]) if i < len(pred_list) else None
            actual_value = float(y_list[i]) if i < len(y_list) else None

            predictions_formatted.append({
                'date': date_str,
                'prediction': pred_value,
                'actual': actual_value
            })

        # 计算简单指标（如果有真实值）
        metrics = {}
        if len(y_list) > 0:
            try:
                # 过滤掉None值
                valid_pairs = [(p['prediction'], p['actual'])
                              for p in predictions_formatted
                              if p['prediction'] is not None and p['actual'] is not None]

                if valid_pairs:
                    preds = np.array([p[0] for p in valid_pairs])
                    actuals = np.array([p[1] for p in valid_pairs])

                    # RMSE
                    rmse = float(np.sqrt(np.mean((preds - actuals) ** 2)))
                    metrics['rmse'] = rmse

                    # R²
                    ss_res = np.sum((actuals - preds) ** 2)
                    ss_tot = np.sum((actuals - np.mean(actuals)) ** 2)
                    r2 = float(1 - (ss_res / ss_tot)) if ss_tot != 0 else 0.0
                    metrics['r2'] = r2

                    # 样本数
                    metrics['samples'] = len(valid_pairs)
            except Exception as e:
                logger.warning(f"计算指标失败: {e}")
                metrics = {'samples': len(pred_list)}

        # 构建预测结果
        result = {
            'predictions': predictions_formatted,
            'metrics': metrics
        }

        # 清理无效值
        result = sanitize_float_values(result)

        logger.info(f"✓ 预测完成: {len(predictions_formatted)} 个样本")

        return result

    async def _prepare_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        config: Dict[str, Any]
    ) -> tuple:
        """
        准备预测数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            config: 配置信息

        Returns:
            (X, y, dates): 特征、标签、日期
        """
        # 导入配置类
        from src.data_pipeline.pipeline_config import PipelineConfig

        # 创建数据管道
        pipeline = DataPipeline(
            target_periods=config.get('target_period', 5),
            scaler_type=config.get('scaler_type', 'robust'),
            cache_features=False,
            verbose=False
        )

        # 创建管道配置
        pipeline_config = PipelineConfig(
            target_period=config.get('target_period', 5),
            use_cache=False,
            force_refresh=False,
            scaler_type=config.get('scaler_type', 'robust')
        )

        # 获取训练数据
        X, y = await asyncio.to_thread(
            pipeline.get_training_data,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            config=pipeline_config
        )

        # 获取日期索引
        dates = X.index.tolist() if hasattr(X, 'index') else []

        return X, y, dates

    async def _load_model_and_scaler(self, model_path: str) -> tuple:
        """
        加载模型和Scaler

        Args:
            model_path: 模型文件路径

        Returns:
            (model, scaler): 模型和Scaler对象
        """
        model_path = Path(model_path)

        # 加载模型
        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

        # 根据文件扩展名判断模型类型并加载
        # LightGBM: 使用 booster.save_model() 保存为文本格式 (.txt)
        # GRU/其他: 使用 pickle 保存为二进制格式 (.pkl)
        if model_path.suffix == '.txt':
            # LightGBM 模型（需要使用 lgb.Booster 加载）
            import lightgbm as lgb
            model = lgb.Booster(model_file=str(model_path))
            logger.info(f"✓ 已加载 LightGBM 模型: {model_path}")
        elif model_path.suffix in ['.pkl', '.pickle']:
            # Pickle 序列化模型（GRU 或其他深度学习模型）
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            logger.info(f"✓ 已加载 Pickle 模型: {model_path}")
        else:
            # 向后兼容：尝试 pickle 加载未知扩展名
            try:
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                logger.info(f"✓ 已加载模型: {model_path}")
            except Exception as e:
                raise ValueError(f"不支持的模型文件格式: {model_path.suffix}，错误: {e}")

        # 加载scaler
        scaler_path = model_path.with_name(model_path.stem + '_scaler.pkl')
        scaler = None

        if scaler_path.exists():
            try:
                with open(scaler_path, 'rb') as f:
                    scaler = pickle.load(f)

                # 检查加载的scaler是否有效
                if scaler is not None:
                    logger.info(f"✓ 已加载scaler: {scaler_path}")
                else:
                    logger.warning(f"⚠️ Scaler文件损坏（内容为None）: {scaler_path}")
            except Exception as e:
                logger.error(f"加载scaler失败: {e}")
                scaler = None
        else:
            logger.warning(f"⚠️ Scaler文件不存在: {scaler_path}")

        return model, scaler

    async def batch_predict(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
        model_source: Optional[Union[str, int]] = None,
        task_id: Optional[str] = None,
        experiment_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        批量预测多只股票

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            model_source: 模型来源
            task_id: 任务ID
            experiment_id: 实验ID

        Returns:
            批量预测结果
        """
        results = []
        errors = []

        for symbol in symbols:
            try:
                result = await self.predict(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    model_source=model_source,
                    task_id=task_id,
                    experiment_id=experiment_id
                )
                results.append(result)
            except Exception as e:
                logger.error(f"预测失败 {symbol}: {e}")
                errors.append({
                    'symbol': symbol,
                    'error': str(e)
                })

        return {
            'total': len(symbols),
            'success': len(results),
            'failed': len(errors),
            'results': results,
            'errors': errors
        }

    # ==================== 向后兼容方法 ====================

    async def predict_from_task(
        self,
        task_info: Dict[str, Any],
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        向后兼容：使用任务信息进行预测

        Args:
            task_info: 任务信息
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            预测结果
        """
        logger.warning("predict_from_task() 已弃用，请使用 predict(task_id=...)")

        config = task_info['config']
        model_path = task_info.get('model_path')

        return await self.predict(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            model_path=model_path,
            config=config
        )

    async def predict_from_experiment(
        self,
        experiment_id: int,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        向后兼容：使用实验ID进行预测

        Args:
            experiment_id: 实验ID
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            预测结果
        """
        logger.warning("predict_from_experiment() 已弃用，请使用 predict(experiment_id=...)")

        return await self.predict(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            experiment_id=experiment_id
        )
