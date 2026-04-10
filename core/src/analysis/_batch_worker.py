"""
因子批量分析并行 Worker 函数

模块级函数，供 multiprocessing/concurrent.futures 的 executor.map() 使用。
必须是模块级而非类方法，Python 的 pickle 机制才能序列化它传给子进程。

注意：故意放在独立模块而非 factor_analyzer.py，是为了避免循环导入：
      factor_analyzer → _batch_worker → factor_analyzer (FactorAnalyzer)
"""

from src.utils.logger import get_logger

logger = get_logger(__name__)

# 并行支持特性检测（与 factor_analyzer.py 保持一致）
try:
    from utils.parallel_executor import ParallelExecutor  # noqa: F401
    from config.features import ParallelComputingConfig   # noqa: F401
    HAS_PARALLEL_SUPPORT = True
except ImportError:
    HAS_PARALLEL_SUPPORT = False


def _analyze_single_factor_worker_v2(args):
    """
    分析单个因子（模块级函数，用于批量并行分析）

    Args:
        args: (factor_name, factor_df, prices, forward_periods, n_layers,
               holding_period, method, long_short)

    Returns:
        (factor_name, report, error)
    """
    factor_name, factor_df, prices, forward_periods, n_layers, holding_period, method, long_short = args

    try:
        # 创建禁用并行的分析器（避免嵌套并行）
        if HAS_PARALLEL_SUPPORT:
            from config.features import ParallelComputingConfig
            sub_config = ParallelComputingConfig(enable_parallel=False)
        else:
            sub_config = None

        # 在这里导入，避免模块级循环导入
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
        from src.exceptions import (
            AnalysisError, DataValidationError,
            InsufficientDataError, FeatureCalculationError
        )
        if isinstance(e, (DataValidationError, InsufficientDataError,
                          FeatureCalculationError, AnalysisError)):
            logger.warning(f"并行分析因子{factor_name}失败(已知异常): {e}")
            error_dict = {
                'error_type': e.__class__.__name__,
                'error_code': getattr(e, 'error_code', 'KNOWN_ANALYSIS_ERROR'),
                'message': str(e),
                'context': {'factor_name': factor_name}
            }
        else:
            logger.warning(f"并行分析因子{factor_name}失败(未预期异常): {e}")
            error_dict = {
                'error_type': 'Exception',
                'error_code': 'PARALLEL_ANALYSIS_FAILED',
                'message': f'并行分析因子失败: {str(e)}',
                'context': {'factor_name': factor_name}
            }
        return (factor_name, None, error_dict)
