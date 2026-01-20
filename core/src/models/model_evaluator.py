"""
模型评估器
实现量化交易专用的评估指标：IC, RankIC, Sharpe, 信息系数等
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from scipy import stats
import warnings

warnings.filterwarnings('ignore')


class ModelEvaluator:
    """模型评估器（量化交易专用指标）"""

    def __init__(self):
        """初始化评估器"""
        self.metrics = {}

    @staticmethod
    def calculate_ic(
        predictions: np.ndarray,
        actual_returns: np.ndarray,
        method: str = 'pearson'
    ) -> float:
        """
        计算IC (Information Coefficient)
        衡量预测值与实际收益率的相关性

        参数:
            predictions: 预测值
            actual_returns: 实际收益率
            method: 相关系数方法 ('pearson', 'spearman')

        返回:
            IC值
        """
        # 移除NaN值
        mask = ~(np.isnan(predictions) | np.isnan(actual_returns))
        predictions = predictions[mask]
        actual_returns = actual_returns[mask]

        if len(predictions) < 2:
            return np.nan

        if method == 'pearson':
            ic, _ = stats.pearsonr(predictions, actual_returns)
        elif method == 'spearman':
            ic, _ = stats.spearmanr(predictions, actual_returns)
        else:
            raise ValueError(f"不支持的方法: {method}")

        return ic

    @staticmethod
    def calculate_rank_ic(
        predictions: np.ndarray,
        actual_returns: np.ndarray
    ) -> float:
        """
        计算Rank IC (秩相关系数)
        使用Spearman相关系数，对异常值更稳健

        参数:
            predictions: 预测值
            actual_returns: 实际收益率

        返回:
            Rank IC值
        """
        return ModelEvaluator.calculate_ic(predictions, actual_returns, method='spearman')

    @staticmethod
    def calculate_ic_ir(
        ic_series: pd.Series
    ) -> float:
        """
        计算IC IR (Information Ratio)
        IC的均值除以IC的标准差

        参数:
            ic_series: IC时间序列

        返回:
            IC IR值
        """
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()

        if ic_std == 0 or np.isnan(ic_std):
            return np.nan

        return ic_mean / ic_std

    @staticmethod
    def calculate_group_returns(
        predictions: np.ndarray,
        actual_returns: np.ndarray,
        n_groups: int = 5
    ) -> Dict[int, float]:
        """
        计算分组收益率
        将预测值分成N组，计算各组的平均收益率

        参数:
            predictions: 预测值
            actual_returns: 实际收益率
            n_groups: 分组数量

        返回:
            {组号: 平均收益率} 字典
        """
        # 移除NaN
        mask = ~(np.isnan(predictions) | np.isnan(actual_returns))
        predictions = predictions[mask]
        actual_returns = actual_returns[mask]

        # 按预测值分组
        df = pd.DataFrame({
            'pred': predictions,
            'ret': actual_returns
        })

        df['group'] = pd.qcut(df['pred'], q=n_groups, labels=False, duplicates='drop')

        # 计算各组平均收益
        group_returns = df.groupby('group')['ret'].mean().to_dict()

        return group_returns

    @staticmethod
    def calculate_long_short_return(
        predictions: np.ndarray,
        actual_returns: np.ndarray,
        top_pct: float = 0.2,
        bottom_pct: float = 0.2
    ) -> Dict[str, float]:
        """
        计算多空组合收益率
        做多预测值最高的top_pct，做空预测值最低的bottom_pct

        参数:
            predictions: 预测值
            actual_returns: 实际收益率
            top_pct: 做多比例
            bottom_pct: 做空比例

        返回:
            {'long': 多头收益, 'short': 空头收益, 'long_short': 多空收益}
        """
        # 移除NaN
        mask = ~(np.isnan(predictions) | np.isnan(actual_returns))
        predictions = predictions[mask]
        actual_returns = actual_returns[mask]

        # 排序
        df = pd.DataFrame({
            'pred': predictions,
            'ret': actual_returns
        }).sort_values('pred', ascending=False)

        # 计算多头和空头
        n_stocks = len(df)
        n_long = int(n_stocks * top_pct)
        n_short = int(n_stocks * bottom_pct)

        long_return = df.head(n_long)['ret'].mean()
        short_return = df.tail(n_short)['ret'].mean()
        long_short_return = long_return - short_return

        return {
            'long': long_return,
            'short': short_return,
            'long_short': long_short_return
        }

    @staticmethod
    def calculate_sharpe_ratio(
        returns: np.ndarray,
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252
    ) -> float:
        """
        计算Sharpe比率
        (年化收益率 - 无风险利率) / 年化波动率

        参数:
            returns: 收益率序列
            risk_free_rate: 无风险利率（年化）
            periods_per_year: 每年期数（日频=252）

        返回:
            Sharpe比率
        """
        # 移除NaN
        returns = returns[~np.isnan(returns)]

        if len(returns) < 2:
            return np.nan

        # 年化收益率
        mean_return = np.mean(returns) * periods_per_year

        # 年化波动率
        std_return = np.std(returns, ddof=1) * np.sqrt(periods_per_year)

        if std_return == 0:
            return np.nan

        sharpe = (mean_return - risk_free_rate) / std_return

        return sharpe

    @staticmethod
    def calculate_max_drawdown(
        returns: np.ndarray
    ) -> float:
        """
        计算最大回撤

        参数:
            returns: 收益率序列

        返回:
            最大回撤（正值）
        """
        # 累计收益
        cum_returns = (1 + returns).cumprod()

        # 历史最高点
        running_max = np.maximum.accumulate(cum_returns)

        # 回撤
        drawdown = (cum_returns - running_max) / running_max

        # 最大回撤
        max_dd = -drawdown.min()

        return max_dd

    @staticmethod
    def calculate_win_rate(
        returns: np.ndarray,
        threshold: float = 0.0
    ) -> float:
        """
        计算胜率

        参数:
            returns: 收益率序列
            threshold: 盈利阈值

        返回:
            胜率（0-1之间）
        """
        returns = returns[~np.isnan(returns)]

        if len(returns) == 0:
            return np.nan

        win_rate = np.mean(returns > threshold)

        return win_rate

    def evaluate_regression(
        self,
        predictions: np.ndarray,
        actual_returns: np.ndarray,
        verbose: bool = True
    ) -> Dict[str, float]:
        """
        全面评估回归预测

        参数:
            predictions: 预测值
            actual_returns: 实际收益率
            verbose: 是否打印结果

        返回:
            评估指标字典
        """
        from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error

        # 移除NaN
        mask = ~(np.isnan(predictions) | np.isnan(actual_returns))
        preds = predictions[mask]
        actuals = actual_returns[mask]

        metrics = {}

        # 传统回归指标
        metrics['mse'] = mean_squared_error(actuals, preds)
        metrics['rmse'] = np.sqrt(metrics['mse'])
        metrics['mae'] = mean_absolute_error(actuals, preds)
        metrics['r2'] = r2_score(actuals, preds)

        # 量化交易专用指标
        metrics['ic'] = self.calculate_ic(preds, actuals, method='pearson')
        metrics['rank_ic'] = self.calculate_rank_ic(preds, actuals)

        # 分组收益率
        group_returns = self.calculate_group_returns(preds, actuals, n_groups=5)
        for group, ret in group_returns.items():
            metrics[f'group_{group}_return'] = ret

        # 多空收益
        long_short = self.calculate_long_short_return(preds, actuals, top_pct=0.2, bottom_pct=0.2)
        metrics.update({
            'long_return': long_short['long'],
            'short_return': long_short['short'],
            'long_short_return': long_short['long_short']
        })

        # 保存指标
        self.metrics = metrics

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
        评估时间序列预测（计算每日IC并汇总）

        参数:
            predictions_by_date: {日期: 预测值数组} 字典
            actuals_by_date: {日期: 实际收益率数组} 字典
            verbose: 是否打印结果

        返回:
            评估指标字典
        """
        # 计算每日IC
        daily_ic = []
        daily_rank_ic = []

        for date in sorted(predictions_by_date.keys()):
            if date in actuals_by_date:
                preds = predictions_by_date[date]
                actuals = actuals_by_date[date]

                ic = self.calculate_ic(preds, actuals, method='pearson')
                rank_ic = self.calculate_rank_ic(preds, actuals)

                if not np.isnan(ic):
                    daily_ic.append(ic)
                if not np.isnan(rank_ic):
                    daily_rank_ic.append(rank_ic)

        ic_series = pd.Series(daily_ic)
        rank_ic_series = pd.Series(daily_rank_ic)

        metrics = {
            'ic_mean': ic_series.mean(),
            'ic_std': ic_series.std(),
            'ic_ir': self.calculate_ic_ir(ic_series),
            'ic_positive_rate': (ic_series > 0).mean(),
            'rank_ic_mean': rank_ic_series.mean(),
            'rank_ic_std': rank_ic_series.std(),
            'rank_ic_ir': self.calculate_ic_ir(rank_ic_series),
            'rank_ic_positive_rate': (rank_ic_series > 0).mean()
        }

        self.metrics = metrics

        if verbose:
            self.print_metrics()

        return metrics

    def print_metrics(self):
        """打印评估指标"""
        if not self.metrics:
            print("没有可用的评估指标")
            return

        print("\n" + "="*60)
        print("模型评估指标")
        print("="*60)

        # 分类显示
        regression_metrics = ['mse', 'rmse', 'mae', 'r2']
        ic_metrics = ['ic', 'rank_ic', 'ic_mean', 'ic_std', 'ic_ir',
                     'rank_ic_mean', 'rank_ic_std', 'rank_ic_ir']
        return_metrics = ['long_return', 'short_return', 'long_short_return']

        # 传统回归指标
        if any(m in self.metrics for m in regression_metrics):
            print("\n回归指标:")
            for metric in regression_metrics:
                if metric in self.metrics:
                    print(f"  {metric.upper():12s}: {self.metrics[metric]:.6f}")

        # IC指标
        if any(m in self.metrics for m in ic_metrics):
            print("\nIC指标:")
            for metric in ic_metrics:
                if metric in self.metrics:
                    print(f"  {metric.upper():18s}: {self.metrics[metric]:.6f}")

        # 分组收益率
        group_metrics = [k for k in self.metrics.keys() if k.startswith('group_')]
        if group_metrics:
            print("\n分组收益率:")
            for metric in sorted(group_metrics):
                print(f"  {metric:20s}: {self.metrics[metric]:.6f}")

        # 多空收益
        if any(m in self.metrics for m in return_metrics):
            print("\n多空收益:")
            for metric in return_metrics:
                if metric in self.metrics:
                    print(f"  {metric:20s}: {self.metrics[metric]:.6f}")

        # 其他指标
        other_metrics = [k for k in self.metrics.keys()
                        if k not in regression_metrics + ic_metrics + return_metrics + group_metrics]
        if other_metrics:
            print("\n其他指标:")
            for metric in other_metrics:
                print(f"  {metric:20s}: {self.metrics[metric]:.6f}")

        print("="*60 + "\n")

    def get_metrics(self) -> Dict[str, float]:
        """获取评估指标"""
        return self.metrics.copy()


