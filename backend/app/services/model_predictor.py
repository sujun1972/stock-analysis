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

from data_pipeline import DataPipeline
from models.model_trainer import ModelTrainer
from database.db_manager import DatabaseManager
from app.utils.data_cleaning import sanitize_float_values


class ModelPredictor:
    """
    模型预测服务

    职责：
    - 加载训练好的模型
    - 执行预测
    - 处理预测结果
    """

    def __init__(self):
        """初始化预测服务"""
        self.db = DatabaseManager()

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
            X_scaled = X

        # 执行预测
        predictions = await asyncio.to_thread(model.predict, X_scaled)

        # 构建预测结果
        result = {
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'predictions': predictions.tolist() if hasattr(predictions, 'tolist') else predictions,
            'dates': dates,
            'total_samples': len(predictions),
            'config': config
        }

        # 清理无效值
        result = sanitize_float_values(result)

        logger.info(f"✓ 预测完成: {len(predictions)} 个样本")

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
        # 创建数据管道
        pipeline = DataPipeline(
            target_periods=config.get('target_period', 5),
            scaler_type=config.get('scaler_type', 'robust'),
            cache_features=False,
            verbose=False
        )

        # 获取训练数据
        X, y = await asyncio.to_thread(
            pipeline.get_training_data,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            use_cache=False
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

        with open(model_path, 'rb') as f:
            model = pickle.load(f)

        logger.info(f"✓ 已加载模型: {model_path}")

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
