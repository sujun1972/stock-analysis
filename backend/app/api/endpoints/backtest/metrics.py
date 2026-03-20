"""
回测模块 - 指标计算

包含回测绩效指标和风险指标计算
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



# ==================== POST /metrics ====================

@router.post("/metrics")
async def calculate_metrics(
    portfolio_value: List[float] = Body(..., description="投资组合价值序列"),
    dates: List[str] = Body(..., description="日期序列"),
    trades: List[Dict[str, Any]] = Body(default_factory=list, description="交易记录"),
    positions: List[Dict[str, Any]] = Body(default_factory=list, description="持仓记录"),
    current_user: User = Depends(get_current_active_user)
):
    """
    计算回测绩效指标

    ✅ 架构修正版：
    - Backend 只负责：参数验证、调用 Core Adapter、响应格式化
    - Core 负责：指标计算（20+ 指标）

    参数:
    - portfolio_value: 投资组合价值序列
    - dates: 日期序列
    - trades: 交易记录列表（可选）
    - positions: 持仓记录列表（可选）

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "total_return": 0.25,
            "annual_return": 0.28,
            "sharpe_ratio": 1.5,
            "sortino_ratio": 2.1,
            "max_drawdown": -0.15,
            "calmar_ratio": 1.87,
            "win_rate": 0.65,
            "profit_factor": 2.5,
            "total_trades": 100,
            "avg_holding_period": 5.2,
            ...
        }
    }
    """
    try:
        logger.info(f"计算绩效指标: {len(portfolio_value)} 个数据点")

        # 1. 转换为 pandas 数据结构
        portfolio_series = pd.Series(portfolio_value, index=pd.to_datetime(dates))

        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        positions_df = pd.DataFrame(positions) if positions else pd.DataFrame()

        # 2. 调用 Core Adapter 计算指标
        metrics = await backtest_adapter.calculate_metrics(
            portfolio_value=portfolio_series, positions=positions_df, trades=trades_df
        )

        # 3. Backend 职责：清理 NaN 并响应格式化
        clean_metrics = sanitize_float_values(metrics)
        return ApiResponse.success(data=clean_metrics, message="指标计算完成").to_dict()

    except ValueError as e:
        logger.warning(f"参数验证失败: {e}")
        return ApiResponse.bad_request(message=f"参数错误: {str(e)}").to_dict()

    except Exception as e:
        logger.error(f"指标计算失败: {e}", exc_info=True)
        return ApiResponse.internal_error(message=f"指标计算失败: {str(e)}").to_dict()



# ==================== POST /risk-metrics ====================

@router.post("/risk-metrics")
async def calculate_risk_metrics(
    returns: List[float] = Body(..., description="收益率序列"),
    dates: List[str] = Body(..., description="日期序列"),
    positions: List[Dict[str, Any]] = Body(default_factory=list, description="持仓记录"),
    current_user: User = Depends(get_current_active_user)
):
    """
    计算风险指标

    ✅ 架构修正版：
    - Backend 只负责：参数验证、调用 Core Adapter、响应格式化
    - Core 负责：风险指标计算

    参数:
    - returns: 收益率序列
    - dates: 日期序列
    - positions: 持仓记录（可选）

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "volatility": 0.18,
            "annual_volatility": 0.28,
            "var_95": -0.025,
            "cvar_95": -0.035,
            "downside_volatility": 0.15
        }
    }
    """
    try:
        logger.info(f"计算风险指标: {len(returns)} 个数据点")

        # 1. 转换为 pandas 数据结构
        returns_series = pd.Series(returns, index=pd.to_datetime(dates))
        positions_df = pd.DataFrame(positions) if positions else pd.DataFrame()

        # 2. 调用 Core Adapter 计算风险指标
        risk_metrics = await backtest_adapter.calculate_risk_metrics(
            returns=returns_series, positions=positions_df
        )

        # 3. Backend 职责：响应格式化
        return ApiResponse.success(data=risk_metrics, message="风险指标计算完成").to_dict()

    except ValueError as e:
        logger.warning(f"参数验证失败: {e}")
        return ApiResponse.bad_request(message=f"参数错误: {str(e)}").to_dict()

    except Exception as e:
        logger.error(f"风险指标计算失败: {e}", exc_info=True)
        return ApiResponse.internal_error(message=f"风险指标计算失败: {str(e)}").to_dict()



