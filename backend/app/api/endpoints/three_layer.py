"""
三层架构策略 API

✅ 任务 2: REST API 端点实现
- 5个API端点：获取选股器/入场/退出/验证/回测
- Pydantic 模型定义完整
- 参数验证正确
- 错误处理完善
- OpenAPI 文档自动生成

作者: Backend Team
创建日期: 2026-02-06
版本: 1.0.0
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

from app.core_adapters.three_layer_adapter import ThreeLayerAdapter
from app.models.api_response import ApiResponse

router = APIRouter()

# 全局适配器实例
three_layer_adapter = ThreeLayerAdapter()


# ==================== Pydantic 模型 ====================


class ParameterMetadata(BaseModel):
    """参数元数据"""

    name: str = Field(..., description="参数名称")
    label: str = Field(..., description="参数标签")
    type: str = Field(..., description="参数类型")
    default: Any = Field(..., description="默认值")
    description: str = Field(..., description="参数描述")
    min_value: Optional[float] = Field(None, description="最小值")
    max_value: Optional[float] = Field(None, description="最大值")
    options: Optional[List[Any]] = Field(None, description="可选值列表")


class StrategyMetadata(BaseModel):
    """策略元数据"""

    id: str = Field(..., description="策略ID")
    name: str = Field(..., description="策略名称")
    description: str = Field(..., description="策略描述")
    version: str = Field(..., description="版本号")
    parameters: List[ParameterMetadata] = Field(..., description="参数列表")


class StrategyConfig(BaseModel):
    """策略配置"""

    id: str = Field(..., description="策略ID")
    params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")


class ValidationRequest(BaseModel):
    """策略验证请求"""

    selector: StrategyConfig = Field(..., description="选股器配置")
    entry: StrategyConfig = Field(..., description="入场策略配置")
    exit: StrategyConfig = Field(..., description="退出策略配置")
    rebalance_freq: str = Field(..., description="调仓频率: D/W/M")

    class Config:
        json_schema_extra = {
            "example": {
                "selector": {"id": "momentum", "params": {"lookback_period": 20, "top_n": 50}},
                "entry": {"id": "immediate", "params": {}},
                "exit": {"id": "fixed_stop_loss", "params": {"stop_loss_pct": -5.0}},
                "rebalance_freq": "W",
            }
        }


class BacktestRequest(BaseModel):
    """回测请求"""

    selector: StrategyConfig = Field(..., description="选股器配置")
    entry: StrategyConfig = Field(..., description="入场策略配置")
    exit: StrategyConfig = Field(..., description="退出策略配置")
    rebalance_freq: str = Field("W", description="调仓频率: D/W/M")
    start_date: str = Field(..., description="开始日期: YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期: YYYY-MM-DD")
    initial_capital: float = Field(1000000.0, gt=0, description="初始资金")
    stock_codes: Optional[List[str]] = Field(None, description="股票池（可选）")

    class Config:
        json_schema_extra = {
            "example": {
                "selector": {"id": "momentum", "params": {"lookback_period": 20, "top_n": 50}},
                "entry": {"id": "immediate", "params": {}},
                "exit": {"id": "fixed_stop_loss", "params": {"stop_loss_pct": -5.0}},
                "rebalance_freq": "W",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "initial_capital": 1000000.0,
                "stock_codes": None,
            }
        }


# ==================== API 端点 ====================


@router.get("/selectors")
async def get_selectors():
    """
    获取所有可用的选股器

    返回所有选股器的元数据，包括：
    - 选股器ID和名称
    - 策略描述和版本
    - 参数定义（名称、类型、默认值、取值范围）

    响应缓存: Redis 1天

    返回:
    {
        "code": 200,
        "message": "获取选股器列表成功",
        "data": [
            {
                "id": "momentum",
                "name": "动量选股器",
                "description": "选择近期涨幅最大的股票",
                "version": "1.0.0",
                "parameters": [
                    {
                        "name": "lookback_period",
                        "label": "动量计算周期（天）",
                        "type": "integer",
                        "default": 20,
                        "description": "计算动量的回溯天数",
                        "min_value": 5,
                        "max_value": 200
                    },
                    ...
                ]
            },
            ...
        ]
    }
    """
    try:
        logger.info("获取选股器列表")
        selectors = await three_layer_adapter.get_selectors()
        return ApiResponse.success(data=selectors, message="获取选股器列表成功").to_dict()
    except Exception as e:
        logger.error(f"获取选股器列表失败: {e}", exc_info=True)
        return ApiResponse.internal_error(message=f"获取选股器列表失败: {str(e)}").to_dict()


@router.get("/entries")
async def get_entries():
    """
    获取所有可用的入场策略

    返回所有入场策略的元数据，包括：
    - 策略ID和名称
    - 策略描述和版本
    - 参数定义（名称、类型、默认值、取值范围）

    响应缓存: Redis 1天

    返回:
    {
        "code": 200,
        "message": "获取入场策略列表成功",
        "data": [
            {
                "id": "immediate",
                "name": "立即入场",
                "description": "选股后立即入场",
                "version": "1.0.0",
                "parameters": []
            },
            ...
        ]
    }
    """
    try:
        logger.info("获取入场策略列表")
        entries = await three_layer_adapter.get_entries()
        return ApiResponse.success(data=entries, message="获取入场策略列表成功").to_dict()
    except Exception as e:
        logger.error(f"获取入场策略列表失败: {e}", exc_info=True)
        return ApiResponse.internal_error(message=f"获取入场策略列表失败: {str(e)}").to_dict()


@router.get("/exits")
async def get_exits():
    """
    获取所有可用的退出策略

    返回所有退出策略的元数据，包括：
    - 策略ID和名称
    - 策略描述和版本
    - 参数定义（名称、类型、默认值、取值范围）

    响应缓存: Redis 1天

    返回:
    {
        "code": 200,
        "message": "获取退出策略列表成功",
        "data": [
            {
                "id": "fixed_stop_loss",
                "name": "固定止损",
                "description": "固定百分比止损策略",
                "version": "1.0.0",
                "parameters": [
                    {
                        "name": "stop_loss_pct",
                        "label": "止损百分比",
                        "type": "float",
                        "default": -5.0,
                        "description": "触发止损的跌幅百分比",
                        "min_value": -50.0,
                        "max_value": 0.0
                    }
                ]
            },
            ...
        ]
    }
    """
    try:
        logger.info("获取退出策略列表")
        exits = await three_layer_adapter.get_exits()
        return ApiResponse.success(data=exits, message="获取���出策略列表成功").to_dict()
    except Exception as e:
        logger.error(f"获取退出策略列表失败: {e}", exc_info=True)
        return ApiResponse.internal_error(message=f"获取退出策略列表失败: {str(e)}").to_dict()


@router.post("/validate")
async def validate_strategy(request: ValidationRequest):
    """
    验证策略组合的有效性

    验证内容：
    1. 策略ID是否存在
    2. 参数类型和取值范围是否正确
    3. 调仓频率是否合法（D/W/M）
    4. 策略组合是否兼容

    参数:
    - selector: 选股器配置 (id + params)
    - entry: 入场策略配置 (id + params)
    - exit: 退出策略配置 (id + params)
    - rebalance_freq: 调仓频率 (D/W/M)

    返回:
    {
        "code": 200,
        "message": "策略组合有效",
        "data": {
            "valid": true
        }
    }

    错误响应 (400):
    {
        "code": 400,
        "message": "策略验证失败",
        "data": {
            "errors": ["未知的选股器: unknown_selector", ...]
        }
    }
    """
    try:
        logger.info(
            f"验证策略组合: selector={request.selector.id}, "
            f"entry={request.entry.id}, exit={request.exit.id}"
        )

        # 调用适配器验证
        result = await three_layer_adapter.validate_strategy_combo(
            selector_id=request.selector.id,
            selector_params=request.selector.params,
            entry_id=request.entry.id,
            entry_params=request.entry.params,
            exit_id=request.exit.id,
            exit_params=request.exit.params,
            rebalance_freq=request.rebalance_freq,
        )

        # 检查验证结果
        if not result.get("valid"):
            errors = result.get("errors", ["未知错误"])
            logger.warning(f"策略验证失败: {errors}")
            return ApiResponse.bad_request(message="策略验证失败", data={"errors": errors}).to_dict()

        return ApiResponse.success(data={"valid": True}, message="策略组合有效").to_dict()

    except Exception as e:
        logger.error(f"策略验证过程出错: {e}", exc_info=True)
        return ApiResponse.internal_error(message=f"策略验证过程出错: {str(e)}").to_dict()


@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """
    执行三层架构回测

    使用指定的选股器、入场策略和退出策略进行回测。

    参数:
    - selector: 选股器配置
        - id: 选股器ID (momentum/value/external/ml)
        - params: 选股器参数
    - entry: 入场策略配置
        - id: 入场策略ID (immediate/ma_breakout/rsi_oversold)
        - params: 入场策略参数
    - exit: 退出策略配置
        - id: 退出策略ID (fixed_stop_loss/atr_stop_loss/time_based/combined)
        - params: 退出策略参数
    - rebalance_freq: 调仓频率 (D=每日, W=每周, M=每月)
    - start_date: 回测开始日期 (YYYY-MM-DD)
    - end_date: 回测结束日期 (YYYY-MM-DD)
    - initial_capital: 初始资金（默认100万）
    - stock_codes: 股票池（可选，不指定则使用全市场）

    响应缓存: Redis 1小时

    返回:
    {
        "code": 200,
        "message": "回测完成",
        "data": {
            "success": true,
            "data": {
                "metrics": {
                    "total_return": 0.32,
                    "annual_return": 0.32,
                    "sharpe_ratio": 1.85,
                    "max_drawdown": -0.12,
                    "win_rate": 0.62,
                    "total_trades": 150,
                    ...
                },
                "trades": [...],
                "daily_portfolio": [...]
            }
        }
    }

    错误响应 (500):
    {
        "code": 500,
        "message": "回测执行失败",
        "data": {
            "error": "数据获取失败: ..."
        }
    }
    """
    try:
        logger.info(
            f"收到回测请求: selector={request.selector.id}, "
            f"entry={request.entry.id}, exit={request.exit.id}, "
            f"period={request.start_date}~{request.end_date}"
        )

        # 调用适配器执行回测
        result = await three_layer_adapter.run_backtest(
            selector_id=request.selector.id,
            selector_params=request.selector.params,
            entry_id=request.entry.id,
            entry_params=request.entry.params,
            exit_id=request.exit.id,
            exit_params=request.exit.params,
            rebalance_freq=request.rebalance_freq,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            stock_codes=request.stock_codes,
        )

        # 检查回测结果
        if not result.get("success"):
            error_msg = result.get("error", "未知错误")
            logger.error(f"回测执行失败: {error_msg}")
            return ApiResponse.internal_error(message="回测执行失败", data={"error": error_msg}).to_dict()

        logger.info("回测执行成功")
        return ApiResponse.success(data=result, message="回测完成").to_dict()

    except ValueError as e:
        logger.warning(f"回测参数错误: {e}")
        return ApiResponse.bad_request(message=f"回测参数错误: {str(e)}").to_dict()

    except Exception as e:
        logger.error(f"回测执行失败: {e}", exc_info=True)
        return ApiResponse.internal_error(message=f"回测执行失败: {str(e)}").to_dict()
