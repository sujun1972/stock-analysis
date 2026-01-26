"""
回测服务接口定义
使用 Protocol 提供结构化类型约束
"""

from typing import Protocol, Dict, List, Optional, Union, Tuple
import pandas as pd


class IBacktestDataLoader(Protocol):
    """
    回测数据加载器接口

    定义回测数据加载的标准契约
    """

    def normalize_symbol(self, symbol: str) -> str:
        """标准化股票代码"""
        ...

    async def load_single_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """加载单只股票数据"""
        ...

    async def load_multi_stock_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """加载多只股票数据"""
        ...

    async def load_benchmark_data(
        self,
        start_date: str,
        end_date: str,
        benchmark_code: str = '000300'
    ) -> Optional[pd.DataFrame]:
        """加载基准数据"""
        ...


class IBacktestExecutor(Protocol):
    """
    回测执行器接口

    定义回测执行逻辑的标准契约
    """

    def execute_single_stock_backtest(
        self,
        df: pd.DataFrame,
        strategy: Any,
        initial_cash: float,
        benchmark_data: Optional[pd.DataFrame] = None
    ) -> Dict:
        """执行单股回测"""
        ...

    def execute_multi_stock_backtest(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        strategy: Any,
        initial_cash: float,
        benchmark_data: Optional[pd.DataFrame] = None
    ) -> Dict:
        """执行多股组合回测"""
        ...

    def simulate_trades(
        self,
        df: pd.DataFrame,
        signals: pd.Series,
        initial_cash: float
    ) -> Tuple[pd.DataFrame, List[Dict]]:
        """模拟交易执行"""
        ...

    def generate_alpha_signals(
        self,
        prices_dict: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """生成Alpha因子信号"""
        ...

    def calculate_metrics(
        self,
        equity_curve: pd.DataFrame,
        benchmark_data: Optional[pd.DataFrame] = None
    ) -> Dict:
        """计算绩效指标"""
        ...


class IBacktestResultFormatter(Protocol):
    """
    回测结果格式化器接口

    定义回测结果格式化的标准契约
    """

    def optimize_kline_data(
        self,
        df: pd.DataFrame,
        max_points: int = 1000
    ) -> List[Dict]:
        """优化K线数据"""
        ...

    def optimize_equity_curve(
        self,
        df: pd.DataFrame,
        max_points: int = 500
    ) -> List[Dict]:
        """优化净值曲线"""
        ...

    def extract_signal_points(self, trades: List[Dict]) -> Dict:
        """提取买卖信号点"""
        ...

    def format_portfolio_value(
        self,
        portfolio_value: pd.DataFrame
    ) -> List[Dict]:
        """格式化组合净值"""
        ...


class IBacktestService(Protocol):
    """
    回测服务接口（Facade）

    定义回测服务的统一接口契约
    """

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
            strategy_id: 策略ID

        Returns:
            Dict: 回测结果
        """
        ...

    def get_task_result(self, task_id: str) -> Optional[Dict]:
        """获取任务结果"""
        ...
