"""
回测服务（重构版）
使用 Facade 模式委托给专门的服务类
"""

from typing import Dict, List, Optional, Union
from datetime import datetime
from loguru import logger
import uuid

from src.database.db_manager import DatabaseManager
from app.strategies.strategy_manager import strategy_manager
from app.services.backtest_data_loader import BacktestDataLoader
from app.services.backtest_executor import BacktestExecutor
from app.services.backtest_result_formatter import BacktestResultFormatter
from app.core.exceptions import BacktestError, DataQueryError


class BacktestService:
    """
    回测服务（Facade模式）

    将数据加载、回测执行和结果格式化功能委托给专门的服务类，
    提供统一的接口供API层调用。
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化回测服务

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        # 委托给专门的服务
        self.data_loader = BacktestDataLoader(db)
        self.executor = BacktestExecutor()
        self.formatter = BacktestResultFormatter()

        # 缓存运行中的回测任务
        self._running_tasks: Dict[str, Dict] = {}

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

        Args:
            symbols: 股票代码(单个或列表)
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金
            strategy_params: 策略参数
            strategy_id: 策略ID (默认使用复合指标策略)

        Returns:
            回测结果字典
        """
        task_id = str(uuid.uuid4())

        # 标准化symbols为列表
        if isinstance(symbols, str):
            symbols = [symbols]

        # 获取策略实例
        strategy = strategy_manager.get_strategy(strategy_id, strategy_params)

        logger.info(
            f"开始回测任务 {task_id}: "
            f"symbols={symbols}, strategy={strategy_id}, period={start_date}~{end_date}"
        )

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

            logger.info(f"回测任务 {task_id} 完成")
            return result

        except (DataQueryError, BacktestError):
            # 已知的业务异常向上传播
            raise
        except ValueError as e:
            # 参数验证错误
            logger.error(f"回测任务 {task_id} 参数错误: {e}")
            raise BacktestError(
                f"回测参数错误: {str(e)}",
                error_code="BACKTEST_INVALID_PARAMS",
                task_id=task_id,
                symbols=symbols,
                reason=str(e)
            )
        except Exception as e:
            logger.error(f"回测任务 {task_id} 失败: {e}")
            raise BacktestError(
                "回测执行失败",
                error_code="BACKTEST_EXECUTION_FAILED",
                task_id=task_id,
                symbols=symbols,
                reason=str(e)
            )

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

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金
            strategy: 策略实例

        Returns:
            K线数据 + 买卖信号点 + 每日净值
        """
        logger.info(f"运行单股回测: {symbol}, 策略: {strategy.name}")

        # 1. 加载数据
        price_data = await self.data_loader.load_single_stock_data(
            symbol, start_date, end_date
        )
        benchmark_data = await self.data_loader.load_benchmark_data(
            start_date, end_date
        )

        # 2. 执行回测
        backtest_result = self.executor.execute_single_stock_backtest(
            df=price_data,
            strategy=strategy,
            initial_cash=initial_cash,
            benchmark_data=benchmark_data
        )

        # 3. 格式化结果
        kline_data = self.formatter.optimize_kline_data(price_data)
        signal_points = self.formatter.extract_signal_points(
            backtest_result['trades']
        )
        equity_data = self.formatter.optimize_equity_curve(
            backtest_result['equity_curve']
        )

        # 基准净值曲线
        benchmark_equity = None
        if benchmark_data is not None:
            benchmark_equity = self.formatter.optimize_equity_curve(benchmark_data)

        return {
            'mode': 'single',
            'symbol': symbol,
            'kline_data': kline_data,
            'signal_points': signal_points,
            'equity_curve': equity_data,
            'benchmark_curve': benchmark_equity,
            'metrics': backtest_result['metrics'],
            'trades': backtest_result['trades'][:100],  # 只返回最近100笔交易
            'total_trades': len(backtest_result['trades'])
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

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金
            strategy: 策略实例

        Returns:
            组合净值曲线 + 绩效指标
        """
        logger.info(f"运行多股组合回测: {len(symbols)}只股票, 策略: {strategy.name}")

        # 1. 加载数据
        prices_dict = await self.data_loader.load_multi_stock_data(
            symbols, start_date, end_date
        )
        benchmark_data = await self.data_loader.load_benchmark_data(
            start_date, end_date
        )

        # 2. 执行回测
        backtest_result = self.executor.execute_multi_stock_backtest(
            prices_dict=prices_dict,
            strategy=strategy,
            initial_cash=initial_cash,
            benchmark_data=benchmark_data
        )

        # 3. 格式化结果
        equity_data = self.formatter.format_portfolio_value(
            backtest_result['portfolio_value']
        )

        # 基准数据
        benchmark_equity = None
        if benchmark_data is not None:
            benchmark_equity = self.formatter.optimize_equity_curve(benchmark_data)

        return {
            'mode': 'multi',
            'symbols': symbols,
            'equity_curve': equity_data,
            'benchmark_curve': benchmark_equity,
            'metrics': backtest_result['metrics'],
            'positions_count': len(backtest_result['positions'])
        }

    def get_task_result(self, task_id: str) -> Optional[Dict]:
        """
        获取任务结果

        Args:
            task_id: 任务ID

        Returns:
            任务结果字典，不存在则返回 None
        """
        return self._running_tasks.get(task_id)
