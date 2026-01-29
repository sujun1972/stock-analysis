"""
IC计算器（Information Coefficient）

用于评估因子的预测能力：
- IC：因子值与未来收益率的相关性
- RankIC：秩相关系数（更稳健）
- ICIR：IC信息比率（IC均值/IC标准差）
- IC时间序列分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple
from loguru import logger
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')


@dataclass
class ICResult:
    """IC计算结果数据类"""
    mean_ic: float  # IC均值
    std_ic: float  # IC标准差
    ic_ir: float  # ICIR（信息比率）
    positive_rate: float  # IC>0的比例
    t_stat: float  # t统计量
    p_value: float  # p值
    ic_series: pd.Series  # IC时间序列

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'mean_ic': self.mean_ic,
            'std_ic': self.std_ic,
            'ic_ir': self.ic_ir,
            'positive_rate': self.positive_rate,
            't_stat': self.t_stat,
            'p_value': self.p_value
        }

    def __str__(self) -> str:
        """格式化输出"""
        return (
            f"IC统计摘要:\n"
            f"  均值: {self.mean_ic:.4f}\n"
            f"  标准差: {self.std_ic:.4f}\n"
            f"  ICIR: {self.ic_ir:.4f}\n"
            f"  正值率: {self.positive_rate:.2%}\n"
            f"  t统计量: {self.t_stat:.4f}\n"
            f"  p值: {self.p_value:.4f}"
        )


class ICCalculator:
    """
    IC计算器 - 评估因子的预测能力

    IC（Information Coefficient）是因子值与未来收益率的相关系数，
    用于衡量因子的预测能力。

    典型判断标准：
    - |IC| > 0.03：有效因子
    - ICIR > 0.5：稳定的有效因子
    - 正值率 > 55%：有方向性
    """

    def __init__(self, forward_periods: int = 5, method: str = 'pearson'):
        """
        初始化IC计算器

        Args:
            forward_periods: 前瞻期（天数），默认5天
            method: 相关性计算方法 ('pearson' 或 'spearman')
                - pearson: 线性相关
                - spearman: 秩相关（更稳健，推荐）
        """
        self.forward_periods = forward_periods
        self.method = method

        if method not in ['pearson', 'spearman']:
            raise ValueError(f"method必须是'pearson'或'spearman'，得到: {method}")

        logger.info(f"初始化IC计算器: 前瞻期={forward_periods}天, 方法={method}")

    def calculate_ic(
        self,
        factor: pd.Series,
        future_returns: pd.Series
    ) -> float:
        """
        计算单个时间点的IC值

        Args:
            factor: 因子值序列（横截面数据）
            future_returns: 未来收益率序列

        Returns:
            IC值（-1到1之间）
        """
        # 删除NaN值
        valid_mask = factor.notna() & future_returns.notna()
        factor_clean = factor[valid_mask]
        returns_clean = future_returns[valid_mask]

        if len(factor_clean) < 10:  # 至少需要10个有效样本
            return np.nan

        try:
            if self.method == 'pearson':
                ic = factor_clean.corr(returns_clean, method='pearson')
            else:  # spearman
                ic = factor_clean.corr(returns_clean, method='spearman')

            return ic

        except Exception as e:
            logger.debug(f"计算IC失败: {e}")
            return np.nan

    def calculate_ic_series(
        self,
        factor_df: pd.DataFrame,
        prices_df: pd.DataFrame,
        min_periods: int = 20
    ) -> pd.Series:
        """
        计算IC时间序列

        Args:
            factor_df: 因子DataFrame (index=date, columns=stock_codes)
            prices_df: 价格DataFrame (index=date, columns=stock_codes)
            min_periods: 最少需要的股票数量

        Returns:
            IC时间序列
        """
        logger.info(f"计算IC时间序列: 数据范围={factor_df.index[0]} 到 {factor_df.index[-1]}")

        # 计算未来收益率
        future_returns = prices_df.pct_change(self.forward_periods).shift(-self.forward_periods)

        ic_series = {}
        dates = factor_df.index

        for date in dates:
            if date not in future_returns.index:
                continue

            # 获取当期因子值和未来收益率
            factor_values = factor_df.loc[date]
            return_values = future_returns.loc[date]

            # 计算IC
            ic = self.calculate_ic(factor_values, return_values)

            if not np.isnan(ic):
                ic_series[date] = ic

        ic_series = pd.Series(ic_series)
        logger.info(f"IC计算完成: {len(ic_series)}个有效值/{len(dates)}个交易日")

        return ic_series

    def calculate_ic_stats(
        self,
        factor_df: pd.DataFrame,
        prices_df: pd.DataFrame
    ) -> ICResult:
        """
        计算IC统计指标（完整分析）

        Args:
            factor_df: 因子DataFrame
            prices_df: 价格DataFrame

        Returns:
            ICResult对象，包含所有IC统计指标
        """
        logger.info("开始计算IC统计指标...")

        # 1. 计算IC时间序列
        ic_series = self.calculate_ic_series(factor_df, prices_df)

        if len(ic_series) < 10:
            raise ValueError(f"有效IC值太少({len(ic_series)})，无法计算统计指标")

        # 2. 计算统计指标
        mean_ic = ic_series.mean()
        std_ic = ic_series.std()
        ic_ir = mean_ic / std_ic if std_ic > 0 else 0.0
        positive_rate = (ic_series > 0).mean()

        # 3. 计算t统计量和p值
        n = len(ic_series)
        t_stat = mean_ic / (std_ic / np.sqrt(n)) if std_ic > 0 else 0.0

        # 简化的p值计算（双侧检验）
        from scipy import stats
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n-1))

        result = ICResult(
            mean_ic=mean_ic,
            std_ic=std_ic,
            ic_ir=ic_ir,
            positive_rate=positive_rate,
            t_stat=t_stat,
            p_value=p_value,
            ic_series=ic_series
        )

        logger.success(f"IC统计完成: IC={mean_ic:.4f}, ICIR={ic_ir:.4f}")

        return result

    def calculate_multi_factor_ic(
        self,
        factor_dict: Dict[str, pd.DataFrame],
        prices_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        批量计算多个因子的IC

        Args:
            factor_dict: 因子字典 {因子名: 因子DataFrame}
            prices_df: 价格DataFrame

        Returns:
            IC统计表 (index=因子名, columns=统计指标)
        """
        logger.info(f"开始批量计算{len(factor_dict)}个因子的IC...")

        results = []

        for factor_name, factor_df in factor_dict.items():
            try:
                logger.debug(f"计算因子: {factor_name}")
                ic_result = self.calculate_ic_stats(factor_df, prices_df)

                row = {
                    '因子名': factor_name,
                    'IC均值': ic_result.mean_ic,
                    'IC标准差': ic_result.std_ic,
                    'ICIR': ic_result.ic_ir,
                    'IC正值率': ic_result.positive_rate,
                    't统计量': ic_result.t_stat,
                    'p值': ic_result.p_value,
                    '有效天数': len(ic_result.ic_series)
                }
                results.append(row)

            except Exception as e:
                logger.error(f"计算因子{factor_name}的IC失败: {e}")
                continue

        if not results:
            raise ValueError("所有因子的IC计算均失败")

        df = pd.DataFrame(results).set_index('因子名')

        # 按ICIR降序排序
        df = df.sort_values('ICIR', ascending=False)

        logger.success(f"批量IC计算完成，成功{len(df)}/{len(factor_dict)}个因子")

        return df

    def calculate_rolling_ic(
        self,
        factor_df: pd.DataFrame,
        prices_df: pd.DataFrame,
        window: int = 60
    ) -> pd.DataFrame:
        """
        计算滚动IC（评估因子稳定性）

        Args:
            factor_df: 因子DataFrame
            prices_df: 价格DataFrame
            window: 滚动窗口大小（天数）

        Returns:
            滚动IC统计DataFrame (columns=['IC均值', 'ICIR', 'IC正值率'])
        """
        logger.info(f"计算{window}天滚动IC...")

        # 先计算完整IC时间序列
        ic_series = self.calculate_ic_series(factor_df, prices_df)

        # 计算滚动统计
        rolling_mean = ic_series.rolling(window=window).mean()
        rolling_std = ic_series.rolling(window=window).std()
        rolling_ir = rolling_mean / rolling_std
        rolling_positive = ic_series.rolling(window=window).apply(lambda x: (x > 0).mean())

        result_df = pd.DataFrame({
            'IC均值': rolling_mean,
            'IC标准差': rolling_std,
            'ICIR': rolling_ir,
            'IC正值率': rolling_positive
        })

        logger.success(f"滚动IC计算完成")

        return result_df

    def analyze_ic_decay(
        self,
        factor_df: pd.DataFrame,
        prices_df: pd.DataFrame,
        max_period: int = 20
    ) -> pd.DataFrame:
        """
        分析IC衰减（不同持有期的IC）

        Args:
            factor_df: 因子DataFrame
            prices_df: 价格DataFrame
            max_period: 最大持有期

        Returns:
            IC衰减DataFrame (index=持有期, columns=['IC均值', 'ICIR'])
        """
        logger.info(f"分析IC衰减: 1-{max_period}天")

        decay_results = []

        for period in range(1, max_period + 1):
            # 临时修改前瞻期
            original_period = self.forward_periods
            self.forward_periods = period

            try:
                ic_result = self.calculate_ic_stats(factor_df, prices_df)

                decay_results.append({
                    '持有期': period,
                    'IC均值': ic_result.mean_ic,
                    'ICIR': ic_result.ic_ir,
                    'IC正值率': ic_result.positive_rate
                })

            except Exception as e:
                logger.warning(f"持有期{period}天的IC计算失败: {e}")

            # 恢复原始前瞻期
            self.forward_periods = original_period

        decay_df = pd.DataFrame(decay_results).set_index('持有期')

        logger.success(f"IC衰减分析完成")

        return decay_df

    def plot_ic_series(
        self,
        ic_result: ICResult,
        title: str = "IC时间序列",
        save_path: Optional[str] = None
    ):
        """
        绘制IC时间序列图

        Args:
            ic_result: IC计算结果
            title: 图表标题
            save_path: 保存路径（可选）
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')  # 无图形界面模式

            plt.rcParams['font.sans-serif'] = ['SimHei']  # 中文字体
            plt.rcParams['axes.unicode_minus'] = False

            fig, axes = plt.subplots(2, 1, figsize=(14, 10))

            # 1. IC时间序列图
            ax1 = axes[0]
            ic_result.ic_series.plot(ax=ax1, label='IC', linewidth=1)
            ax1.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
            ax1.axhline(y=ic_result.mean_ic, color='red', linestyle='--',
                       label=f'均值={ic_result.mean_ic:.4f}', linewidth=1)
            ax1.fill_between(
                ic_result.ic_series.index,
                ic_result.mean_ic - ic_result.std_ic,
                ic_result.mean_ic + ic_result.std_ic,
                alpha=0.2, color='red', label=f'±1标准差'
            )
            ax1.set_title(f"{title}\nICIR={ic_result.ic_ir:.4f}, 正值率={ic_result.positive_rate:.2%}")
            ax1.set_ylabel('IC值')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 2. IC累积分布图
            ax2 = axes[1]
            cumulative_ic = ic_result.ic_series.cumsum()
            cumulative_ic.plot(ax=ax2, label='累积IC', linewidth=2, color='green')
            ax2.set_title('累积IC曲线')
            ax2.set_ylabel('累积IC值')
            ax2.set_xlabel('日期')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"IC图表已保存: {save_path}")
            else:
                plt.savefig('/tmp/ic_series.png', dpi=300, bbox_inches='tight')
                logger.info("IC图表已保存: /tmp/ic_series.png")

            plt.close()

        except ImportError:
            logger.warning("matplotlib未安装，跳过绘图")
        except Exception as e:
            logger.error(f"绘制IC图表失败: {e}")


