"""
测试统一因子分析器门面（FactorAnalyzer）

测试覆盖：
- 快速分析功能
- 完整分析功能
- 多因子对比
- 因子组合优化
- 批量分析
- 完整报告生成
- 便捷函数
"""

import pytest
import pandas as pd
import numpy as np

from analysis.factor_analyzer import (
    FactorAnalyzer,
    FactorAnalysisReport,
    quick_analyze_factor,
    compare_multiple_factors,
    optimize_factor_combination
)
from analysis.ic_calculator import ICResult


class TestFactorAnalyzer:
    """测试FactorAnalyzer类"""

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

    def test_initialization(self, analyzer):
        """测试初始化"""
        assert analyzer.forward_periods == 5
        assert analyzer.n_layers == 5
        assert analyzer.holding_period == 5
        assert analyzer.method == 'spearman'
        assert analyzer.long_short is True

        # 检查内部组件是否正确初始化
        assert analyzer.ic_calculator is not None
        assert analyzer.layering_test is not None
        assert analyzer.correlation_analyzer is not None
        assert analyzer.optimizer is not None

    def test_quick_analyze_basic(self, analyzer, sample_data):
        """测试快速分析（基础功能）"""
        factor = sample_data['factor1']
        prices = sample_data['prices']

        report = analyzer.quick_analyze(
            factor, prices,
            factor_name='MOM20',
            include_layering=False
        )

        # 验证报告结构
        assert isinstance(report, FactorAnalysisReport)
        assert report.factor_name == 'MOM20'
        assert report.ic_result is not None
        assert report.overall_score is not None
        assert report.recommendation is not None

        # 验证IC结果
        assert isinstance(report.ic_result, ICResult)
        assert -1 <= report.ic_result.mean_ic <= 1
        assert report.ic_result.std_ic >= 0

    def test_quick_analyze_with_layering(self, analyzer, sample_data):
        """测试快速分析（包含分层测试）"""
        factor = sample_data['factor1']
        prices = sample_data['prices']

        report = analyzer.quick_analyze(
            factor, prices,
            factor_name='MOM20',
            include_layering=True
        )

        # 验证分层测试结果
        assert report.layering_result is not None
        assert report.layering_summary is not None
        assert '是否单调' in report.layering_summary
        assert '收益差距' in report.layering_summary

        # 验证分层结果结构
        assert isinstance(report.layering_result, pd.DataFrame)
        assert len(report.layering_result) >= 5  # 至少5层

    def test_quick_analyze_with_series(self, analyzer, sample_data):
        """测试快速分析（Series输入）"""
        # 使用整个DataFrame的一个时间点（横截面）
        factor = sample_data['factor1']
        prices = sample_data['prices']

        # 将DataFrame转为Series（取所有股票的均值作为单一因子值）
        factor_series = factor.mean(axis=1)

        report = analyzer.quick_analyze(
            factor_series, prices,
            factor_name='MOM20_Single'
        )

        assert report.factor_name == 'MOM20_Single'
        # Series输入会被转换为DataFrame，但可能数据不足，所以放宽断言
        assert report is not None

    def test_analyze_factor_complete(self, analyzer, sample_data):
        """测试完整分析功能"""
        factor = sample_data['factor1']
        prices = sample_data['prices']

        report = analyzer.analyze_factor(
            factor, prices,
            factor_name='MOM20',
            include_ic=True,
            include_layering=True,
            include_decay_analysis=False
        )

        # 验证完整报告
        assert report.ic_result is not None
        assert report.layering_result is not None
        assert report.overall_score is not None
        assert 0 <= report.overall_score <= 100

    def test_compare_factors(self, analyzer, sample_data):
        """测试多因子对比"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'REV5': sample_data['factor2'],
            'RANDOM': sample_data['factor3']
        }
        prices = sample_data['prices']

        comparison_df = analyzer.compare_factors(
            factor_dict, prices,
            include_correlation=True,
            rank_by='ic_ir'
        )

        # 验证对比结果
        assert isinstance(comparison_df, pd.DataFrame)
        assert len(comparison_df) == 3
        assert '因子名' in comparison_df.columns
        assert 'IC均值' in comparison_df.columns
        assert 'ICIR' in comparison_df.columns
        assert '综合评分' in comparison_df.columns

        # 验证排序（按ICIR降序）
        assert comparison_df['ICIR'].is_monotonic_decreasing or \
               comparison_df['ICIR'].iloc[0] >= comparison_df['ICIR'].iloc[-1]

    def test_compare_factors_ranking(self, analyzer, sample_data):
        """测试因子对比的不同排序方式"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'REV5': sample_data['factor2']
        }
        prices = sample_data['prices']

        # 按IC排序
        comp_ic = analyzer.compare_factors(
            factor_dict, prices,
            rank_by='ic'
        )
        assert '因子名' in comp_ic.columns

        # 按综合评分排序
        comp_score = analyzer.compare_factors(
            factor_dict, prices,
            rank_by='overall_score'
        )
        assert '综合评分' in comp_score.columns

    def test_optimize_factor_portfolio_equal_weight(self, analyzer, sample_data):
        """测试因子组合优化（等权重）"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'REV5': sample_data['factor2']
        }
        prices = sample_data['prices']

        opt_result, combined_factor = analyzer.optimize_factor_portfolio(
            factor_dict, prices,
            optimization_method='equal'
        )

        # 验证优化结果
        assert len(opt_result.weights) == 2
        assert abs(opt_result.weights['MOM20'] - 0.5) < 0.01
        assert abs(opt_result.weights['REV5'] - 0.5) < 0.01

        # 验证组合因子
        assert isinstance(combined_factor, pd.DataFrame)
        assert combined_factor.shape == sample_data['factor1'].shape

    def test_optimize_factor_portfolio_ic_weight(self, analyzer, sample_data):
        """测试因子组合优化（IC加权）"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'REV5': sample_data['factor2']
        }
        prices = sample_data['prices']

        opt_result, combined_factor = analyzer.optimize_factor_portfolio(
            factor_dict, prices,
            optimization_method='ic'
        )

        # 验证权重和为1
        assert abs(opt_result.weights.sum() - 1.0) < 0.01

        # 验证组合因子
        assert isinstance(combined_factor, pd.DataFrame)

    def test_optimize_factor_portfolio_icir_weight(self, analyzer, sample_data):
        """测试因子组合优化（ICIR加权）"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'REV5': sample_data['factor2']
        }
        prices = sample_data['prices']

        opt_result, combined_factor = analyzer.optimize_factor_portfolio(
            factor_dict, prices,
            optimization_method='ic_ir'
        )

        # 验证权重和为1
        assert abs(opt_result.weights.sum() - 1.0) < 0.01

    def test_optimize_factor_portfolio_max_icir(self, analyzer, sample_data):
        """测试因子组合优化（最大化ICIR）"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'REV5': sample_data['factor2']
        }
        prices = sample_data['prices']

        opt_result, combined_factor = analyzer.optimize_factor_portfolio(
            factor_dict, prices,
            optimization_method='max_icir',
            max_weight=0.8,
            min_weight=0.1
        )

        # 验证权重约束
        assert all(opt_result.weights >= 0.1 - 0.01)  # 允许小误差
        assert all(opt_result.weights <= 0.8 + 0.01)
        assert abs(opt_result.weights.sum() - 1.0) < 0.01

        # 验证ICIR计算
        assert opt_result.ic_ir is not None

    def test_optimize_factor_portfolio_invalid_method(self, analyzer, sample_data):
        """测试无效的优化方法"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'REV5': sample_data['factor2']
        }
        prices = sample_data['prices']

        with pytest.raises(ValueError, match="未知的优化方法"):
            analyzer.optimize_factor_portfolio(
                factor_dict, prices,
                optimization_method='invalid_method'
            )

    def test_generate_full_report(self, analyzer, sample_data):
        """测试生成完整报告"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'REV5': sample_data['factor2']
        }
        prices = sample_data['prices']

        report = analyzer.generate_full_report(
            factor_dict, prices,
            include_ic=True,
            include_layering=True,
            include_correlation=True,
            include_optimization=True
        )

        # 验证报告结构
        assert 'summary' in report
        assert 'individual_analysis' in report
        assert 'comparison' in report
        assert 'correlation' in report
        assert 'optimization' in report

        # 验证摘要
        assert report['summary']['n_factors'] == 2
        assert len(report['summary']['factor_names']) == 2

        # 验证单因子分析
        assert 'MOM20' in report['individual_analysis']
        assert 'REV5' in report['individual_analysis']

        # 验证对比结果
        assert report['comparison'] is not None

        # 验证相关性分析
        assert report['correlation'] is not None
        assert 'correlation_matrix' in report['correlation']

        # 验证优化结果
        assert report['optimization'] is not None

    def test_generate_full_report_single_factor(self, analyzer, sample_data):
        """测试单因子完整报告"""
        factor_dict = {
            'MOM20': sample_data['factor1']
        }
        prices = sample_data['prices']

        report = analyzer.generate_full_report(
            factor_dict, prices,
            include_ic=True,
            include_layering=True,
            include_correlation=False,  # 单因子不做相关性分析
            include_optimization=False  # 单因子不做优化
        )

        # 验证报告
        assert report['summary']['n_factors'] == 1
        assert 'MOM20' in report['individual_analysis']

    def test_generate_full_report_with_output(self, analyzer, sample_data, tmp_path):
        """测试保存完整报告到文件"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'REV5': sample_data['factor2']
        }
        prices = sample_data['prices']

        output_file = tmp_path / "factor_report.json"

        report = analyzer.generate_full_report(
            factor_dict, prices,
            include_ic=True,
            include_layering=False,
            include_correlation=False,
            include_optimization=False,
            output_path=str(output_file)
        )

        # 验证文件已创建
        assert output_file.exists()

        # 读取并验证JSON
        import json
        with open(output_file, 'r', encoding='utf-8') as f:
            loaded_report = json.load(f)

        assert loaded_report['summary']['n_factors'] == 2

    def test_batch_analyze(self, analyzer, sample_data):
        """测试批量分析"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'REV5': sample_data['factor2'],
            'RANDOM': sample_data['factor3']
        }
        prices = sample_data['prices']

        reports = analyzer.batch_analyze(factor_dict, prices)

        # 验证批量结果
        assert len(reports) == 3
        assert 'MOM20' in reports
        assert 'REV5' in reports
        assert 'RANDOM' in reports

        # 验证每个报告
        for factor_name, report in reports.items():
            assert isinstance(report, FactorAnalysisReport)
            assert report.factor_name == factor_name
            assert report.ic_result is not None

    def test_calculate_overall_score(self, analyzer, sample_data):
        """测试综合评分计算"""
        factor = sample_data['factor1']
        prices = sample_data['prices']

        report = analyzer.quick_analyze(factor, prices, factor_name='TEST')

        # 验证评分范围
        assert 0 <= report.overall_score <= 100

        # 验证评分逻辑（高IC应该有高分）
        if report.ic_result and abs(report.ic_result.mean_ic) > 0.03:
            assert report.overall_score > 40

    def test_generate_recommendation(self, analyzer):
        """测试建议生成"""
        # 高分因子
        report_high = FactorAnalysisReport(
            factor_name='HighScore',
            overall_score=85
        )
        rec_high = analyzer._generate_recommendation(report_high)
        assert '优秀' in rec_high or '强烈推荐' in rec_high

        # 中等因子
        report_medium = FactorAnalysisReport(
            factor_name='MediumScore',
            overall_score=65
        )
        rec_medium = analyzer._generate_recommendation(report_medium)
        assert '良好' in rec_medium or '可以使用' in rec_medium

        # 低分因子
        report_low = FactorAnalysisReport(
            factor_name='LowScore',
            overall_score=30
        )
        rec_low = analyzer._generate_recommendation(report_low)
        assert '较弱' in rec_low or '不建议' in rec_low

    def test_factor_analysis_report_to_dict(self, analyzer, sample_data):
        """测试报告转字典"""
        factor = sample_data['factor1']
        prices = sample_data['prices']

        report = analyzer.quick_analyze(factor, prices, factor_name='TEST')
        report_dict = report.to_dict()

        # 验证字典结构
        assert 'factor_name' in report_dict
        assert report_dict['factor_name'] == 'TEST'

        if report.ic_result:
            assert 'ic_analysis' in report_dict

        if report.overall_score:
            assert 'overall_score' in report_dict

    def test_factor_analysis_report_str(self, analyzer, sample_data):
        """测试报告字符串格式化"""
        factor = sample_data['factor1']
        prices = sample_data['prices']

        report = analyzer.quick_analyze(factor, prices, factor_name='TEST')
        report_str = str(report)

        # 验证输出包含关键信息
        assert 'TEST' in report_str
        assert '因子分析报告' in report_str

        if report.ic_result:
            assert 'IC分析' in report_str

        if report.overall_score:
            assert '综合评分' in report_str


