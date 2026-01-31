#!/usr/bin/env python3
"""
性能测试 Pytest 配置文件

导入所有fixtures和公共配置
"""

# 从benchmarks模块导入所有fixtures
from .benchmarks import (
    benchmark_data_large,
    benchmark_data_medium,
    single_stock_data,
    single_stock_data_long,
    model_training_data,
    model_training_data_small,
)

# 导出fixtures供pytest使用
__all__ = [
    'benchmark_data_large',
    'benchmark_data_medium',
    'single_stock_data',
    'single_stock_data_long',
    'model_training_data',
    'model_training_data_small',
]
