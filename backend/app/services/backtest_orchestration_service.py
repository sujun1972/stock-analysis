"""
回测编排服务 (Backtest Orchestration Service)

负责协调整个回测流程，包括：
- 策略加载和验证
- 市场数据准备
- 特征工程计算
- 回测执行
- 结果格式化

作者: Backend Team
创建日期: 2026-03-19
版本: 1.0.0
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

import pandas as pd
from loguru import logger

from app.core_adapters.data_adapter import DataAdapter
from app.repositories.strategy_repository import StrategyRepository
from app.services.strategy_loader import StrategyDynamicLoader
from app.utils.data_cleaning import sanitize_float_values
from app.schemas.backtest_schemas import BacktestExecutionParams

# 添加 core 项目到 Python 路径
if Path("/app/core").exists():
    core_path = Path("/app/core")
else:
    core_path = Path(__file__).parent.parent.parent.parent / "core"

if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

# 导入 Core 模块
from src.backtest import BacktestEngine
from src.backtest.performance_analyzer import PerformanceAnalyzer
from src.data_pipeline.feature_engineer import FeatureEngineer


class BacktestOrchestrationService:
    """
    回测编排服务

    职责：
    - 协调策略加载、数据准备、特征计算、回测执行等步骤
    - 提供统一的回测执行接口
    - 处理进度回调和结果格式化
    """

    def __init__(self):
        """初始化回测编排服务"""
        self.data_adapter = DataAdapter()
        self.strategy_repo = StrategyRepository()

    def execute_backtest(
        self,
        params: BacktestExecutionParams,
        execution_id: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        执行回测

        Args:
            params: 回测执行参数
            execution_id: 执行记录ID（可选）
            progress_callback: 进度回调函数(current, total, status)

        Returns:
            Dict containing:
                - execution_id: 执行记录ID
                - strategy_info: 策略信息
                - metrics: 绩效指标
                - equity_curve: 权益曲线
                - trades: 交易记录
                - stock_charts: 股票K线图数据
                - backtest_params: 回测参数
                - execution_time_ms: 执行时间（毫秒）
        """
        start_time = datetime.now()

        logger.info(
            f"[回测编排] 开始: strategy_id={params.strategy_id}, "
            f"stocks={len(params.stock_pool)}, period={params.start_date}~{params.end_date}"
        )

        try:
            # 1. 加载策略
            if progress_callback:
                progress_callback(1, 11, '加载策略配置...')

            strategy_record, strategy = self._load_strategy(params)

            # 2. 加载市场数据
            if progress_callback:
                progress_callback(3, 11, '加载市场数据...')

            market_data = self._load_market_data(
                params.stock_pool,
                params.start_date,
                params.end_date
            )

            # 3. 准备价格数据
            if progress_callback:
                progress_callback(4, 11, '准备价格数据...')

            prices = self._prepare_prices(market_data)

            # 4. 计算特征数据（如果策略需要）
            if progress_callback:
                progress_callback(5, 11, '计算特征数据...')

            features = self._compute_features(strategy, params.stock_pool, market_data, prices)

            # 5. 生成交易信号
            if progress_callback:
                progress_callback(6, 11, '生成交易信号...')

            signals = self._generate_signals(strategy, prices, features)

            # 6. 加载离场策略
            if progress_callback:
                progress_callback(7, 11, '加载离场策略...')

            exit_manager = self._load_exit_manager(params.exit_strategy_ids)

            # 7. 执行回测
            if progress_callback:
                progress_callback(8, 11, '执行回测引擎...')

            result = self._run_backtest_engine(
                signals=signals,
                prices=prices,
                market_data=market_data,
                strategy=strategy,
                rebalance_freq=params.rebalance_freq,
                exit_manager=exit_manager
            )

            # 8. 计算绩效指标
            if progress_callback:
                progress_callback(9, 11, '计算绩效指标...')

            metrics = self._calculate_metrics(result)

            # 9. 格式化结果
            if progress_callback:
                progress_callback(10, 11, '生成图表数据...')

            equity_curve = self._format_equity_curve(result)
            trades = self._format_trades(result, market_data)
            stock_charts = self._generate_stock_charts(params.stock_pool, market_data, trades)

            # 10. 构建返回结果
            if progress_callback:
                progress_callback(11, 11, '保存结果...')

            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            logger.success(
                f"[回测编排] 完成: strategy_id={params.strategy_id}, "
                f"return={metrics.get('total_return', 0.0):.2%}, "
                f"sharpe={metrics.get('sharpe_ratio', 0.0):.2f}, time={execution_time_ms}ms"
            )

            return {
                "execution_id": execution_id,
                "strategy_info": self._build_strategy_info(strategy_record),
                "metrics": metrics,
                "equity_curve": equity_curve,
                "trades": trades[:500],  # 限制返回最多500条交易记录
                "stock_charts": stock_charts,
                "execution_time_ms": execution_time_ms,
                "backtest_params": {
                    "stock_pool": params.stock_pool,
                    "start_date": params.start_date,
                    "end_date": params.end_date,
                    "initial_capital": params.initial_capital,
                }
            }

        except Exception as e:
            logger.error(f"[回测编排] 失败: {e}", exc_info=True)
            raise

    def _load_strategy(self, params: BacktestExecutionParams) -> tuple:
        """加载策略"""
        strategy_record = self.strategy_repo.get_by_id(params.strategy_id)

        if not strategy_record:
            raise ValueError(f"策略不存在: strategy_id={params.strategy_id}")

        if not strategy_record['is_enabled']:
            raise ValueError(f"策略未启用: {strategy_record['name']}")

        if strategy_record['validation_status'] != 'passed' and params.strict_mode:
            raise ValueError(f"策略验证未通过: {strategy_record['validation_status']}")

        # 使用统一的策略动态加载器
        if strategy_record['source_type'] in ['builtin', 'ai', 'custom']:
            try:
                strategy = StrategyDynamicLoader.load_strategy(
                    strategy_record=strategy_record,
                    custom_config=params.strategy_params
                )
                logger.info(f"[回测编排] 策略加载成功: {strategy_record['name']}")
                return strategy_record, strategy
            except Exception as e:
                logger.error(f"加载策略失败: {e}", exc_info=True)
                raise ValueError(f"加载策略失败: {str(e)}")
        else:
            raise ValueError(f"不支持的策略来源类型: {strategy_record['source_type']}")

    def _load_market_data(
        self,
        stock_pool: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """加载市场数据"""
        market_data = pd.DataFrame()
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

        query_manager = self.data_adapter.query_manager
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

        logger.info(f"[回测编排] 加载市场数据完成: {len(market_data)} 条记录")
        return market_data

    def _prepare_prices(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """准备价格数据"""
        # 准备日期列
        if 'date' in market_data.columns:
            market_data['trade_date'] = pd.to_datetime(market_data['date'])
        elif 'trade_date' not in market_data.columns:
            raise ValueError(f"市场数据缺少日期列")

        # 去重：同一天同一股票只保留最后一条记录
        market_data = market_data.drop_duplicates(subset=['trade_date', 'code'], keep='last')

        # Pivot to wide format: index=dates, columns=stock codes
        ohlcv_dfs = {
            'open': market_data.pivot(index='trade_date', columns='code', values='open').sort_index(),
            'high': market_data.pivot(index='trade_date', columns='code', values='high').sort_index(),
            'low': market_data.pivot(index='trade_date', columns='code', values='low').sort_index(),
            'close': market_data.pivot(index='trade_date', columns='code', values='close').sort_index(),
            'volume': market_data.pivot(index='trade_date', columns='code', values='volume').sort_index()
        }

        # 合并成多层列结构的 DataFrame
        prices = pd.concat(ohlcv_dfs, axis=1, keys=ohlcv_dfs.keys())

        logger.info(f"[回测编排] 价格数据: {len(prices)} 天 x {len(prices['close'].columns)} 只股票")
        return prices

    def _compute_features(
        self,
        strategy: Any,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        prices: pd.DataFrame
    ) -> Optional[pd.DataFrame]:
        """计算特征数据（如果策略需要）"""
        features = None

        try:
            import inspect
            if hasattr(strategy, 'generate_signals'):
                sig = inspect.signature(strategy.generate_signals)
                # 如果generate_signals有features参数，则计算特征
                if 'features' in sig.parameters:
                    logger.info(f"[回测编排] 开始计算特征数据...")

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

                            # 计算特征
                            engineer = FeatureEngineer(verbose=False)
                            stock_data = engineer._compute_technical_indicators(stock_data)
                            stock_data = engineer._compute_alpha_factors(stock_data)

                            # 存储特征
                            features_dict[code] = stock_data

                        except Exception as e:
                            logger.warning(f"计算股票 {code} 特征失败: {e}")
                            continue

                    if features_dict:
                        # 提取所有因子名称
                        first_stock = list(features_dict.keys())[0]
                        factor_columns = [col for col in features_dict[first_stock].columns
                                         if col not in ['open', 'high', 'low', 'close', 'volume', 'amount', 'code']]

                        # 构建因子数据
                        all_dates = prices.index
                        features_data = {}

                        for factor in factor_columns:
                            factor_data = pd.DataFrame(index=all_dates, columns=prices['close'].columns)
                            for code in prices['close'].columns:
                                if code in features_dict:
                                    stock_features = features_dict[code]
                                    if factor in stock_features.columns:
                                        factor_data[code] = stock_features[factor].reindex(all_dates)
                            features_data[factor] = factor_data

                        # 转换为MultiIndex DataFrame
                        features = pd.concat(features_data, axis=1)
                        logger.info(f"[回测编排] 特征计算完成: {len(factor_columns)} 个因子")
                    else:
                        logger.warning(f"[回测编排] 没有成功计算任何特征数据")
        except Exception as e:
            logger.warning(f"[回测编排] 特征计算失败: {e}", exc_info=True)

        return features

    def _generate_signals(
        self,
        strategy: Any,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame]
    ) -> pd.DataFrame:
        """生成交易信号"""
        if hasattr(strategy, 'generate_signals'):
            # 标准信号生成接口
            if features is not None:
                signals = strategy.generate_signals(prices, features=features)
            else:
                signals = strategy.generate_signals(prices)
        elif hasattr(strategy, 'calculate_momentum'):
            # 动量策略
            momentum_raw = strategy.calculate_momentum(prices)
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
            raise ValueError("策略缺少信号生成方法（generate_signals/calculate_momentum/calculate_scores）")

        logger.info(f"[回测编排] 信号生成完成: {len(signals)} 个交易日")
        return signals

    def _load_exit_manager(self, exit_strategy_ids: Optional[List[int]]) -> Optional[Any]:
        """加载离场策略"""
        exit_manager = None
        if exit_strategy_ids and len(exit_strategy_ids) > 0:
            try:
                exit_manager = StrategyDynamicLoader.load_exit_manager(
                    exit_strategy_ids=exit_strategy_ids,
                    repo=self.strategy_repo
                )
                logger.info(f"[回测编排] 离场策略加载成功")
            except Exception as e:
                logger.warning(f"[回测编排] 加载离场策略失败: {e}", exc_info=True)

        return exit_manager

    def _run_backtest_engine(
        self,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        market_data: pd.DataFrame,
        strategy: Any,
        rebalance_freq: str,
        exit_manager: Optional[Any]
    ) -> Any:
        """运行回测引擎"""
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

        return result

    def _calculate_metrics(self, result: Any) -> Dict[str, Any]:
        """计算绩效指标"""
        result_data = result.data if isinstance(result.data, dict) else {}

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
                metrics = self._get_default_metrics(positions)
        elif portfolio_value_df is not None and not portfolio_value_df.empty:
            # 降级：从portfolio_value计算简单指标
            logger.info("使用 portfolio_value 计算简单指标")
            initial_value = portfolio_value_df['total'].iloc[0]
            final_value = portfolio_value_df['total'].iloc[-1]
            total_return = (final_value / initial_value - 1) if initial_value > 0 else 0.0

            metrics = self._get_default_metrics(positions)
            metrics['total_return'] = float(total_return)
        else:
            logger.warning("portfolio_value 和 daily_returns 数据都为空，无法计算指标")
            metrics = self._get_default_metrics(None)

        return sanitize_float_values(metrics)

    def _format_equity_curve(self, result: Any) -> List[Dict[str, Any]]:
        """格式化权益曲线"""
        result_data = result.data if isinstance(result.data, dict) else {}
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

        return sanitize_float_values(equity_curve)

    def _format_trades(self, result: Any, market_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """格式化交易记录"""
        result_data = result.data if isinstance(result.data, dict) else {}
        trades = []

        # 提取交易记录
        if 'recorder' in result_data:
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

        # 从数据库查询股票名称
        stock_name_map = self._get_stock_names(market_data)

        # 统一交易记录日期格式并添加股票名称
        for trade in trades:
            # 标准化日期
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

        return sanitize_float_values(trades)

    def _generate_stock_charts(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成K线图表数据"""
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

        logger.info(f"K线图表生成完成，成功生成 {len(stock_charts)} 个股票的图表（股票池: {len(stock_pool)}）")
        return sanitize_float_values(stock_charts)

    def _get_stock_names(self, market_data: pd.DataFrame) -> Dict[str, str]:
        """获取股票名称映射"""
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
                        result_df = pd.read_sql(query, conn)
                        if not result_df.empty:
                            stock_name_map = dict(zip(result_df['code'], result_df['name']))
                            logger.debug(f"已获取 {len(stock_name_map)} 个股票名称")
                        else:
                            logger.warning("stock_basic表中未找到股票名称")
        except Exception as e:
            logger.warning(f"查询股票名称失败: {e}")

        return stock_name_map

    def _build_strategy_info(self, strategy_record: Dict[str, Any]) -> Dict[str, Any]:
        """构建策略信息"""
        return {
            'strategy_id': strategy_record['id'],
            'name': strategy_record['name'],
            'display_name': strategy_record['display_name'],
            'source_type': strategy_record['source_type'],
            'class_name': strategy_record['class_name'],
            'category': strategy_record['category'],
        }

    @staticmethod
    def _get_default_metrics(positions=None) -> Dict[str, Any]:
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
