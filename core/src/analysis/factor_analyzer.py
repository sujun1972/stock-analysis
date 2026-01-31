"""
统一因子分析器门面（Facade Pattern）

提供一站式因子分析服务，整合：
- IC分析
- 分层回测
- 相关性分析
- 因子组合优化

设计理念：
- 统一入口：一个类完成所有因子分析
- 便捷方法：高层封装，减少重复代码
- 链式调用：支持流式API
- 自动化报告：一键生成完整分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
from loguru import logger
from dataclasses import dataclass
import warnings
import time

from .ic_calculator import ICCalculator, ICResult
from .layering_test import LayeringTest
from .factor_correlation import FactorCorrelation
from .factor_optimizer import FactorOptimizer, OptimizationResult
from ..utils.response import Response, ResponseStatus

warnings.filterwarnings('ignore')

# 导入并行计算工具
try:
    from ..utils.parallel_executor import ParallelExecutor
    from ..config.features import ParallelComputingConfig, get_feature_config
    HAS_PARALLEL_SUPPORT = True
except ImportError:
    HAS_PARALLEL_SUPPORT = False
    logger.warning("并行计算模块未找到，批量分析将使用串行执行")


# ==================== 模块级辅助函数（用于并行计算） ====================

def _analyze_single_factor_worker_v2(args):
    """
    分析单个因子（模块级函数，用于批量并行分析）

    Args:
        args: (factor_name, factor_df, prices, forward_periods, n_layers, holding_period, method, long_short)

    Returns:
        (factor_name, report, error)
    """
    factor_name, factor_df, prices, forward_periods, n_layers, holding_period, method, long_short = args

    try:
        # 创建禁用并行的分析器（避免嵌套并行）
        if HAS_PARALLEL_SUPPORT:
            from ..config.features import ParallelComputingConfig
            sub_config = ParallelComputingConfig(enable_parallel=False)
        else:
            sub_config = None

        # 必须在这里导入，避免循环导入
        from .factor_analyzer import FactorAnalyzer

        analyzer = FactorAnalyzer(
            forward_periods=forward_periods,
            n_layers=n_layers,
            holding_period=holding_period,
            method=method,
            long_short=long_short,
            parallel_config=sub_config
        )

        response = analyzer.quick_analyze(
            factor_df, prices,
            factor_name=factor_name,
            include_layering=True
        )

        # 从Response中提取报告数据
        if response.is_success() or response.status.value == "warning":
            return (factor_name, response.data, None)
        else:
            return (factor_name, None, response.error)

    except Exception as e:
        logger.warning(f"并行分析因子{factor_name}失败: {e}")
        return (factor_name, None, str(e))


@dataclass
class FactorAnalysisReport:
    """因子分析完整报告"""
    factor_name: str

    # IC分析结果
    ic_result: Optional[ICResult] = None

    # 分层测试结果
    layering_result: Optional[pd.DataFrame] = None
    layering_summary: Optional[Dict] = None

    # 相关性分析结果（多因子时）
    correlation_matrix: Optional[pd.DataFrame] = None
    high_corr_pairs: Optional[List[Tuple[str, str, float]]] = None

    # 优化结果（多因子时）
    optimization_result: Optional[OptimizationResult] = None

    # 综合评价
    overall_score: Optional[float] = None
    recommendation: Optional[str] = None

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        result = {
            'factor_name': self.factor_name,
        }

        if self.ic_result:
            result['ic_analysis'] = self.ic_result.to_dict()

        if self.layering_result is not None:
            result['layering_test'] = self.layering_result.to_dict()

        if self.layering_summary:
            result['layering_summary'] = self.layering_summary

        if self.correlation_matrix is not None:
            result['correlation_matrix'] = self.correlation_matrix.to_dict()

        if self.high_corr_pairs:
            result['high_correlation_pairs'] = [
                {'factor1': f1, 'factor2': f2, 'correlation': corr}
                for f1, f2, corr in self.high_corr_pairs
            ]

        if self.optimization_result:
            result['optimization'] = self.optimization_result.to_dict()

        if self.overall_score is not None:
            result['overall_score'] = self.overall_score

        if self.recommendation:
            result['recommendation'] = self.recommendation

        return result

    def __str__(self) -> str:
        """格式化输出"""
        lines = [f"\n{'='*60}"]
        lines.append(f"因子分析报告: {self.factor_name}")
        lines.append(f"{'='*60}\n")

        if self.ic_result:
            lines.append("【IC分析】")
            lines.append(str(self.ic_result))
            lines.append("")

        if self.layering_summary:
            lines.append("【分层测试】")
            for key, value in self.layering_summary.items():
                if isinstance(value, (int, float)):
                    lines.append(f"  {key}: {value:.4f}")
                else:
                    lines.append(f"  {key}: {value}")
            lines.append("")

        if self.overall_score is not None:
            lines.append(f"【综合评分】: {self.overall_score:.2f}/100")

        if self.recommendation:
            lines.append(f"【建议】: {self.recommendation}")

        lines.append(f"{'='*60}\n")

        return '\n'.join(lines)


class FactorAnalyzer:
    """
    统一因子分析器门面

    功能：
    - 单因子快速分析
    - 多因子对比分析
    - 因子组合优化
    - 一键生成完整报告

    使用示例：
        # 基础用法
        analyzer = FactorAnalyzer()
        report = analyzer.quick_analyze(factor_df, prices_df)

        # 多因子对比
        comparison = analyzer.compare_factors(factor_dict, prices_df)

        # 完整分析
        full_report = analyzer.generate_full_report(
            factor_dict, prices_df,
            include_ic=True,
            include_layering=True,
            include_correlation=True,
            include_optimization=True
        )
    """

    def __init__(
        self,
        forward_periods: int = 5,
        n_layers: int = 5,
        holding_period: int = 5,
        method: str = 'spearman',
        long_short: bool = True,
        parallel_config: Optional['ParallelComputingConfig'] = None
    ):
        """
        初始化因子分析器

        Args:
            forward_periods: IC计算的前瞻期（天数）
            n_layers: 分层测试的层数
            holding_period: 分层测试的持有期
            method: 相关性计算方法（'pearson'或'spearman'）
            long_short: 是否计算多空组合收益
            parallel_config: 并行计算配置（可选）
        """
        self.forward_periods = forward_periods
        self.n_layers = n_layers
        self.holding_period = holding_period
        self.method = method
        self.long_short = long_short

        # 并行计算配置
        if HAS_PARALLEL_SUPPORT:
            self.parallel_config = parallel_config or get_feature_config().parallel_computing
        else:
            self.parallel_config = None

        # 初始化各个分析工具
        self.ic_calculator = ICCalculator(
            forward_periods=forward_periods,
            method=method,
            parallel_config=self.parallel_config
        )

        self.layering_test = LayeringTest(
            n_layers=n_layers,
            holding_period=holding_period,
            long_short=long_short
        )

        self.correlation_analyzer = FactorCorrelation(method=method)

        self.optimizer = FactorOptimizer()

        logger.info(
            f"初始化FactorAnalyzer: "
            f"前瞻期={forward_periods}, 分层={n_layers}, "
            f"持有期={holding_period}, 方法={method}, "
            f"并行={'启用' if self.parallel_config and self.parallel_config.enable_parallel else '禁用'}"
        )

    def quick_analyze(
        self,
        factor: Union[pd.DataFrame, pd.Series],
        prices: pd.DataFrame,
        factor_name: str = "Factor",
        include_layering: bool = True
    ) -> Response:
        """
        快速分析单个因子（初级用法）

        Args:
            factor: 因子DataFrame或Series
            prices: 价格DataFrame
            factor_name: 因子名称
            include_layering: 是否包含分层测试

        Returns:
            Response对象，data字段包含FactorAnalysisReport

        Examples:
            >>> analyzer = FactorAnalyzer()
            >>> response = analyzer.quick_analyze(factor_df, prices_df, factor_name='MOM')
            >>> if response.is_success():
            >>>     report = response.data
            >>>     print(f"IC均值: {report.ic_result.mean_ic}")
        """
        try:
            start_time = time.time()
            logger.info(f"快速分析因子: {factor_name}")

            # 数据验证
            if factor is None or prices is None:
                return Response.error(
                    error="因子数据或价格数据为空",
                    error_code="INVALID_INPUT",
                    factor_name=factor_name
                )

            # 确保factor是DataFrame格式
            if isinstance(factor, pd.Series):
                factor = factor.to_frame(name=factor_name)

            if factor.empty or prices.empty:
                return Response.error(
                    error="因子数据或价格数据为空DataFrame",
                    error_code="EMPTY_DATA",
                    factor_name=factor_name
                )

            report = FactorAnalysisReport(factor_name=factor_name)
            warnings = []

            # 1. IC分析（必选）
            try:
                ic_response = self.ic_calculator.calculate_ic_stats(factor, prices)
                if ic_response.is_success():
                    ic_result = ic_response.data
                    report.ic_result = ic_result
                    logger.info(f"IC分析完成: IC={ic_result.mean_ic:.4f}, ICIR={ic_result.ic_ir:.4f}")
                else:
                    error_msg = ic_response.error if hasattr(ic_response, 'error') else str(ic_response)
                    logger.warning(f"IC分析失败: {error_msg}")
                    warnings.append(f"IC分析失败: {error_msg}")
            except Exception as e:
                logger.warning(f"IC分析失败: {e}")
                warnings.append(f"IC分析失败: {str(e)}")

            # 2. 分层测试（可选）
            if include_layering:
                try:
                    layering_result = self.layering_test.perform_layering_test(
                        factor, prices
                    )
                    report.layering_result = layering_result

                    # 分析单调性
                    monotonicity = self.layering_test.analyze_monotonicity(layering_result)
                    report.layering_summary = monotonicity

                    logger.info(f"分层测试完成: 单调性={monotonicity['是否单调']}")
                except Exception as e:
                    logger.warning(f"分层测试失败: {e}")
                    warnings.append(f"分层测试失败: {str(e)}")

            # 3. 综合评分
            report.overall_score = self._calculate_overall_score(report)
            report.recommendation = self._generate_recommendation(report)

            elapsed_time = time.time() - start_time

            # 判断是否有警告
            if warnings:
                return Response.warning(
                    message=f"因子分析完成但有{len(warnings)}个警告",
                    data=report,
                    factor_name=factor_name,
                    elapsed_time=f"{elapsed_time:.2f}s",
                    warnings=warnings,
                    overall_score=report.overall_score,
                    recommendation=report.recommendation
                )
            else:
                return Response.success(
                    data=report,
                    message=f"因子 {factor_name} 分析完成",
                    factor_name=factor_name,
                    elapsed_time=f"{elapsed_time:.2f}s",
                    overall_score=report.overall_score,
                    recommendation=report.recommendation
                )

        except Exception as e:
            logger.error(f"快速分析因子失败: {e}", exc_info=True)
            return Response.error(
                error=f"快速分析因子失败: {str(e)}",
                error_code="ANALYSIS_ERROR",
                factor_name=factor_name
            )

    def analyze_factor(
        self,
        factor: Union[pd.DataFrame, pd.Series],
        prices: pd.DataFrame,
        factor_name: str = "Factor",
        include_ic: bool = True,
        include_layering: bool = True,
        include_decay_analysis: bool = False
    ) -> Response:
        """
        完整分析单个因子（中级用法）

        Args:
            factor: 因子DataFrame或Series
            prices: 价格DataFrame
            factor_name: 因子名称
            include_ic: 是否包含IC分析
            include_layering: 是否包含分层测试
            include_decay_analysis: 是否包含IC衰减分析

        Returns:
            Response对象，data字段包含FactorAnalysisReport

        Examples:
            >>> analyzer = FactorAnalyzer()
            >>> response = analyzer.analyze_factor(
            ...     factor_df, prices_df,
            ...     factor_name='REV',
            ...     include_ic=True,
            ...     include_layering=True
            ... )
            >>> if response.is_success():
            ...     report = response.data
            ...     print(report.to_dict())
        """
        try:
            start_time = time.time()
            logger.info(f"完整分析因子: {factor_name}")

            # 数据验证
            if factor is None or prices is None:
                return Response.error(
                    error="因子数据或价格数据为空",
                    error_code="INVALID_INPUT",
                    factor_name=factor_name
                )

            # 确保factor是DataFrame格式
            if isinstance(factor, pd.Series):
                factor = factor.to_frame(name=factor_name)

            if factor.empty or prices.empty:
                return Response.error(
                    error="因子数据或价格数据为空DataFrame",
                    error_code="EMPTY_DATA",
                    factor_name=factor_name
                )

            report = FactorAnalysisReport(factor_name=factor_name)
            warnings_list = []

            # 1. IC分析
            if include_ic:
                try:
                    ic_response = self.ic_calculator.calculate_ic_stats(factor, prices)
                    if ic_response.is_success():
                        ic_result = ic_response.data
                        report.ic_result = ic_result
                        logger.info(f"IC分析完成: IC={ic_result.mean_ic:.4f}, ICIR={ic_result.ic_ir:.4f}")
                    else:
                        error_msg = ic_response.error if hasattr(ic_response, 'error') else str(ic_response)
                        logger.warning(f"IC分析失败: {error_msg}")
                        warnings_list.append(f"IC分析失败: {error_msg}")
                except Exception as e:
                    logger.warning(f"IC分析失败: {e}")
                    warnings_list.append(f"IC分析失败: {str(e)}")

            # 2. 分层测试
            if include_layering:
                try:
                    layering_result = self.layering_test.perform_layering_test(
                        factor, prices
                    )
                    report.layering_result = layering_result

                    # 分析单调性
                    monotonicity = self.layering_test.analyze_monotonicity(layering_result)
                    report.layering_summary = monotonicity

                    logger.info(f"分层测试完成: 单调性={monotonicity['是否单调']}")
                except Exception as e:
                    logger.warning(f"分层测试失败: {e}")
                    warnings_list.append(f"分层测试失败: {str(e)}")

            # 3. IC衰减分析（可选）
            if include_decay_analysis:
                try:
                    # TODO: 添加IC衰减分析实现
                    logger.info("IC衰减分析功能待实现")
                    warnings_list.append("IC衰减分析功能待实现")
                except Exception as e:
                    logger.warning(f"IC衰减分析失败: {e}")
                    warnings_list.append(f"IC衰减分析失败: {str(e)}")

            # 4. 综合评分
            report.overall_score = self._calculate_overall_score(report)
            report.recommendation = self._generate_recommendation(report)

            elapsed_time = time.time() - start_time

            # 检查是否有足够的分析结果
            if report.ic_result is None and report.layering_result is None:
                return Response.error(
                    error="所有分析项目均失败",
                    error_code="ALL_ANALYSIS_FAILED",
                    factor_name=factor_name,
                    warnings=warnings_list
                )

            # 判断是否有警告
            if warnings_list:
                return Response.warning(
                    message=f"因子完整分析完成但有{len(warnings_list)}个警告",
                    data=report,
                    factor_name=factor_name,
                    elapsed_time=f"{elapsed_time:.2f}s",
                    warnings=warnings_list,
                    overall_score=report.overall_score,
                    recommendation=report.recommendation
                )
            else:
                return Response.success(
                    data=report,
                    message=f"因子 {factor_name} 完整分析成功",
                    factor_name=factor_name,
                    elapsed_time=f"{elapsed_time:.2f}s",
                    overall_score=report.overall_score,
                    recommendation=report.recommendation
                )

        except Exception as e:
            logger.error(f"完整分析因子失败: {e}", exc_info=True)
            return Response.error(
                error=f"完整分析因子失败: {str(e)}",
                error_code="ANALYSIS_ERROR",
                factor_name=factor_name
            )

    def compare_factors(
        self,
        factor_dict: Dict[str, pd.DataFrame],
        prices: pd.DataFrame,
        include_correlation: bool = True,
        rank_by: str = 'ic_ir'
    ) -> pd.DataFrame:
        """
        对比多个因子（中级用法）

        Args:
            factor_dict: 因子字典 {因子名: 因子DataFrame}
            prices: 价格DataFrame
            include_correlation: 是否计算因子间相关性
            rank_by: 排序依据 ('ic', 'ic_ir', 'overall_score')

        Returns:
            因子对比DataFrame
        """
        logger.info(f"对比{len(factor_dict)}个因子...")

        results = []

        for factor_name, factor_df in factor_dict.items():
            try:
                # 快速分析每个因子
                report = self.quick_analyze(
                    factor_df, prices,
                    factor_name=factor_name,
                    include_layering=True
                )

                # 提取关键指标
                row = {
                    '因子名': factor_name,
                }

                if report.ic_result:
                    row.update({
                        'IC均值': report.ic_result.mean_ic,
                        'IC标准差': report.ic_result.std_ic,
                        'ICIR': report.ic_result.ic_ir,
                        'IC正值率': report.ic_result.positive_rate,
                    })

                if report.layering_summary:
                    row.update({
                        '是否单调': report.layering_summary.get('是否单调', False),
                        '收益差距': report.layering_summary.get('收益差距', 0),
                    })

                row['综合评分'] = report.overall_score or 0

                results.append(row)

            except Exception as e:
                logger.warning(f"分析因子{factor_name}失败: {e}")

        comparison_df = pd.DataFrame(results)

        # 排序
        if rank_by == 'ic':
            comparison_df = comparison_df.sort_values('IC均值', ascending=False)
        elif rank_by == 'ic_ir':
            comparison_df = comparison_df.sort_values('ICIR', ascending=False)
        elif rank_by == 'overall_score':
            comparison_df = comparison_df.sort_values('综合评分', ascending=False)

        # 相关性分析
        if include_correlation and len(factor_dict) > 1:
            try:
                corr_matrix = self.correlation_analyzer.calculate_factor_correlation(
                    factor_dict,
                    aggregate_method='concat'
                )
                logger.info(f"相关性分析完成: {corr_matrix.shape}")
            except Exception as e:
                logger.warning(f"相关性分析失败: {e}")

        logger.info(f"因子对比完成，共{len(comparison_df)}个因子")

        return comparison_df

    def optimize_factor_portfolio(
        self,
        factor_dict: Dict[str, pd.DataFrame],
        prices: pd.DataFrame,
        optimization_method: str = 'max_icir',
        max_weight: float = 0.5,
        min_weight: float = 0.0
    ) -> Tuple[OptimizationResult, pd.DataFrame]:
        """
        优化因子组合权重（高级用法）

        Args:
            factor_dict: 因子字典
            prices: 价格DataFrame
            optimization_method: 优化方法
                - 'equal': 等权重
                - 'ic': IC加权
                - 'ic_ir': ICIR加权
                - 'max_icir': 最大化ICIR（优化算法）
            max_weight: 单因子最大权重
            min_weight: 单因子最小权重

        Returns:
            (优化结果, 组合因子DataFrame)
        """
        logger.info(f"优化因子组合: {len(factor_dict)}个因子, 方法={optimization_method}")

        # 1. 计算各因子的IC序列
        ic_series_dict = {}
        ic_stats_list = []

        for factor_name, factor_df in factor_dict.items():
            try:
                ic_response = self.ic_calculator.calculate_ic_stats(factor_df, prices)
                if ic_response.is_success():
                    ic_result = ic_response.data
                    ic_series_dict[factor_name] = ic_result.ic_series
                    ic_stats_list.append({
                        '因子名': factor_name,
                        'IC均值': ic_result.mean_ic,
                        'IC标准差': ic_result.std_ic,
                        'ICIR': ic_result.ic_ir
                    })
                else:
                    error_msg = ic_response.error if hasattr(ic_response, 'error') else str(ic_response)
                    logger.warning(f"计算{factor_name}的IC失败: {error_msg}")
            except Exception as e:
                logger.warning(f"计算{factor_name}的IC失败: {e}")

        ic_stats_df = pd.DataFrame(ic_stats_list).set_index('因子名')

        # 2. 根据方法选择权重
        if optimization_method == 'equal':
            weights = self.optimizer.equal_weight(list(factor_dict.keys()))
            opt_result = OptimizationResult(
                weights=weights,
                objective_value=0,
                ic_mean=0,
                ic_ir=0,
                method='equal'
            )

        elif optimization_method == 'ic':
            weights = self.optimizer.ic_weight(ic_stats_df)
            opt_result = OptimizationResult(
                weights=weights,
                objective_value=0,
                ic_mean=0,
                ic_ir=0,
                method='ic'
            )

        elif optimization_method == 'ic_ir':
            weights = self.optimizer.ic_ir_weight(ic_stats_df)
            opt_result = OptimizationResult(
                weights=weights,
                objective_value=0,
                ic_mean=0,
                ic_ir=0,
                method='ic_ir'
            )

        elif optimization_method == 'max_icir':
            opt_result = self.optimizer.optimize_max_icir(
                ic_series_dict,
                method='SLSQP',
                max_weight=max_weight,
                min_weight=min_weight
            )
            weights = opt_result.weights

        else:
            raise ValueError(f"未知的优化方法: {optimization_method}")

        # 3. 组合因子
        combined_factor = self.optimizer.combine_factors(
            factor_dict,
            weights,
            normalize=True
        )

        logger.info(f"因子组合完成: ICIR={opt_result.ic_ir:.4f}")

        return opt_result, combined_factor

    def generate_full_report(
        self,
        factor_dict: Dict[str, pd.DataFrame],
        prices: pd.DataFrame,
        include_ic: bool = True,
        include_layering: bool = True,
        include_correlation: bool = True,
        include_optimization: bool = True,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成完整的多因子分析报告（高级用法）

        Args:
            factor_dict: 因子字典
            prices: 价格DataFrame
            include_ic: 是否包含IC分析
            include_layering: 是否包含分层测试
            include_correlation: 是否包含相关性分析
            include_optimization: 是否包含组合优化
            output_path: 报告输出路径（可选）

        Returns:
            完整报告字典
        """
        logger.info(f"生成完整报告: {len(factor_dict)}个因子")

        report = {
            'summary': {
                'n_factors': len(factor_dict),
                'factor_names': list(factor_dict.keys()),
                'analysis_date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'individual_analysis': {},
            'comparison': None,
            'correlation': None,
            'optimization': None
        }

        # 1. 单因子分析
        if include_ic or include_layering:
            for factor_name, factor_df in factor_dict.items():
                try:
                    factor_report = self.analyze_factor(
                        factor_df, prices,
                        factor_name=factor_name,
                        include_ic=include_ic,
                        include_layering=include_layering
                    )
                    report['individual_analysis'][factor_name] = factor_report.to_dict()
                except Exception as e:
                    logger.warning(f"分析因子{factor_name}失败: {e}")

        # 2. 因子对比
        try:
            comparison_df = self.compare_factors(
                factor_dict, prices,
                include_correlation=False,
                rank_by='ic_ir'
            )
            report['comparison'] = comparison_df.to_dict('records')
        except Exception as e:
            logger.warning(f"因子对比失败: {e}")

        # 3. 相关性分析
        if include_correlation and len(factor_dict) > 1:
            try:
                corr_matrix = self.correlation_analyzer.calculate_factor_correlation(
                    factor_dict,
                    aggregate_method='concat'
                )

                high_corr_pairs = self.correlation_analyzer.find_high_correlation_pairs(
                    corr_matrix,
                    threshold=0.7
                )

                report['correlation'] = {
                    'correlation_matrix': corr_matrix.to_dict(),
                    'high_correlation_pairs': [
                        {'factor1': f1, 'factor2': f2, 'correlation': float(corr)}
                        for f1, f2, corr in high_corr_pairs
                    ]
                }
            except Exception as e:
                logger.warning(f"相关性分析失败: {e}")

        # 4. 组合优化
        if include_optimization and len(factor_dict) > 1:
            try:
                opt_result, combined_factor = self.optimize_factor_portfolio(
                    factor_dict, prices,
                    optimization_method='max_icir'
                )

                report['optimization'] = opt_result.to_dict()
            except Exception as e:
                logger.warning(f"组合优化失败: {e}")

        # 5. 保存报告（如果指定路径）
        if output_path:
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"报告已保存到: {output_path}")

        logger.info("完整报告生成完成")

        return report

    def batch_analyze(
        self,
        factor_dict: Dict[str, pd.DataFrame],
        prices: pd.DataFrame,
        n_jobs: int = None
    ) -> Response:
        """
        批量分析多个因子（支持并行）

        Args:
            factor_dict: 因子字典 {因子名: 因子DataFrame}
            prices: 价格DataFrame
            n_jobs: 并行任务数（向后兼容参数，优先使用parallel_config）

        Returns:
            Response对象，data字段包含 {因子名: FactorAnalysisReport} 字典

        Examples:
            >>> analyzer = FactorAnalyzer()
            >>> response = analyzer.batch_analyze(factor_dict, prices)
            >>> if response.is_success():
            ...     reports = response.data
            ...     for name, report in reports.items():
            ...         print(f"{name}: {report.overall_score}")

            >>> # 或显式指定worker数量
            >>> response = analyzer.batch_analyze(factor_dict, prices, n_jobs=8)
        """
        try:
            start_time = time.time()
            logger.info(f"批量分析{len(factor_dict)}个因子...")

            # 数据验证
            if not factor_dict:
                return Response.error(
                    error="因子字典为空",
                    error_code="EMPTY_FACTOR_DICT"
                )

            if prices is None or prices.empty:
                return Response.error(
                    error="价格数据为空",
                    error_code="EMPTY_PRICE_DATA"
                )

            # 向后兼容：n_jobs覆盖配置
            if n_jobs is not None and n_jobs != 1:
                if HAS_PARALLEL_SUPPORT:
                    self.parallel_config.n_workers = n_jobs
                    self.parallel_config.enable_parallel = True
                else:
                    logger.warning("并行计算模块未找到，将忽略n_jobs参数")

            # 判断是否使用并行
            use_parallel = (
                HAS_PARALLEL_SUPPORT and
                self.parallel_config and
                self.parallel_config.enable_parallel and
                self.parallel_config.n_workers > 1 and
                len(factor_dict) >= 4  # 至少4个因子才并行
            )

            if use_parallel:
                logger.debug(
                    f"使用并行批量分析: {len(factor_dict)}个因子, "
                    f"{self.parallel_config.n_workers}个worker"
                )
                reports = self._batch_analyze_parallel(factor_dict, prices)
            else:
                if not use_parallel and len(factor_dict) < 4:
                    logger.debug(f"因子数量较少({len(factor_dict)})，使用串行分析")
                reports = self._batch_analyze_serial(factor_dict, prices)

            elapsed_time = time.time() - start_time
            success_count = len(reports)
            total_count = len(factor_dict)
            failed_count = total_count - success_count

            logger.info(f"批量分析完成: {success_count}/{total_count}个成功")

            # 判断结果
            if success_count == 0:
                return Response.error(
                    error="所有因子分析均失败",
                    error_code="ALL_FACTORS_FAILED",
                    total_factors=total_count,
                    elapsed_time=f"{elapsed_time:.2f}s"
                )
            elif failed_count > 0:
                return Response.warning(
                    message=f"批量分析完成，但有{failed_count}个因子失败",
                    data=reports,
                    total_factors=total_count,
                    success_count=success_count,
                    failed_count=failed_count,
                    elapsed_time=f"{elapsed_time:.2f}s",
                    parallel_mode="并行" if use_parallel else "串行"
                )
            else:
                return Response.success(
                    data=reports,
                    message=f"批量分析成功完成{total_count}个因子",
                    total_factors=total_count,
                    success_count=success_count,
                    elapsed_time=f"{elapsed_time:.2f}s",
                    parallel_mode="并行" if use_parallel else "串行"
                )

        except Exception as e:
            logger.error(f"批量分析失败: {e}", exc_info=True)
            return Response.error(
                error=f"批量分析失败: {str(e)}",
                error_code="BATCH_ANALYSIS_ERROR",
                total_factors=len(factor_dict) if factor_dict else 0
            )

    def _batch_analyze_serial(
        self,
        factor_dict: Dict[str, pd.DataFrame],
        prices: pd.DataFrame
    ) -> Dict[str, FactorAnalysisReport]:
        """串行批量分析（内部方法）"""
        reports = {}

        for factor_name, factor_df in factor_dict.items():
            try:
                response = self.quick_analyze(
                    factor_df, prices,
                    factor_name=factor_name
                )
                # 提取Response中的报告数据
                if response.is_success() or response.status == ResponseStatus.WARNING:
                    reports[factor_name] = response.data
                else:
                    logger.warning(f"分析因子{factor_name}失败: {response.error}")
            except Exception as e:
                logger.warning(f"分析因子{factor_name}失败: {e}")

        return reports

    def _batch_analyze_parallel(
        self,
        factor_dict: Dict[str, pd.DataFrame],
        prices: pd.DataFrame
    ) -> Dict[str, FactorAnalysisReport]:
        """
        并行批量分析

        策略：
        - 按因子分片，每个worker处理若干因子
        - 子任务禁用并行，避免嵌套并行
        - 捕获所有异常，返回部分结果
        """
        # 转为列表以便分片
        factor_items = list(factor_dict.items())

        # 准备任务参数（包含所有需要的配置）
        tasks = [
            (
                factor_name,
                factor_df,
                prices,
                self.forward_periods,
                self.n_layers,
                self.holding_period,
                self.method,
                self.long_short
            )
            for factor_name, factor_df in factor_items
        ]

        # 创建并行执行器
        executor = ParallelExecutor(self.parallel_config)

        try:
            # 并行执行（使用模块级函数）
            results = executor.map(
                _analyze_single_factor_worker_v2,
                tasks,
                desc="批量因子分析"
            )

            # 聚合结果
            reports = {}
            failed_count = 0

            for factor_name, report, error in results:
                if report is not None:
                    reports[factor_name] = report
                else:
                    failed_count += 1

            if failed_count > 0:
                logger.warning(f"{failed_count}个因子分析失败")

            return reports

        finally:
            executor.shutdown()

    def _calculate_overall_score(self, report: FactorAnalysisReport) -> float:
        """
        计算因子综合评分（0-100分）

        评分维度：
        - IC均值（40分）
        - ICIR（30分）
        - IC正值率（15分）
        - 单调性（15分）
        """
        score = 0.0

        # IC均值得分（40分）
        if report.ic_result:
            ic_mean = abs(report.ic_result.mean_ic)
            if ic_mean >= 0.05:
                score += 40
            elif ic_mean >= 0.03:
                score += 30
            elif ic_mean >= 0.01:
                score += 20
            else:
                score += ic_mean / 0.05 * 40

        # ICIR得分（30分）
        if report.ic_result:
            ic_ir = abs(report.ic_result.ic_ir)
            if ic_ir >= 1.0:
                score += 30
            elif ic_ir >= 0.5:
                score += 20
            else:
                score += ic_ir / 1.0 * 30

        # IC正值率得分（15分）
        if report.ic_result:
            positive_rate = report.ic_result.positive_rate
            if positive_rate >= 0.6:
                score += 15
            elif positive_rate >= 0.55:
                score += 10
            else:
                score += (positive_rate - 0.5) / 0.1 * 15

        # 单调性得分（15分）
        if report.layering_summary:
            if report.layering_summary.get('是否单调', False):
                score += 15
            else:
                # 根据收益差距给部分分
                revenue_gap = abs(report.layering_summary.get('收益差距', 0))
                score += min(revenue_gap / 0.02 * 15, 15)

        return min(max(score, 0), 100)

    def _generate_recommendation(self, report: FactorAnalysisReport) -> str:
        """生成使用建议"""
        score = report.overall_score or 0

        if score >= 80:
            return "优秀因子，强烈推荐使用"
        elif score >= 60:
            return "良好因子，可以使用"
        elif score >= 40:
            return "一般因子，需要进一步优化或组合"
        else:
            return "较弱因子，不建议单独使用"


