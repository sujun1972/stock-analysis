"""
模型评估器
实现量化交易专用的评估指标：IC, RankIC, Sharpe, 信息系数等

重构说明：
- 模块化设计：分离指标计算、结果格式化和主评估逻辑
- 统一日志系统：使用 loguru 替代 print
- 增强错误处理：自定义异常类和数据验证
- 性能优化：向量化操作和结果缓存
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple, Union
from scipy import stats
from functools import wraps
from dataclasses import dataclass
from loguru import logger
import warnings

warnings.filterwarnings('ignore')


# ==================== 异常类 ====================

class EvaluationError(Exception):
    """评估过程错误基类"""
    pass


class InsufficientDataError(EvaluationError):
    """数据不足错误"""
    pass


class InvalidInputError(EvaluationError):
    """无效输入错误"""
    pass


# ==================== 数据类 ====================

@dataclass
class EvaluationConfig:
    """评估配置"""
    n_groups: int = 5
    top_pct: float = 0.2
    bottom_pct: float = 0.2
    risk_free_rate: float = 0.0
    periods_per_year: int = 252
    min_samples: int = 2


# ==================== 装饰器 ====================

def validate_input_arrays(func):
    """
    验证输入数组的装饰器
    - 检查是否为 None
    - 检查长度是否一致
    - 检查是否有足够的数据
    """
    @wraps(func)
    def wrapper(self, predictions: np.ndarray, actual_returns: np.ndarray, *args, **kwargs):
        # 检查 None
        if predictions is None or actual_returns is None:
            raise InvalidInputError("预测值或实际收益率为 None")

        # 转换为 numpy 数组
        predictions = np.asarray(predictions)
        actual_returns = np.asarray(actual_returns)

        # 检查长度
        if len(predictions) != len(actual_returns):
            raise InvalidInputError(
                f"预测值和实际收益率长度不一致: {len(predictions)} vs {len(actual_returns)}"
            )

        # 检查数据量
        if len(predictions) == 0:
            raise InsufficientDataError("输入数据为空")

        return func(self, predictions, actual_returns, *args, **kwargs)

    return wrapper


def safe_compute(metric_name: str, default_value=np.nan):
    """
    安全计算装饰器，捕获并记录异常

    Args:
        metric_name: 指标名称
        default_value: 出错时的默认返回值
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # 只对数值类型检查 NaN 和 Inf
                if isinstance(result, (int, float, np.number)):
                    if np.isnan(result) or np.isinf(result):
                        logger.warning(f"{metric_name} 计算结果为 NaN 或 Inf")
                return result
            except Exception as e:
                logger.error(f"计算 {metric_name} 时出错: {str(e)}")
                return default_value
        return wrapper
    return decorator


# ==================== 辅助函数 ====================

def filter_valid_pairs(
    predictions: np.ndarray,
    actual_returns: np.ndarray,
    min_samples: int = 2
) -> Tuple[np.ndarray, np.ndarray]:
    """
    过滤有效的预测-收益对

    Args:
        predictions: 预测值
        actual_returns: 实际收益率
        min_samples: 最小样本数

    Returns:
        过滤后的 (predictions, actual_returns)

    Raises:
        InsufficientDataError: 有效数据不足
    """
    # 移除 NaN 和 Inf
    mask = (
        ~np.isnan(predictions) &
        ~np.isnan(actual_returns) &
        ~np.isinf(predictions) &
        ~np.isinf(actual_returns)
    )

    valid_preds = predictions[mask]
    valid_returns = actual_returns[mask]

    if len(valid_preds) < min_samples:
        raise InsufficientDataError(
            f"有效数据不足: {len(valid_preds)} < {min_samples}"
        )

    return valid_preds, valid_returns


# ==================== 指标计算器 ====================

