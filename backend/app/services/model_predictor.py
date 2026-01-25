"""
模型预测服务
负责使用训练好的模型进行预测
"""

import asyncio
import pickle
from pathlib import Path
from typing import Dict, Any, Optional
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

    async def predict_from_task(
        self,
        task_info: Dict[str, Any],
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        使用任务中的模型进行预测

        Args:
            task_info: 任务信息（包含 config 和 model_path）
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            预测结果
        """
        config = task_info['config']
        model_path = task_info.get('model_path')

        if not model_path or not Path(model_path).exists():
            raise ValueError(f"模型文件不存在: {model_path}")

        logger.info(f"使用模型进行预测: {model_path}")

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
            logger.warning("Scaler 不存在，使用原始特征")
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
            'total_samples': len(predictions)
        }

        # 清理无效值
        result = sanitize_float_values(result)

        logger.info(f"✓ 预测完成: {len(predictions)} 个样本")

        return result

    async def predict_from_experiment(
        self,
        experiment_id: int,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        使用实验表中的模型进行预测

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

        logger.info(f"使用实验 {experiment_id} 的模型 {model_id} 进行预测...")

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
            'experiment_id': experiment_id,
            'model_id': model_id,
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
        experiment_id: int,
        symbols: list[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        批量预测多只股票

        Args:
            experiment_id: 实验ID
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            批量预测结果
        """
        results = []
        errors = []

        for symbol in symbols:
            try:
                result = await self.predict_from_experiment(
                    experiment_id=experiment_id,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
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
