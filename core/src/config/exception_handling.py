"""
异常处理增强配置

包含重试、断路器、断点续传、数据源降级等配置
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class RetryConfig:
    """重试配置"""

    # 重试次数
    max_attempts: int = 5

    # 基础延迟（秒）
    base_delay: float = 1.0

    # 最大延迟（秒）
    max_delay: float = 60.0

    # 退避系数
    backoff_factor: float = 2.0

    # 抖动因子（0-1）
    jitter_factor: float = 0.1

    # 重试时间预算（秒），None表示无限制
    retry_budget: float | None = 300.0

    # 是否启用断路器
    use_circuit_breaker: bool = True

    # 是否收集指标
    collect_metrics: bool = True


@dataclass
class CircuitBreakerConfig:
    """断路器配置"""

    # 失败阈值（连续失败多少次后打开断路器）
    failure_threshold: int = 5

    # 恢复超时（秒，打开后等待多久尝试恢复）
    recovery_timeout: float = 60.0

    # 半开状态最大调用次数
    half_open_max_calls: int = 3


@dataclass
class CheckpointConfig:
    """断点续传配置"""

    # 是否启用断点续传
    enable_checkpoint: bool = True

    # 保存检查点的间隔（秒）
    save_interval_seconds: int = 30

    # 清理已完成检查点的天数
    cleanup_after_days: int = 7

    # 最大并发下载任务数
    max_concurrent_downloads: int = 5


@dataclass
class FallbackConfig:
    """数据源降级配置"""

    # 是否启用自动降级
    enable_auto_fallback: bool = True

    # 健康检查间隔（秒）
    health_check_interval: int = 60

    # 降级阈值（连续失败多少次后降级）
    fallback_threshold: int = 3

    # 恢复尝试时间（秒）
    recovery_time_seconds: int = 300

    # 是否启用自动恢复
    enable_auto_recovery: bool = True

    # 失败惩罚分数
    failure_penalty: float = 10.0

    # 成功奖励分数
    success_reward: float = 5.0


@dataclass
class DataSourcePriorityConfig:
    """数据源优先级配置"""

    # 数据源优先级配置
    # 格式: {data_type: {'primary': 'provider_name', 'secondaries': ['provider2', ...]}}
    priority_map: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        'daily_data': {
            'primary': 'akshare',
            'secondaries': ['tushare'],
        },
        'realtime_data': {
            'primary': 'akshare',
            'secondaries': [],
        },
        'stock_list': {
            'primary': 'akshare',
            'secondaries': ['tushare'],
        }
    })


@dataclass
class ExceptionHandlingConfig:
    """异常处理增强总配置"""

    # 重试配置
    retry: RetryConfig = field(default_factory=RetryConfig)

    # 断路器配置
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    # 断点续传配置
    checkpoint: CheckpointConfig = field(default_factory=CheckpointConfig)

    # 降级配置
    fallback: FallbackConfig = field(default_factory=FallbackConfig)

    # 数据源优先级配置
    data_source_priority: DataSourcePriorityConfig = field(default_factory=DataSourcePriorityConfig)


# 默认配置实例
DEFAULT_EXCEPTION_HANDLING_CONFIG = ExceptionHandlingConfig()


# 生产环境配置（更保守的重试策略）
PRODUCTION_EXCEPTION_HANDLING_CONFIG = ExceptionHandlingConfig(
    retry=RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=120.0,
        retry_budget=600.0,
        use_circuit_breaker=True,
        collect_metrics=True
    ),
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=120.0,
        half_open_max_calls=2
    ),
    checkpoint=CheckpointConfig(
        enable_checkpoint=True,
        save_interval_seconds=60,
        cleanup_after_days=30,
        max_concurrent_downloads=3
    ),
    fallback=FallbackConfig(
        enable_auto_fallback=True,
        fallback_threshold=2,
        recovery_time_seconds=600,
        enable_auto_recovery=True
    )
)


# 开发环境配置（更激进的重试策略）
DEVELOPMENT_EXCEPTION_HANDLING_CONFIG = ExceptionHandlingConfig(
    retry=RetryConfig(
        max_attempts=10,
        base_delay=0.5,
        max_delay=30.0,
        retry_budget=None,  # 无限制
        use_circuit_breaker=False,
        collect_metrics=True
    ),
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=10,
        recovery_timeout=30.0,
        half_open_max_calls=5
    ),
    checkpoint=CheckpointConfig(
        enable_checkpoint=True,
        save_interval_seconds=10,
        cleanup_after_days=3,
        max_concurrent_downloads=10
    ),
    fallback=FallbackConfig(
        enable_auto_fallback=True,
        fallback_threshold=5,
        recovery_time_seconds=60,
        enable_auto_recovery=True
    )
)


def get_exception_handling_config(environment: str = 'default') -> ExceptionHandlingConfig:
    """
    获取异常处理配置

    Args:
        environment: 环境名称 ('default', 'production', 'development')

    Returns:
        异常处理配置实例
    """
    if environment == 'production':
        return PRODUCTION_EXCEPTION_HANDLING_CONFIG
    elif environment == 'development':
        return DEVELOPMENT_EXCEPTION_HANDLING_CONFIG
    else:
        return DEFAULT_EXCEPTION_HANDLING_CONFIG
