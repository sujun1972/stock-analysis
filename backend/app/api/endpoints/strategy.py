"""
策略API端点
提供策略元数据查询接口
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from loguru import logger

from app.strategies.strategy_manager import strategy_manager

router = APIRouter()


@router.get("/list")
async def list_strategies() -> Dict[str, Any]:
    """
    获取所有可用策略列表

    返回:
        {
            "status": "success",
            "data": [
                {
                    "id": "complex_indicator",
                    "name": "复合指标策略",
                    "description": "...",
                    "version": "1.0.0",
                    "parameter_count": 13
                }
            ]
        }
    """
    try:
        strategies = strategy_manager.list_strategies()
        return {
            "status": "success",
            "data": strategies
        }
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata")
async def get_strategy_metadata(strategy_id: str = "complex_indicator") -> Dict[str, Any]:
    """
    获取策略完整元数据（包含参数定义）

    参数:
        strategy_id: 策略ID，默认 "complex_indicator"

    返回:
        {
            "status": "success",
            "data": {
                "id": "complex_indicator",
                "name": "复合指标策略",
                "description": "...",
                "version": "1.0.0",
                "parameters": [
                    {
                        "name": "ma_period",
                        "label": "长期均线周期",
                        "type": "integer",
                        "default": 200,
                        "min_value": 50,
                        "max_value": 300,
                        "step": 10,
                        "description": "用于判断长期趋势的移动平均线周期",
                        "category": "趋势"
                    },
                    ...
                ]
            }
        }
    """
    try:
        metadata = strategy_manager.get_strategy_metadata(strategy_id)
        return {
            "status": "success",
            "data": metadata
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取策略元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_strategy_params(
    strategy_id: str,
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    验证策略参数

    参数:
        strategy_id: 策略ID
        params: 策略参数字典

    返回:
        {
            "status": "success",
            "data": {
                "valid": true,
                "message": "参数验证通过"
            }
        }
    """
    try:
        is_valid = strategy_manager.validate_strategy_params(strategy_id, params)

        if is_valid:
            return {
                "status": "success",
                "data": {
                    "valid": True,
                    "message": "参数验证通过"
                }
            }
        else:
            return {
                "status": "error",
                "data": {
                    "valid": False,
                    "message": "参数验证失败"
                }
            }
    except Exception as e:
        logger.error(f"参数验证异常: {e}")
        raise HTTPException(status_code=400, detail=str(e))
