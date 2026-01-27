"""
主评估器
协调各个模块完成模型评估
"""
import numpy as np
import pandas as pd
from typing import Optional, Dict
from loguru import logger

from .config import EvaluationConfig
from .exceptions import InvalidInputError, InsufficientDataError
from .decorators import validate_input_arrays
from .utils import filter_valid_pairs
from .metrics.calculator import MetricsCalculator
from .formatter import ResultFormatter


class ModelEvaluator:
    """
    模型评估器（量化交易专用指标）

    重构后的主评估器作为协调者，使用 MetricsCalculator 计算指标，
    使用 ResultFormatter 格式化输出。

    Attributes:
        config: 评估配置
        metrics: 评估指标字典
        calculator: 指标计算器
        formatter: 结果格式化器
    """

    def __init__(self, config: Optional[EvaluationConfig] = None):
        """
        初始化评估器

        Args:
            config: 评估配置，默认使用 EvaluationConfig()
        """
        self.config = config or EvaluationConfig()
        self.metrics: Dict[str, float] = {}
        self.calculator = MetricsCalculator()
        self.formatter = ResultFormatter()
        logger.debug(f"初始化 ModelEvaluator，配置: {self.config}")

    # ==================== 向后兼容的静态方法 ====================

    @staticmethod
    def calculate_ic(
        predictions: np.ndarray,
        actual_returns: np.ndarray,
        method: str = 'pearson'
    ) -> float:
        """
        计算 IC (Information Coefficient)
        衡量预测值与实际收益率的相关性

        Args:
            predictions: 预测值
            actual_returns: 实际收益率
            method: 相关系数方法 ('pearson', 'spearman')

        Returns:
            IC 值
        """
        return MetricsCalculator.calculate_ic(predictions, actual_returns, method)

    @staticmethod
    def calculate_rank_ic(
        predictions: np.ndarray,
        actual_returns: np.ndarray
    ) -> float:
        """
        计算 Rank IC (秩相关系数)
        使用 Spearman 相关系数，对异常值更稳健

        Args:
            predictions: 预测值
            actual_returns: 实际收益率

        Returns:
            Rank IC 值
        """
        return MetricsCalculator.calculate_rank_ic(predictions, actual_returns)

    @staticmethod
    def calculate_ic_ir(ic_series: pd.Series) -> float:
        """
        计算 IC IR (Information Ratio)
        IC 的均值除以 IC 的标准差

        Args:
            ic_series: IC 时间序列

        Returns:
            IC IR 值
        """
        return MetricsCalculator.calculate_ic_ir(ic_series)

    @staticmethod
    def calculate_group_returns(
        predictions: np.ndarray,
        actual_returns: np.ndarray,
        n_groups: int = 5
    ) -> Dict[int, float]:
        """
        计算分组收益率
        将预测值分成 N 组，计算各组的平均收益率

        Args:
            predictions: 预测值
            actual_returns: 实际收益率
            n_groups: 分组数量

        Returns:
            {组号: 平均收益率} 字典
        """
        return MetricsCalculator.calculate_group_returns(predictions, actual_returns, n_groups)

    @staticmethod
    def calculate_long_short_return(
        predictions: np.ndarray,
        actual_returns: np.ndarray,
        top_pct: float = 0.2,
        bottom_pct: float = 0.2
    ) -> Dict[str, float]:
        """
        计算多空组合收益率
        做多预测值最高的 top_pct，做空预测值最低的 bottom_pct

        Args:
            predictions: 预测值
            actual_returns: 实际收益率
            top_pct: 做多比例
            bottom_pct: 做空比例

        Returns:
            {'long': 多头收益, 'short': 空头收益, 'long_short': 多空收益}
        """
        return MetricsCalculator.calculate_long_short_return(
            predictions, actual_returns, top_pct, bottom_pct
        )

    @staticmethod
    def calculate_sharpe_ratio(
        returns: np.ndarray,
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252
    ) -> float:
        """
        计算 Sharpe 比率
        (年化收益率 - 无风险利率) / 年化波动率

        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率（年化）
            periods_per_year: 每年期数（日频=252）

        Returns:
            Sharpe 比率
        """
        return MetricsCalculator.calculate_sharpe_ratio(returns, risk_free_rate, periods_per_year)

    @staticmethod
    def calculate_max_drawdown(returns: np.ndarray) -> float:
        """
        计算最大回撤

        Args:
            returns: 收益率序列

        Returns:
            最大回撤（正值）
        """
        return MetricsCalculator.calculate_max_drawdown(returns)

    @staticmethod
    def calculate_win_rate(
        returns: np.ndarray,
        threshold: float = 0.0
    ) -> float:
        """
        计算胜率

        Args:
            returns: 收益率序列
            threshold: 盈利阈值

        Returns:
            胜率（0-1 之间）
        """
        return MetricsCalculator.calculate_win_rate(returns, threshold)

    # ==================== 实例方法 ====================

    @validate_input_arrays
    def evaluate_regression(
        self,
        predictions: np.ndarray,
        actual_returns: np.ndarray,
        verbose: bool = True
    ) -> Dict[str, float]:
        """
        全面评估回归预测

        Args:
            predictions: 预测值
            actual_returns: 实际收益率
            verbose: 是否打印结果

        Returns:
            评估指标字典

        Raises:
            InvalidInputError: 输入数据无效
            InsufficientDataError: 数据不足
        """
        logger.info("开始回归评估...")

        try:
            from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
        except ImportError:
            logger.error("缺少 scikit-learn 依赖")
            raise ImportError("需要安装 scikit-learn: pip install scikit-learn")

        # 过滤有效数据
        try:
            preds, actuals = filter_valid_pairs(predictions, actual_returns)
            logger.debug(f"有效数据: {len(preds)}/{len(predictions)}")
        except InsufficientDataError as e:
            logger.error(f"回归评估失败: {e}")
            raise

        metrics = {}

        # 传统回归指标
        logger.debug("计算传统回归指标...")
        metrics['mse'] = float(mean_squared_error(actuals, preds))
        metrics['rmse'] = float(np.sqrt(metrics['mse']))
        metrics['mae'] = float(mean_absolute_error(actuals, preds))
        metrics['r2'] = float(r2_score(actuals, preds))

        # 量化交易专用指标
        logger.debug("计算 IC 指标...")
        metrics['ic'] = self.calculator.calculate_ic(preds, actuals, method='pearson')
        metrics['rank_ic'] = self.calculator.calculate_rank_ic(preds, actuals)

        # 分组收益率
        logger.debug(f"计算分组收益率（{self.config.n_groups} 组）...")
        group_returns = self.calculator.calculate_group_returns(
            preds, actuals, n_groups=self.config.n_groups
        )
        for group, ret in group_returns.items():
            metrics[f'group_{group}_return'] = ret

        # 多空收益
        logger.debug("计算多空收益...")
        long_short = self.calculator.calculate_long_short_return(
            preds, actuals,
            top_pct=self.config.top_pct,
            bottom_pct=self.config.bottom_pct
        )
        metrics.update({
            'long_return': long_short['long'],
            'short_return': long_short['short'],
            'long_short_return': long_short['long_short']
        })

        # 保存指标
        self.metrics = metrics
        logger.info(f"回归评估完成，计算了 {len(metrics)} 个指标")

        # 打印结果
        if verbose:
            self.print_metrics()

        return metrics

    def evaluate_timeseries(
        self,
        predictions_by_date: Dict[str, np.ndarray],
        actuals_by_date: Dict[str, np.ndarray],
        verbose: bool = True
    ) -> Dict[str, float]:
        """
        评估时间序列预测（计算每日 IC 并汇总）

        Args:
            predictions_by_date: {日期: 预测值数组} 字典
            actuals_by_date: {日期: 实际收益率数组} 字典
            verbose: 是否打印结果

        Returns:
            评估指标字典

        Raises:
            InvalidInputError: 输入数据无效
        """
        logger.info("开始时间序列评估...")

        if not predictions_by_date or not actuals_by_date:
            raise InvalidInputError("预测值或实际收益率字典为空")

        # 计算每日 IC
        daily_ic = []
        daily_rank_ic = []
        dates_processed = []

        for date in sorted(predictions_by_date.keys()):
            if date not in actuals_by_date:
                logger.warning(f"日期 {date} 缺少实际收益率数据，跳过")
                continue

            preds = predictions_by_date[date]
            actuals = actuals_by_date[date]

            # 检查数据有效性
            if len(preds) == 0 or len(actuals) == 0:
                logger.warning(f"日期 {date} 的数据为空，跳过")
                continue

            ic = self.calculator.calculate_ic(preds, actuals, method='pearson')
            rank_ic = self.calculator.calculate_rank_ic(preds, actuals)

            if not np.isnan(ic):
                daily_ic.append(ic)
                dates_processed.append(date)
            if not np.isnan(rank_ic):
                daily_rank_ic.append(rank_ic)

        if not daily_ic:
            logger.error("没有计算出有效的 IC 值")
            raise InsufficientDataError("无法计算时间序列指标")

        logger.info(f"成功处理 {len(dates_processed)} 个交易日")

        ic_series = pd.Series(daily_ic)
        rank_ic_series = pd.Series(daily_rank_ic)

        metrics = {
            'ic_mean': float(ic_series.mean()),
            'ic_std': float(ic_series.std()),
            'ic_ir': self.calculator.calculate_ic_ir(ic_series),
            'ic_positive_rate': float((ic_series > 0).mean()),
            'rank_ic_mean': float(rank_ic_series.mean()),
            'rank_ic_std': float(rank_ic_series.std()),
            'rank_ic_ir': self.calculator.calculate_ic_ir(rank_ic_series),
            'rank_ic_positive_rate': float((rank_ic_series > 0).mean())
        }

        self.metrics = metrics
        logger.info(f"时间序列评估完成，计算了 {len(metrics)} 个指标")

        if verbose:
            self.print_metrics()

        return metrics

    def print_metrics(self) -> None:
        """打印评估指标（使用 ResultFormatter）"""
        self.formatter.print_metrics(self.metrics)

    def get_metrics(self) -> Dict[str, float]:
        """
        获取评估指标

        Returns:
            评估指标字典的副本
        """
        return self.metrics.copy()

    def clear_metrics(self) -> None:
        """清空评估指标"""
        self.metrics = {}
        logger.debug("已清空评估指标")