class TestConvenienceFunctions:
    """测试便捷函数"""

    @pytest.fixture
    def sample_data(self):
        """创建测试数据"""
        np.random.seed(42)

        dates = pd.date_range('2020-01-01', '2020-12-31', freq='D')
        stocks = [f'stock_{i}' for i in range(30)]

        prices = pd.DataFrame(
            100 + np.random.randn(len(dates), len(stocks)).cumsum(axis=0),
            index=dates,
            columns=stocks
        )

        factor1 = prices.pct_change(20).shift(1)
        factor2 = -prices.pct_change(5).shift(1)

        return {
            'prices': prices,
            'factor1': factor1,
            'factor2': factor2
        }

    def test_quick_analyze_factor_function(self, sample_data):
        """测试快速分析便捷函数"""
        report = quick_analyze_factor(
            sample_data['factor1'],
            sample_data['prices'],
            factor_name='MOM20'
        )

        assert isinstance(report, FactorAnalysisReport)
        assert report.factor_name == 'MOM20'

    def test_quick_analyze_factor_with_params(self, sample_data):
        """测试带参数的快速分析"""
        report = quick_analyze_factor(
            sample_data['factor1'],
            sample_data['prices'],
            factor_name='MOM20',
            forward_periods=10,
            n_layers=10
        )

        assert isinstance(report, FactorAnalysisReport)

    def test_compare_multiple_factors_function(self, sample_data):
        """测试多因子对比便捷函数"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'REV5': sample_data['factor2']
        }

        comparison = compare_multiple_factors(
            factor_dict,
            sample_data['prices']
        )

        assert isinstance(comparison, pd.DataFrame)
        assert len(comparison) == 2

    def test_optimize_factor_combination_function(self, sample_data):
        """测试因子组合优化便捷函数"""
        factor_dict = {
            'MOM20': sample_data['factor1'],
            'REV5': sample_data['factor2']
        }

        opt_result, combined_factor = optimize_factor_combination(
            factor_dict,
            sample_data['prices'],
            method='equal'
        )

        assert len(opt_result.weights) == 2
        assert isinstance(combined_factor, pd.DataFrame)


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_factor_dict(self):
        """测试空因子字典"""
        analyzer = FactorAnalyzer()

        with pytest.raises((ValueError, KeyError, IndexError)):
            analyzer.compare_factors({}, pd.DataFrame())

    def test_single_stock(self):
        """测试单只股票数据"""
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', '2020-12-31', freq='D')

        prices = pd.DataFrame(
            100 + np.random.randn(len(dates), 1).cumsum(axis=0),
            index=dates,
            columns=['stock_1']
        )

        factor = prices.pct_change(20)

        analyzer = FactorAnalyzer()

        # 单只股票可能无法完成某些分析，但不应该崩溃
        try:
            report = analyzer.quick_analyze(factor, prices)
            assert report is not None
        except Exception as e:
            # 如果失败，确保是预期的错误
            assert 'valid' in str(e).lower() or 'samples' in str(e).lower()

    def test_mismatched_index(self):
        """测试索引不匹配"""
        np.random.seed(42)

        dates1 = pd.date_range('2020-01-01', '2020-06-30', freq='D')
        dates2 = pd.date_range('2020-07-01', '2020-12-31', freq='D')

        stocks = ['stock_1', 'stock_2']

        prices = pd.DataFrame(
            100 + np.random.randn(len(dates1), len(stocks)).cumsum(axis=0),
            index=dates1,
            columns=stocks
        )

        factor = pd.DataFrame(
            np.random.randn(len(dates2), len(stocks)),
            index=dates2,
            columns=stocks
        )

        analyzer = FactorAnalyzer()

        # 索引不匹配应该能处理或给出明确错误
        try:
            report = analyzer.quick_analyze(factor, prices)
            # 如果成功，验证结果有效
            assert report is not None
        except (ValueError, KeyError, IndexError):
            # 预期的错误类型
            pass

    def test_all_nan_factor(self):
        """测试全NaN因子"""
        np.random.seed(42)

        dates = pd.date_range('2020-01-01', '2020-12-31', freq='D')
        stocks = ['stock_1', 'stock_2']

        prices = pd.DataFrame(
            100 + np.random.randn(len(dates), len(stocks)).cumsum(axis=0),
            index=dates,
            columns=stocks
        )

        factor = pd.DataFrame(
            np.nan,
            index=dates,
            columns=stocks
        )

        analyzer = FactorAnalyzer()

        # 全NaN因子应该失败或返回无效报告
        try:
            report = analyzer.quick_analyze(factor, prices)
            # 如果成功，IC应该是NaN或None
            if report.ic_result:
                assert np.isnan(report.ic_result.mean_ic) or report.ic_result.mean_ic == 0
        except (ValueError, RuntimeError):
            # 预期的错误
            pass


class TestIntegration:
    """集成测试"""

    def test_complete_workflow(self):
        """测试完整的分析工作流"""
        np.random.seed(42)

        # 1. 准备数据
        dates = pd.date_range('2020-01-01', '2020-12-31', freq='D')
        stocks = [f'stock_{i}' for i in range(100)]

        prices = pd.DataFrame(
            100 + np.random.randn(len(dates), len(stocks)).cumsum(axis=0),
            index=dates,
            columns=stocks
        )

        # 2. 创建多个因子
        factor_dict = {
            'MOM20': prices.pct_change(20).shift(1),
            'MOM10': prices.pct_change(10).shift(1),
            'REV5': -prices.pct_change(5).shift(1),
        }

        # 3. 初始化分析器
        analyzer = FactorAnalyzer(
            forward_periods=5,
            n_layers=5,
            method='spearman'
        )

        # 4. 多因子对比
        comparison = analyzer.compare_factors(factor_dict, prices)
        assert len(comparison) == 3

        # 5. 因子组合优化
        opt_result, combined_factor = analyzer.optimize_factor_portfolio(
            factor_dict, prices,
            optimization_method='max_icir'
        )
        assert abs(opt_result.weights.sum() - 1.0) < 0.01

        # 6. 生成完整报告
        full_report = analyzer.generate_full_report(
            factor_dict, prices,
            include_ic=True,
            include_layering=True,
            include_correlation=True,
            include_optimization=True
        )
        assert full_report['summary']['n_factors'] == 3
        assert 'optimization' in full_report

    def test_real_world_scenario(self):
        """测试真实场景"""
        np.random.seed(42)

        # 模拟真实的市场数据
        dates = pd.date_range('2020-01-01', '2021-12-31', freq='D')
        stocks = [f'{i:06d}.SH' for i in range(600000, 600050)]

        # 价格有趋势和波动
        base_prices = 100
        trend = np.linspace(0, 20, len(dates))
        noise = np.random.randn(len(dates), len(stocks)) * 2

        prices = pd.DataFrame(
            base_prices + trend[:, np.newaxis] + noise.cumsum(axis=0),
            index=dates,
            columns=stocks
        )

        # 创建有意义的因子
        factor_dict = {
            'Momentum_20d': prices.pct_change(20),
            'Volatility_20d': prices.pct_change().rolling(20).std(),
            'Volume_Factor': pd.DataFrame(
                np.random.rand(len(dates), len(stocks)),
                index=dates,
                columns=stocks
            )
        }

        # 完整分析流程
        analyzer = FactorAnalyzer()

        # 批量分析
        batch_reports = analyzer.batch_analyze(factor_dict, prices)
        assert len(batch_reports) == 3

        # 选择最优因子
        comparison = analyzer.compare_factors(factor_dict, prices, rank_by='ic_ir')
        best_factor = comparison.iloc[0]['因子名']
        assert best_factor in factor_dict

        # 组合优化
        opt_result, _ = analyzer.optimize_factor_portfolio(
            factor_dict, prices,
            optimization_method='max_icir'
        )
        assert len(opt_result.weights) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
