"""
机器学习训练和预测 API
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio
import json
import pandas as pd

from app.models.ml_models import (
    MLTrainingTaskCreate,
    MLTrainingTaskResponse,
    MLPredictionRequest,
    MLPredictionResponse
)
from app.services.ml_training_service import MLTrainingService

router = APIRouter()

# 全局服务实例
ml_service = MLTrainingService()


@router.post("/train", response_model=MLTrainingTaskResponse)
async def create_training_task(
    request: MLTrainingTaskCreate,
    background_tasks: BackgroundTasks
):
    """
    创建训练任务

    - **symbol**: 股票代码
    - **model_type**: 模型类型 (lightgbm/gru)
    - **target_period**: 预测周期（天数）
    """
    try:
        # 创建任务
        task_id = await ml_service.create_task(request.dict())

        # 后台启动训练
        background_tasks.add_task(ml_service.start_training, task_id)

        # 返回任务信息
        task = ml_service.get_task(task_id)

        return MLTrainingTaskResponse(**task)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=MLTrainingTaskResponse)
async def get_task_status(task_id: str):
    """
    获取任务状态

    - **task_id**: 任务ID
    """
    task = ml_service.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return MLTrainingTaskResponse(**task)


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 50
):
    """
    列出训练任务

    - **status**: 状态过滤 (pending/running/completed/failed)
    - **limit**: 返回数量限制
    """
    tasks = ml_service.list_tasks(status=status, limit=limit)

    return {
        "total": len(tasks),
        "tasks": [MLTrainingTaskResponse(**t) for t in tasks]
    }


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务

    - **task_id**: 任务ID
    """
    success = ml_service.delete_task(task_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return {"message": "删除成功", "task_id": task_id}


@router.get("/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """
    流式推送训练进度（SSE）

    - **task_id**: 任务ID
    """
    task = ml_service.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    async def event_generator():
        """生成SSE事件"""
        while True:
            task = ml_service.get_task(task_id)

            if not task:
                break

            # 发送进度数据
            data = {
                'status': task['status'],
                'progress': task['progress'],
                'current_step': task['current_step'],
                'metrics': task['metrics'],
                'error_message': task['error_message']
            }

            yield f"data: {json.dumps(data)}\n\n"

            # 如果任务完成或失败，停止推送
            if task['status'] in ['completed', 'failed']:
                break

            # 每秒推送一次
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/predict", response_model=MLPredictionResponse)
async def predict(request: MLPredictionRequest):
    """
    使用训练好的模型进行预测

    - **model_id**: 模型ID（任务ID）
    - **symbol**: 股票代码
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    """
    try:
        result = await ml_service.predict(
            model_id=request.model_id,
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date
        )

        return MLPredictionResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(
    symbol: Optional[str] = None,
    model_type: Optional[str] = None,
    limit: int = 50
):
    """
    列出可用的模型

    - **symbol**: 股票代码过滤
    - **model_type**: 模型类型过滤
    - **limit**: 返回数量限制
    """
    # 获取所有已完成的任务
    tasks = ml_service.list_tasks(status='completed', limit=limit)

    # 过滤
    if symbol:
        tasks = [t for t in tasks if t['config']['symbol'] == symbol]

    if model_type:
        tasks = [t for t in tasks if t['config']['model_type'] == model_type]

    # 转换为模型元数据
    models = []
    for task in tasks:
        if task['metrics']:
            models.append({
                'model_id': task['task_id'],
                'symbol': task['config']['symbol'],
                'model_type': task['config']['model_type'],
                'target_period': task['config'].get('target_period', 5),
                'metrics': task['metrics'],
                'feature_importance': task['feature_importance'],
                'model_path': task['model_path'],
                'trained_at': task['completed_at'],
                'config': task['config']
            })

    return {
        "total": len(models),
        "models": models
    }


@router.get("/features/available")
async def get_available_features():
    """
    获取可用的特征列表

    返回所有可选的技术指标和Alpha因子
    """
    # 技术指标
    technical_indicators = {
        "MA": {"label": "移动平均线", "params": [5, 10, 20, 60, 120, 250]},
        "EMA": {"label": "指数移动平均线", "params": [12, 26, 50]},
        "RSI": {"label": "相对强弱指标", "params": [6, 12, 24]},
        "MACD": {"label": "MACD指标", "params": []},
        "KDJ": {"label": "KDJ指标", "params": []},
        "BOLL": {"label": "布林带", "params": [20]},
        "ATR": {"label": "真实波动幅度", "params": [14, 28]},
        "OBV": {"label": "能量潮", "params": []},
        "CCI": {"label": "顺势指标", "params": [14, 28]},
    }

    # Alpha因子
    alpha_factors = {
        "MOMENTUM": {"label": "动量因子", "params": [5, 10, 20, 60, 120]},
        "REVERSAL": {"label": "反转因子", "params": [1, 3, 5, 20, 60]},
        "VOLATILITY": {"label": "波动率因子", "params": [5, 10, 20, 60]},
        "VOLUME": {"label": "成交量因子", "params": [5, 10, 20]},
        "TREND": {"label": "趋势强度", "params": [20, 60]},
    }

    return {
        "technical_indicators": technical_indicators,
        "alpha_factors": alpha_factors
    }


@router.get("/features/snapshot")
async def get_feature_snapshot(
    symbol: str,
    date: str,
    model_id: Optional[str] = None
):
    """
    获取指定日期的特征快照

    注意：此功能需要先训练模型，从已训练模型的数据中提取特征快照

    - **symbol**: 股票代码
    - **date**: 日期（格式：YYYY-MM-DD或YYYYMMDD）
    - **model_id**: 模型ID（必需，用于从训练数据中获取特征）
    """
    try:
        if not model_id:
            raise HTTPException(
                status_code=400,
                detail="请先选择一个模型，特征快照需要从模型的训练数据中提取"
            )

        # 获取模型任务信息
        task = ml_service.get_task(model_id)
        if not task:
            raise HTTPException(status_code=404, detail="模型不存在")

        # 从任务的训练数据缓存中获取特征数据
        # 训练过程会保存特征数据到文件
        import pickle
        import os
        from datetime import datetime

        # 前端发送的是 YYYY-MM-DD 格式，需要转换
        if '-' in date:
            target_date = datetime.strptime(date, '%Y-%m-%d')
        else:
            target_date = datetime.strptime(date, '%Y%m%d')

        date_obj = pd.Timestamp(target_date.date())

        # 从任务信息中获取模型文件名
        model_name = task.get('model_name')
        if not model_name:
            # 如果没有model_name，使用旧格式
            model_name = f"{symbol}_{task.get('model_type', 'lightgbm')}_{model_id[:8]}"

        # 特征文件路径 - 使用绝对路径
        from pathlib import Path
        models_dir = Path("/data/models/ml_models")
        features_file = models_dir / f"{model_name}_features.pkl"

        if not os.path.exists(features_file):
            # 如果没有保存的特征文件，返回提示信息
            raise HTTPException(
                status_code=404,
                detail="该模型没有保存特征数据，请重新训练模型以保存特征快照"
            )

        # 加载特征数据
        with open(features_file, 'rb') as f:
            data = pickle.load(f)
            X = data.get('X')  # 特征矩阵
            y = data.get('y')  # 目标值

        if X is None or len(X) == 0:
            raise HTTPException(
                status_code=404,
                detail="特征数据为空"
            )

        # 查找指定日期的数据
        if date_obj not in X.index:
            # 尝试查找最接近的日期
            closest_dates = X.index[X.index <= date_obj]
            if len(closest_dates) == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"日期 {date} 不在模型训练数据范围内 ({X.index.min().strftime('%Y-%m-%d')} 到 {X.index.max().strftime('%Y-%m-%d')})"
                )
            date_obj = closest_dates[-1]

        # 获取该日期的所有特征
        row = X.loc[date_obj]

        # 构建特征字典
        features = {}
        for col in X.columns:
            features[col] = float(row[col]) if pd.notna(row[col]) else None

        # 获取目标值
        target = float(y.loc[date_obj]) if date_obj in y.index and pd.notna(y.loc[date_obj]) else None

        # 尝试获取预测值
        prediction = None
        if task.get('predictions'):
            pred_list = task['predictions']
            actual_date_str = date_obj.strftime('%Y-%m-%d')
            for pred in pred_list:
                if pred['date'] == actual_date_str or pred['date'] == date:
                    prediction = pred['prediction']
                    break

        return {
            "date": date_obj.strftime('%Y-%m-%d'),
            "features": features,
            "target": target,
            "prediction": prediction
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
