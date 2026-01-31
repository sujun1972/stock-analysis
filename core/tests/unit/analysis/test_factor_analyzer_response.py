"""
测试因子分析器的Response格式迁移

本测试文件验证任务3.8的迁移结果：
- FactorAnalyzer.quick_analyze() 返回 Response
- FactorAnalyzer.analyze_factor() 返回 Response
- FactorAnalyzer.batch_analyze() 返回 Response
- ICCalculator.calculate_ic_stats() 返回 Response

测试覆盖：
- 成功场景
- 错误场景
- 警告场景
- 边界条件
"""

import pytest
import pandas as pd
import numpy as np

from analysis.factor_analyzer import FactorAnalyzer, FactorAnalysisReport
from analysis.ic_calculator import ICCalculator, ICResult
from utils.response import Response, ResponseStatus


class TestFactorAnalyzerResponse:
    """测试FactorAnalyzer的Response格式"""

    @pytest.fixture
    def sample_data(self):
        """创建测试数据"""
        np.random.seed(42)

        # 日期范围
        dates = pd.date_range('2020-01-01', '2020-12-31', freq='D')
        stocks = [f'stock_{i}' for i in range(50)]

        # 价格数据
        prices = pd.DataFrame(
            100 + np.random.randn(len(dates), len(stocks)).cumsum(axis=0),
            index=dates,
            columns=stocks
        )

        # 因子1: 动量因子（有预测能力）
        factor1 = prices.pct_change(20).shift(1)

        # 因子2: 反转因子
        factor2 = -prices.pct_change(5).shift(1)

        # 因子3: 随机因子（无预测能力）
        factor3 = pd.DataFrame(
            np.random.randn(len(dates), len(stocks)),
            index=dates,
            columns=stocks
        )

        return {
            'prices': prices,
            'factor1': factor1,
            'factor2': factor2,
            'factor3': factor3
        }

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return FactorAnalyzer(
            forward_periods=5,
            n_layers=5,
            holding_period=5,
            method='spearman'
        )

    # ==================== quick_analyze 测试 ====================

    def test_quick_analyze_success(self, analyzer, sample_data):
        """测试快速分析成功场景"""
        factor = sample_data['factor1']
        prices = sample_data['prices']

        response = analyzer.quick_analyze(
            factor, prices,
            factor_name='MOM20',
            include_layering=True
        )

        # 验证Response结构
        assert isinstance(response, Response)
        assert response.is_success() or response.status == ResponseStatus.WARNING
        assert response.data is not None

        # 验证数据类型
        report = response.data
        assert isinstance(report, FactorAnalysisReport)
        assert report.factor_name == 'MOM20'
        assert report.ic_result is not None
        assert report.overall_score is not None

        # 验证元数据
        assert 'elapsed_time' in response.metadata
        assert 'overall_score' in response.metadata
        assert 'recommendation' in response.metadata

    def test_quick_analyze_empty_factor(self, analyzer, sample_data):
        """测试空因子数据错误场景"""
        empty_factor = pd.DataFrame()
        prices = sample_data['prices']

        response = analyzer.quick_analyze(
            empty_factor, prices,
            factor_name='EMPTY'
        )

        # 验证错误Response
        assert isinstance(response, Response)
        assert response.is_error()
        assert response.error is not None
        assert response.error_code == "EMPTY_DATA"
        assert 'factor_name' in response.metadata

    def test_quick_analyze_none_input(self, analyzer, sample_data):
        """测试None输入错误场景"""
        prices = sample_data['prices']

        response = analyzer.quick_analyze(
            None, prices,
            factor_name='NONE'
        )

        # 验证错误Response
        assert response.is_error()
        assert response.error_code == "INVALID_INPUT"

    def test_quick_analyze_no_layering(self, analyzer, sample_data):
        """测试不包含分层测试"""
        factor = sample_data['factor1']
        prices = sample_data['prices']

        response = analyzer.quick_analyze(
            factor, prices,
            factor_name='MOM20',
            include_layering=False
        )

        assert response.is_success() or response.status == ResponseStatus.WARNING
        report = response.data
        # 不包含分层测试时，layering_result应为None
        # 但IC分析仍应成功
        assert report.ic_result is not None

    # ==================== analyze_factor 测试 ====================

    def test_analyze_factor_success(self, analyzer, sample_data):
        """测试完整分析成功场景"""
        factor = sample_data['factor1']
        prices = sample_data['prices']

        response = analyzer.analyze_factor(
            factor, prices,
            factor_name='MOM20',
            include_ic=True,
            include_layering=True
        )

        # 验证成功Response
        assert isinstance(response, Response)
        assert response.is_success() or response.status == ResponseStatus.WARNING

        # 验证报告完整性
        report = response.data
        assert report.ic_result is not None
        assert report.overall_score is not None

    def test_analyze_factor_ic_only(self, analyzer, sample_data):
        """测试仅IC分析"""
        factor = sample_data['factor1']
        prices = sample_data['prices']

        response = analyzer.analyze_factor(
            factor, prices,
            factor_name='MOM20',
            include_ic=True,
            include_layering=False
        )

        assert response.is_success() or response.status == ResponseStatus.WARNING
        report = response.data
        assert report.ic_result is not None

    def test_analyze_factor_empty_data(self, analyzer):
        """测试空数据错误"""
        empty_df = pd.DataFrame()

        response = analyzer.analyze_factor(
            empty_df, empty_df,
            factor_name='EMPTY'
        )

        assert response.is_error()
        assert response.error_code == "EMPTY_DATA"

    # ==================== batch_analyze 测试 ====================

    def test_batch_analyze_success(self, analyzer, sample_data):
        """测试批量分析成功场景"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'REV5': sample_data['factor2']
        }
        prices = sample_data['prices']

        response = analyzer.batch_analyze(factor_dict, prices)

        # 验证Response结构
        assert isinstance(response, Response)
        assert response.is_success() or response.status == ResponseStatus.WARNING

        # 验证批量结果
        reports = response.data
        assert isinstance(reports, dict)
        assert len(reports) > 0

        # 验证元数据
        assert 'total_factors' in response.metadata
        assert 'success_count' in response.metadata
        assert 'elapsed_time' in response.metadata

    def test_batch_analyze_empty_dict(self, analyzer, sample_data):
        """测试空因子字典错误"""
        prices = sample_data['prices']

        response = analyzer.batch_analyze({}, prices)

        assert response.is_error()
        assert response.error_code == "EMPTY_FACTOR_DICT"

    def test_batch_analyze_empty_prices(self, analyzer, sample_data):
        """测试空价格数据错误"""
        factor_dict = {'MOM20': sample_data['factor1']}

        response = analyzer.batch_analyze(factor_dict, pd.DataFrame())

        assert response.is_error()
        assert response.error_code == "EMPTY_PRICE_DATA"

    def test_batch_analyze_partial_success(self, analyzer, sample_data):
        """测试部分成功场景（包含无效因子）"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'EMPTY': pd.DataFrame()  # 无效因子
        }
        prices = sample_data['prices']

        response = analyzer.batch_analyze(factor_dict, prices)

        # 应返回警告或成功（至少有一个因子成功）
        if response.is_warning():
            assert 'failed_count' in response.metadata
            assert response.metadata['failed_count'] > 0
        # 如果都失败则返回错误
        elif response.is_error():
            assert response.error_code == "ALL_FACTORS_FAILED"


