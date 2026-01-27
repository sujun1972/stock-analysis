"""
模型评估模块

提供量化交易专用的模型评估指标和工具，包括 IC、Rank IC、分组收益、
多空收益、Sharpe 比率等。

重构说明：
- 模块化设计：指标计算、格式化和评估逻辑分离
- 统一日志系统：使用 loguru
- 增强错误处理：自定义异常和数据验证
- 性能优化：向量化操作

示例用法：
    from models.evaluation import ModelEvaluator, EvaluationConfig, evaluate_model

    # 方式 1: 使用评估器
    evaluator = ModelEvaluator()
    metrics = evaluator.evaluate_regression(predictions, actual_returns)

    # 方式 2: 使用便捷函数
    metrics = evaluate_model(predictions, actual_returns, evaluation_type='regression')

    # 方式 3: 使用自定义配置
    config = EvaluationConfig(n_groups=10, top_pct=0.1)
    evaluator = ModelEvaluator(config=config)
    metrics = evaluator.evaluate_regression(predictions, actual_returns)
"""

# 主评估器
from .evaluator import ModelEvaluator

# 配置和异常
from .config import EvaluationConfig
from .exceptions import EvaluationError, InsufficientDataError, InvalidInputError

# 便捷函数
from .convenience import evaluate_model

# 指标计算器（可选导出，供高级用户使用）
from .metrics.calculator import MetricsCalculator

# 结果格式化器（可选导出）
from .formatter import ResultFormatter

# 向后兼容：保持原有的导入方式
# 用户可以直接从 evaluation 导入这些类和函数
__all__ = [
    # 主要接口
    'ModelEvaluator',
    'EvaluationConfig',
    'evaluate_model',

    # 异常类
    'EvaluationError',
    'InsufficientDataError',
    'InvalidInputError',

    # 高级接口（可选）
    'MetricsCalculator',
    'ResultFormatter',
]

# 版本信息
__version__ = '2.0.0'
