"""
回测API
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field
from loguru import logger

from app.services.backtest_service import BacktestService

router = APIRouter()
backtest_service = BacktestService()


class BacktestRequest(BaseModel):
    """回测请求模型"""
    symbols: Union[str, List[str]] = Field(..., description="股票代码(单个或列表)")
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD")
    initial_cash: float = Field(1000000.0, description="初始资金")
    strategy_params: Optional[Dict[str, Any]] = Field(
        default={
            'top_n': 10,
            'holding_period': 5,
            'rebalance_freq': 'W'
        },
        description="策略参数"
    )


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """
    运行回测

    参数:
    - symbols: 股票代码(单个字符串或列表)
    - start_date: 开始日期
    - end_date: 结束日期
    - initial_cash: 初始资金
    - strategy_params: 策略参数
      - top_n: 选股数量(多股模式)
      - holding_period: 持仓期（天）
      - rebalance_freq: 调仓频率（D/W/M）

    返回:
    - 单股模式: K线数据 + 买卖信号点 + 每日净值 + 基准对比
    - 多股模式: 组合净值曲线 + 绩效指标 + 基准对比
    """
    try:
        logger.info(f"收到回测请求: symbols={request.symbols}")

        result = await backtest_service.run_backtest(
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_cash=request.initial_cash,
            strategy_params=request.strategy_params
        )

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"启动回测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{task_id}")
async def get_backtest_result(task_id: str):
    """
    获取回测结果

    参数:
    - task_id: 任务ID

    返回:
    - 回测结果
    """
    try:
        result = backtest_service.get_task_result(task_id)

        if result is None:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

        return {
            "status": "success",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取回测结果失败 {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