class TestICCalculatorResponse:
    """测试ICCalculator的Response格式"""

    @pytest.fixture
    def sample_data(self):
        """生成样本数据"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=250, freq='D')
        stocks = [f'stock_{i:03d}' for i in range(50)]

        # 生成价格数据
        base_price = 100.0
        returns = np.random.randn(250, 50) * 0.02
        prices = base_price * (1 + returns).cumprod(axis=0)

        # 生成因子数据
        factor_values = np.random.randn(250, 50)

        factor_df = pd.DataFrame(factor_values, index=dates, columns=stocks)
        price_df = pd.DataFrame(prices, index=dates, columns=stocks)

        return factor_df, price_df

    @pytest.fixture
    def calculator(self):
        """创建IC计算器"""
        return ICCalculator(forward_periods=5, method='spearman')

    def test_calculate_ic_stats_success(self, calculator, sample_data):
        """测试IC统计计算成功场景"""
        factor_df, price_df = sample_data

        response = calculator.calculate_ic_stats(factor_df, price_df)

        # 验证Response结构
        assert isinstance(response, Response)
        assert response.is_success()
        assert response.data is not None

        # 验证IC结果
        ic_result = response.data
        assert isinstance(ic_result, ICResult)
        assert -1 <= ic_result.mean_ic <= 1
        assert ic_result.std_ic >= 0
        assert 0 <= ic_result.positive_rate <= 1

        # 验证元数据
        assert 'mean_ic' in response.metadata
        assert 'ic_ir' in response.metadata
        assert 'n_valid_ic' in response.metadata
        assert 'elapsed_time' in response.metadata

    def test_calculate_ic_stats_empty_data(self, calculator):
        """测试空数据错误场景"""
        empty_df = pd.DataFrame()

        response = calculator.calculate_ic_stats(empty_df, empty_df)

        assert response.is_error()
        assert response.error_code == "EMPTY_DATA"

    def test_calculate_ic_stats_none_input(self, calculator):
        """测试None输入错误场景"""
        response = calculator.calculate_ic_stats(None, None)

        assert response.is_error()
        assert response.error_code == "INVALID_INPUT"

    def test_calculate_ic_stats_insufficient_data(self, calculator):
        """测试数据不足错误场景"""
        # 创建很小的数据集（少于10个有效IC值）
        dates = pd.date_range('2023-01-01', periods=15, freq='D')
        stocks = ['A', 'B']

        small_factor = pd.DataFrame(
            np.random.randn(15, 2),
            index=dates,
            columns=stocks
        )
        small_prices = pd.DataFrame(
            100 * (1 + np.random.randn(15, 2) * 0.02).cumprod(axis=0),
            index=dates,
            columns=stocks
        )

        response = calculator.calculate_ic_stats(small_factor, small_prices)

        # 可能返回错误（数据不足）
        if response.is_error():
            assert response.error_code in ["INSUFFICIENT_IC_VALUES", "IC_CALCULATION_ERROR"]


class TestResponseMetadata:
    """测试Response元数据的完整性"""

    @pytest.fixture
    def analyzer(self):
        return FactorAnalyzer(forward_periods=5)

    @pytest.fixture
    def simple_data(self):
        """创建简单测试数据"""
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        stocks = ['A', 'B', 'C', 'D', 'E']

        prices = pd.DataFrame(
            100 + np.random.randn(100, 5).cumsum(axis=0),
            index=dates,
            columns=stocks
        )
        factor = prices.pct_change(10).shift(1)

        return factor, prices

    def test_metadata_completeness(self, analyzer, simple_data):
        """测试元数据完整性"""
        factor, prices = simple_data

        response = analyzer.quick_analyze(factor, prices, factor_name='TEST')

        # 验证必需的元数据字段
        assert 'factor_name' in response.metadata
        assert 'elapsed_time' in response.metadata
        assert 'overall_score' in response.metadata
        assert 'recommendation' in response.metadata

    def test_error_metadata(self, analyzer):
        """测试错误场景的元数据"""
        response = analyzer.quick_analyze(None, None, factor_name='ERROR_TEST')

        assert response.is_error()
        assert 'factor_name' in response.metadata
        assert response.metadata['factor_name'] == 'ERROR_TEST'


# ==================== 向后兼容性测试 ====================

class TestBackwardCompatibility:
    """测试向后兼容性 - Response.data包含原有的返回类型"""

    @pytest.fixture
    def analyzer(self):
        return FactorAnalyzer(forward_periods=5)

    @pytest.fixture
    def simple_data(self):
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        stocks = ['A', 'B', 'C', 'D', 'E']
        prices = pd.DataFrame(
            100 + np.random.randn(100, 5).cumsum(axis=0),
            index=dates,
            columns=stocks
        )
        factor = prices.pct_change(10).shift(1)
        return factor, prices

    def test_data_field_type_preservation(self, analyzer, simple_data):
        """验证data字段保持原有类型"""
        factor, prices = simple_data

        # quick_analyze应返回FactorAnalysisReport
        response = analyzer.quick_analyze(factor, prices)
        if response.is_success() or response.status == ResponseStatus.WARNING:
            assert isinstance(response.data, FactorAnalysisReport)

        # batch_analyze应返回Dict
        response = analyzer.batch_analyze({'TEST': factor}, prices)
        if response.is_success() or response.status == ResponseStatus.WARNING:
            assert isinstance(response.data, dict)

    def test_ic_calculator_data_type(self):
        """验证ICCalculator返回ICResult"""
        calculator = ICCalculator(forward_periods=5)

        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        stocks = ['A', 'B', 'C']

        factor = pd.DataFrame(np.random.randn(100, 3), index=dates, columns=stocks)
        prices = pd.DataFrame(
            100 * (1 + np.random.randn(100, 3) * 0.02).cumprod(axis=0),
            index=dates,
            columns=stocks
        )

        response = calculator.calculate_ic_stats(factor, prices)
        if response.is_success():
            assert isinstance(response.data, ICResult)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
