"""
回测模块 - 成本和交易分析

包含交易成本分析和交易统计功能
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
from .schemas import CostAnalysisRequest, TradeStatisticsRequest

router = APIRouter()

# 全局适配器实例
backtest_adapter = BacktestAdapter()
data_adapter = DataAdapter()



# ==================== POST /cost-analysis ====================

@router.post("/cost-analysis")
async def analyze_trading_costs(
    request: CostAnalysisRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    分析交易成本

    ✅ 架构修正版：
    - Backend 只负责：参数验证、调用 Core Adapter、响应格式化
    - Core 负责：成本分析算法

    参数:
    - trades: 交易记录列表

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "total_commission": 1500.0,
            "total_stamp_tax": 5000.0,
            "total_slippage": 200.0,
            "total_cost": 6700.0,
            "cost_ratio": 0.0067,
            "cost_breakdown": {...}
        }
    }
    """
    try:
        logger.info(f"分析交易成本: {len(request.trades)} 笔交易")

        # 1. 转换为 DataFrame
        trades_df = pd.DataFrame(request.trades)

        if trades_df.empty:
            return ApiResponse.bad_request(message="交易记录不能为空").to_dict()

        # 2. 调用 Core Adapter 分析成本
        cost_analysis = await backtest_adapter.analyze_trading_costs(trades_df)

        # 3. Backend 职责：响应格式化
        return ApiResponse.success(data=cost_analysis, message="成本分析完成").to_dict()

    except ValueError as e:
        logger.warning(f"参数验证失败: {e}")
        return ApiResponse.bad_request(message=f"参数错误: {str(e)}").to_dict()

    except Exception as e:
        logger.error(f"成本分析失败: {e}", exc_info=True)
        return ApiResponse.internal_error(message=f"成本分析失败: {str(e)}").to_dict()



# ==================== POST /trade-statistics ====================

@router.post("/trade-statistics")
async def get_trade_statistics(
    request: TradeStatisticsRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取交易统计

    ✅ 架构修正版：
    - Backend 只负责：参数验证、调用 Core Adapter、响应格式化
    - Core 负责：交易统计计算

    参数:
    - trades: 交易记录列表

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "total_trades": 100,
            "winning_trades": 65,
            "losing_trades": 35,
            "win_rate": 0.65,
            "avg_profit": 2500.0,
            "avg_loss": -1200.0,
            "profit_factor": 2.5,
            "total_profit": 162500.0,
            "total_loss": -42000.0
        }
    }
    """
    try:
        logger.info(f"计算交易统计: {len(request.trades)} 笔交易")

        # 1. 转换为 DataFrame
        trades_df = pd.DataFrame(request.trades)

        # 2. 调用 Core Adapter 获取交易统计
        trade_stats = await backtest_adapter.get_trade_statistics(trades_df)

        # 3. Backend 职责：响应格式化
        return ApiResponse.success(data=trade_stats, message="交易统计完成").to_dict()

    except ValueError as e:
        logger.warning(f"参数验证失败: {e}")
        return ApiResponse.bad_request(message=f"参数错误: {str(e)}").to_dict()

    except Exception as e:
        logger.error(f"交易统计失败: {e}", exc_info=True)
        return ApiResponse.internal_error(message=f"交易统计失败: {str(e)}").to_dict()



