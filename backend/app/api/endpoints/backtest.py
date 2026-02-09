"""
回测 API (Core v6.0 适配版)

支持三种策略类型:
1. 预定义策略 (Predefined) - 硬编码策略，性能最优
2. 配置驱动策略 (Config) - 从数据库加载配置
3. 动态代码策略 (Dynamic) - 动态加载Python代码

作者: Backend Team
创建日期: 2026-02-02
更新日期: 2026-02-09
版本: 3.0.0 (Core v6.0 适配版)
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Body, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field, validator

from app.core_adapters.backtest_adapter import BacktestAdapter
from app.core_adapters.data_adapter import DataAdapter
from app.core_adapters.config_strategy_adapter import ConfigStrategyAdapter
from app.core_adapters.dynamic_strategy_adapter import DynamicStrategyAdapter
from app.models.api_response import ApiResponse
from app.utils.data_cleaning import sanitize_float_values
from app.repositories.strategy_execution_repository import StrategyExecutionRepository
from app.api.error_handler import handle_api_errors

# 添加 core 项目到 Python 路径
core_path = Path(__file__).parent.parent.parent.parent.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

# 导入 Core 模块
from src.strategies import StrategyFactory
from src.backtest import BacktestEngine

router = APIRouter()

# 全局适配器实例
backtest_adapter = BacktestAdapter()
data_adapter = DataAdapter()


# ==================== Pydantic 模型 ====================


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


# ==================== API 端点 ====================


@router.post("/run-v2", summary="统一回测接口 (Core v6.0)", status_code=status.HTTP_200_OK)
@handle_api_errors
async def run_unified_backtest(request: UnifiedBacktestRequest) -> Dict[str, Any]:
    """
    运行回测 - 统一接口 (Core v6.0)

    支持三种策略类型:
    - **predefined**: 预定义策略（硬编码，性能最优）
    - **config**: 配置驱动策略（从数据库加载配置）
    - **dynamic**: 动态代码策略（动态加载Python代码）

    Returns:
        {
            "success": true,
            "data": {
                "execution_id": 1,
                "strategy_info": {...},
                "metrics": {...},
                "equity_curve": [...],
                "trades": [...]
            }
        }
    """
    start_time = datetime.now()

    logger.info(
        f"[统一回测] 开始: strategy_type={request.strategy_type}, "
        f"stocks={len(request.stock_pool)}, period={request.start_date}~{request.end_date}"
    )

    try:
        # 1. 创建策略实例
        factory = StrategyFactory()
        strategy_info = {}

        if request.strategy_type == 'predefined':
            if not request.strategy_name:
                raise ValueError("预定义策略需要提供 strategy_name")
            strategy = factory.create(request.strategy_name, request.strategy_config or {})
            strategy_info = {
                'type': 'predefined',
                'name': request.strategy_name,
                'config': request.strategy_config,
                'class': strategy.__class__.__name__
            }

        elif request.strategy_type == 'config':
            if not request.strategy_id:
                raise ValueError("配置驱动策略需要提供 strategy_id")
            config_adapter = ConfigStrategyAdapter()
            strategy = await config_adapter.create_strategy_from_config(request.strategy_id)
            config = await config_adapter.get_config_by_id(request.strategy_id)
            strategy_info = {
                'type': 'config',
                'config_id': request.strategy_id,
                'strategy_type': config['strategy_type'],
                'name': config.get('name', 'N/A'),
                'class': strategy.__class__.__name__
            }

        elif request.strategy_type == 'dynamic':
            if not request.strategy_id:
                raise ValueError("动态代码策略需要提供 strategy_id")
            dynamic_adapter = DynamicStrategyAdapter()
            strategy = await dynamic_adapter.create_strategy_from_code(
                strategy_id=request.strategy_id,
                strict_mode=request.strict_mode
            )
            metadata = await dynamic_adapter.get_strategy_metadata(request.strategy_id)
            strategy_info = {
                'type': 'dynamic',
                'strategy_id': request.strategy_id,
                'strategy_name': metadata['strategy_name'],
                'class_name': metadata['class_name'],
                'validation_status': metadata['validation_status'],
                'class': strategy.__class__.__name__
            }
        else:
            raise ValueError(f"不支持的策略类型: {request.strategy_type}")

        # 2. 加载市场数据
        market_data = await data_adapter.load_market_data(
            stock_codes=request.stock_pool,
            start_date=request.start_date,
            end_date=request.end_date
        )
        logger.info(f"[统一回测] 加载市场数据完成: {len(market_data)} 条")

        # 3. 运行回测
        engine = BacktestEngine()
        result = engine.run(
            strategy=strategy,
            stock_pool=request.stock_pool,
            market_data=market_data,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate,
            stamp_tax_rate=request.stamp_tax_rate,
            min_commission=request.min_commission,
            slippage=request.slippage,
        )

        # 4. 格式化结果
        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        metrics = {
            'total_return': float(result.total_return) if hasattr(result, 'total_return') else 0.0,
            'annual_return': float(result.annual_return) if hasattr(result, 'annual_return') else 0.0,
            'sharpe_ratio': float(result.sharpe_ratio) if hasattr(result, 'sharpe_ratio') else 0.0,
            'max_drawdown': float(result.max_drawdown) if hasattr(result, 'max_drawdown') else 0.0,
            'win_rate': float(result.win_rate) if hasattr(result, 'win_rate') else 0.0,
            'total_trades': int(result.total_trades) if hasattr(result, 'total_trades') else 0,
        }
        metrics = sanitize_float_values(metrics)

        equity_curve = []
        if hasattr(result, 'equity_curve'):
            equity_curve = result.equity_curve.to_dict('records')
            equity_curve = sanitize_float_values(equity_curve)

        trades = []
        if hasattr(result, 'trades'):
            trades = result.trades.to_dict('records')
            trades = sanitize_float_values(trades)

        # 5. 保存执行记录
        repo = StrategyExecutionRepository()
        execution_data = {
            'execution_type': 'backtest',
            'execution_params': request.dict(),
            'metrics': metrics,
            'execution_duration_ms': execution_time_ms,
            'status': 'completed',
            'started_at': start_time,
            'completed_at': datetime.now(),
        }

        if request.strategy_type == 'predefined':
            execution_data['predefined_strategy_type'] = request.strategy_name
        elif request.strategy_type == 'config':
            execution_data['config_strategy_id'] = request.strategy_id
        elif request.strategy_type == 'dynamic':
            execution_data['dynamic_strategy_id'] = request.strategy_id

        execution_id = repo.create(execution_data)

        logger.success(
            f"[统一回测] 完成: execution_id={execution_id}, "
            f"return={metrics['total_return']:.2%}, "
            f"sharpe={metrics['sharpe_ratio']:.2f}, time={execution_time_ms}ms"
        )

        return {
            "success": True,
            "data": {
                "execution_id": execution_id,
                "strategy_info": strategy_info,
                "metrics": metrics,
                "equity_curve": equity_curve[:1000],
                "trades": trades[:500],
                "execution_time_ms": execution_time_ms,
                "backtest_params": {
                    "stock_pool": request.stock_pool,
                    "start_date": request.start_date,
                    "end_date": request.end_date,
                    "initial_capital": request.initial_capital,
                }
            },
            "message": "回测完成"
        }

    except ValueError as e:
        logger.error(f"[统一回测] 参数错误: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        logger.error(f"[统一回测] 失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"回测失败: {str(e)}"
        )


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """
    运行回测

    ✅ 架构修正版：
    - Backend 只负责：参数验证、调用 Core Adapter、响应格式化
    - Core 负责：回测引擎、绩效计算、交易记录

    参数:
    - stock_codes: 股票代码列表
    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - strategy_params: 策略参数字典
    - initial_capital: 初始资金 (默认 100万)
    - commission_rate: 佣金费率 (默认 0.03%)
    - stamp_tax_rate: 印花税率 (默认 0.1%)
    - min_commission: 最小佣金 (默认 5元)
    - slippage: 滑点 (默认 0)

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "portfolio_value": [...],
            "positions": [...],
            "trades": [...],
            "metrics": {
                "total_return": 0.25,
                "annual_return": 0.28,
                "sharpe_ratio": 1.5,
                "max_drawdown": -0.15,
                "win_rate": 0.65,
                ...
            },
            "daily_returns": [...],
            "trade_statistics": {...},
            "cost_analysis": {...}
        }
    }
    """
    try:
        logger.info(
            f"收到回测请求: codes={request.stock_codes}, period={request.start_date}~{request.end_date}"
        )

        # 1. 参数转换
        start_dt = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(request.end_date, "%Y-%m-%d").date()

        # 2. 验证日期
        if start_dt >= end_dt:
            return ApiResponse.bad_request(message="开始日期必须小于结束日期").to_dict()

        # 3. 创建回测适配器（使用请求参数）
        adapter = BacktestAdapter(
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate,
            stamp_tax_rate=request.stamp_tax_rate,
            min_commission=request.min_commission,
            slippage=request.slippage,
        )

        # 4. 调用 Core Adapter 运行回测
        backtest_result = await adapter.run_backtest(
            stock_codes=request.stock_codes,
            strategy_params=request.strategy_params,
            start_date=start_dt,
            end_date=end_dt,
        )

        # 5. Backend 职责：响应格式化
        return ApiResponse.success(data=backtest_result, message="回测完成").to_dict()

    except ValueError as e:
        logger.warning(f"参数验证失败: {e}")
        return ApiResponse.bad_request(message=f"参数错误: {str(e)}").to_dict()

    except Exception as e:
        logger.error(f"回测执行失败: {e}", exc_info=True)
        return ApiResponse.internal_error(message=f"回测执行失败: {str(e)}").to_dict()


@router.post("/metrics")
async def calculate_metrics(
    portfolio_value: List[float] = Body(..., description="投资组合价值序列"),
    dates: List[str] = Body(..., description="日期序列"),
    trades: List[Dict[str, Any]] = Body(default_factory=list, description="交易记录"),
    positions: List[Dict[str, Any]] = Body(default_factory=list, description="持仓记录"),
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


@router.post("/parallel")
async def run_parallel_backtest(request: ParallelBacktestRequest):
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


@router.post("/optimize")
async def optimize_strategy_params(request: OptimizeParamsRequest):
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


@router.post("/cost-analysis")
async def analyze_trading_costs(request: CostAnalysisRequest):
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


@router.post("/risk-metrics")
async def calculate_risk_metrics(
    returns: List[float] = Body(..., description="收益率序列"),
    dates: List[str] = Body(..., description="日期序列"),
    positions: List[Dict[str, Any]] = Body(default_factory=list, description="持仓记录"),
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


@router.post("/trade-statistics")
async def get_trade_statistics(request: TradeStatisticsRequest):
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