# ==================== 便捷函数 ====================

def evaluate_model(
    predictions: np.ndarray,
    actual_returns: np.ndarray,
    evaluation_type: str = 'regression'
) -> Dict[str, float]:
    """
    便捷函数：评估模型

    参数:
        predictions: 预测值
        actual_returns: 实际收益率
        evaluation_type: 评估类型 ('regression', 'ranking')

    返回:
        评估指标字典
    """
    evaluator = ModelEvaluator()

    if evaluation_type == 'regression':
        return evaluator.evaluate_regression(predictions, actual_returns)
    elif evaluation_type == 'ranking':
        # 仅计算排名相关指标
        metrics = {
            'rank_ic': evaluator.calculate_rank_ic(predictions, actual_returns)
        }
        long_short = evaluator.calculate_long_short_return(predictions, actual_returns)
        metrics.update(long_short)
        return metrics
    else:
        raise ValueError(f"不支持的评估类型: {evaluation_type}")


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("模型评估器测试\n")

    # 创建测试数据
    np.random.seed(42)
    n_samples = 1000

    # 模拟预测值和实际收益率（有一定相关性）
    true_signal = np.random.randn(n_samples)
    predictions = true_signal + np.random.randn(n_samples) * 0.5
    actual_returns = true_signal * 0.02 + np.random.randn(n_samples) * 0.01

    print("数据准备:")
    print(f"  样本数: {n_samples}")
    print(f"  预测值均值: {predictions.mean():.4f}")
    print(f"  实际收益率均值: {actual_returns.mean():.4f}")

    # 评估模型
    print("\n1. 回归评估:")
    evaluator = ModelEvaluator()
    metrics = evaluator.evaluate_regression(predictions, actual_returns)

    # 测试IC计算
    print("\n2. IC指标:")
    ic = ModelEvaluator.calculate_ic(predictions, actual_returns, method='pearson')
    rank_ic = ModelEvaluator.calculate_rank_ic(predictions, actual_returns)
    print(f"  IC: {ic:.4f}")
    print(f"  Rank IC: {rank_ic:.4f}")

    # 测试分组收益
    print("\n3. 分组收益:")
    group_returns = ModelEvaluator.calculate_group_returns(predictions, actual_returns, n_groups=5)
    for group, ret in sorted(group_returns.items()):
        print(f"  Group {group}: {ret:.6f}")

    # 测试多空收益
    print("\n4. 多空收益:")
    long_short = ModelEvaluator.calculate_long_short_return(predictions, actual_returns)
    print(f"  Long: {long_short['long']:.6f}")
    print(f"  Short: {long_short['short']:.6f}")
    print(f"  Long-Short: {long_short['long_short']:.6f}")

    # 测试Sharpe比率
    print("\n5. Sharpe比率:")
    sharpe = ModelEvaluator.calculate_sharpe_ratio(actual_returns)
    print(f"  Sharpe Ratio: {sharpe:.4f}")

    # 测试最大回撤
    print("\n6. 最大回撤:")
    max_dd = ModelEvaluator.calculate_max_drawdown(actual_returns)
    print(f"  Max Drawdown: {max_dd:.4%}")

    # 测试胜率
    print("\n7. 胜率:")
    win_rate = ModelEvaluator.calculate_win_rate(actual_returns)
    print(f"  Win Rate: {win_rate:.4%}")

    print("\n✓ 模型评估器测试完成")
