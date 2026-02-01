"""
因子相关性分析工具

分析多个因子之间的相关性：
- 皮尔逊相关系数
- 斯皮尔曼秩相关系数
- 相关性热力图
- 因子聚类分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from loguru import logger
import warnings

# 导入异常类
try:
    from ..exceptions import (
        AnalysisError,
        DataValidationError,
        InsufficientDataError,
        FeatureCalculationError
    )
except ImportError:
    from src.exceptions import (
        AnalysisError,
        DataValidationError,
        InsufficientDataError,
        FeatureCalculationError
    )

warnings.filterwarnings('ignore')


class FactorCorrelation:
    """
    因子相关性分析工具

    用途：
    - 识别高度相关的因子（避免重复）
    - 因子降维（选择低相关性因子）
    - 因子聚类（将相似因子分组）
    """

    def __init__(self, method: str = 'pearson'):
        """
        初始化相关性分析工具

        Args:
            method: 相关性计算方法
                - 'pearson': 线性相关（默认）
                - 'spearman': 秩相关（更稳健）
                - 'kendall': 肯德尔相关
        """
        self.method = method

        if method not in ['pearson', 'spearman', 'kendall']:
            raise ValueError(f"method必须是pearson/spearman/kendall，得到: {method}")

        logger.info(f"初始化因子相关性分析: 方法={method}")

    def calculate_factor_correlation(
        self,
        factor_dict: Dict[str, pd.DataFrame],
        aggregate_method: str = 'mean'
    ) -> pd.DataFrame:
        """
        计算因子间的相关性矩阵

        Args:
            factor_dict: 因子字典 {因子名: 因子DataFrame}
            aggregate_method: 跨时间聚合方法
                - 'mean': 先计算每个时间点的相关性,再平均
                - 'concat': 将所有时间点拼接后计算（适合大样本）

        Returns:
            相关性矩阵DataFrame
        """
        logger.info(f"计算{len(factor_dict)}个因子的相关性...")

        factor_names = list(factor_dict.keys())
        n_factors = len(factor_names)

        if aggregate_method == 'concat':
            # 方法1：拼接所有时间点后计算相关性
            all_factors = pd.DataFrame()

            for name, factor_df in factor_dict.items():
                # 将二维DataFrame展平为一维Series
                factor_values = factor_df.stack()
                all_factors[name] = factor_values

            # 删除NaN
            all_factors = all_factors.dropna()

            # 计算相关性
            corr_matrix = all_factors.corr(method=self.method)

        else:  # mean
            # 方法2：每个时间点计算相关性，然后平均
            dates = list(factor_dict.values())[0].index
            corr_matrices = []

            for date in dates:
                # 提取当期所有因子的值
                date_factors = pd.DataFrame()

                for name, factor_df in factor_dict.items():
                    if date in factor_df.index:
                        date_factors[name] = factor_df.loc[date]

                # 删除NaN
                date_factors = date_factors.dropna()

                if len(date_factors) < 10:  # 至少10个股票
                    continue

                # 计算当期相关性
                date_corr = date_factors.corr(method=self.method)
                corr_matrices.append(date_corr)

            # 平均所有时间点的相关性
            if len(corr_matrices) == 0:
                raise ValueError("所有时间点的相关性计算均失败")

            # 堆叠并求平均
            corr_matrix = pd.concat(corr_matrices).groupby(level=0).mean()

        logger.success(f"相关性矩阵计算完成")

        return corr_matrix

    def find_high_correlation_pairs(
        self,
        corr_matrix: pd.DataFrame,
        threshold: float = 0.7
    ) -> pd.DataFrame:
        """
        找出高相关性因子对

        Args:
            corr_matrix: 相关性矩阵
            threshold: 相关性阈值（默认0.7）

        Returns:
            高相关性因子对DataFrame
        """
        logger.info(f"查找相关性>{threshold}的因子对...")

        pairs = []

        n = len(corr_matrix)
        for i in range(n):
            for j in range(i+1, n):
                corr_value = corr_matrix.iloc[i, j]

                if abs(corr_value) >= threshold:
                    pairs.append({
                        '因子1': corr_matrix.index[i],
                        '因子2': corr_matrix.columns[j],
                        '相关系数': corr_value,
                        '绝对值': abs(corr_value)
                    })

        if len(pairs) == 0:
            logger.warning(f"未找到相关性>{threshold}的因子对")
            return pd.DataFrame()

        pairs_df = pd.DataFrame(pairs).sort_values('绝对值', ascending=False)

        logger.success(f"找到{len(pairs_df)}对高相关因子")

        return pairs_df

    def select_low_correlation_factors(
        self,
        corr_matrix: pd.DataFrame,
        max_corr: float = 0.7,
        ic_scores: Optional[pd.Series] = None
    ) -> List[str]:
        """
        选择低相关性因子（贪心算法）

        Args:
            corr_matrix: 相关性矩阵
            max_corr: 最大允许相关性
            ic_scores: 因子IC评分（可选，用于优先选择）

        Returns:
            选中的因子列表
        """
        logger.info(f"选择低相关性因子（阈值={max_corr}）...")

        factor_names = corr_matrix.index.tolist()

        # 如果提供了IC评分，按IC降序排序因子
        if ic_scores is not None:
            factor_names = ic_scores.sort_values(ascending=False).index.tolist()
            logger.debug(f"按IC评分排序: 最优={factor_names[0]}")

        selected = []

        for factor in factor_names:
            # 检查与已选因子的相关性
            if len(selected) == 0:
                selected.append(factor)
                continue

            max_corr_with_selected = max(
                abs(corr_matrix.loc[factor, s]) for s in selected
            )

            if max_corr_with_selected < max_corr:
                selected.append(factor)

        logger.success(f"选出{len(selected)}/{len(factor_names)}个低相关因子")

        return selected

    def cluster_factors(
        self,
        corr_matrix: pd.DataFrame,
        n_clusters: int = 5,
        method: str = 'ward'
    ) -> Dict[int, List[str]]:
        """
        因子聚类分析

        Args:
            corr_matrix: 相关性矩阵
            n_clusters: 聚类数量
            method: 聚类方法 ('ward', 'average', 'complete')

        Returns:
            聚类结果字典 {簇ID: [因子列表]}
        """
        try:
            from scipy.cluster.hierarchy import linkage, fcluster
            from scipy.spatial.distance import squareform

            logger.info(f"因子层次聚类: {n_clusters}个簇...")

            # 将相关性转换为距离
            distance_matrix = 1 - abs(corr_matrix)

            # 转换为压缩距离矩阵
            condensed_dist = squareform(distance_matrix, checks=False)

            # 层次聚类
            linkage_matrix = linkage(condensed_dist, method=method)

            # 切分为n个簇
            clusters = fcluster(linkage_matrix, n_clusters, criterion='maxclust')

            # 组织结果
            cluster_dict = {}
            for cluster_id in range(1, n_clusters + 1):
                factors_in_cluster = corr_matrix.index[clusters == cluster_id].tolist()
                cluster_dict[cluster_id] = factors_in_cluster

            logger.success(f"聚类完成: {len(cluster_dict)}个簇")

            # 打印每个簇的大小
            for cluster_id, factors in cluster_dict.items():
                logger.debug(f"  簇{cluster_id}: {len(factors)}个因子")

            return cluster_dict

        except ImportError:
            logger.error("scipy未安装，无法执行聚类分析")
            return {}

    def plot_correlation_heatmap(
        self,
        corr_matrix: pd.DataFrame,
        title: str = "因子相关性热力图",
        save_path: Optional[str] = None,
        figsize: tuple = (12, 10)
    ):
        """
        绘制因子相关性热力图

        Args:
            corr_matrix: 相关性矩阵
            title: 图表标题
            save_path: 保存路径（可选）
            figsize: 图表大小
        """
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            import matplotlib
            matplotlib.use('Agg')

            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False

            fig, ax = plt.subplots(figsize=figsize)

            # 绘制热力图
            sns.heatmap(
                corr_matrix,
                annot=True,  # 显示数值
                fmt='.2f',
                cmap='RdYlGn_r',  # 红黄绿配色（红=高相关）
                center=0,
                vmin=-1,
                vmax=1,
                square=True,
                linewidths=0.5,
                cbar_kws={"shrink": 0.8},
                ax=ax
            )

            plt.title(title, fontsize=14, fontweight='bold', pad=20)
            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"相关性热力图已保存: {save_path}")
            else:
                plt.savefig('/tmp/factor_correlation_heatmap.png', dpi=300, bbox_inches='tight')
                logger.info("相关性热力图已保存: /tmp/factor_correlation_heatmap.png")

            plt.close()

        except ImportError as e:
            logger.warning(f"绘图库未安装: {e}")
        except (DataValidationError, InsufficientDataError, FeatureCalculationError, AnalysisError) as e:
            logger.warning(f"绘制热力图失败(已知异常): {e}")
        except Exception as e:
            logger.warning(f"绘制热力图失败(未预期异常): {e}", exc_info=True)

    def plot_correlation_network(
        self,
        corr_matrix: pd.DataFrame,
        threshold: float = 0.5,
        title: str = "因子相关性网络图",
        save_path: Optional[str] = None
    ):
        """
        绘制因子相关性网络图

        Args:
            corr_matrix: 相关性矩阵
            threshold: 显示边的最小相关性阈值
            title: 图表标题
            save_path: 保存路径（可选）
        """
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
            import matplotlib
            matplotlib.use('Agg')

            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False

            logger.info(f"绘制相关性网络图（阈值={threshold}）...")

            # 创建图
            G = nx.Graph()

            # 添加节点
            factors = corr_matrix.index.tolist()
            G.add_nodes_from(factors)

            # 添加边（仅高相关性）
            n = len(corr_matrix)
            for i in range(n):
                for j in range(i+1, n):
                    corr_value = abs(corr_matrix.iloc[i, j])
                    if corr_value >= threshold:
                        G.add_edge(
                            factors[i],
                            factors[j],
                            weight=corr_value
                        )

            # 绘图
            fig, ax = plt.subplots(figsize=(14, 12))

            # 使用spring布局
            pos = nx.spring_layout(G, k=2, iterations=50)

            # 绘制节点
            nx.draw_networkx_nodes(
                G, pos,
                node_size=1000,
                node_color='lightblue',
                alpha=0.8,
                ax=ax
            )

            # 绘制边（粗细表示相关性强度）
            edges = G.edges()
            weights = [G[u][v]['weight'] for u, v in edges]

            nx.draw_networkx_edges(
                G, pos,
                width=[w*5 for w in weights],  # 相关性越高，线越粗
                alpha=0.5,
                edge_color='gray',
                ax=ax
            )

            # 绘制标签
            nx.draw_networkx_labels(
                G, pos,
                font_size=8,
                font_family='SimHei',
                ax=ax
            )

            plt.title(f"{title}\n(显示相关性>{threshold}的连接)", fontsize=14, fontweight='bold')
            plt.axis('off')
            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"网络图已保存: {save_path}")
            else:
                plt.savefig('/tmp/factor_correlation_network.png', dpi=300, bbox_inches='tight')
                logger.info("网络图已保存: /tmp/factor_correlation_network.png")

            plt.close()

        except ImportError as e:
            logger.warning(f"networkx或matplotlib未安装: {e}")
        except (DataValidationError, InsufficientDataError, FeatureCalculationError, AnalysisError) as e:
            logger.warning(f"绘制网络图失败(已知异常): {e}")
        except Exception as e:
            logger.warning(f"绘制网络图失败(未预期异常): {e}", exc_info=True)


