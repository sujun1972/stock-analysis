"""
Utils模块 - 通用工具函数集合

该模块提供了项目中各个模块共享的工具函数，旨在解耦模块依赖。

模块分类:
- data_utils: 数据处理通用函数（填充、异常检测、验证）
- calculation_utils: 计算相关函数（收益率、滚动统计、技术指标）
- validation_utils: 数据验证函数（参数检查、数据完整性）
- market_utils: 市场工具函数（交易时段、交易日历）
- type_utils: 类型相关工具
- logger: 日志工具
- parallel_executor: 并行计算工具
- memory_profiler: 内存分析工具
- decorators: 装饰器工具
- retry_strategy: 重试策略
- circuit_breaker: 熔断器
- gpu_utils: GPU工具
- memory_pool: 内存池
- task_partitioner: 任务分区器

作者: Quant Team
日期: 2026-01-31
版本: 2.0.0
"""

# 数据处理工具
from .data_utils import (
    # 数据填充
    forward_fill_series,
    backward_fill_series,
    interpolate_series,
    fill_with_value,
    # 异常检测
    detect_outliers_iqr,
    detect_outliers_zscore,
    detect_outliers_mad,
    # 数据验证
    check_missing_values,
    check_data_types,
    check_index_continuity,
    # 数据转换
    standardize_series,
    normalize_series,
    rank_series,
    # 辅助函数
    winsorize_series,
    remove_outliers,
)

# 计算工具
from .calculation_utils import (
    # 收益率计算
    calculate_returns,
    calculate_cumulative_returns,
    annualize_returns,
    calculate_excess_returns,
    # 滚动统计
    rolling_mean,
    rolling_std,
    rolling_var,
    rolling_corr,
    rolling_cov,
    rolling_min,
    rolling_max,
    rolling_sum,
    # 指数加权
    exponential_moving_average,
    exponential_weighted_std,
    # 技术指标基础
    calculate_momentum,
    calculate_roc,
    calculate_rsi,
    calculate_bollinger_bands,
    calculate_atr,
    # 统计函数
    calculate_correlation,
    calculate_beta,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    # 辅助函数
    shift_series,
    diff_series,
)

# 验证工具
from .validation_utils import (
    # DataFrame验证
    validate_columns_exist,
    validate_dataframe_not_empty,
    validate_no_missing_values,
    validate_datetime_index,
    validate_sorted_index,
    # 股票数据验证
    validate_ohlcv_data,
    validate_price_range,
    validate_daily_return_range,
    # 参数验证
    validate_positive_number,
    validate_range,
    validate_type,
    validate_enum,
    validate_window_size,
    # 时间序列验证
    validate_date_range,
    validate_frequency_consistency,
)

# 市场工具
from .market_utils import MarketUtils

# 类型工具
try:
    from .type_utils import *
except ImportError:
    pass

# 并行计算工具
try:
    from .parallel_executor import ParallelExecutor
except ImportError:
    pass

# 装饰器工具
try:
    from .decorators import *
except ImportError:
    pass


__all__ = [
    # ==================== 数据处理工具 ====================
    # 数据填充
    'forward_fill_series',
    'backward_fill_series',
    'interpolate_series',
    'fill_with_value',
    # 异常检测
    'detect_outliers_iqr',
    'detect_outliers_zscore',
    'detect_outliers_mad',
    # 数据验证
    'check_missing_values',
    'check_data_types',
    'check_index_continuity',
    # 数据转换
    'standardize_series',
    'normalize_series',
    'rank_series',
    # 辅助函数
    'winsorize_series',
    'remove_outliers',

    # ==================== 计算工具 ====================
    # 收益率计算
    'calculate_returns',
    'calculate_cumulative_returns',
    'annualize_returns',
    'calculate_excess_returns',
    # 滚动统计
    'rolling_mean',
    'rolling_std',
    'rolling_var',
    'rolling_corr',
    'rolling_cov',
    'rolling_min',
    'rolling_max',
    'rolling_sum',
    # 指数加权
    'exponential_moving_average',
    'exponential_weighted_std',
    # 技术指标基础
    'calculate_momentum',
    'calculate_roc',
    'calculate_rsi',
    'calculate_bollinger_bands',
    'calculate_atr',
    # 统计函数
    'calculate_correlation',
    'calculate_beta',
    'calculate_sharpe_ratio',
    'calculate_sortino_ratio',
    'calculate_max_drawdown',
    # 辅助函数
    'shift_series',
    'diff_series',

    # ==================== 验证工具 ====================
    # DataFrame验证
    'validate_columns_exist',
    'validate_dataframe_not_empty',
    'validate_no_missing_values',
    'validate_datetime_index',
    'validate_sorted_index',
    # 股票数据验证
    'validate_ohlcv_data',
    'validate_price_range',
    'validate_daily_return_range',
    # 参数验证
    'validate_positive_number',
    'validate_range',
    'validate_type',
    'validate_enum',
    'validate_window_size',
    # 时间序列验证
    'validate_date_range',
    'validate_frequency_consistency',

    # ==================== 市场工具 ====================
    'MarketUtils',

    # ==================== 其他工具 ====================
    # ParallelExecutor, decorators, etc. (如果成功导入)
]
