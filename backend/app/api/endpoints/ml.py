"""
机器学习训练和预测 API
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio
import json
import pandas as pd
import math

from app.models.ml_models import (
    MLTrainingTaskCreate,
    MLTrainingTaskResponse,
    MLPredictionRequest,
    MLPredictionResponse
)
from app.services.ml_training_service import MLTrainingService
from app.utils.data_cleaning import sanitize_float_values
from app.services.experiment_service import ExperimentService
from app.api.error_handler import handle_api_errors

router = APIRouter()

# 全局服务实例
ml_service = MLTrainingService()
experiment_service = ExperimentService()


@router.post("/train", response_model=MLTrainingTaskResponse)
@handle_api_errors
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
@handle_api_errors
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
@handle_api_errors
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
@handle_api_errors
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
@handle_api_errors
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
@handle_api_errors
async def predict(request: MLPredictionRequest):
    """
    使用训练好的模型进行预测

    - **model_id**: 模型ID（任务ID，兼容旧版）
    - **experiment_id**: 实验ID（新版，优先使用）
    - **symbol**: 股票代码
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    """
    try:
        # 优先使用 experiment_id（新版）
        if request.experiment_id:
            result = await ml_service.predict_from_experiment(
                experiment_id=request.experiment_id,
                symbol=request.symbol,
                start_date=request.start_date,
                end_date=request.end_date
            )
        # 向后兼容：使用 model_id（旧版）
        elif request.model_id:
            result = await ml_service.predict(
                model_id=request.model_id,
                symbol=request.symbol,
                start_date=request.start_date,
                end_date=request.end_date
            )
        else:
            raise HTTPException(status_code=400, detail="必须提供 experiment_id 或 model_id")

        return MLPredictionResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
@handle_api_errors
async def list_models(
    symbol: Optional[str] = None,
    model_type: Optional[str] = None,
    source: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "desc"
):
    """
    列出可用的模型（支持分页和排序）
    统一从 experiments 表读取所有模型（手动训练和自动实验）

    - **symbol**: 股票代码过滤
    - **model_type**: 模型类型过滤 (lightgbm/gru)
    - **source**: 来源过滤 (auto_experiment/manual_training)
    - **page**: 页码（从1开始）
    - **page_size**: 每页数量
    - **sort_by**: 排序字段 (rmse/r2/ic/rank_ic/rank_score/annual_return/sharpe_ratio/max_drawdown)
    - **sort_order**: 排序顺序 (asc/desc)，默认降序
    """
    try:
        # 构建查询条件
        conditions = ["status = %s"]
        params = ['completed']

        # 应用过滤条件
        if symbol:
            conditions.append("config->>'symbol' = %s")
            params.append(symbol)

        if model_type:
            conditions.append("config->>'model_type' = %s")
            params.append(model_type)

        if source:
            if source == 'manual_training':
                conditions.append("batch_id IS NULL")
            elif source == 'auto_experiment':
                conditions.append("batch_id IS NOT NULL")

        where_clause = " AND ".join(conditions)

        # 计算总数
        count_query = f"""
            SELECT COUNT(*) FROM experiments
            WHERE {where_clause}
        """

        from src.database.db_manager import get_database
        db = get_database()

        count_result = await asyncio.to_thread(db._execute_query, count_query, tuple(params))
        total = count_result[0][0] if count_result else 0

        # 计算分页
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        page = max(1, min(page, total_pages))

        # 构建排序子句
        order_clause = "train_completed_at DESC NULLS LAST"  # 默认排序
        if sort_by:
            # 验证排序字段和顺序
            valid_sort_fields = {
                'rmse': "train_metrics->>'rmse'",
                'r2': "train_metrics->>'r2'",
                'ic': "train_metrics->>'ic'",
                'rank_ic': "train_metrics->>'rank_ic'",
                'rank_score': "rank_score",
                'annual_return': "backtest_metrics->>'annualized_return'",
                'sharpe_ratio': "backtest_metrics->>'sharpe_ratio'",
                'max_drawdown': "backtest_metrics->>'max_drawdown'"
            }

            if sort_by in valid_sort_fields:
                sort_direction = "ASC" if sort_order and sort_order.lower() == "asc" else "DESC"
                field_expr = valid_sort_fields[sort_by]

                # 对于JSON字段，需要转换为浮点数进行排序
                if '->' in field_expr:
                    order_clause = f"CAST({field_expr} AS FLOAT) {sort_direction} NULLS LAST"
                else:
                    order_clause = f"{field_expr} {sort_direction} NULLS LAST"

        # 查询数据（带分页和排序），添加回测指标
        offset = (page - 1) * page_size
        data_query = f"""
            SELECT
                id, batch_id, experiment_name, model_id, config,
                train_metrics, backtest_metrics, feature_importance, model_path,
                train_completed_at, rank_score, created_at
            FROM experiments
            WHERE {where_clause}
            ORDER BY {order_clause}
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])

        results = await asyncio.to_thread(db._execute_query, data_query, tuple(params))

        models = []
        for row in results:
            exp_id, batch_id, exp_name, model_id, config, train_metrics, backtest_metrics, feature_importance, model_path, trained_at, rank_score, created_at = row

            # 判断来源
            is_manual = batch_id is None
            source_type = 'manual_training' if is_manual else 'auto_experiment'

            # 提取配置信息
            symbol_code = config.get('symbol', 'Unknown')
            model_type_str = config.get('model_type', 'lightgbm')
            target_period = config.get('target_period', 5)

            # 提取训练指标
            metrics_data = None
            has_metrics = False
            if train_metrics:
                metrics_data = sanitize_float_values({
                    'rmse': train_metrics.get('rmse'),
                    'r2': train_metrics.get('r2'),
                    'ic': train_metrics.get('ic'),
                    'rank_ic': train_metrics.get('rank_ic'),
                    'samples': train_metrics.get('samples'),
                })
                has_metrics = True

            # 提取并扁平化回测指标（与 model_ranker.py 保持一致）
            backtest_data = backtest_metrics or {}

            # 转换为百分比
            annual_return_pct = None
            if backtest_data.get('annualized_return') is not None:
                annual_return_pct = backtest_data['annualized_return'] * 100

            max_drawdown_pct = None
            if backtest_data.get('max_drawdown') is not None:
                max_drawdown_pct = backtest_data['max_drawdown'] * 100

            model_data = {
                'id': exp_id,  # 实验表主键，唯一标识
                'model_id': model_id,  # 模型名称（可能重复）
                'symbol': symbol_code,
                'model_type': model_type_str,
                'target_period': target_period,
                'metrics': metrics_data,
                'feature_importance': sanitize_float_values(feature_importance) if feature_importance else None,
                'model_path': model_path,
                'trained_at': trained_at.isoformat() if trained_at else (created_at.isoformat() if created_at else None),
                'config': config,
                'source': source_type,
                'has_metrics': has_metrics,
                'rank_score': float(rank_score) if rank_score else None,
                'batch_id': batch_id,

                # 扁平化回测指标（与 Top Models 一致）
                'annual_return': annual_return_pct,
                'sharpe_ratio': backtest_data.get('sharpe_ratio'),
                'max_drawdown': max_drawdown_pct,
                'win_rate': backtest_data.get('win_rate'),
                'calmar_ratio': backtest_data.get('calmar_ratio'),
                'backtest_metrics': backtest_data  # 保留完整的回测指标
            }
            models.append(model_data)

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "models": models
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")