class MetricsCalculator:
    """指标计算器：负责各种量化指标的计算"""

    @staticmethod
    @safe_compute("IC")
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
        try:
            valid_preds, valid_returns = filter_valid_pairs(predictions, actual_returns)
        except InsufficientDataError:
            logger.warning("计算 IC 时数据不足")
            return np.nan

        if method == 'pearson':
            ic, _ = stats.pearsonr(valid_preds, valid_returns)
        elif method == 'spearman':
            ic, _ = stats.spearmanr(valid_preds, valid_returns)
        else:
            raise ValueError(f"不支持的方法: {method}")

        return float(ic)

    @staticmethod
    @safe_compute("Rank IC")
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
        return MetricsCalculator.calculate_ic(predictions, actual_returns, method='spearman')

    @staticmethod
    @safe_compute("IC IR")
    def calculate_ic_ir(ic_series: pd.Series) -> float:
        """
        计算 IC IR (Information Ratio)
        IC 的均值除以 IC 的标准差

        Args:
            ic_series: IC 时间序列

        Returns:
            IC IR 值
        """
        if len(ic_series) < 2:
            return np.nan

        ic_mean = ic_series.mean()
        ic_std = ic_series.std()

        if ic_std == 0 or np.isnan(ic_std):
            return np.nan

        return float(ic_mean / ic_std)

    @staticmethod
    @safe_compute("分组收益率", default_value={})
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
        try:
            valid_preds, valid_returns = filter_valid_pairs(predictions, actual_returns)
        except InsufficientDataError:
            logger.warning("计算分组收益率时数据不足")
            return {}

        # 按预测值分组
        df = pd.DataFrame({
            'pred': valid_preds,
            'ret': valid_returns
        })

        try:
            df['group'] = pd.qcut(df['pred'], q=n_groups, labels=False, duplicates='drop')
        except ValueError as e:
            logger.warning(f"分组失败: {e}，使用简单分组")
            # 使用简单的等间隔分组
            df['group'] = pd.cut(df['pred'], bins=n_groups, labels=False)

        # 计算各组平均收益
        group_returns = df.groupby('group')['ret'].mean().to_dict()

        return group_returns

    @staticmethod
    @safe_compute("多空收益", default_value={'long': np.nan, 'short': np.nan, 'long_short': np.nan})
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
        try:
            valid_preds, valid_returns = filter_valid_pairs(predictions, actual_returns)
        except InsufficientDataError:
            logger.warning("计算多空收益时数据不足")
            return {'long': np.nan, 'short': np.nan, 'long_short': np.nan}

        # 排序
        df = pd.DataFrame({
            'pred': valid_preds,
            'ret': valid_returns
        }).sort_values('pred', ascending=False)

        # 计算多头和空头
        n_stocks = len(df)
        n_long = max(1, int(n_stocks * top_pct))
        n_short = max(1, int(n_stocks * bottom_pct))

        long_return = df.head(n_long)['ret'].mean()
        short_return = df.tail(n_short)['ret'].mean()
        long_short_return = long_return - short_return

        return {
            'long': float(long_return),
            'short': float(short_return),
            'long_short': float(long_short_return)
        }

    @staticmethod
    @safe_compute("Sharpe 比率")
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
        # 移除 NaN 和 Inf
        returns = returns[~np.isnan(returns) & ~np.isinf(returns)]

        if len(returns) < 2:
            return np.nan

        # 年化收益率
        mean_return = np.mean(returns) * periods_per_year

        # 年化波动率
        std_return = np.std(returns, ddof=1) * np.sqrt(periods_per_year)

        if std_return == 0:
            return np.nan

        sharpe = (mean_return - risk_free_rate) / std_return

        return float(sharpe)

    @staticmethod
    @safe_compute("最大回撤")
    def calculate_max_drawdown(returns: np.ndarray) -> float:
        """
        计算最大回撤

        Args:
            returns: 收益率序列

        Returns:
            最大回撤（正值）
        """
        # 移除 NaN
        returns = returns[~np.isnan(returns) & ~np.isinf(returns)]

        if len(returns) == 0:
            return np.nan

        # 累计收益
        cum_returns = (1 + returns).cumprod()

        # 历史最高点
        running_max = np.maximum.accumulate(cum_returns)

        # 回撤
        drawdown = (cum_returns - running_max) / running_max

        # 最大回撤
        max_dd = -drawdown.min()

        return float(max_dd)

    @staticmethod
    @safe_compute("胜率")
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
        returns = returns[~np.isnan(returns) & ~np.isinf(returns)]

        if len(returns) == 0:
            return np.nan

        win_rate = np.mean(returns > threshold)

        return float(win_rate)


# ==================== 结果格式化器 ====================

