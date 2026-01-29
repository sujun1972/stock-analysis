"""
因子分层回测工具

将股票按因子值分为N层，比较各层的收益表现：
- 测试因子的单调性（是否分层越高收益越高）
- 多空组合收益（最高层-最低层）
- 各层的风险收益特征
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')


@dataclass
class LayerResult:
    """单层回测结果"""
    layer_name: str
    mean_return: float  # 平均收益率
    std_return: float  # 收益率标准差
    sharpe_ratio: float  # 夏普比率
    win_rate: float  # 胜率
    max_return: float  # 最大收益率
    min_return: float  # 最小收益率
    total_periods: int  # 总期数

    def to_dict(self) -> Dict:
        return {
            '分层': self.layer_name,
            '平均收益': self.mean_return,
            '收益标准差': self.std_return,
            '夏普比率': self.sharpe_ratio,
            '胜率': self.win_rate,
            '最大收益': self.max_return,
            '最小收益': self.min_return,
            '样本数': self.total_periods
        }


class LayeringTest:
    """
    因子分层测试工具

    用法：
        将股票按因子值分为5层（或10层），
        观察各层的平均收益率是否呈现单调性。

    判断标准：
        - 单调性强：好因子（层1<层2<...<层5）
        - 多空收益高：可用于对冲策略
        - 各层夏普比率：评估风险调整后收益
    """

    def __init__(
        self,
        n_layers: int = 5,
        holding_period: int = 5,
        long_short: bool = True
    ):
        """
        初始化分层测试工具

        Args:
            n_layers: 分层数量（默认5层）
            holding_period: 持有期（天数）
            long_short: 是否计算多空组合收益
        """
        if n_layers < 2:
            raise ValueError("分层数必须至少为2")

        self.n_layers = n_layers
        self.holding_period = holding_period
        self.long_short = long_short

        logger.info(f"初始化分层测试: {n_layers}层, 持有期={holding_period}天")

    def _assign_layers(
        self,
        factor_values: pd.Series,
        n_layers: int
    ) -> pd.Series:
        """
        将股票分配到各层

        Args:
            factor_values: 因子值序列
            n_layers: 分层数

        Returns:
            层级序列（0表示第1层，n_layers-1表示最高层）
        """
        try:
            # 使用qcut进行等频分层
            layers = pd.qcut(
                factor_values,
                q=n_layers,
                labels=False,
                duplicates='drop'  # 处理重复值
            )
            return layers
        except Exception as e:
            logger.debug(f"分层失败: {e}")
            return pd.Series(index=factor_values.index, dtype=float)

    def perform_layering_test(
        self,
        factor_df: pd.DataFrame,
        prices_df: pd.DataFrame,
        returns_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        执行分层测试

        Args:
            factor_df: 因子DataFrame (index=date, columns=stock_codes)
            prices_df: 价格DataFrame (index=date, columns=stock_codes)
            returns_df: 收益率DataFrame（可选，不提供则自动计算）

        Returns:
            分层统计DataFrame
        """
        logger.info("开始执行分层测试...")

        # 计算收益率（如果未提供）
        if returns_df is None:
            returns_df = prices_df.pct_change(self.holding_period).shift(-self.holding_period)

        # 存储各层的收益率
        layer_returns = {f'Layer_{i+1}': [] for i in range(self.n_layers)}

        dates = factor_df.index
        valid_count = 0

        for date in dates:
            if date not in returns_df.index:
                continue

            # 获取当期因子值和下期收益
            factor_values = factor_df.loc[date].dropna()
            next_returns = returns_df.loc[date]

            # 找到共同有效的股票
            common_stocks = factor_values.index.intersection(next_returns.index)
            if len(common_stocks) < self.n_layers:
                continue

            factor_values = factor_values[common_stocks]
            next_returns = next_returns[common_stocks]

            # 分层
            layers = self._assign_layers(factor_values, self.n_layers)

            # 计算各层平均收益
            for i in range(self.n_layers):
                stocks_in_layer = layers[layers == i].index
                if len(stocks_in_layer) > 0:
                    layer_ret = next_returns[stocks_in_layer].mean()
                    layer_returns[f'Layer_{i+1}'].append(layer_ret)

            valid_count += 1

        logger.info(f"有效期数: {valid_count}/{len(dates)}")

        # 计算统计指标
        results = []

        for layer_name, returns_list in layer_returns.items():
            if len(returns_list) == 0:
                continue

            returns_series = pd.Series(returns_list)

            result = LayerResult(
                layer_name=layer_name,
                mean_return=returns_series.mean(),
                std_return=returns_series.std(),
                sharpe_ratio=returns_series.mean() / returns_series.std() if returns_series.std() > 0 else 0,
                win_rate=(returns_series > 0).mean(),
                max_return=returns_series.max(),
                min_return=returns_series.min(),
                total_periods=len(returns_series)
            )

            results.append(result.to_dict())

        # 创建结果DataFrame
        if len(results) == 0:
            # 没有有效结果，返回空DataFrame
            logger.warning("没有有效的分层结果")
            return pd.DataFrame()

        summary_df = pd.DataFrame(results).set_index('分层')

        # 计算多空组合（如果启用）
        if self.long_short and len(layer_returns[f'Layer_{self.n_layers}']) > 0:
            long_returns = pd.Series(layer_returns[f'Layer_{self.n_layers}'])
            short_returns = pd.Series(layer_returns['Layer_1'])

            # 确保长度一致
            min_len = min(len(long_returns), len(short_returns))
            long_short_returns = long_returns[:min_len] - short_returns[:min_len]

            long_short_result = LayerResult(
                layer_name='Long_Short',
                mean_return=long_short_returns.mean(),
                std_return=long_short_returns.std(),
                sharpe_ratio=long_short_returns.mean() / long_short_returns.std()
                            if long_short_returns.std() > 0 else 0,
                win_rate=(long_short_returns > 0).mean(),
                max_return=long_short_returns.max(),
                min_return=long_short_returns.min(),
                total_periods=len(long_short_returns)
            )

            # 添加多空组合行
            long_short_df = pd.DataFrame([long_short_result.to_dict()]).set_index('分层')
            summary_df = pd.concat([summary_df, long_short_df])

        logger.success(f"分层测试完成: {len(summary_df)}个分层")

        return summary_df

    def analyze_monotonicity(
        self,
        layering_result: pd.DataFrame
    ) -> Dict:
        """
        分析因子单调性

        Args:
            layering_result: 分层测试结果DataFrame

        Returns:
            单调性分析字典
        """
        # 提取各层平均收益（排除多空组合）
        layers = [f'Layer_{i+1}' for i in range(self.n_layers)]
        layer_returns = layering_result.loc[layers, '平均收益'].values

        # 计算单调性指标
        is_monotonic = all(layer_returns[i] <= layer_returns[i+1]
                          for i in range(len(layer_returns)-1))

        # 计算斯皮尔曼秩相关系数
        rank = np.arange(1, len(layer_returns) + 1)
        spearman_corr = pd.Series(rank).corr(pd.Series(layer_returns), method='spearman')

        # 计算收益差距（最高层-最低层）
        spread = layer_returns[-1] - layer_returns[0]

        result = {
            '是否单调': is_monotonic,
            'Spearman相关系数': spearman_corr,
            '收益差距': spread,
            '最低层收益': layer_returns[0],
            '最高层收益': layer_returns[-1],
            '分层数': self.n_layers
        }

        return result

    def plot_layering_result(
        self,
        layering_result: pd.DataFrame,
        title: str = "因子分层回测结果",
        save_path: Optional[str] = None
    ):
        """
        绘制分层回测结果图

        Args:
            layering_result: 分层测试结果
            title: 图表标题
            save_path: 保存路径（可选）
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')

            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False

            fig, axes = plt.subplots(2, 2, figsize=(14, 10))

            # 排除多空组合
            layers_only = layering_result.drop('Long_Short', errors='ignore')

            # 1. 平均收益柱状图
            ax1 = axes[0, 0]
            layers_only['平均收益'].plot(kind='bar', ax=ax1, color='steelblue')
            ax1.set_title('各层平均收益率')
            ax1.set_ylabel('收益率')
            ax1.grid(True, alpha=0.3)
            ax1.axhline(y=0, color='red', linestyle='--', linewidth=0.8)

            # 2. 夏普比率柱状图
            ax2 = axes[0, 1]
            layers_only['夏普比率'].plot(kind='bar', ax=ax2, color='green')
            ax2.set_title('各层夏普比率')
            ax2.set_ylabel('夏普比率')
            ax2.grid(True, alpha=0.3)

            # 3. 胜率柱状图
            ax3 = axes[1, 0]
            layers_only['胜率'].plot(kind='bar', ax=ax3, color='orange')
            ax3.set_title('各层胜率')
            ax3.set_ylabel('胜率')
            ax3.grid(True, alpha=0.3)
            ax3.axhline(y=0.5, color='red', linestyle='--', linewidth=0.8)

            # 4. 收益-风险散点图
            ax4 = axes[1, 1]
            ax4.scatter(
                layers_only['收益标准差'],
                layers_only['平均收益'],
                s=100,
                alpha=0.6,
                c=range(len(layers_only))
            )
            for idx, row in layers_only.iterrows():
                ax4.annotate(
                    idx,
                    (row['收益标准差'], row['平均收益']),
                    fontsize=9
                )
            ax4.set_title('收益-风险散点图')
            ax4.set_xlabel('收益标准差')
            ax4.set_ylabel('平均收益')
            ax4.grid(True, alpha=0.3)

            plt.suptitle(title, fontsize=14, fontweight='bold')
            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"分层图表已保存: {save_path}")
            else:
                plt.savefig('/tmp/layering_test.png', dpi=300, bbox_inches='tight')
                logger.info("分层图表已保存: /tmp/layering_test.png")

            plt.close()

        except ImportError:
            logger.warning("matplotlib未安装，跳过绘图")
        except Exception as e:
            logger.error(f"绘制分层图表失败: {e}")

    def backtest_layers(
        self,
        factor_df: pd.DataFrame,
        prices_df: pd.DataFrame,
        initial_capital: float = 1000000
    ) -> Dict[str, pd.Series]:
        """
        对各层进行完整回测（计算净值曲线）

        Args:
            factor_df: 因子DataFrame
            prices_df: 价格DataFrame
            initial_capital: 初始资金

        Returns:
            各层净值曲线字典 {层名: 净值序列}
        """
        logger.info("开始各层净值回测...")

        # 计算持有期收益率
        returns_df = prices_df.pct_change(self.holding_period).shift(-self.holding_period)

        # 初始化各层净值
        layer_values = {f'Layer_{i+1}': [initial_capital] for i in range(self.n_layers)}
        dates_list = []

        dates = factor_df.index

        for date in dates:
            if date not in returns_df.index:
                continue

            factor_values = factor_df.loc[date].dropna()
            next_returns = returns_df.loc[date]

            common_stocks = factor_values.index.intersection(next_returns.index)
            if len(common_stocks) < self.n_layers:
                continue

            factor_values = factor_values[common_stocks]
            next_returns = next_returns[common_stocks]

            # 分层
            layers = self._assign_layers(factor_values, self.n_layers)

            # 计算各层净值
            for i in range(self.n_layers):
                stocks_in_layer = layers[layers == i].index
                if len(stocks_in_layer) > 0:
                    layer_return = next_returns[stocks_in_layer].mean()
                    current_value = layer_values[f'Layer_{i+1}'][-1]
                    new_value = current_value * (1 + layer_return)
                    layer_values[f'Layer_{i+1}'].append(new_value)

            dates_list.append(date)

        # 转换为Series
        equity_curves = {}
        for layer_name, values in layer_values.items():
            # 确保长度一致
            equity_curves[layer_name] = pd.Series(
                values[:len(dates_list)+1],
                index=[dates[0]] + dates_list
            )

        # 添加多空组合（如果启用）
        if self.long_short and len(dates_list) > 0:
            long_curve = equity_curves[f'Layer_{self.n_layers}']
            short_curve = equity_curves['Layer_1']

            # 计算多空组合：做多最高层，做空最低层
            # 初始资金各半
            long_short_curve = (long_curve / long_curve.iloc[0] - 1) - (short_curve / short_curve.iloc[0] - 1)
            long_short_curve = initial_capital * (1 + long_short_curve)

            equity_curves['Long_Short'] = long_short_curve

        logger.success("净值回测完成")

        return equity_curves


