"""
回测模块 - Pydantic 数据模型

统一管理所有回测相关的请求和响应模型
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator


class UnifiedBacktestRequest(BaseModel):
    """统一回测请求模型 (Core v6.0)"""

    # 策略选择 (三选一)
    strategy_type: str = Field(
        ...,
        description="策略类型: predefined (预定义), config (配置驱动), dynamic (动态代码)"
    )
    strategy_id: Optional[int] = Field(
        None,
        description="配置ID或动态策略ID (当strategy_type='config'或'dynamic'时必需)"
    )
    strategy_name: Optional[str] = Field(
        None,
        description="预定义策略名称 (当strategy_type='predefined'时必需)"
    )
    strategy_config: Optional[Dict[str, Any]] = Field(
        None,
        description="预定义策略配置 (当strategy_type='predefined'时可选)"
    )

    # 回测参数
    stock_pool: List[str] = Field(..., description="股票代码列表", min_items=1)
    start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    initial_capital: float = Field(1000000.0, gt=0, description="初始资金")

    # 交易成本参数 (可选)
    commission_rate: float = Field(0.0003, ge=0, le=0.01, description="佣金费率")
    stamp_tax_rate: float = Field(0.001, ge=0, le=0.01, description="印花税率")
    min_commission: float = Field(5.0, ge=0, description="最小佣金")
    slippage: float = Field(0.0, ge=0, description="滑点")

    # 高级选项
    strict_mode: bool = Field(
        True,
        description="严格模式（仅对dynamic策略有效）"
    )

    @validator("strategy_type")
    def validate_strategy_type(cls, v):
        allowed_types = ["predefined", "config", "dynamic"]
        if v not in allowed_types:
            raise ValueError(f"策略类型必须是以下之一: {', '.join(allowed_types)}")
        return v

    @validator("start_date", "end_date")
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"日期格式错误，应为 YYYY-MM-DD: {v}")
        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "name": "预定义策略",
                    "value": {
                        "strategy_type": "predefined",
                        "strategy_name": "momentum",
                        "strategy_config": {"lookback_period": 20, "top_n": 20},
                        "stock_pool": ["000001.SZ", "600000.SH"],
                        "start_date": "2023-01-01",
                        "end_date": "2023-12-31",
                        "initial_capital": 1000000.0
                    }
                },
                {
                    "name": "配置驱动策略",
                    "value": {
                        "strategy_type": "config",
                        "strategy_id": 1,
                        "stock_pool": ["000001.SZ"],
                        "start_date": "2023-01-01",
                        "end_date": "2023-12-31"
                    }
                },
                {
                    "name": "动态代码策略",
                    "value": {
                        "strategy_type": "dynamic",
                        "strategy_id": 1,
                        "stock_pool": ["000001.SZ"],
                        "start_date": "2023-01-01",
                        "end_date": "2023-12-31",
                        "strict_mode": True
                    }
                }
            ]
        }


class BacktestRequest(BaseModel):
    """回测请求模型"""

    stock_codes: List[str] = Field(..., description="股票代码列表", min_items=1)
    start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    strategy_params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")
    initial_capital: float = Field(1000000.0, gt=0, description="初始资金")
    commission_rate: float = Field(0.0003, ge=0, le=0.01, description="佣金费率")
    stamp_tax_rate: float = Field(0.001, ge=0, le=0.01, description="印花税率")
    min_commission: float = Field(5.0, ge=0, description="最小佣金")
    slippage: float = Field(0.0, ge=0, description="滑点")

    class Config:
        json_schema_extra = {
            "example": {
                "stock_codes": ["000001", "000002"],
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "strategy_params": {"type": "ma_cross", "short_window": 5, "long_window": 20},
                "initial_capital": 1000000.0,
                "commission_rate": 0.0003,
                "stamp_tax_rate": 0.001,
                "min_commission": 5.0,
                "slippage": 0.0,
            }
        }


class ParallelBacktestRequest(BaseModel):
    """并行回测请求模型"""

    stock_codes: List[str] = Field(..., description="股票代码列表", min_items=1)
    strategy_params_list: List[Dict[str, Any]] = Field(..., description="策略参数列表", min_items=1)
    start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    initial_capital: float = Field(1000000.0, gt=0, description="初始资金")
    n_processes: int = Field(4, ge=1, le=16, description="进程数")


class OptimizeParamsRequest(BaseModel):
    """参数优化请求模型"""

    stock_codes: List[str] = Field(..., description="股票代码列表", min_items=1)
    param_grid: Dict[str, List[Any]] = Field(..., description="参数网格")
    start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    initial_capital: float = Field(1000000.0, gt=0, description="初始资金")
    metric: str = Field("sharpe_ratio", description="优化目标指标")

    class Config:
        json_schema_extra = {
            "example": {
                "stock_codes": ["000001"],
                "param_grid": {"short_window": [5, 10, 20], "long_window": [20, 40, 60]},
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "initial_capital": 1000000.0,
                "metric": "sharpe_ratio",
            }
        }


class CostAnalysisRequest(BaseModel):
    """成本分析请求模型"""

    trades: List[Dict[str, Any]] = Field(..., description="交易记录列表")


class TradeStatisticsRequest(BaseModel):
    """交易统计请求模型"""

    trades: List[Dict[str, Any]] = Field(..., description="交易记录列表")
