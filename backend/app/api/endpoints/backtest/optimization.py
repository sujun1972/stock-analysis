"""
回测模块 - 参数优化

支持策略参数网格搜索优化
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
from .schemas import OptimizeParamsRequest

router = APIRouter()

# 全局适配器实例
backtest_adapter = BacktestAdapter()
data_adapter = DataAdapter()



# ==================== POST /optimize ====================

@router.post("/optimize")
async def optimize_strategy_params(
    request: OptimizeParamsRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    优化策略参数

    ✅ 架构修正版：
    - Backend 只负责：参数验证、调用 Core Adapter、响应格式化
    - Core 负责：参数优化算法

    参数:
    - stock_codes: 股票代码列表
    - param_grid: 参数网格
      例如: {"short_window": [5, 10, 20], "long_window": [20, 40, 60]}
    - start_date: 开始日期
    - end_date: 结束日期
    - initial_capital: 初始资金
    - metric: 优化目标指标 (默认 sharpe_ratio)

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "best_params": {
                "short_window": 10,
                "long_window": 40
            },
            "best_metric_value": 1.85,
            "metric": "sharpe_ratio",
            "total_combinations": 9,
            "backtest_result": {...}
        }
    }
    """
    try:
        logger.info(f"收到参数优化请求: metric={request.metric}")

        # 1. 参数转换
        start_dt = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(request.end_date, "%Y-%m-%d").date()

        # 2. 调用 Core Adapter 优化参数
        adapter = BacktestAdapter(initial_capital=request.initial_capital)
        optimization_result = await adapter.optimize_strategy_params(
            stock_codes=request.stock_codes,
            param_grid=request.param_grid,
            start_date=start_dt,
            end_date=end_dt,
            metric=request.metric,
        )

        # 3. Backend 职责：响应格式化
        return ApiResponse.success(data=optimization_result, message="参数优化完成").to_dict()

    except ValueError as e:
        logger.warning(f"参数验证失败: {e}")
        return ApiResponse.bad_request(message=f"参数错误: {str(e)}").to_dict()

    except Exception as e:
        logger.error(f"参数优化失败: {e}", exc_info=True)
        return ApiResponse.internal_error(message=f"参数优化失败: {str(e)}").to_dict()



