"""
回测服务层
处理单股和多股回测任务
"""

from typing import Dict, List, Optional, Union
from datetime import datetime, date
import pandas as pd
import numpy as np
from loguru import logger
import uuid

from src.backtest import BacktestEngine, PerformanceAnalyzer
from src.features import TechnicalIndicators, AlphaFactors
from src.database.db_manager import DatabaseManager
from app.strategies.strategy_manager import strategy_manager


class BacktestService:
    """回测服务"""

    def __init__(self):
        self.db = DatabaseManager()
        # 缓存运行中的回测任务
        self._running_tasks: Dict[str, Dict] = {}

    def _normalize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码,去除交易所后缀
        数据库中存储的是不带后缀的代码
        """
        # 去除后缀 .SH .SZ .BJ
        if '.' in symbol:
            return symbol.split('.')[0]
        return symbol

    async def run_backtest(
        self,
        symbols: Union[str, List[str]],
        start_date: str,
        end_date: str,
        initial_cash: float = 1000000.0,
        strategy_params: Optional[Dict] = None,
        strategy_id: str = "complex_indicator"
    ) -> Dict:
        """
        运行回测任务

        参数:
            symbols: 股票代码(单个或列表)
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金
            strategy_params: 策略参数
            strategy_id: 策略ID (默认使用复合指标策略)

        返回:
            回测结果字典
        """
        task_id = str(uuid.uuid4())

        # 标准化symbols为列表
        if isinstance(symbols, str):
            symbols = [symbols]

        # 获取策略实例
        strategy = strategy_manager.get_strategy(strategy_id, strategy_params)

        logger.info(f"开始回测任务 {task_id}: symbols={symbols}, strategy={strategy_id}, period={start_date}~{end_date}")

        try:
            # 判断单股还是多股模式
            if len(symbols) == 1:
                result = await self._run_single_stock_backtest(
                    symbol=symbols[0],
                    start_date=start_date,
                    end_date=end_date,
                    initial_cash=initial_cash,
                    strategy=strategy
                )
            else:
                result = await self._run_multi_stock_backtest(
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                    initial_cash=initial_cash,
                    strategy=strategy
                )

            # 添加任务元信息
            result['task_id'] = task_id
            result['symbols'] = symbols
            result['start_date'] = start_date
            result['end_date'] = end_date
            result['initial_cash'] = initial_cash
            result['strategy_id'] = strategy_id
            result['strategy_name'] = strategy.name
            result['strategy_params'] = strategy.params
            result['created_at'] = datetime.now().isoformat()

            # 缓存结果
            self._running_tasks[task_id] = result

            # 将task_id添加到结果中
            result['task_id'] = task_id

            logger.info(f"回测任务 {task_id} 完成")
            return result

        except Exception as e:
            logger.error(f"回测任务 {task_id} 失败: {e}")
            raise

    async def _run_single_stock_backtest(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_cash: float,
        strategy
    ) -> Dict:
        """
        单股回测模式
        返回: K线数据 + 买卖信号点 + 每日净值
        """
        logger.info(f"运行单股回测: {symbol}, 策略: {strategy.name}")

        # 标准化股票代码(去除后缀)
        normalized_symbol = self._normalize_symbol(symbol)

        # 1. 获取价格数据
        import asyncio
        price_data_df = await asyncio.to_thread(
            self.db.load_daily_data,
            normalized_symbol,
            start_date=start_date,
            end_date=end_date
        )

        if price_data_df is None or len(price_data_df) == 0:
            raise ValueError(f"股票 {symbol} 无数据")

        # DataFrame已经有date作为索引,直接使用
        df = price_data_df.copy()
        # 确保索引是datetime类型
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        # 确保按日期排序
        df = df.sort_index()

        # 2. 生成交易信号 (使用策略)
        logger.info(f"使用策略生成信号: {strategy.name}")
        signals = strategy.generate_signals(df)

        # 3. 模拟交易并计算净值
        equity_curve, trades = self._simulate_trades(
            df,
            signals,
            initial_cash
        )

        # 4. 获取基准数据(沪深300)
        benchmark_data = await self._get_benchmark_data(start_date, end_date)

        # 5. 计算绩效指标
        analyzer = PerformanceAnalyzer(equity_curve['returns'])
        if benchmark_data is not None and len(benchmark_data) > 0:
            analyzer.set_benchmark(benchmark_data['returns'])

        metrics = {
            'total_return': analyzer.total_return(),
            'annualized_return': analyzer.annualized_return(),
            'sharpe_ratio': analyzer.sharpe_ratio(),
            'max_drawdown': analyzer.max_drawdown(),
            'max_drawdown_duration': analyzer.max_drawdown_duration(),
            'volatility': analyzer.volatility(),
            'win_rate': analyzer.win_rate() if len(trades) > 0 else 0.0,
            'calmar_ratio': analyzer.calmar_ratio(),
            'sortino_ratio': analyzer.sortino_ratio()
        }

        # 6. 准备返回数据
        # K线数据(优化传输,降采样)
        kline_data = self._optimize_kline_data(df)

        # 买卖信号点
        signal_points = self._extract_signal_points(trades)

        # 每日净值曲线
        equity_data = self._optimize_equity_curve(equity_curve)

        # 基准净值曲线
        benchmark_equity = None
        if benchmark_data is not None:
            benchmark_equity = self._optimize_equity_curve(benchmark_data)

        return {
            'mode': 'single',
            'symbol': symbol,
            'kline_data': kline_data,
            'signal_points': signal_points,
            'equity_curve': equity_data,
            'benchmark_curve': benchmark_equity,
            'metrics': metrics,
            'trades': trades[:100],  # 只返回最近100笔交易
            'total_trades': len(trades)
        }

    async def _run_multi_stock_backtest(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        initial_cash: float,
        strategy
    ) -> Dict:
        """
        多股组合回测模式
        返回: 组合净值曲线 + 绩效指标
        """
        logger.info(f"运行多股组合回测: {len(symbols)}只股票, 策略: {strategy.name}")

        # 1. 获取所有股票的价格数据
        import asyncio
        prices_dict = {}
        for symbol in symbols:
            # 标准化股票代码(去除后缀)
            normalized_symbol = self._normalize_symbol(symbol)
            try:
                df = await asyncio.to_thread(
                    self.db.load_daily_data,
                    normalized_symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                if df is not None and len(df) > 0:
                    # DataFrame的date已经是索引,确保是datetime类型
                    if not isinstance(df.index, pd.DatetimeIndex):
                        df.index = pd.to_datetime(df.index)
                    prices_dict[symbol] = df
                else:
                    logger.warning(f"股票 {symbol} 无数据,跳过")
            except Exception as e:
                logger.error(f"获取股票 {symbol} 数据失败: {e}")

        if len(prices_dict) == 0:
            raise ValueError("所有股票均无有效数据")

        # 2. 构建价格矩阵
        prices_df = pd.DataFrame({
            symbol: df['close'] for symbol, df in prices_dict.items()
        })

        # 3. 计算Alpha因子作为选股信号
        signals_df = self._generate_alpha_signals(prices_dict)

        # 4. 运���回测引擎
        engine = BacktestEngine(
            initial_capital=initial_cash,
            verbose=False
        )

        results = engine.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=strategy_params.get('top_n', 10),
            holding_period=strategy_params.get('holding_period', 5),
            rebalance_freq=strategy_params.get('rebalance_freq', 'W')
        )

        # 5. 获取基准数据
        benchmark_data = await self._get_benchmark_data(start_date, end_date)

        # 6. 计算绩效指标
        analyzer = PerformanceAnalyzer(results['daily_returns'])
        if benchmark_data is not None and len(benchmark_data) > 0:
            analyzer.set_benchmark(benchmark_data['returns'])

        metrics = {
            'total_return': analyzer.total_return(),
            'annualized_return': analyzer.annualized_return(),
            'sharpe_ratio': analyzer.sharpe_ratio(),
            'max_drawdown': analyzer.max_drawdown(),
            'max_drawdown_duration': analyzer.max_drawdown_duration(),
            'volatility': analyzer.volatility(),
            'calmar_ratio': analyzer.calmar_ratio(),
            'sortino_ratio': analyzer.sortino_ratio(),
            'alpha': analyzer.alpha() if benchmark_data is not None else None,
            'beta': analyzer.beta() if benchmark_data is not None else None,
            'information_ratio': analyzer.information_ratio() if benchmark_data is not None else None
        }

        # 7. 优化传输数据
        portfolio_value = results['portfolio_value']
        equity_data = [{
            'date': idx.strftime('%Y-%m-%d'),
            'total': float(row['total']),
            'cash': float(row['cash']),
            'holdings': float(row['holdings'])
        } for idx, row in portfolio_value.iterrows()]

        # 基准数据
        benchmark_equity = None
        if benchmark_data is not None:
            benchmark_equity = self._optimize_equity_curve(benchmark_data)

        return {
            'mode': 'multi',
            'symbols': symbols,
            'equity_curve': equity_data,
            'benchmark_curve': benchmark_equity,
            'metrics': metrics,
            'positions_count': len(results['positions'])
        }

    def _generate_simple_ma_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        生成简单均线交叉信号
        返回: 1=买入, -1=卖出, 0=持有
        """
        signals = pd.Series(0, index=df.index)

        # MA5上穿MA20 = 买入信号
        # MA5下穿MA20 = 卖出信号
        if 'MA5' in df.columns and 'MA20' in df.columns:
            ma5 = df['MA5']
            ma20 = df['MA20']

            # 金叉
            golden_cross = (ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))
            signals[golden_cross] = 1

            # 死叉
            death_cross = (ma5 < ma20) & (ma5.shift(1) >= ma20.shift(1))
            signals[death_cross] = -1

        return signals

    def _simulate_trades(
        self,
        df: pd.DataFrame,
        signals: pd.Series,
        initial_cash: float
    ) -> tuple:
        """
        模拟交易执行
        返回: (净值曲线DataFrame, 交易记录列表)
        """
        cash = initial_cash
        shares = 0
        equity = []
        trades = []

        for date, signal in signals.items():
            if date not in df.index:
                continue

            price = df.loc[date, 'close']

            # 买入信号
            if signal == 1 and shares == 0:
                shares = int(cash / price / 100) * 100  # A股100股为1手
                if shares >= 100:
                    cost = shares * price * 1.0003  # 佣金
                    cash -= cost
                    trades.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'type': 'buy',
                        'price': float(price),
                        'shares': int(shares),
                        'amount': float(cost)
                    })

            # 卖出信号
            elif signal == -1 and shares > 0:
                proceeds = shares * price * 0.9987  # 佣金+印花税
                cash += proceeds
                trades.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'type': 'sell',
                    'price': float(price),
                    'shares': int(shares),
                    'amount': float(proceeds)
                })
                shares = 0

            # 记录每日净值
            market_value = shares * price
            total_value = cash + market_value
            equity.append({
                'date': date,
                'total': total_value,
                'cash': cash,
                'holdings': market_value
            })

        equity_df = pd.DataFrame(equity).set_index('date')
        equity_df['returns'] = equity_df['total'].pct_change()

        return equity_df, trades

    def _generate_alpha_signals(self, prices_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        生成Alpha因子信号矩阵
        """
        signals_dict = {}
        alpha = AlphaFactors()

        for symbol, df in prices_dict.items():
            try:
                # 计算多个Alpha因子
                momentum = alpha.calculate_momentum(df['close'], period=20)
                mean_reversion = alpha.calculate_mean_reversion(df['close'], period=10)

                # 综合信号(简单平均)
                signal = (momentum + mean_reversion) / 2
                signals_dict[symbol] = signal
            except Exception as e:
                logger.error(f"计算 {symbol} Alpha因子失败: {e}")

        return pd.DataFrame(signals_dict)

    async def _get_benchmark_data(
        self,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        获取基准数据(沪深300)
        """
        try:
            # 获取沪深300指数数据
            import asyncio
            benchmark_code = '000300'  # 数据库中存储不带后缀
            df = await asyncio.to_thread(
                self.db.load_daily_data,
                benchmark_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) == 0:
                logger.warning("无法获取基准数据")
                return None

            # DataFrame的date已经是索引,确保是datetime类型
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            # 计算收益率
            df['returns'] = df['close'].pct_change()

            # 归一化为净值曲线(初始值=1)
            df['total'] = (1 + df['returns']).cumprod()

            return df

        except Exception as e:
            logger.error(f"获取基准数据失败: {e}")
            return None

    def _optimize_kline_data(self, df: pd.DataFrame) -> List[Dict]:
        """
        优化K线数据传输(降采样)
        """
        # 如果数据量小于1000条,直接返回
        if len(df) <= 1000:
            return self._df_to_kline_list(df)

        # 否则采样最近1000条
        sampled = df.tail(1000)
        return self._df_to_kline_list(sampled)

    def _df_to_kline_list(self, df: pd.DataFrame) -> List[Dict]:
        """转换DataFrame为K线列表"""
        result = []
        for idx, row in df.iterrows():
            item = {
                'date': idx.strftime('%Y-%m-%d'),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row.get('volume', 0))
            }
            # 添加技术指标
            for col in ['MA5', 'MA20', 'MA60', 'MACD', 'MACD_SIGNAL', 'MACD_HIST',
                       'KDJ_K', 'KDJ_D', 'KDJ_J', 'RSI6', 'RSI12', 'RSI24',
                       'BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER']:
                if col in row.index:
                    value = row[col]
                    item[col] = float(value) if pd.notna(value) else None

            result.append(item)
        return result

    def _extract_signal_points(self, trades: List[Dict]) -> Dict:
        """
        提取买卖信号点
        """
        buy_points = []
        sell_points = []

        for trade in trades:
            if trade['type'] == 'buy':
                buy_points.append({
                    'date': trade['date'],
                    'price': trade['price']
                })
            elif trade['type'] == 'sell':
                sell_points.append({
                    'date': trade['date'],
                    'price': trade['price']
                })

        return {
            'buy': buy_points,
            'sell': sell_points
        }

    def _optimize_equity_curve(self, df: pd.DataFrame) -> List[Dict]:
        """
        优化净值曲线数据传输
        """
        # 如果数据量小于500条,直接返回
        if len(df) <= 500:
            return [
                {
                    'date': idx.strftime('%Y-%m-%d'),
                    'value': float(row['total'])
                }
                for idx, row in df.iterrows()
            ]

        # 否则等间隔采样500个点
        step = len(df) // 500
        sampled = df.iloc[::step]

        return [
            {
                'date': idx.strftime('%Y-%m-%d'),
                'value': float(row['total'])
            }
            for idx, row in sampled.iterrows()
        ]

    def get_task_result(self, task_id: str) -> Optional[Dict]:
        """获取任务结果"""
        return self._running_tasks.get(task_id)
