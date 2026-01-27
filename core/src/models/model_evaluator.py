"""
模型评估器 - 向后兼容层

此文件保持向后兼容，所有功能已迁移到 evaluation 模块。
推荐使用新的模块化导入方式：
    from models.evaluation import ModelEvaluator, EvaluationConfig

但为了不破坏现有代码，此文件仍然可用：
    from models.model_evaluator import ModelEvaluator

重构说明：
- 所有功能已拆分到 models/evaluation/ 模块
- 模块化设计：指标计算、结果格式化和主评估逻辑分离
- 统一日志系统：使用 loguru 替代 print
- 增强错误处理：自定义异常类和数据验证
- 性能优化：向量化操作和结果缓存
"""

# 从新的 evaluation 模块导入所有内容
from .evaluation import (
    # 主要接口
    ModelEvaluator,
    EvaluationConfig,
    evaluate_model,

    # 异常类
    EvaluationError,
    InsufficientDataError,
    InvalidInputError,

    # 高级接口
    MetricsCalculator,
    ResultFormatter,
)

# 导入辅助函数（测试文件需要）
from .evaluation.utils import filter_valid_pairs

# 保持所有原有的导出
__all__ = [
    'ModelEvaluator',
    'EvaluationConfig',
    'evaluate_model',
    'EvaluationError',
    'InsufficientDataError',
    'InvalidInputError',
    'MetricsCalculator',
    'ResultFormatter',
    'filter_valid_pairs',  # 测试文件需要
]

# 向后兼容：支持旧的导入方式
# 例如: from models.model_evaluator import ModelEvaluator
