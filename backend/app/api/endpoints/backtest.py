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
# 在 Docker 容器中，core 目录在 /app/core
# 在本地开发环境中，相对路径为 backend/../core
if Path("/app/core").exists():
    core_path = Path("/app/core")
else:
    core_path = Path(__file__).parent.parent.parent.parent.parent / "core"

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


@router.post("", summary="运行回测", status_code=status.HTTP_200_OK)
@handle_api_errors
async def run_backtest_main(
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
    strategy_params: Optional[Dict[str, Any]] = Body(None, description="策略参数（覆盖默认参数，用于ML模型ID等）")
) -> Dict[str, Any]:
    """
    运行回测

    根据策略ID从 strategies 表加载策略并执行回测。
    自动识别策略类型（builtin/ai/custom）。

    Args:
        strategy_id: 策略ID
        stock_pool: 股票代码列表
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        initial_capital: 初始资金
        rebalance_freq: 调仓频率 (D/W/M)
        commission_rate: 佣金费率
        stamp_tax_rate: 印花税率
        min_commission: 最小佣金
        slippage: 滑点
        strict_mode: 严格模式（代码验证）

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
        f"[回测] 开始: strategy_id={strategy_id}, "
        f"stocks={len(stock_pool)}, period={start_date}~{end_date}"
    )

    try:
        # 1. 从 strategies 表加载策略
        from app.repositories.strategy_repository import StrategyRepository

        repo = StrategyRepository()
        strategy_record = repo.get_by_id(strategy_id)

        if not strategy_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"策略不存在: strategy_id={strategy_id}"
            )

        if not strategy_record['is_enabled']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"策略未启用: {strategy_record['name']}"
            )

        if strategy_record['validation_status'] != 'passed':
            logger.warning(
                f"策略验证未通过: strategy_id={strategy_id}, "
                f"status={strategy_record['validation_status']}"
            )
            if strict_mode:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"策略验证未通过: {strategy_record['validation_status']}"
                )

        # 2. 加载策略实例
        strategy = None

        # 准备执行环境：添加 core 路径和必要的导入
        import sys
        from pathlib import Path

        # 在 Docker 容器中，core 目录在 /app/core
        # 在本地开发环境中，相对路径为 backend/../core
        if Path("/app/core").exists():
            core_path = Path("/app/core")
        else:
            core_path = Path(__file__).parent.parent.parent.parent.parent / "core"

        if str(core_path) not in sys.path:
            sys.path.insert(0, str(core_path))

        if strategy_record['source_type'] in ['builtin', 'ai', 'custom']:
            # 所有策略类型都使用统一的动态加载方式
            try:
                # 导入 core 模块（实际路径是 src）
                from src.strategies.base_strategy import BaseStrategy
                from src.strategies.signal_generator import SignalGenerator
                import src.strategies

                # 创建命名空间，预导入常用模块和 core 模块
                namespace = {
                    '__builtins__': __builtins__,
                    'pd': pd,
                    'np': __import__('numpy'),
                    'logger': logger,
                    'BaseStrategy': BaseStrategy,
                    'SignalGenerator': SignalGenerator,
                }

                # 修复策略代码中的导入路径（将 core. 替换为 src.）
                code = strategy_record['code']
                code = code.replace('from core.', 'from src.')
                code = code.replace('import core.', 'import src.')

                # 执行代码
                exec(code, namespace)

                # 获取策略类
                strategy_class = namespace.get(strategy_record['class_name'])
                if not strategy_class:
                    raise ValueError(f"策略类 {strategy_record['class_name']} 未找到")

                # 解析默认参数
                default_params = strategy_record.get('default_params', {})
                if isinstance(default_params, str):
                    import json
                    default_params = json.loads(default_params) if default_params else {}

                # 合并策略参数：优先使用传入的参数，否则使用默认参数
                strategy_name = strategy_record['name']
                strategy_config = default_params or {}
                if strategy_params:
                    strategy_config.update(strategy_params)
                    logger.info(f"使用自定义策略参数: {strategy_params}")

                strategy = strategy_class(name=strategy_name, config=strategy_config)

                logger.info(f"成功加载{strategy_record['source_type']}策略: {strategy_record['name']}")

            except Exception as e:
                logger.error(f"加载策略失败: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"加载策略失败: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的策略来源类型: {strategy_record['source_type']}"
            )

        # 3. 加载市场数据
        market_data = pd.DataFrame()
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

        for code in stock_pool:
            try:
                code_data = await data_adapter.get_daily_data(
                    code=code,
                    start_date=start_dt,
                    end_date=end_dt
                )
                if not code_data.empty:
                    # 确保DatetimeIndex转为date列
                    if isinstance(code_data.index, pd.DatetimeIndex):
                        code_data = code_data.reset_index()

                    code_data['code'] = code
                    market_data = pd.concat([market_data, code_data], ignore_index=True)
            except Exception as e:
                logger.warning(f"加载股票 {code} 数据失败: {e}")

        if market_data.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到股票池的历史数据"
            )

        logger.info(f"[回测] 加载市场数据完成: {len(market_data)} 条记录")

        # 4. 准备价格数据
        if 'date' in market_data.columns:
            market_data['trade_date'] = pd.to_datetime(market_data['date'])
        elif 'trade_date' not in market_data.columns:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"市场数据缺少日期列"
            )

        # 去重：同一天同一股票只保留最后一条记录
        market_data = market_data.drop_duplicates(subset=['trade_date', 'code'], keep='last')

        # Pivot to wide format: index=dates, columns=stock codes, values=close prices
        prices = market_data.pivot(index='trade_date', columns='code', values='close').sort_index()

        logger.info(f"[回测] 价格数据: {len(prices)} 天 x {len(prices.columns)} 只股票")

        # 5. 计算特征数据（如果策略需要）
        features = None
        try:
            # 检查策略是否需要特征
            import inspect
            if hasattr(strategy, 'generate_signals'):
                sig = inspect.signature(strategy.generate_signals)
                # 如果generate_signals有features参数，则计算特征
                if 'features' in sig.parameters:
                    logger.info(f"[回测] 开始计算特征数据...")
                    from src.data_pipeline.feature_engineer import FeatureEngineer

                    # 为每只股票计算特征
                    features_dict = {}
                    for code in stock_pool:
                        try:
                            # 获取该股票的数据
                            stock_data = market_data[market_data['code'] == code].copy()
                            if stock_data.empty:
                                continue

                            # 设置trade_date为索引
                            stock_data = stock_data.set_index('trade_date').sort_index()

                            # 计算特征（不需要target_period，因为回测不需要标签）
                            engineer = FeatureEngineer(verbose=False)

                            # 只计算技术指标和Alpha因子，不计算目标标签
                            stock_data = engineer._compute_technical_indicators(stock_data)
                            stock_data = engineer._compute_alpha_factors(stock_data)

                            # 存储特征
                            features_dict[code] = stock_data

                        except Exception as e:
                            logger.warning(f"计算股票 {code} 特征失败: {e}")
                            continue

                    if features_dict:
                        # 构建特征DataFrame：MultiIndex格式 (date, factor) -> stock values
                        # 或者简单格式：date -> factors (所有股票的因子在列中)

                        # 使用简单格式：每个因子作为一列，股票代码也作为列的一部分
                        # 格式: index=dates, columns=factor_names (对所有股票相同)

                        # 提取所有因子名称（从第一只股票）
                        first_stock = list(features_dict.keys())[0]
                        factor_columns = [col for col in features_dict[first_stock].columns
                                         if col not in ['open', 'high', 'low', 'close', 'volume', 'amount', 'code']]

                        # 构建MultiIndex: (date, stock) -> factors
                        all_dates = prices.index
                        features_data = {}

                        for factor in factor_columns:
                            factor_data = pd.DataFrame(index=all_dates, columns=prices.columns)
                            for code in prices.columns:
                                if code in features_dict:
                                    stock_features = features_dict[code]
                                    if factor in stock_features.columns:
                                        # 对齐日期
                                        factor_data[code] = stock_features[factor].reindex(all_dates)
                            features_data[factor] = factor_data

                        # 转换为MultiIndex DataFrame: columns=(factor, stock)
                        features = pd.concat(features_data, axis=1)

                        logger.info(f"[回测] 特征计算完成: {len(factor_columns)} 个因子")
                    else:
                        logger.warning(f"[回测] 没有成功计算任何特征数据")
        except Exception as e:
            logger.warning(f"[回测] 特征计算失败: {e}", exc_info=True)

        # 6. 生成交易信号
        # 优先使用 generate_signals 方法（标准接口）
        if hasattr(strategy, 'generate_signals'):
            # 标准信号生成接口，传入features参数（如果计算了的话）
            if features is not None:
                signals = strategy.generate_signals(prices, features=features)
            else:
                signals = strategy.generate_signals(prices)
        elif hasattr(strategy, 'calculate_momentum'):
            # 动量策略：使用动量分数
            momentum_raw = strategy.calculate_momentum(prices)
            # 重建DataFrame以确保index正确（动量计算可能导致DatetimeIndex丢失）
            if len(momentum_raw) == len(prices):
                signals = pd.DataFrame(
                    data=momentum_raw.values,
                    index=prices.index,
                    columns=momentum_raw.columns
                )
            else:
                logger.warning(f"信号长度({len(momentum_raw)})与价格长度({len(prices)})不匹配")
                signals = momentum_raw
        elif hasattr(strategy, 'calculate_scores'):
            # 其他策略：使用通用评分方法（指定dtype避免object类型）
            signals = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
            for date in prices.index:
                scores = strategy.calculate_scores(prices, date=date)
                signals.loc[date] = scores
        else:
            # 降级：无可用信号生成方法
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="策略缺少信号生成方法（generate_signals/calculate_momentum/calculate_scores）"
            )

        logger.info(f"[回测] 信号生成完成: {len(signals)} 个交易日")

        # 7. 运行回测
        engine = BacktestEngine()
        engine.set_market_data(market_data)

        # 获取策略配置中的参数
        strategy_config = strategy.config if hasattr(strategy, 'config') else {}
        top_n = strategy_config.get('top_n', 50) if isinstance(strategy_config, dict) else 50
        holding_period = strategy_config.get('holding_period', 5) if isinstance(strategy_config, dict) else 5

        result = engine.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=top_n,
            holding_period=holding_period,
            rebalance_freq=rebalance_freq
        )

        # 8. 检查结果
        if not result.is_success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"回测执行失败: {result.error_message or result.message}"
            )

        # 9. 格式化结果
        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        try:
            result_data = result.data if isinstance(result.data, dict) else {}

            # 使用 PerformanceAnalyzer 计算指标
            portfolio_value_df = result_data.get('portfolio_value')
            daily_returns = result_data.get('daily_returns')
            positions = result_data.get('positions')

            if daily_returns is not None and not daily_returns.empty:
                analyzer = PerformanceAnalyzer(returns=daily_returns)
                metrics_response = analyzer.calculate_all_metrics(verbose=False)

                if metrics_response.is_success():
                    calculated_metrics = metrics_response.data

                    metrics = {
                        # 基础收益指标
                        'total_return': calculated_metrics.get('total_return', 0.0),
                        'annual_return': calculated_metrics.get('annualized_return', 0.0),

                        # 风险指标
                        'volatility': calculated_metrics.get('volatility', 0.0),
                        'downside_deviation': calculated_metrics.get('downside_deviation', 0.0),
                        'max_drawdown': calculated_metrics.get('max_drawdown', 0.0),
                        'max_drawdown_duration': calculated_metrics.get('max_drawdown_duration', 0),

                        # 风险调整收益指标
                        'sharpe_ratio': calculated_metrics.get('sharpe_ratio', 0.0),
                        'sortino_ratio': calculated_metrics.get('sortino_ratio', 0.0),
                        'calmar_ratio': calculated_metrics.get('calmar_ratio', 0.0),

                        # 交易统计指标
                        'win_rate': calculated_metrics.get('win_rate', 0.0),
                        'profit_factor': calculated_metrics.get('profit_factor', 0.0),
                        'average_win': calculated_metrics.get('average_win', 0.0),
                        'average_loss': calculated_metrics.get('average_loss', 0.0),
                        'win_loss_ratio': calculated_metrics.get('win_loss_ratio', 0.0),
                        'total_trades': len(positions) if positions else 0,
                    }
                else:
                    logger.warning(f"性能指标计算失败: {metrics_response.message}")
                    metrics = {
                        # 基础收益指标
                        'total_return': 0.0,
                        'annual_return': 0.0,

                        # 风险指标
                        'volatility': 0.0,
                        'downside_deviation': 0.0,
                        'max_drawdown': 0.0,
                        'max_drawdown_duration': 0,

                        # 风险调整收益指标
                        'sharpe_ratio': 0.0,
                        'sortino_ratio': 0.0,
                        'calmar_ratio': 0.0,

                        # 交易统计指标
                        'win_rate': 0.0,
                        'profit_factor': 0.0,
                        'average_win': 0.0,
                        'average_loss': 0.0,
                        'win_loss_ratio': 0.0,
                        'total_trades': 0,
                    }
            elif portfolio_value_df is not None and not portfolio_value_df.empty:
                # 降级：从portfolio_value计算简单指标
                logger.info("使用 portfolio_value 计算简单指标")
                initial_value = portfolio_value_df['total'].iloc[0]
                final_value = portfolio_value_df['total'].iloc[-1]
                total_return = (final_value / initial_value - 1) if initial_value > 0 else 0.0

                metrics = {
                    # 基础收益指标
                    'total_return': float(total_return),
                    'annual_return': 0.0,  # 需要日期信息

                    # 风险指标
                    'volatility': 0.0,  # 需要daily_returns
                    'downside_deviation': 0.0,  # 需要daily_returns
                    'max_drawdown': 0.0,  # 需要完整序列
                    'max_drawdown_duration': 0,  # 需要完整序列

                    # 风险调整收益指标
                    'sharpe_ratio': 0.0,  # 需要daily_returns
                    'sortino_ratio': 0.0,  # 需要daily_returns
                    'calmar_ratio': 0.0,  # 需要max_drawdown

                    # 交易统计指标
                    'win_rate': 0.0,  # 需要交易记录
                    'profit_factor': 0.0,  # 需要交易记录
                    'average_win': 0.0,  # 需要交易记录
                    'average_loss': 0.0,  # 需要交易记录
                    'win_loss_ratio': 0.0,  # 需要交易记录
                    'total_trades': len(positions) if positions else len(portfolio_value_df),
                }
            else:
                logger.warning("portfolio_value 和 daily_returns 数据都为空，无法计算指标")
                metrics = {
                    # 基础收益指标
                    'total_return': 0.0,
                    'annual_return': 0.0,

                    # 风险指标
                    'volatility': 0.0,
                    'downside_deviation': 0.0,
                    'max_drawdown': 0.0,
                    'max_drawdown_duration': 0,

                    # 风险调整收益指标
                    'sharpe_ratio': 0.0,
                    'sortino_ratio': 0.0,
                    'calmar_ratio': 0.0,

                    # 交易统计指标
                    'win_rate': 0.0,
                    'profit_factor': 0.0,
                    'average_win': 0.0,
                    'average_loss': 0.0,
                    'win_loss_ratio': 0.0,
                    'total_trades': 0,
                }

            metrics = sanitize_float_values(metrics)

            # 提取权益曲线
            equity_curve = []
            if 'portfolio_value' in result_data:
                portfolio_value = result_data['portfolio_value']
                if isinstance(portfolio_value, pd.DataFrame):
                    # 将DatetimeIndex转为date列，避免丢失日期信息
                    if isinstance(portfolio_value.index, pd.DatetimeIndex):
                        portfolio_value = portfolio_value.reset_index()
                        if 'index' in portfolio_value.columns:
                            portfolio_value = portfolio_value.rename(columns={'index': 'date'})
                    equity_curve = portfolio_value.to_dict('records')
                elif isinstance(portfolio_value, list):
                    equity_curve = portfolio_value

            # 标准化日期格式为 YYYY-MM-DD（与K线数据保持一致）
            for item in equity_curve:
                if 'date' in item:
                    date_value = item['date']
                    if isinstance(date_value, pd.Timestamp):
                        item['date'] = date_value.strftime('%Y-%m-%d')
                    elif isinstance(date_value, str) and 'T' in date_value:
                        item['date'] = date_value.split('T')[0]

            equity_curve = sanitize_float_values(equity_curve)

            # 提取交易记录（优先从trades字段，否则从cost_analyzer获取）
            trades = []
            if 'trades' in result_data:
                trades_data = result_data['trades']
                if isinstance(trades_data, pd.DataFrame):
                    trades = trades_data.to_dict('records')
                elif isinstance(trades_data, list):
                    trades = trades_data
            elif 'cost_analyzer' in result_data:
                cost_analyzer = result_data['cost_analyzer']
                if hasattr(cost_analyzer, 'get_trades_dataframe'):
                    trades_df = cost_analyzer.get_trades_dataframe()
                    if not trades_df.empty:
                        trades_df = trades_df.reset_index()
                        trades = trades_df.to_dict('records')

            # 从数据库查询股票名称映射（stock_code -> stock_name）
            stock_name_map = {}
            try:
                if not market_data.empty and 'code' in market_data.columns:
                    stock_codes = set(market_data['code'].unique())

                    if stock_codes:
                        from src.database import DatabaseManager
                        db = DatabaseManager()

                        codes_str = "','".join(stock_codes)
                        query = f"SELECT code, name FROM stock_basic WHERE code IN ('{codes_str}')"

                        with db.get_connection() as conn:
                            result = pd.read_sql(query, conn)
                            if not result.empty:
                                stock_name_map = dict(zip(result['code'], result['name']))
                                logger.debug(f"已获取 {len(stock_name_map)} 个股票名称")
                            else:
                                logger.warning("stock_basic表中未找到股票名称")
            except Exception as e:
                logger.warning(f"查询股票名称失败: {e}")

            # 统一交易记录日期格式并添加股票名称
            for trade in trades:
                # 标准化日期为 YYYY-MM-DD 格式
                if 'date' in trade:
                    date_value = trade['date']
                    if isinstance(date_value, pd.Timestamp):
                        trade['date'] = date_value.strftime('%Y-%m-%d')
                    elif isinstance(date_value, str) and 'T' in date_value:
                        trade['date'] = date_value.split('T')[0]

                # 添加股票名称（兼容 stock_code/code/symbol 字段）
                stock_code = trade.get('stock_code') or trade.get('code') or trade.get('symbol')
                if stock_code and stock_code in stock_name_map:
                    trade['stock_name'] = stock_name_map[stock_code]

            trades = sanitize_float_values(trades)

            # 生成K线图表数据（最多前10只股票）
            stock_charts = {}
            for code in stock_pool[:10]:
                try:
                    stock_data = market_data[market_data['code'] == code].copy()
                    if stock_data.empty:
                        continue

                    # 转换K线数据
                    stock_data = stock_data.sort_values('trade_date')
                    kline_data = []
                    for _, row in stock_data.iterrows():
                        kline_data.append({
                            'date': row['trade_date'].strftime('%Y-%m-%d') if isinstance(row['trade_date'], pd.Timestamp) else str(row['trade_date']),
                            'open': float(row['open']) if 'open' in row and pd.notna(row['open']) else float(row['close']),
                            'high': float(row['high']) if 'high' in row and pd.notna(row['high']) else float(row['close']),
                            'low': float(row['low']) if 'low' in row and pd.notna(row['low']) else float(row['close']),
                            'close': float(row['close']),
                            'volume': float(row['volume']) if 'volume' in row and pd.notna(row['volume']) else 0.0,
                        })

                    # 提取买卖信号
                    buy_signals = []
                    sell_signals = []
                    for trade in trades:
                        trade_code = trade.get('code') or trade.get('symbol') or trade.get('stock_code')
                        if trade_code == code:
                            trade_date = trade.get('date')
                            if isinstance(trade_date, pd.Timestamp):
                                trade_date = trade_date.strftime('%Y-%m-%d')
                            elif trade_date:
                                trade_date = str(trade_date)

                            signal_point = {'date': trade_date, 'price': float(trade.get('price', 0))}
                            action = trade.get('type') or trade.get('action')
                            if action == 'buy':
                                buy_signals.append(signal_point)
                            elif action == 'sell':
                                sell_signals.append(signal_point)

                    stock_charts[code] = {
                        'kline_data': kline_data,
                        'buy_signals': buy_signals,
                        'sell_signals': sell_signals,
                    }

                except Exception as e:
                    logger.warning(f"生成股票 {code} 图表数据失败: {e}")
                    continue

            stock_charts = sanitize_float_values(stock_charts)

        except Exception as e:
            logger.error(f"格式化结果失败: {e}", exc_info=True)
            # 使用默认值
            metrics = {
                # 基础收益指标
                'total_return': 0.0,
                'annual_return': 0.0,

                # 风险指标
                'volatility': 0.0,
                'downside_deviation': 0.0,
                'max_drawdown': 0.0,
                'max_drawdown_duration': 0,

                # 风险调整收益指标
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'calmar_ratio': 0.0,

                # 交易统计指标
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'win_loss_ratio': 0.0,
                'total_trades': 0,
            }
            equity_curve = []
            trades = []

        # 10. 更新策略统计
        try:
            repo.increment_backtest_count(strategy_id)
            repo.update_backtest_metrics(
                strategy_id=strategy_id,
                sharpe_ratio=metrics.get('sharpe_ratio', 0.0),
                annual_return=metrics.get('annual_return', 0.0)
            )
        except Exception as e:
            logger.warning(f"更新策略统计失败: {e}")

        logger.success(
            f"[回测] 完成: strategy_id={strategy_id}, "
            f"return={metrics.get('total_return', 0.0):.2%}, "
            f"sharpe={metrics.get('sharpe_ratio', 0.0):.2f}, time={execution_time_ms}ms"
        )

        strategy_info = {
            'strategy_id': strategy_record['id'],
            'name': strategy_record['name'],
            'display_name': strategy_record['display_name'],
            'source_type': strategy_record['source_type'],
            'class_name': strategy_record['class_name'],
            'category': strategy_record['category'],
        }

        return {
            "success": True,
            "data": {
                "strategy_info": strategy_info,
                "metrics": metrics,
                "equity_curve": equity_curve,  # 权益曲线数据，用于K线图叠加显示
                "trades": trades[:500],  # 限制返回最多500条交易记录
                "stock_charts": stock_charts,  # 股票K线数据和买卖信号
                "execution_time_ms": execution_time_ms,
                "backtest_params": {
                    "stock_pool": stock_pool,
                    "start_date": start_date,
                    "end_date": end_date,
                    "initial_capital": initial_capital,
                }
            },
            "message": "回测完成"
        }

    except HTTPException:
        raise

    except ValueError as e:
        error_msg = str(e).replace('{', '{{').replace('}', '}}')  # 转义大括号避免格式化错误
        logger.error(f"[回测] 参数错误: {error_msg}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        logger.error(f"[回测] 失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"回测失败: {str(e)}"
        )


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


# ==================== 工具类接口 ====================
# 以下接口用于计算指标、分析成本等辅助功能