# 便捷函数

def quick_analyze_factor(
    factor: Union[pd.DataFrame, pd.Series],
    prices: pd.DataFrame,
    factor_name: str = "Factor",
    **kwargs
) -> FactorAnalysisReport:
    """
    快速分析单个因子的便捷函数

    Args:
        factor: 因子数据
        prices: 价格数据
        factor_name: 因子名称
        **kwargs: 传递给FactorAnalyzer的参数

    Returns:
        因子分析报告
    """
    analyzer = FactorAnalyzer(**kwargs)
    return analyzer.quick_analyze(factor, prices, factor_name)


def compare_multiple_factors(
    factor_dict: Dict[str, pd.DataFrame],
    prices: pd.DataFrame,
    **kwargs
) -> pd.DataFrame:
    """
    对比多个因子的便捷函数

    Args:
        factor_dict: 因子字典
        prices: 价格数据
        **kwargs: 传递给FactorAnalyzer的参数

    Returns:
        因子对比DataFrame
    """
    analyzer = FactorAnalyzer(**kwargs)
    return analyzer.compare_factors(factor_dict, prices)


def optimize_factor_combination(
    factor_dict: Dict[str, pd.DataFrame],
    prices: pd.DataFrame,
    method: str = 'max_icir',
    **kwargs
) -> Tuple[OptimizationResult, pd.DataFrame]:
    """
    优化因子组合的便捷函数

    Args:
        factor_dict: 因子字典
        prices: 价格数据
        method: 优化方法
        **kwargs: 传递给FactorAnalyzer的参数

    Returns:
        (优化结果, 组合因子)
    """
    analyzer = FactorAnalyzer(**kwargs)
    return analyzer.optimize_factor_portfolio(factor_dict, prices, method)