@router.get("/features/available")
@handle_api_errors
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
@handle_api_errors
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

        # 导入必要的模块
        import pickle
        import os
        from datetime import datetime
        from pathlib import Path

        # 前端发送的是 YYYY-MM-DD 格式，需要转换
        if '-' in date:
            target_date = datetime.strptime(date, '%Y-%m-%d')
        else:
            target_date = datetime.strptime(date, '%Y%m%d')

        date_obj = pd.Timestamp(target_date.date())

        # 直接使用model_id作为文件名（不再依赖任务查找）
        # model_id本身就是模型名称（如：000001_lightgbm_T5_robust_1234567890）
        models_dir = Path("/data/models/ml_models")
        features_file = models_dir / f"{model_id}_features.pkl"

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
            value = float(row[col]) if pd.notna(row[col]) else None
            features[col] = value

        # 获取目标值
        target = float(y.loc[date_obj]) if date_obj in y.index and pd.notna(y.loc[date_obj]) else None

        # 注意：预测值不在特征快照中存储，需要单独运行预测获取
        # 特征快照主要用于查看训练数据的原始特征值

        # 统一清理所有浮点数值（将 NaN/Inf 转换为 None）
        return {
            "date": date_obj.strftime('%Y-%m-%d'),
            "features": sanitize_float_values(features),
            "target": sanitize_float_values(target),
            "prediction": None  # 预测值需要单独运行预测接口获取
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
