"""
实验管理API端点
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import json
from loguru import logger

from app.services.experiment_service import ExperimentService
from app.services.parameter_grid import ParameterSpaceTemplates
from app.services.model_ranker import ModelRanker
from app.repositories.batch_repository import BatchRepository
from app.repositories.experiment_repository import ExperimentRepository
from app.api.error_handler import handle_api_errors

router = APIRouter()
experiment_service = ExperimentService()
batch_repo = BatchRepository()
experiment_repo = ExperimentRepository()


# ==================== 请求模型 ====================

class BatchCreateRequest(BaseModel):
    """创建批次请求"""
    batch_name: str = Field(..., description="批次名称（唯一）")
    param_space: Optional[Dict[str, Any]] = Field(None, description="参数空间定义")
    template: Optional[str] = Field(None, description="模板名称（与param_space二选一）")
    strategy: str = Field('grid', description="参数生成策略")
    max_experiments: Optional[int] = Field(None, description="最大实验数")
    description: Optional[str] = Field(None, description="批次描述")
    config: Optional[Dict] = Field(None, description="批次配置")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class BatchStartRequest(BaseModel):
    """启动批次请求"""
    max_workers: Optional[int] = Field(None, description="最大并行Worker数")


# ==================== 批次管理 ====================

@router.post("/batch")
@handle_api_errors
async def create_batch(request: BatchCreateRequest):
    """
    创建实验批次

    可以使用预定义模板或自定义参数空间
    """
    try:
        # 获取参数空间
        if request.param_space:
            param_space = request.param_space
        elif request.template:
            templates = {
                'minimal_test': ParameterSpaceTemplates.minimal_test(),
                'small_grid': ParameterSpaceTemplates.small_grid(),
                'medium_grid': ParameterSpaceTemplates.medium_grid(),
                'large_random': ParameterSpaceTemplates.large_random()
            }
            param_space = templates.get(request.template)
            if not param_space:
                raise HTTPException(status_code=400, detail=f"未知模板: {request.template}")
        else:
            raise HTTPException(status_code=400, detail="必须提供param_space或template")

        # 创建批次
        batch_id = await experiment_service.create_batch(
            batch_name=request.batch_name,
            param_space=param_space,
            strategy=request.strategy,
            max_experiments=request.max_experiments,
            description=request.description,
            config=request.config,
            tags=request.tags
        )

        return {
            "status": "success",
            "message": "批次创建成功",
            "data": {"batch_id": batch_id}
        }

    except Exception as e:
        logger.error(f"创建批次失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/{batch_id}")
@handle_api_errors
async def get_batch_info(batch_id: int):
    """获取批次详细信息"""
    try:
        info = await experiment_service.get_batch_info(batch_id)
        if not info:
            raise HTTPException(status_code=404, detail="批次不存在")

        return {
            "status": "success",
            "data": info
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取批次信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches")
@handle_api_errors
async def list_batches(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None
):
    """列出所有批次"""
    try:
        offset = (page - 1) * limit

        # 使用 Repository 查询批次
        batches = await asyncio.to_thread(
            batch_repo.find_batches_with_stats,
            status=status,
            limit=limit,
            offset=offset
        )

        # 获取总数
        total = await asyncio.to_thread(batch_repo.count_batches, status=status)

        return {
            "status": "success",
            "data": {
                "batches": batches,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            }
        }

    except Exception as e:
        logger.error(f"列出批次失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/batch/{batch_id}")
@handle_api_errors
async def delete_batch(batch_id: int):
    """删除批次（级联删除所有实验）"""
    try:
        # 使用 Repository 删除批次
        result = await asyncio.to_thread(batch_repo.delete_batch_cascade, batch_id)

        return {
            "status": "success",
            "message": f"批次 {batch_id} 已删除",
            "data": result
        }

    except Exception as e:
        logger.error(f"删除批次失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 批次执行 ====================

@router.post("/batch/{batch_id}/start")
@handle_api_errors
async def start_batch(batch_id: int, background_tasks: BackgroundTasks, request: Optional[BatchStartRequest] = None):
    """启动批次（后台任务）"""
    try:
        max_workers = request.max_workers if request else None

        # 在后台运行批次（不阻塞HTTP响应）
        background_tasks.add_task(
            experiment_service.run_batch,
            batch_id,
            max_workers
        )

        return {
            "status": "success",
            "message": f"批次 {batch_id} 已启动，正在后台运行"
        }

    except Exception as e:
        logger.error(f"启动批次失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/{batch_id}/pause")
@handle_api_errors
async def pause_batch(batch_id: int):
    """暂停批次（暂未实现）"""
    raise HTTPException(status_code=501, detail="暂停功能尚未实现")


@router.post("/batch/{batch_id}/cancel")
@handle_api_errors
async def cancel_batch(batch_id: int):
    """取消批次"""
    try:
        # 更新批次状态为 'cancelled'
        await asyncio.to_thread(batch_repo.update_batch_status, batch_id, 'cancelled')

        # 取消所有pending的实验 - 使用 'skipped' 状态（experiments 表的约束只允许 skipped，不允许 cancelled）
        query = "UPDATE experiments SET status = 'skipped' WHERE batch_id = %s AND status = 'pending'"
        await asyncio.to_thread(experiment_repo.execute_update, query, (batch_id,))

        return {
            "status": "success",
            "message": f"批次 {batch_id} 已取消"
        }

    except Exception as e:
        logger.error(f"取消批次失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 实验查询 ====================

@router.get("/batch/{batch_id}/experiments")
@handle_api_errors
async def list_experiments(
    batch_id: int,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500)
):
    """列出批次下的实验"""
    try:
        # 使用 Repository 查询实验
        experiments = await asyncio.to_thread(
            experiment_repo.find_experiments_by_batch,
            batch_id=batch_id,
            status=status,
            limit=limit
        )

        return {
            "status": "success",
            "data": {
                "batch_id": batch_id,
                "experiments": experiments,
                "count": len(experiments)
            }
        }

    except Exception as e:
        logger.error(f"列出实验失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/{batch_id}/top-models")
@handle_api_errors
async def get_top_models(
    batch_id: int,
    top_n: int = Query(10, ge=1, le=100),
    min_sharpe: Optional[float] = None,
    max_drawdown: Optional[float] = None,
    min_annual_return: Optional[float] = None,
    min_win_rate: Optional[float] = None,
    min_ic: Optional[float] = None
):
    """获取Top模型"""
    try:
        ranker = ModelRanker()
        models = ranker.filter_models(
            batch_id=batch_id,
            min_sharpe=min_sharpe,
            max_drawdown=max_drawdown,
            min_annual_return=min_annual_return,
            min_win_rate=min_win_rate,
            min_ic=min_ic,
            top_n=top_n
        )

        return {
            "status": "success",
            "data": {
                "batch_id": batch_id,
                "models": models,
                "count": len(models)
            }
        }

    except Exception as e:
        logger.error(f"获取Top模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/{batch_id}/report")
@handle_api_errors
async def generate_report(batch_id: int):
    """生成实验报告"""
    try:
        ranker = ModelRanker()
        report = ranker.generate_report(batch_id)

        return {
            "status": "success",
            "data": report
        }

    except Exception as e:
        logger.error(f"生成报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/{batch_id}/parameter-importance")
@handle_api_errors
async def get_parameter_importance(batch_id: int):
    """获取参数重要性分析"""
    try:
        ranker = ModelRanker()
        importance = ranker.analyze_parameter_importance(batch_id)

        return {
            "status": "success",
            "data": {
                "batch_id": batch_id,
                "parameter_importance": importance
            }
        }

    except Exception as e:
        logger.error(f"参数重要性分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 实时监控 ====================

@router.get("/batch/{batch_id}/stream")
@handle_api_errors
async def stream_batch_progress(batch_id: int):
    """SSE流式推送批次进度"""

    async def event_generator():
        try:
            while True:
                # 查询批次状态
                info = await experiment_service.get_batch_info(batch_id)

                if not info:
                    yield f"event: error\ndata: {json.dumps({'error': '批次不存在'})}\n\n"
                    break

                # 推送进度（SSE格式：data: {json}\n\n）
                yield f"data: {json.dumps(info)}\n\n"

                # 如果批次已完成，停止推送
                if info['status'] in ['completed', 'failed', 'cancelled']:
                    yield f"event: done\ndata: {json.dumps(info)}\n\n"
                    break

                await asyncio.sleep(2)  # 每2秒推送一次

        except Exception as e:
            logger.error(f"SSE推送失败: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用nginx缓冲
        }
    )


# ==================== 模板管理 ====================

@router.get("/templates")
@handle_api_errors
async def get_templates():
    """获取参数空间模板"""
    templates = {
        'minimal_test': {
            'name': '快速测试',
            'description': '1个实验，用于验证流程',
            'estimated_experiments': 1,
            'param_space': ParameterSpaceTemplates.minimal_test()
        },
        'small_grid': {
            'name': '小规模网格搜索',
            'description': '约100个实验，适合初步探索',
            'estimated_experiments': 100,
            'param_space': ParameterSpaceTemplates.small_grid()
        },
        'medium_grid': {
            'name': '中等规模网格搜索',
            'description': '约500个实验，全面评估',
            'estimated_experiments': 500,
            'param_space': ParameterSpaceTemplates.medium_grid()
        },
        'large_random': {
            'name': '大规模随机采样',
            'description': '配合random策略，可生成数千实验',
            'estimated_experiments': 1000,
            'param_space': ParameterSpaceTemplates.large_random()
        }
    }

    return {
        "status": "success",
        "data": templates
    }


@router.get("/{experiment_id}")
@handle_api_errors
async def get_experiment_detail(experiment_id: int):
    """
    获取单个实验的详细信息

    - **experiment_id**: 实验ID
    """
    try:
        # 使用 Repository 查询实验详情
        experiment = await asyncio.to_thread(experiment_repo.get_experiment_detail, experiment_id)

        if not experiment:
            raise HTTPException(status_code=404, detail=f"实验不存在: {experiment_id}")

        return {
            "status": "success",
            "data": experiment
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实验详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{experiment_id}")
@handle_api_errors
async def delete_experiment(experiment_id: int):
    """
    删除单个实验

    - **experiment_id**: 实验ID
    """
    try:
        # 检查实验是否存在
        experiment = await asyncio.to_thread(experiment_repo.get_experiment_detail, experiment_id)

        if not experiment:
            raise HTTPException(status_code=404, detail=f"实验不存在: {experiment_id}")

        # 删除实验
        await asyncio.to_thread(experiment_repo.delete_experiment, experiment_id)

        return {
            "status": "success",
            "message": f"实验 {experiment_id} 已删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除实验失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 实验详情 ====================

@router.get("/experiment/{exp_id}")
@handle_api_errors
async def get_experiment_detail(exp_id: int):
    """获取单个实验详情"""
    try:
        import sys
        from src.database.db_manager import DatabaseManager
        db = DatabaseManager()

        query = """
            SELECT id, batch_id, experiment_name, model_id, config,
                   train_metrics, backtest_metrics, feature_importance,
                   rank_score, rank_position, status, error_message,
                   train_started_at, train_completed_at, train_duration_seconds,
                   backtest_started_at, backtest_completed_at, backtest_duration_seconds,
                   created_at
            FROM experiments
            WHERE id = %s
        """

        result = await asyncio.to_thread(db._execute_query, query, (exp_id,))

        if not result:
            raise HTTPException(status_code=404, detail="实验不存在")

        row = result[0]
        experiment = {
            'id': row[0],
            'batch_id': row[1],
            'experiment_name': row[2],
            'model_id': row[3],
            'config': row[4],
            'train_metrics': row[5],
            'backtest_metrics': row[6],
            'feature_importance': row[7],
            'rank_score': float(row[8]) if row[8] else None,
            'rank_position': row[9],
            'status': row[10],
            'error_message': row[11],
            'train_started_at': row[12].isoformat() if row[12] else None,
            'train_completed_at': row[13].isoformat() if row[13] else None,
            'train_duration_seconds': row[14],
            'backtest_started_at': row[15].isoformat() if row[15] else None,
            'backtest_completed_at': row[16].isoformat() if row[16] else None,
            'backtest_duration_seconds': row[17],
            'created_at': row[18].isoformat() if row[18] else None
        }

        return {
            "status": "success",
            "data": experiment
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实验详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
