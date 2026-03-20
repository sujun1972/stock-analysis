"""
回测模块 - 核心回测执行

包含核心回测执行函数和主回测 API 端点
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


# ==================== 辅助函数 ====================


def _get_default_metrics(positions=None):
    """获取默认的空指标"""
    return {
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
        'total_trades': len(positions) if positions else 0,
    }


# ==================== 核心回测执行函数 ====================


def execute_backtest_core(
    params: Dict[str, Any],
    execution_id: Optional[int] = None,
    progress_callback: Optional[callable] = None
):
    """
    核心回测执行函数（可被同步和异步调用）

    Args:
        params: 回测参数字典
            - strategy_id: 策略ID
            - stock_pool: 股票代码列表
            - start_date: 开始日期 (YYYY-MM-DD)
            - end_date: 结束日期 (YYYY-MM-DD)
            - initial_capital: 初始资金
            - rebalance_freq: 调仓频率
            - commission_rate: 佣金费率
            - stamp_tax_rate: 印花税率
            - min_commission: 最小佣金
            - slippage: 滑点
            - strict_mode: 严格模式
            - strategy_params: 策略参数（可选）
            - exit_strategy_ids: 离场策略ID列表（可选）
        execution_id: 执行记录ID（可选）
        progress_callback: 进度回调函数(current, total, status)

    Returns:
        Dict containing:
            - strategy_info: 策略信息
            - metrics: 绩效指标
            - equity_curve: 权益曲线
            - trades: 交易记录
            - stock_charts: 股票K线图数据
            - backtest_params: 回测参数
            - execution_time_ms: 执行时间（毫秒）
    """
    start_time = datetime.now()

    # 解析参数
    strategy_id = params['strategy_id']
    stock_pool = params['stock_pool']
    start_date = params['start_date']
    end_date = params['end_date']
    initial_capital = params.get('initial_capital', 1000000.0)
    rebalance_freq = params.get('rebalance_freq', 'W')
    commission_rate = params.get('commission_rate', 0.0003)
    stamp_tax_rate = params.get('stamp_tax_rate', 0.001)
    min_commission = params.get('min_commission', 5.0)
    slippage = params.get('slippage', 0.0)
    strict_mode = params.get('strict_mode', True)
    strategy_params = params.get('strategy_params')
    exit_strategy_ids = params.get('exit_strategy_ids')

    logger.info(
        f"[回测核心] 开始: strategy_id={strategy_id}, "
        f"stocks={len(stock_pool)}, period={start_date}~{end_date}"
    )

    if progress_callback:
        progress_callback(1, 11, '加载策略配置...')

    # 1. 从 strategies 表加载策略
    from app.repositories.strategy_repository import StrategyRepository

    repo = StrategyRepository()
    strategy_record = repo.get_by_id(strategy_id)

    if not strategy_record:
        raise ValueError(f"策略不存在: strategy_id={strategy_id}")

    if not strategy_record['is_enabled']:
        raise ValueError(f"策略未启用: {strategy_record['name']}")

    if strategy_record['validation_status'] != 'passed' and strict_mode:
        raise ValueError(f"策略验证未通过: {strategy_record['validation_status']}")

    if progress_callback:
        progress_callback(2, 11, '动态加载策略代码...')

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
        core_path = Path(__file__).parent.parent.parent.parent.parent.parent / "core"

    if str(core_path) not in sys.path:
        sys.path.insert(0, str(core_path))

    # 使用统一的策略动态加载器
    from app.services.strategy_loader import StrategyDynamicLoader

    if strategy_record['source_type'] in ['builtin', 'ai', 'custom']:
        try:
            strategy = StrategyDynamicLoader.load_strategy(
                strategy_record=strategy_record,
                custom_config=strategy_params
            )
        except Exception as e:
            logger.error(f"加载策略失败: {e}", exc_info=True)
            raise ValueError(f"加载策略失败: {str(e)}")
    else:
        raise ValueError(f"不支持的策略来源类型: {strategy_record['source_type']}")

    if progress_callback:
        progress_callback(3, 11, '加载市场数据...')

    # 3. 加载市场数据
    market_data = pd.DataFrame()
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

    # 使用同步方式加载数据，避免事件循环冲突
    query_manager = data_adapter.query_manager
    if query_manager is None:
        raise ValueError("数据库连接不可用")

    for code in stock_pool:
        try:
            code_data = query_manager.load_daily_data(
                stock_code=code,
                start_date=start_dt.strftime("%Y-%m-%d"),
                end_date=end_dt.strftime("%Y-%m-%d")
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
        raise ValueError(f"未找到股票池的历史数据")

    logger.info(f"[回测核心] 加载市场数据完成: {len(market_data)} 条记录")

    if progress_callback:
        progress_callback(4, 11, '���备价格数据...')

    # 4. 准备价格数据
    if 'date' in market_data.columns:
        market_data['trade_date'] = pd.to_datetime(market_data['date'])
    elif 'trade_date' not in market_data.columns:
        raise ValueError(f"市场数据缺少日期列")

    # 去重：同一天同一股票只保留最后一条记录
    market_data = market_data.drop_duplicates(subset=['trade_date', 'code'], keep='last')

    # Pivot to wide format
    ohlcv_dfs = {
        'open': market_data.pivot(index='trade_date', columns='code', values='open').sort_index(),
        'high': market_data.pivot(index='trade_date', columns='code', values='high').sort_index(),
        'low': market_data.pivot(index='trade_date', columns='code', values='low').sort_index(),
        'close': market_data.pivot(index='trade_date', columns='code', values='close').sort_index(),
        'volume': market_data.pivot(index='trade_date', columns='code', values='volume').sort_index()
    }

    # 合并成多层列结构的 DataFrame
    prices = pd.concat(ohlcv_dfs, axis=1, keys=ohlcv_dfs.keys())

    logger.info(f"[回测核心] 价格数据: {len(prices)} 天 x {len(prices['close'].columns)} 只股票")

    if progress_callback:
        progress_callback(5, 11, '计算特征数据...')

    # 5. 计算特征数据（如果策略需要）
    features = None
    try:
        # 检查策略是否需要特征
        import inspect
        if hasattr(strategy, 'generate_signals'):
            sig = inspect.signature(strategy.generate_signals)
            # 如果generate_signals有features参数，则计算特征
            if 'features' in sig.parameters:
                logger.info(f"[回测核心] 开始计算特征数据...")
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
                    # 提取所有因子名称（从第一只股票）
                    first_stock = list(features_dict.keys())[0]
                    factor_columns = [col for col in features_dict[first_stock].columns
                                     if col not in ['open', 'high', 'low', 'close', 'volume', 'amount', 'code']]

                    # 构建MultiIndex: (date, stock) -> factors
                    all_dates = prices.index
                    features_data = {}

                    for factor in factor_columns:
                        factor_data = pd.DataFrame(index=all_dates, columns=prices['close'].columns)
                        for code in prices['close'].columns:
                            if code in features_dict:
                                stock_features = features_dict[code]
                                if factor in stock_features.columns:
                                    # 对齐日期
                                    factor_data[code] = stock_features[factor].reindex(all_dates)
                        features_data[factor] = factor_data

                    # 转换为MultiIndex DataFrame: columns=(factor, stock)
                    features = pd.concat(features_data, axis=1)

                    logger.info(f"[回测核心] 特征计算完成: {len(factor_columns)} 个因子")
                else:
                    logger.warning(f"[回测核心] 没有成功计算任何特征数据")
    except Exception as e:
        logger.warning(f"[回测核心] 特征计算失败: {e}", exc_info=True)

    if progress_callback:
        progress_callback(6, 11, '生成交易信号...')

    # 6. 生成交易信号
    if hasattr(strategy, 'generate_signals'):
        # 标准信号生成接口，传入features参数（如果计算了的话）
        if features is not None:
            signals = strategy.generate_signals(prices, features=features)
        else:
            signals = strategy.generate_signals(prices)
    elif hasattr(strategy, 'calculate_momentum'):
        # 动量策略：使用动量分数
        momentum_raw = strategy.calculate_momentum(prices)
        # 重建DataFrame以确保index正确
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
        # 其他策略：使用通用评分方法
        signals = pd.DataFrame(index=prices.index, columns=prices['close'].columns, dtype=float)
        for date in prices.index:
            scores = strategy.calculate_scores(prices, date=date)
            signals.loc[date] = scores
    else:
        # 降级：无可用信号生成方法
        raise ValueError("策略缺少信号生成方法（generate_signals/calculate_momentum/calculate_scores）")

    logger.info(f"[回测核心] 信号生成完成: {len(signals)} 个交易日")

    if progress_callback:
        progress_callback(7, 11, '加载离场策略...')

    # 7. 加载离场策略（如果指定）
    exit_manager = None
    if exit_strategy_ids and len(exit_strategy_ids) > 0:
        try:
            exit_manager = StrategyDynamicLoader.load_exit_manager(
                exit_strategy_ids=exit_strategy_ids,
                repo=repo
            )
        except Exception as e:
            logger.warning(f"[回测核心] 加载离场策略失败: {e}", exc_info=True)

    if progress_callback:
        progress_callback(8, 11, '执行回测引擎...')

    # 8. 运行回测
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
        rebalance_freq=rebalance_freq,
        exit_manager=exit_manager
    )

    # 检查结果
    if not result.is_success:
        raise ValueError(f"回测执行失败: {result.error_message or result.message}")

    if progress_callback:
        progress_callback(9, 11, '计算绩效指标...')

    # 9. 格式化结果
    execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

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
            metrics = _get_default_metrics(positions)
    elif portfolio_value_df is not None and not portfolio_value_df.empty:
        # 降级：从portfolio_value计算简单指标
        logger.info("使用 portfolio_value 计算简单指标")
        initial_value = portfolio_value_df['total'].iloc[0]
        final_value = portfolio_value_df['total'].iloc[-1]
        total_return = (final_value / initial_value - 1) if initial_value > 0 else 0.0

        metrics = _get_default_metrics(positions)
        metrics['total_return'] = float(total_return)
    else:
        logger.warning("portfolio_value 和 daily_returns 数据都为空，无法计算指标")
        metrics = _get_default_metrics(None)

    metrics = sanitize_float_values(metrics)

    if progress_callback:
        progress_callback(10, 11, '生成图表数据...')

    # 提取权益曲线
    equity_curve = []
    if 'portfolio_value' in result_data:
        portfolio_value = result_data['portfolio_value']
        if isinstance(portfolio_value, pd.DataFrame):
            # 将DatetimeIndex转为date列
            if isinstance(portfolio_value.index, pd.DatetimeIndex):
                portfolio_value = portfolio_value.reset_index()
                if 'index' in portfolio_value.columns:
                    portfolio_value = portfolio_value.rename(columns={'index': 'date'})
            equity_curve = portfolio_value.to_dict('records')
        elif isinstance(portfolio_value, list):
            equity_curve = portfolio_value

    # 标准化日期格式为 YYYY-MM-DD
    for item in equity_curve:
        if 'date' in item:
            date_value = item['date']
            if isinstance(date_value, pd.Timestamp):
                item['date'] = date_value.strftime('%Y-%m-%d')
            elif isinstance(date_value, str) and 'T' in date_value:
                item['date'] = date_value.split('T')[0]

    equity_curve = sanitize_float_values(equity_curve)

    # 提取交易记录
    trades = []
    if 'recorder' in result_data:
        # 优先使用recorder的交易记录（包含离场原因）
        recorder = result_data['recorder']
        if hasattr(recorder, 'trades'):
            trades = recorder.trades.copy() if isinstance(recorder.trades, list) else []
            logger.info(f"从recorder获取到 {len(trades)} 条交易记录")
    elif 'trades' in result_data:
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

    # 从数据库查询股票名称映射
    stock_name_map = {}
    try:
        if not market_data.empty and 'code' in market_data.columns:
            stock_codes = list(set(market_data['code'].unique()))

            if stock_codes:
                from app.repositories.stock_basic_repository import StockBasicRepository
                stock_repo = StockBasicRepository()
                stock_name_map = stock_repo.get_stock_names(stock_codes)
                logger.debug(f"已获取 {len(stock_name_map)} 个股票名称")
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

        # 添加股票名称
        stock_code = trade.get('stock_code') or trade.get('code') or trade.get('symbol')
        if stock_code and stock_code in stock_name_map:
            trade['stock_name'] = stock_name_map[stock_code]

        # 兼容性处理：direction -> action
        if 'direction' in trade and 'action' not in trade:
            trade['action'] = trade['direction']

    trades = sanitize_float_values(trades)

    # 生成K线图表数据
    stock_charts = {}
    logger.info(f"开始生成K线图表数据，股票池大小: {len(stock_pool)}")

    for code in stock_pool:
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

    logger.info(f"K线图表生成完成，成功生成 {len(stock_charts)} 个股票的图表")
    stock_charts = sanitize_float_values(stock_charts)

    # 修正metrics中的total_trades
    if metrics and isinstance(metrics, dict):
        metrics['total_trades'] = len(trades)

    if progress_callback:
        progress_callback(11, 11, '保存结果...')

    # 10. 构建策略信息
    strategy_info = {
        'strategy_id': strategy_record['id'],
        'name': strategy_record['name'],
        'display_name': strategy_record['display_name'],
        'source_type': strategy_record['source_type'],
        'class_name': strategy_record['class_name'],
        'category': strategy_record['category'],
    }

    logger.success(
        f"[回测核心] 完成: strategy_id={strategy_id}, "
        f"return={metrics.get('total_return', 0.0):.2%}, "
        f"sharpe={metrics.get('sharpe_ratio', 0.0):.2f}, time={execution_time_ms}ms"
    )

    # 返回完整的结果数据
    return {
        "execution_id": execution_id,
        "strategy_info": strategy_info,
        "metrics": metrics,
        "equity_curve": equity_curve,
        "trades": trades[:500],  # 限制返回最多500条交易记录
        "stock_charts": stock_charts,
        "execution_time_ms": execution_time_ms,
        "backtest_params": {
            "stock_pool": stock_pool,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
        }
    }


# ==================== API 端点 ====================


@router.post("/", summary="运行回测", status_code=status.HTTP_200_OK)
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
    strategy_params: Optional[Dict[str, Any]] = Body(None, description="策略参数（覆盖默认参数）"),
    exit_strategy_ids: Optional[List[int]] = Body(None, description="离场策略ID列表（可选）"),
    current_user: User = Depends(get_current_active_user)
):
    """
    运行回测

    根据策略ID从 strategies 表加载策略并执行回测。
    自动识别策略类型（builtin/ai/custom）。
    """
    start_time = datetime.now()

    logger.info(
        f"[回测] 开始: strategy_id={strategy_id}, "
        f"stocks={len(stock_pool)}, period={start_date}~{end_date}"
    )

    # 创建执行记录
    execution_id = None
    execution_repo = StrategyExecutionRepository()

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

        # 创建执行记录（status='running'）
        execution_params = {
            'strategy_id': strategy_id,
            'stock_pool': stock_pool,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'rebalance_freq': rebalance_freq,
            'commission_rate': commission_rate,
            'stamp_tax_rate': stamp_tax_rate,
            'min_commission': min_commission,
            'slippage': slippage,
            'strict_mode': strict_mode,
            'strategy_params': strategy_params,
            'exit_strategy_ids': exit_strategy_ids,
        }

        # 创建执行记录数据
        execution_data = {
            'execution_type': 'backtest',
            'execution_params': execution_params,
            'executed_by': current_user.username,
            'strategy_id': strategy_id,
        }

        execution_id = execution_repo.create(execution_data)
        logger.info(f"[回测] 创建执行记录: execution_id={execution_id}")

        # 更新状态为 running
        execution_repo.update_status(execution_id, 'running')

        # 2. 调用核心回测函数执行回测
        result_data = execute_backtest_core(
            params=execution_params,
            execution_id=execution_id,
            progress_callback=None
        )

        # 3. 保存结果到数据库
        metrics = result_data.get('metrics', {})
        db_result = {
            'equity_curve': result_data.get('equity_curve'),
            'trades': result_data.get('trades'),
            'stock_charts': result_data.get('stock_charts'),
        }

        execution_repo.update_result(
            execution_id=execution_id,
            result=db_result,
            metrics=metrics
        )
        execution_repo.update_status(execution_id, 'completed')
        logger.info(f"[回测] 执行记录已更新: execution_id={execution_id}")

        # 4. 更新策略统计
        try:
            from app.repositories.strategy_repository import StrategyRepository
            repo = StrategyRepository()
            repo.increment_backtest_count(strategy_id)
            repo.update_backtest_metrics(
                strategy_id=strategy_id,
                sharpe_ratio=metrics.get('sharpe_ratio', 0.0),
                annual_return=metrics.get('annual_return', 0.0)
            )
        except Exception as e:
            logger.warning(f"更新策略统计失败: {e}")

        # 5. 返回成功响应
        return ApiResponse.success(data=result_data, message="回测完成").to_dict()

    except HTTPException as he:
        # 更新执行记录状态为失败
        if execution_id:
            try:
                execution_repo.update_status(execution_id, 'failed', error_message=str(he.detail))
            except Exception as update_error:
                logger.error("[回测] 更新执行记录失败状态出错: %s", update_error)
        raise

    except ValueError as e:
        error_msg = str(e)
        logger.error("[回测] 参数错误: %s", error_msg)
        # 更新执行记录状态为失败
        if execution_id:
            try:
                execution_repo.update_status(execution_id, 'failed', error_message=error_msg)
            except Exception as update_error:
                logger.error("[回测] 更新执行记录失败状态出错: %s", update_error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    except Exception as e:
        error_msg = str(e)
        logger.error("[回测] 失败: %s", error_msg, exc_info=True)
        # 更新执行记录状态为失败
        if execution_id:
            try:
                execution_repo.update_status(execution_id, 'failed', error_message=error_msg)
            except Exception as update_error:
                logger.error("[回测] 更新执行记录失败状态出错: %s", update_error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="回测失败: " + error_msg
        )
