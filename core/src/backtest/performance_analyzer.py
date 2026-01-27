"""
绩效分析器
计算回测策略的各项绩效指标
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
import warnings
from loguru import logger

warnings.filterwarnings('ignore')


class PerformanceAnalyzer:
    """策略绩效分析器"""

    def __init__(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        risk_free_rate: float = 0.03,
        periods_per_year: int = 252
    ):
        """
        初始化绩效分析器

        参数:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列
            risk_free_rate: 无风险利率（年化）
            periods_per_year: 每年期数（日频=252, 周频=52, 月频=12）
        """
        self.returns = returns.dropna()
        self.benchmark_returns = benchmark_returns.dropna() if benchmark_returns is not None else None
        self.risk_free_rate = risk_free_rate
        self.periods_per_year = periods_per_year

        self.metrics = {}

    # ==================== 收益指标 ====================

    def total_return(self) -> float:
        """总收益率"""
        return (1 + self.returns).prod() - 1

    def annualized_return(self) -> float:
        """年化收益率"""
        total_return = self.total_return()
        n_periods = len(self.returns)
        n_years = n_periods / self.periods_per_year

        if n_years > 0:
            return (1 + total_return) ** (1 / n_years) - 1
        else:
            return 0.0

    def cumulative_returns(self) -> pd.Series:
        """累计收益率曲线"""
        return (1 + self.returns).cumprod() - 1

    # ==================== 风险指标 ====================

    def volatility(self, annualize: bool = True) -> float:
        """波动率（标准差）"""
        vol = self.returns.std()

        if annualize:
            vol = vol * np.sqrt(self.periods_per_year)

        return vol

    def downside_deviation(self, annualize: bool = True) -> float:
        """下行偏差（仅负收益的标准差）"""
        negative_returns = self.returns[self.returns < 0]

        if len(negative_returns) > 0:
            downside_dev = negative_returns.std()
        else:
            downside_dev = 0.0

        if annualize:
            downside_dev = downside_dev * np.sqrt(self.periods_per_year)

        return downside_dev

    def max_drawdown(self) -> float:
        """最大回撤"""
        cum_returns = self.cumulative_returns()
        running_max = (1 + cum_returns).cummax()
        drawdown = (1 + cum_returns) / running_max - 1
        return drawdown.min()

    def max_drawdown_duration(self) -> int:
        """最大回撤持续期（天数）"""
        cum_returns = self.cumulative_returns()
        running_max = (1 + cum_returns).cummax()
        drawdown = (1 + cum_returns) / running_max - 1

        # 找到回撤期
        is_drawdown = drawdown < 0
        drawdown_groups = (is_drawdown != is_drawdown.shift()).cumsum()

        if is_drawdown.any():
            max_duration = drawdown_groups[is_drawdown].value_counts().max()
            return int(max_duration)
        else:
            return 0

    def calmar_ratio(self) -> float:
        """卡玛比率（年化收益率 / 最大回撤）"""
        ann_return = self.annualized_return()
        max_dd = abs(self.max_drawdown())

        if max_dd > 0:
            return ann_return / max_dd
        else:
            return np.inf if ann_return > 0 else 0.0

    # ==================== 风险调整收益指标 ====================

    def sharpe_ratio(self) -> float:
        """夏普比率"""
        excess_return = self.annualized_return() - self.risk_free_rate
        annual_vol = self.volatility(annualize=True)

        if annual_vol > 0:
            return excess_return / annual_vol
        else:
            return 0.0

    def sortino_ratio(self) -> float:
        """索提诺比率（使用下行偏差）"""
        excess_return = self.annualized_return() - self.risk_free_rate
        downside_dev = self.downside_deviation(annualize=True)

        if downside_dev > 0:
            return excess_return / downside_dev
        else:
            return np.inf if excess_return > 0 else 0.0

    def information_ratio(self) -> float:
        """信息比率（相对基准的超额收益 / 跟踪误差）"""
        if self.benchmark_returns is None:
            return np.nan

        # 对齐数据
        aligned = pd.DataFrame({
            'strategy': self.returns,
            'benchmark': self.benchmark_returns
        }).dropna()

        if len(aligned) == 0:
            return np.nan

        # 超额收益
        excess_returns = aligned['strategy'] - aligned['benchmark']

        # 年化超额收益
        ann_excess_return = excess_returns.mean() * self.periods_per_year

        # 跟踪误差（超额收益的标准差）
        tracking_error = excess_returns.std() * np.sqrt(self.periods_per_year)

        if tracking_error > 0:
            return ann_excess_return / tracking_error
        else:
            return 0.0

    # ==================== 交易统计 ====================

    def win_rate(self) -> float:
        """胜率（正收益天数比例）"""
        return (self.returns > 0).mean()

    def profit_factor(self) -> float:
        """盈亏比（总盈利 / 总亏损）"""
        profits = self.returns[self.returns > 0].sum()
        losses = abs(self.returns[self.returns < 0].sum())

        if losses > 0:
            return profits / losses
        else:
            return np.inf if profits > 0 else 0.0

    def average_win(self) -> float:
        """平均盈利"""
        wins = self.returns[self.returns > 0]
        return wins.mean() if len(wins) > 0 else 0.0

    def average_loss(self) -> float:
        """平均亏损"""
        losses = self.returns[self.returns < 0]
        return losses.mean() if len(losses) > 0 else 0.0

    def win_loss_ratio(self) -> float:
        """盈亏比（平均盈利 / 平均亏损）"""
        avg_win = self.average_win()
        avg_loss = abs(self.average_loss())

        if avg_loss > 0:
            return avg_win / avg_loss
        else:
            return np.inf if avg_win > 0 else 0.0

    # ==================== 综合分析 ====================

    def calculate_all_metrics(self, verbose: bool = True) -> Dict[str, float]:
        """
        计算所有绩效指标

        参数:
            verbose: 是否打印结果

        返回:
            所有指标字典
        """
        self.metrics = {
            # 收益指标
            'total_return': self.total_return(),
            'annualized_return': self.annualized_return(),

            # 风险指标
            'volatility': self.volatility(),
            'downside_deviation': self.downside_deviation(),
            'max_drawdown': self.max_drawdown(),
            'max_drawdown_duration': self.max_drawdown_duration(),

            # 风险调整收益
            'sharpe_ratio': self.sharpe_ratio(),
            'sortino_ratio': self.sortino_ratio(),
            'calmar_ratio': self.calmar_ratio(),

            # 交易统计
            'win_rate': self.win_rate(),
            'profit_factor': self.profit_factor(),
            'average_win': self.average_win(),
            'average_loss': self.average_loss(),
            'win_loss_ratio': self.win_loss_ratio(),
        }

        # 基准相关指标
        if self.benchmark_returns is not None:
            self.metrics['information_ratio'] = self.information_ratio()

            # 计算Alpha和Beta
            aligned = pd.DataFrame({
                'strategy': self.returns,
                'benchmark': self.benchmark_returns
            }).dropna()

            if len(aligned) > 1:
                # Beta
                cov = aligned['strategy'].cov(aligned['benchmark'])
                var = aligned['benchmark'].var()
                beta = cov / var if var > 0 else 0.0

                # Alpha（年化）
                strategy_return = self.annualized_return()
                benchmark_analyzer = PerformanceAnalyzer(
                    self.benchmark_returns,
                    risk_free_rate=self.risk_free_rate,
                    periods_per_year=self.periods_per_year
                )
                benchmark_return = benchmark_analyzer.annualized_return()
                alpha = strategy_return - (self.risk_free_rate + beta * (benchmark_return - self.risk_free_rate))

                self.metrics['alpha'] = alpha
                self.metrics['beta'] = beta

        if verbose:
            self.print_metrics()

        return self.metrics

    def print_metrics(self):
        """打印绩效指标"""
        if not self.metrics:
            self.calculate_all_metrics(verbose=False)

        logger.info("\n" + "="*60)
        logger.info("策略绩效分析")
        logger.info("="*60)

        logger.info("\n收益指标:")
        logger.info(f"  总收益率:           {self.metrics['total_return']*100:>10.2f}%")
        logger.info(f"  年化收益率:         {self.metrics['annualized_return']*100:>10.2f}%")

        logger.info("\n风险指标:")
        logger.info(f"  年化波动率:         {self.metrics['volatility']*100:>10.2f}%")
        logger.info(f"  下行偏差:           {self.metrics['downside_deviation']*100:>10.2f}%")
        logger.info(f"  最大回撤:           {self.metrics['max_drawdown']*100:>10.2f}%")
        logger.info(f"  最大回撤持续期:     {self.metrics['max_drawdown_duration']:>10.0f} 天")

        logger.info("\n风险调整收益:")
        logger.info(f"  夏普比率:           {self.metrics['sharpe_ratio']:>10.4f}")
        logger.info(f"  索提诺比率:         {self.metrics['sortino_ratio']:>10.4f}")
        logger.info(f"  卡玛比率:           {self.metrics['calmar_ratio']:>10.4f}")

        logger.info("\n交易统计:")
        logger.info(f"  胜率:               {self.metrics['win_rate']*100:>10.2f}%")
        logger.info(f"  盈亏比:             {self.metrics['profit_factor']:>10.4f}")
        logger.info(f"  平均盈利:           {self.metrics['average_win']*100:>10.4f}%")
        logger.info(f"  平均亏损:           {self.metrics['average_loss']*100:>10.4f}%")
        logger.info(f"  盈亏比率:           {self.metrics['win_loss_ratio']:>10.4f}")

        if 'alpha' in self.metrics:
            logger.info("\n相对基准:")
            logger.info(f"  Alpha:              {self.metrics['alpha']*100:>10.2f}%")
            logger.info(f"  Beta:               {self.metrics['beta']:>10.4f}")
            logger.info(f"  信息比率:           {self.metrics['information_ratio']:>10.4f}")

        logger.info("="*60 + "\n")

    def get_metrics(self) -> Dict[str, float]:
        """获取所有指标"""
        if not self.metrics:
            self.calculate_all_metrics(verbose=False)
        return self.metrics.copy()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    logger.info("绩效分析器测试\n")

    # 创建测试数据
    np.random.seed(42)
    n_days = 252  # 1年交易日

    # 模拟策略收益率（带正向趋势）
    strategy_returns = pd.Series(
        np.random.normal(0.001, 0.015, n_days),
        index=pd.date_range('2023-01-01', periods=n_days, freq='D')
    )

    # 模拟基准收益率（市场收益）
    benchmark_returns = pd.Series(
        np.random.normal(0.0005, 0.012, n_days),
        index=pd.date_range('2023-01-01', periods=n_days, freq='D')
    )

    logger.info("测试数据:")
    logger.info(f"  交易日数: {n_days}")
    logger.info(f"  策略平均日收益: {strategy_returns.mean()*100:.4f}%")
    logger.info(f"  基准平均日收益: {benchmark_returns.mean()*100:.4f}%")

    # 创建分析器
    logger.info("\n初始化绩效分析器:")
    analyzer = PerformanceAnalyzer(
        returns=strategy_returns,
        benchmark_returns=benchmark_returns,
        risk_free_rate=0.03,
        periods_per_year=252
    )

    # 计算所有指标
    logger.info("\n计算绩效指标:")
    metrics = analyzer.calculate_all_metrics(verbose=True)

    # 测试单项指标
    logger.info("\n测试单项指标:")
    logger.info(f"总收益率: {analyzer.total_return()*100:.2f}%")
    logger.info(f"夏普比率: {analyzer.sharpe_ratio():.4f}")
    logger.info(f"最大回撤: {analyzer.max_drawdown()*100:.2f}%")

    logger.success("\n✓ 绩效分析器测试完成")