class ResultFormatter:
    """结果格式化器：负责格式化和展示评估结果"""

    @staticmethod
    def print_metrics(metrics: Dict[str, float]) -> None:
        """
        打印评估指标

        Args:
            metrics: 指标字典
        """
        if not metrics:
            logger.info("没有可用的评估指标")
            return

        logger.info("\n" + "="*60)
        logger.info("模型评估指标")
        logger.info("="*60)

        # 分类显示
        regression_metrics = ['mse', 'rmse', 'mae', 'r2']
        ic_metrics = [
            'ic', 'rank_ic', 'ic_mean', 'ic_std', 'ic_ir',
            'ic_positive_rate', 'rank_ic_mean', 'rank_ic_std',
            'rank_ic_ir', 'rank_ic_positive_rate'
        ]
        return_metrics = ['long_return', 'short_return', 'long_short_return']

        # 传统回归指标
        if any(m in metrics for m in regression_metrics):
            logger.info("\n回归指标:")
            for metric in regression_metrics:
                if metric in metrics:
                    logger.info(f"  {metric.upper():12s}: {metrics[metric]:.6f}")

        # IC 指标
        if any(m in metrics for m in ic_metrics):
            logger.info("\nIC 指标:")
            for metric in ic_metrics:
                if metric in metrics:
                    logger.info(f"  {metric.upper():24s}: {metrics[metric]:.6f}")

        # 分组收益率
        group_metrics = sorted([k for k in metrics.keys() if k.startswith('group_')])
        if group_metrics:
            logger.info("\n分组收益率:")
            for metric in group_metrics:
                logger.info(f"  {metric:20s}: {metrics[metric]:.6f}")

        # 多空收益
        if any(m in metrics for m in return_metrics):
            logger.info("\n多空收益:")
            for metric in return_metrics:
                if metric in metrics:
                    logger.info(f"  {metric:20s}: {metrics[metric]:.6f}")

        # 其他指标
        other_metrics = [
            k for k in metrics.keys()
            if k not in regression_metrics + ic_metrics + return_metrics + group_metrics
        ]
        if other_metrics:
            logger.info("\n其他指标:")
            for metric in other_metrics:
                logger.info(f"  {metric:20s}: {metrics[metric]:.6f}")

        logger.info("="*60 + "\n")


# ==================== 主评估器 ====================

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


# ==================== 便捷函数 ====================

def evaluate_model(
    predictions: np.ndarray,
    actual_returns: np.ndarray,
    evaluation_type: str = 'regression',
    config: Optional[EvaluationConfig] = None,
    verbose: bool = True
) -> Dict[str, float]:
    """
    便捷函数：评估模型

    Args:
        predictions: 预测值
        actual_returns: 实际收益率
        evaluation_type: 评估类型 ('regression', 'ranking')
        config: 评估配置
        verbose: 是否打印结果

    Returns:
        评估指标字典

    Raises:
        ValueError: 不支持的评估类型
        InvalidInputError: 输入数据无效
    """
    evaluator = ModelEvaluator(config=config)

    if evaluation_type == 'regression':
        return evaluator.evaluate_regression(predictions, actual_returns, verbose=verbose)
    elif evaluation_type == 'ranking':
        # 仅计算排名相关指标
        logger.info("开始排名评估...")
        metrics = {
            'rank_ic': evaluator.calculator.calculate_rank_ic(predictions, actual_returns)
        }
        long_short = evaluator.calculator.calculate_long_short_return(
            predictions, actual_returns,
            top_pct=evaluator.config.top_pct,
            bottom_pct=evaluator.config.bottom_pct
        )
        metrics.update(long_short)

        if verbose:
            evaluator.formatter.print_metrics(metrics)

        return metrics
    else:
        raise ValueError(f"不支持的评估类型: {evaluation_type}，支持: 'regression', 'ranking'")


# ==================== 使用示例 ====================

def _demo_basic_evaluation():
    """基础评估示例"""
    logger.info("="*60)
    logger.info("示例 1: 基础回归评估")
    logger.info("="*60)

    # 创建测试数据
    np.random.seed(42)
    n_samples = 1000

    # 模拟预测值和实际收益率（有一定相关性）
    true_signal = np.random.randn(n_samples)
    predictions = true_signal + np.random.randn(n_samples) * 0.5
    actual_returns = true_signal * 0.02 + np.random.randn(n_samples) * 0.01

    logger.info(f"样本数: {n_samples}")
    logger.info(f"预测值均值: {predictions.mean():.4f}")
    logger.info(f"实际收益率均值: {actual_returns.mean():.4f}\n")

    # 评估模型
    evaluator = ModelEvaluator()
    metrics = evaluator.evaluate_regression(predictions, actual_returns)

    return metrics


