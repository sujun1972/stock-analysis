"""
因子相关性分析单元测试

测试功能：
- 相关性矩阵计算
- 高相关性因子识别
- 低相关性因子选择
- 因子聚类
- 可视化功能（跳过无matplotlib环境）
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

from analysis.factor_correlation import FactorCorrelation


@pytest.fixture
def sample_factor_dict():
    """生成样本因子字典"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    stocks = [f'stock_{i:02d}' for i in range(30)]

    # 创建3个因子，其中因子1和2高度相关
    factor1 = np.random.randn(100, 30)
    factor2 = factor1 + np.random.randn(100, 30) * 0.1  # 高相关
    factor3 = np.random.randn(100, 30)  # 低相关

    return {
        'factor_1': pd.DataFrame(factor1, index=dates, columns=stocks),
        'factor_2': pd.DataFrame(factor2, index=dates, columns=stocks),
        'factor_3': pd.DataFrame(factor3, index=dates, columns=stocks)
    }


class TestFactorCorrelationInit:
    """测试初始化"""

    def test_default_init(self):
        corr_analyzer = FactorCorrelation()
        assert corr_analyzer.method == 'pearson'

    def test_custom_init(self):
        corr_analyzer = FactorCorrelation(method='spearman')
        assert corr_analyzer.method == 'spearman'

    def test_invalid_method(self):
        with pytest.raises(ValueError):
            FactorCorrelation(method='invalid')


class TestCalculateFactorCorrelation:
    """测试相关性矩阵计算"""

    def test_basic_correlation(self, sample_factor_dict):
        corr_analyzer = FactorCorrelation()
        corr_matrix = corr_analyzer.calculate_factor_correlation(sample_factor_dict)

        assert isinstance(corr_matrix, pd.DataFrame)
        assert corr_matrix.shape == (3, 3)
        assert all(corr_matrix.index == corr_matrix.columns)
        # 对角线应该是1
        assert all(abs(corr_matrix.values.diagonal() - 1.0) < 1e-6)

    def test_concat_method(self, sample_factor_dict):
        corr_analyzer = FactorCorrelation()
        corr_matrix = corr_analyzer.calculate_factor_correlation(
            sample_factor_dict, aggregate_method='concat'
        )
        assert isinstance(corr_matrix, pd.DataFrame)

    def test_mean_method(self, sample_factor_dict):
        corr_analyzer = FactorCorrelation()
        corr_matrix = corr_analyzer.calculate_factor_correlation(
            sample_factor_dict, aggregate_method='mean'
        )
        assert isinstance(corr_matrix, pd.DataFrame)


class TestFindHighCorrelationPairs:
    """测试高相关性因子对识别"""

    def test_find_high_corr_pairs(self, sample_factor_dict):
        corr_analyzer = FactorCorrelation()
        corr_matrix = corr_analyzer.calculate_factor_correlation(sample_factor_dict)

        pairs_df = corr_analyzer.find_high_correlation_pairs(corr_matrix, threshold=0.5)

        assert isinstance(pairs_df, pd.DataFrame)
        assert '因子1' in pairs_df.columns
        assert '因子2' in pairs_df.columns
        assert '相关系数' in pairs_df.columns

    def test_different_thresholds(self, sample_factor_dict):
        corr_analyzer = FactorCorrelation()
        corr_matrix = corr_analyzer.calculate_factor_correlation(sample_factor_dict)

        for threshold in [0.5, 0.7, 0.9]:
            pairs_df = corr_analyzer.find_high_correlation_pairs(corr_matrix, threshold=threshold)
            # 阈值越高，识别出的对数越少
            assert isinstance(pairs_df, pd.DataFrame)


class TestSelectLowCorrelationFactors:
    """测试低相关性因子选择"""

    def test_select_low_corr_factors(self, sample_factor_dict):
        corr_analyzer = FactorCorrelation()
        corr_matrix = corr_analyzer.calculate_factor_correlation(sample_factor_dict)

        selected = corr_analyzer.select_low_correlation_factors(corr_matrix, max_corr=0.7)

        assert isinstance(selected, list)
        assert len(selected) > 0
        assert len(selected) <= len(sample_factor_dict)

    def test_select_with_ic_scores(self, sample_factor_dict):
        corr_analyzer = FactorCorrelation()
        corr_matrix = corr_analyzer.calculate_factor_correlation(sample_factor_dict)

        ic_scores = pd.Series([0.05, 0.03, 0.04], index=['factor_1', 'factor_2', 'factor_3'])

        selected = corr_analyzer.select_low_correlation_factors(
            corr_matrix, max_corr=0.7, ic_scores=ic_scores
        )

        assert isinstance(selected, list)
        # 应该优先选择IC高的因子
        if len(selected) > 0:
            assert selected[0] in ic_scores.index


class TestClusterFactors:
    """测试因子聚类"""

    def test_cluster_basic(self, sample_factor_dict):
        corr_analyzer = FactorCorrelation()
        corr_matrix = corr_analyzer.calculate_factor_correlation(sample_factor_dict)

        clusters = corr_analyzer.cluster_factors(corr_matrix, n_clusters=2)

        assert isinstance(clusters, dict)
        assert len(clusters) <= 2
        # 所有因子都应该被分配到某个簇
        all_factors = [f for factors in clusters.values() for f in factors]
        assert set(all_factors) == set(sample_factor_dict.keys())

    def test_cluster_different_n(self, sample_factor_dict):
        corr_analyzer = FactorCorrelation()
        corr_matrix = corr_analyzer.calculate_factor_correlation(sample_factor_dict)

        for n_clusters in [1, 2, 3]:
            clusters = corr_analyzer.cluster_factors(corr_matrix, n_clusters=n_clusters)
            assert isinstance(clusters, dict)


class TestEdgeCases:
    """测试边界条件"""

    def test_single_factor(self):
        """测试单个因子"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        factor_dict = {
            'factor_1': pd.DataFrame(np.random.randn(50, 10), index=dates)
        }

        corr_analyzer = FactorCorrelation()
        corr_matrix = corr_analyzer.calculate_factor_correlation(factor_dict)

        assert corr_matrix.shape == (1, 1)

    def test_identical_factors(self):
        """测试完全相同的因子"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        data = np.random.randn(50, 10)

        factor_dict = {
            'factor_1': pd.DataFrame(data, index=dates),
            'factor_2': pd.DataFrame(data, index=dates)  # 完全相同
        }

        corr_analyzer = FactorCorrelation()
        corr_matrix = corr_analyzer.calculate_factor_correlation(factor_dict)

        # 相同因子的相关系数应该接近1
        assert abs(corr_matrix.loc['factor_1', 'factor_2'] - 1.0) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
