"""
Walk-Forward验证框架

防止参数过拟合的滚动优化验证方法：
- 滚动时间窗口
- 训练集优化参数
- 测试集验证效果
- 避免未来数据泄漏
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Tuple
from loguru import logger
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')


@dataclass
class WalkForwardWindow:
    """Walk-Forward窗口数据类"""
    window_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    optimal_params: Dict[str, Any]
    train_score: float
    test_score: float


class WalkForwardValidator:
    """
    Walk-Forward验证框架

    工作流程：
    1. 将数据分为N个窗口
    2. 每个窗口：训练期优化参数 -> 测试期验证
    3. 滚动前进，重复优化
    4. 汇总所有测试期结果

    优点：
    - 真实模拟实盘情况
    - 避免过拟合
    - 检验参数稳定性
    """

    def __init__(
        self,
        train_period: int = 252,  # 训练期（天数）
        test_period: int = 63,  # 测试期（天数）
        step_size: int = 63,  # 滚动步长（天数）
        min_train_size: int = None  # 最小训练集大小（默认为train_period的一半）
    ):
        """
        初始化Walk-Forward验证器

        Args:
            train_period: 训练窗口大小（天数）
            test_period: 测试窗口大小（天数）
            step_size: 滚动步长（天数）
            min_train_size: 最小训练集大小（默认为train_period的一半）
        """
        self.train_period = train_period
        self.test_period = test_period
        self.step_size = step_size
        # 如果未指定min_train_size，默认为train_period的一半
        self.min_train_size = min_train_size if min_train_size is not None else train_period // 2

        logger.info(
            f"初始化Walk-Forward验证: 训练={train_period}天, "
            f"测试={test_period}天, 步长={step_size}天, 最小训练={self.min_train_size}天"
        )

    def create_windows(
        self,
        dates: List[datetime],
        anchored: bool = False
    ) -> List[Tuple[List[datetime], List[datetime]]]:
        """
        创建滚动窗口

        Args:
            dates: 日期列表（已排序）
            anchored: 是否锚定起始点（True=扩展训练集，False=固定大小）

        Returns:
            窗口列表 [(训练日期, 测试日期), ...]
        """
        logger.info(f"创建滚动窗口（锚定模式={anchored}）...")

        windows = []
        n_dates = len(dates)

        # 第一个窗口的起始位置
        train_start_idx = 0
        current_train_end_idx = self.train_period

        while True:
            # 计算训练期结束位置
            if anchored:
                # 扩展模式：从起点开始，逐渐扩大训练集
                train_end_idx = current_train_end_idx
            else:
                # 滑动模式：固定大小训练集
                train_end_idx = train_start_idx + self.train_period

            # 计算测试期范围
            test_start_idx = train_end_idx
            test_end_idx = test_start_idx + self.test_period

            # 检查是否超出数据范围
            if test_end_idx > n_dates:
                logger.debug(f"已到达数据末尾，共创建{len(windows)}个窗口")
                break

            # 检查训练集是否足够大
            train_size = train_end_idx - train_start_idx
            if train_size < self.min_train_size:
                logger.warning(f"训练集太小({train_size} < {self.min_train_size})，停止创建窗口")
                break

            # 提取日期
            train_dates = dates[train_start_idx:train_end_idx]
            test_dates = dates[test_start_idx:test_end_idx]

            windows.append((train_dates, test_dates))

            # 滚动到下一个窗口
            if anchored:
                # 扩展模式：起点不变，只增加终点
                current_train_end_idx += self.step_size
            else:
                # 滑动模式：起点和终点都前移
                train_start_idx += self.step_size

        logger.success(f"创建了{len(windows)}个窗口")

        return windows

    def validate(
        self,
        objective_func: Callable,
        optimizer: Any,
        data: Dict,
        dates: List[datetime]
    ) -> pd.DataFrame:
        """
        执行Walk-Forward验证

        Args:
            objective_func: 目标函数，接受(params, data)返回得分
            optimizer: 优化器对象（需实现optimize方法）
            data: 完整数据字典 {key: DataFrame}
            dates: 日期列表

        Returns:
            验证结果DataFrame
        """
        logger.info("开始Walk-Forward验证...")

        # 创建窗口
        windows = self.create_windows(dates)

        results = []

        for window_id, (train_dates, test_dates) in enumerate(windows, 1):
            logger.info(f"\n===== 窗口 {window_id}/{len(windows)} =====")
            logger.info(f"训练期: {train_dates[0]} 到 {train_dates[-1]} ({len(train_dates)}天)")
            logger.info(f"测试期: {test_dates[0]} 到 {test_dates[-1]} ({len(test_dates)}天)")

            # 1. 分割训练和测试数据
            train_data = self._split_data(data, train_dates)
            test_data = self._split_data(data, test_dates)

            # 2. 在训练集上优化参数
            try:
                logger.info("在训练集上优化参数...")

                # 使用提供的优化器
                opt_result = optimizer.optimize(
                    lambda params: objective_func(params, train_data),
                    maximize=True
                )

                optimal_params = opt_result.best_params
                train_score = opt_result.best_score

                logger.success(f"训练集最优得分: {train_score:.4f}")
                logger.info(f"最优参数: {optimal_params}")

            except Exception as e:
                logger.error(f"窗口{window_id}优化失败: {e}")
                continue

            # 3. 在测试集上验证
            try:
                logger.info("在测试集上验证...")
                test_score = objective_func(optimal_params, test_data)

                logger.success(f"测试集得分: {test_score:.4f}")

            except Exception as e:
                logger.error(f"窗口{window_id}测试失败: {e}")
                continue

            # 4. 记录结果
            window_result = WalkForwardWindow(
                window_id=window_id,
                train_start=train_dates[0],
                train_end=train_dates[-1],
                test_start=test_dates[0],
                test_end=test_dates[-1],
                optimal_params=optimal_params,
                train_score=train_score,
                test_score=test_score
            )

            results.append(window_result)

        # 整理结果
        results_df = pd.DataFrame([
            {
                '窗口': r.window_id,
                '训练开始': r.train_start,
                '训练结束': r.train_end,
                '测试开始': r.test_start,
                '测试结束': r.test_end,
                '训练得分': r.train_score,
                '测试得分': r.test_score,
                '过拟合度': r.train_score - r.test_score,
                '参数': str(r.optimal_params)
            }
            for r in results
        ])

        logger.success(f"\nWalk-Forward验证完成，共{len(results)}个窗口")

        # 计算统计摘要
        self._print_summary(results_df)

        return results_df

    def _split_data(
        self,
        data: Dict,
        dates: List[datetime]
    ) -> Dict:
        """按日期分割数据"""
        split_data = {}

        for key, df in data.items():
            if isinstance(df, pd.DataFrame) and hasattr(df, 'index'):
                # 筛选日期
                split_data[key] = df.loc[df.index.isin(dates)]
            else:
                # 非时间序列数据，直接传递
                split_data[key] = df

        return split_data

    def _print_summary(self, results_df: pd.DataFrame):
        """打印验证摘要"""
        logger.info("\n" + "=" * 60)
        logger.info("Walk-Forward验证摘要")
        logger.info("=" * 60)

        logger.info(f"窗口数量: {len(results_df)}")

        if len(results_df) == 0:
            logger.warning("没有有效的验证窗口")
            logger.info("=" * 60)
            return

        logger.info(f"平均训练得分: {results_df['训练得分'].mean():.4f}")
        logger.info(f"平均测试得分: {results_df['测试得分'].mean():.4f}")
        logger.info(f"平均过拟合度: {results_df['过拟合度'].mean():.4f}")

        logger.info(f"\n测试得分稳定性:")
        logger.info(f"  标准差: {results_df['测试得分'].std():.4f}")
        logger.info(f"  最小值: {results_df['测试得分'].min():.4f}")
        logger.info(f"  最大值: {results_df['测试得分'].max():.4f}")

        # 检查过拟合
        overfitting_windows = (results_df['过拟合度'] > 0.1).sum()
        logger.info(f"\n过拟合窗口: {overfitting_windows}/{len(results_df)}")

        logger.info("=" * 60)

    def plot_validation_results(
        self,
        results_df: pd.DataFrame,
        save_path: Optional[str] = None
    ):
        """绘制验证结果图"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')

            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False

            fig, axes = plt.subplots(2, 1, figsize=(14, 10))

            # 1. 训练vs测试得分
            ax1 = axes[0]
            x = results_df['窗口']

            ax1.plot(x, results_df['训练得分'], marker='o', label='训练得分', linewidth=2)
            ax1.plot(x, results_df['测试得分'], marker='s', label='测试得分', linewidth=2)
            ax1.axhline(
                y=results_df['测试得分'].mean(),
                color='red',
                linestyle='--',
                label=f'平均测试得分={results_df["测试得分"].mean():.4f}'
            )

            ax1.set_xlabel('窗口', fontsize=12)
            ax1.set_ylabel('得分', fontsize=12)
            ax1.set_title('Walk-Forward验证：训练vs测试得分', fontsize=14, fontweight='bold')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 2. 过拟合度
            ax2 = axes[1]
            ax2.bar(x, results_df['过拟合度'], alpha=0.7, color='orange')
            ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
            ax2.axhline(y=0.1, color='red', linestyle='--', label='过拟合阈值=0.1')

            ax2.set_xlabel('窗口', fontsize=12)
            ax2.set_ylabel('过拟合度', fontsize=12)
            ax2.set_title('过拟合度分析（训练得分 - 测试得分）', fontsize=14, fontweight='bold')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"验证结果图已保存: {save_path}")
            else:
                plt.savefig('/tmp/walk_forward_validation.png', dpi=300, bbox_inches='tight')
                logger.info("验证结果图已保存: /tmp/walk_forward_validation.png")

            plt.close()

        except ImportError:
            logger.warning("matplotlib未安装，跳过绘图")
        except Exception as e:
            logger.error(f"绘制验证结果图失败: {e}")