def _demo_custom_config():
    """自定义配置示例"""
    logger.info("\n" + "="*60)
    logger.info("示例 2: 使用自定义配置")
    logger.info("="*60)

    # 自定义配置
    config = EvaluationConfig(
        n_groups=10,  # 10 分组
        top_pct=0.1,  # 做多前 10%
        bottom_pct=0.1,  # 做空后 10%
        periods_per_year=250  # 每年 250 个交易日
    )

    # 创建测试数据
    np.random.seed(123)
    n_samples = 500
    predictions = np.random.randn(n_samples)
    actual_returns = predictions * 0.01 + np.random.randn(n_samples) * 0.02

    # 使用便捷函数
    metrics = evaluate_model(
        predictions,
        actual_returns,
        evaluation_type='regression',
        config=config,
        verbose=True
    )

    return metrics


def _demo_timeseries_evaluation():
    """时间序列评估示例"""
    logger.info("\n" + "="*60)
    logger.info("示例 3: 时间序列评估")
    logger.info("="*60)

    # 模拟多日数据
    np.random.seed(456)
    dates = pd.date_range('2023-01-01', periods=60, freq='D')

    predictions_by_date = {}
    actuals_by_date = {}

    for date in dates:
        date_str = date.strftime('%Y-%m-%d')
        n_stocks = np.random.randint(50, 100)

        # 每日的预测值和实际收益率
        true_signal = np.random.randn(n_stocks)
        predictions_by_date[date_str] = true_signal + np.random.randn(n_stocks) * 0.3
        actuals_by_date[date_str] = true_signal * 0.015 + np.random.randn(n_stocks) * 0.01

    # 评估
    evaluator = ModelEvaluator()
    metrics = evaluator.evaluate_timeseries(
        predictions_by_date,
        actuals_by_date,
        verbose=True
    )

    return metrics


def _demo_individual_metrics():
    """单个指标计算示例"""
    logger.info("\n" + "="*60)
    logger.info("示例 4: 单个指标计算")
    logger.info("="*60)

    # 测试数据
    np.random.seed(789)
    n_samples = 200
    predictions = np.random.randn(n_samples)
    actual_returns = predictions * 0.02 + np.random.randn(n_samples) * 0.01

    # 单独计算各指标
    logger.info("\n单独计算各指标:")

    ic = MetricsCalculator.calculate_ic(predictions, actual_returns, method='pearson')
    logger.info(f"  IC: {ic:.4f}")

    rank_ic = MetricsCalculator.calculate_rank_ic(predictions, actual_returns)
    logger.info(f"  Rank IC: {rank_ic:.4f}")

    group_returns = MetricsCalculator.calculate_group_returns(predictions, actual_returns, n_groups=5)
    logger.info(f"\n  分组收益:")
    for group, ret in sorted(group_returns.items()):
        logger.info(f"    Group {group}: {ret:.6f}")

    long_short = MetricsCalculator.calculate_long_short_return(predictions, actual_returns)
    logger.info(f"\n  多空收益:")
    logger.info(f"    Long: {long_short['long']:.6f}")
    logger.info(f"    Short: {long_short['short']:.6f}")
    logger.info(f"    Long-Short: {long_short['long_short']:.6f}")

    sharpe = MetricsCalculator.calculate_sharpe_ratio(actual_returns)
    logger.info(f"\n  Sharpe 比率: {sharpe:.4f}")

    max_dd = MetricsCalculator.calculate_max_drawdown(actual_returns)
    logger.info(f"  最大回撤: {max_dd:.4%}")

    win_rate = MetricsCalculator.calculate_win_rate(actual_returns)
    logger.info(f"  胜率: {win_rate:.4%}")


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        lambda msg: logger.info(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | {message}",
        level="INFO"
    )

    logger.info("\n" + "="*60)
    logger.info("模型评估器测试")
    logger.info("="*60 + "\n")

    # 运行示例
    try:
        _demo_basic_evaluation()
        _demo_custom_config()
        _demo_timeseries_evaluation()
        _demo_individual_metrics()

        logger.success("\n✓ 所有测试完成")

    except Exception as e:
        logger.error(f"\n✗ 测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
