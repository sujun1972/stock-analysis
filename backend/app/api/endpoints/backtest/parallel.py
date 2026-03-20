"""
回测模块 - 并行回测

支持多策略/多参数并行回测
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

# 导入 schemas
from .schemas import ParallelBacktestRequest

router = APIRouter()

# 全局适配器实例
backtest_adapter = BacktestAdapter()
data_adapter = DataAdapter()



# ==================== POST /parallel ====================

@router.post("/parallel")
async def run_parallel_backtest(
    request: ParallelBacktestRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    运行并行回测（多策略/多参数）

    ✅ 架构修正版：
    - Backend 只负责：参数验证、调用 Core Adapter、响应格式化
    - Core 负责：并行回测引擎

    参数:
    - stock_codes: 股票代码列表
    - strategy_params_list: 策略参数列表
    - start_date: 开始日期
    - end_date: 结束日期
    - initial_capital: 初始资金
    - n_processes: 进程数 (默认 4)

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "total_runs": 10,
            "successful_runs": 9,
            "failed_runs": 1,
            "results": [
                {
                    "params": {...},
                    "metrics": {...}
                },
                ...
            ],
            "best_result": {
                "params": {...},
                "metrics": {...}
            }
        }
    }
    """
    try:
        logger.info(f"收到并行回测请求: {len(request.strategy_params_list)} 个策略")

        # 1. 参数转换
        start_dt = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(request.end_date, "%Y-%m-%d").date()

        # 2. 调用 Core Adapter 并行回测
        results = await backtest_adapter.run_parallel_backtest(
            stock_codes=request.stock_codes,
            strategy_params_list=request.strategy_params_list,
            start_date=start_dt,
            end_date=end_dt,
            n_processes=request.n_processes,
        )

        # 3. Backend 职责：结果汇总和格式化
        successful_runs = [r for r in results if r.get("error") is None]
        failed_runs = [r for r in results if r.get("error") is not None]

        # 找出最佳结果
        best_result = None
        if successful_runs:
            best_result = max(
                successful_runs,
                key=lambda x: x.get("metrics", {}).get("sharpe_ratio", float("-inf")),
            )

        response_data = {
            "total_runs": len(results),
            "successful_runs": len(successful_runs),
            "failed_runs": len(failed_runs),
            "results": results,
            "best_result": best_result,
        }

        return ApiResponse.success(
            data=response_data, message=f"并行回测完成: {len(successful_runs)}/{len(results)} 成功"
        ).to_dict()

    except ValueError as e:
        logger.warning(f"参数验证失败: {e}")
        return ApiResponse.bad_request(message=f"参数错误: {str(e)}").to_dict()

    except Exception as e:
        logger.error(f"并行回测失败: {e}", exc_info=True)
        return ApiResponse.internal_error(message=f"并行回测失败: {str(e)}").to_dict()



