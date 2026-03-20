"""
回测模块 - 异步回测

支持异步回测任务的启动、查询和取消
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Body, Depends, HTTPException, status
from loguru import logger

from app.core_adapters.backtest_adapter import BacktestAdapter
from app.core_adapters.data_adapter import DataAdapter
from app.models.api_response import ApiResponse
from app.utils.data_cleaning import sanitize_float_values
from app.repositories.strategy_execution_repository import StrategyExecutionRepository
from app.api.error_handler import handle_api_errors
from app.core.dependencies import get_current_active_user
from app.models.user import User

# 添加 core 项目到 Python 路径
if Path("/app/core").exists():
    core_path = Path("/app/core")
else:
    core_path = Path(__file__).parent.parent.parent.parent.parent.parent / "core"

if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

# 导入 Core 模块
from src.strategies import StrategyFactory
from src.backtest import BacktestEngine
from src.backtest.performance_analyzer import PerformanceAnalyzer

router = APIRouter()

# 全局适配器实例
backtest_adapter = BacktestAdapter()
data_adapter = DataAdapter()


# 导入核心回测函数
from .execution import execute_backtest_core

# ==================== POST /async ====================

@router.post("/async", summary="启动异步回测（立即返回task_id）", status_code=status.HTTP_202_ACCEPTED)
@handle_api_errors
async def start_async_backtest(
    strategy_id: int = Body(..., description="策略ID（从 strategies 表）"),
    stock_pool: List[str] = Body(..., description="股票代码列表", min_items=1),
    start_date: str = Body(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Body(..., description="结束日期 (YYYY-MM-DD)"),
    initial_capital: float = Body(1000000.0, gt=0, description="初始资金"),
    rebalance_freq: str = Body("W", description="调仓频率 (D/W/M)"),
    commission_rate: float = Body(0.0003, ge=0, le=0.01, description="佣金费率"),
    stamp_tax_rate: float = Body(0.001, ge=0, le=0.01, description="印花税率"),
    min_commission: float = Body(5.0, ge=0, description="最小佣金"),
    slippage: float = Body(0.0, ge=0, description="滑点"),
    strict_mode: bool = Body(True, description="严格模式（代码验证）"),
    strategy_params: Optional[Dict[str, Any]] = Body(None, description="策略参数"),
    exit_strategy_ids: Optional[List[int]] = Body(None, description="离场策略ID列表（可选，支持多个）"),
    current_user: User = Depends(get_current_active_user)
):
    """
    启动异步回测任务（立即返回）

    适用于大规模回测或长时间运行的任务。
    返回 task_id 后，客户端需要通过 GET /backtest/status/{task_id} 轮询任务状态。

    Args:
        strategy_id: 策略ID
        stock_pool: 股票代码列表
        start_date-end_date: 回测时间范围
        其他参数: 与同步接口相同

    Returns:
        {
            "code": 200,
            "message": "回测任务已提交，请使用 task_id 查询进度",
            "data": {
                "task_id": "abc-123-def",
                "execution_id": 456,
                "status": "pending"
            }
        }
    """
    logger.info(f"[异步回测] 启动任务: strategy_id={strategy_id}, stocks={len(stock_pool)}")

    try:
        # 1. 创建执行记录
        execution_repo = StrategyExecutionRepository()
        execution_params = {
            'strategy_id': strategy_id,
            'stock_pool': stock_pool,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'rebalance_freq': rebalance_freq,
            'commission_rate': commission_rate,
            'stamp_tax_rate': stamp_tax_rate,
            'min_commission': min_commission,
            'slippage': slippage,
            'strict_mode': strict_mode,
            'strategy_params': strategy_params,
            'exit_strategy_ids': exit_strategy_ids,
        }

        execution_data = {
            'execution_type': 'backtest',
            'execution_params': execution_params,
            'executed_by': current_user.username,
            'strategy_id': strategy_id,
        }

        execution_id = execution_repo.create(execution_data)
        logger.info(f"[异步回测] 创建执行记录: execution_id={execution_id}")

        # 2. 提交 Celery 异步任务
        from app.tasks.backtest_tasks import run_backtest_async

        task = run_backtest_async.delay(execution_id, execution_params)

        # 3. 更新执行记录的 task_id
        execution_repo.update_task_id(execution_id, task.id)

        logger.info(f"[异步回测] 任务已提交: task_id={task.id}, execution_id={execution_id}")

        return ApiResponse.success(
            data={
                "task_id": task.id,
                "execution_id": execution_id,
                "status": "pending"
            },
            message="回测任务已提交，请使用 task_id 查询进度"
        ).to_dict()

    except Exception as e:
        logger.error(f"[异步回测] 启动失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动异步回测失败: {str(e)}"
        )



# ==================== GET /status/{task_id} ====================

@router.get("/status/{task_id}", summary="查询异步回测任务状态")
@handle_api_errors
async def get_backtest_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    查询异步回测任务状态

    状态说明:
    - PENDING: 任务排队中
    - PROGRESS: 执行中（可能包含进度信息）
    - SUCCESS: 成功完成
    - FAILURE: 执行失败

    Args:
        task_id: 任务ID

    Returns:
        {
            "task_id": "abc-123",
            "status": "SUCCESS",
            "result": {...},  # 成功时返回
            "error": "...",   # 失败时返回
            "progress": {"current": 5, "total": 11, "status": "计算特征..."}  # 执行中时返回
        }
    """
    from celery.result import AsyncResult
    from app.celery_app import celery_app

    try:
        # 查询 Celery 任务状态
        task = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "status": task.state,
        }

        if task.state == 'PENDING':
            response["message"] = "任务排队中..."

        elif task.state == 'PROGRESS':
            # 返回进度信息
            response["progress"] = task.info

        elif task.state == 'SUCCESS':
            # 从数据库获取完整结果
            execution_repo = StrategyExecutionRepository()
            execution = execution_repo.get_by_task_id(task_id)

            if execution and execution.get('result'):
                response["result"] = execution['result']
                response["metrics"] = execution.get('metrics')
                response["execution_id"] = execution['id']
            else:
                # 降级：直接从 Celery 结果获取
                response["result"] = task.result

        elif task.state == 'FAILURE':
            # 返回错误信息
            response["error"] = str(task.info)
            response["message"] = "任务执行失败"

        return response

    except Exception as e:
        logger.error(f"[异步回测] 查询状态失败: task_id={task_id}, error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询任务状态失败: {str(e)}"
        )



# ==================== DELETE /cancel/{task_id} ====================

@router.delete("/cancel/{task_id}", summary="取消异步回测任务")
@handle_api_errors
async def cancel_async_backtest(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    取消正在执行的异步回测任务

    Args:
        task_id: 任务ID

    Returns:
        {"message": "任务已取消"}
    """
    from celery.result import AsyncResult
    from app.celery_app import celery_app

    try:
        # 撤销 Celery 任务
        task = AsyncResult(task_id, app=celery_app)
        task.revoke(terminate=True)

        # 更新数据库状态
        execution_repo = StrategyExecutionRepository()
        execution = execution_repo.get_by_task_id(task_id)

        if execution:
            execution_repo.update_status(execution['id'], 'cancelled')

        logger.info(f"[异步回测] 任务已取消: task_id={task_id}")

        return ApiResponse.success(data={"task_id": task_id}, message="任务已取消").to_dict()

    except Exception as e:
        logger.error(f"[异步回测] 取消任务失败: task_id={task_id}, error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消任务失败: {str(e)}"
        )



