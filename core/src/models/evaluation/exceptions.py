"""
评估模块异常类定义

该模块已迁移到统一异常系统，所有异常类继承自src.exceptions中的基类。

Migration Notes:
    - EvaluationError 现在继承自 ModelError
    - InsufficientDataError 继承自 InsufficientDataError（统一异常系统）
    - InvalidInputError 继承自 DataValidationError
    - 完全向后兼容
"""

# 导入统一异常系统
from src.exceptions import ModelError, InsufficientDataError as BaseInsufficientDataError, DataValidationError


class EvaluationError(ModelError):
    """评估过程错误基类（迁移到统一异常系统）

    该异常类现在继承自统一异常系统的ModelError。
    支持错误代码和上下文信息。

    Examples:
        >>> raise EvaluationError(
        ...     "模型评估失败",
        ...     error_code="EVALUATION_FAILED",
        ...     model_name="lgb_model_v1",
        ...     metric="ic",
        ...     reason="预测值全为NaN"
        ... )
    """
    pass


class InsufficientDataError(BaseInsufficientDataError):
    """数据不足错误（迁移到统一异常系统）

    当数据量不足以完成评估时抛出。

    Examples:
        >>> raise InsufficientDataError(
        ...     "评估数据不足",
        ...     error_code="INSUFFICIENT_EVAL_DATA",
        ...     required_samples=100,
        ...     actual_samples=50,
        ...     metric="sharpe_ratio"
        ... )
    """
    pass


class InvalidInputError(DataValidationError):
    """无效输入错误（迁移到统一异常系统）

    当输入数据格式或类型不正确时抛出。

    Examples:
        >>> raise InvalidInputError(
        ...     "预测值和真实值长度不匹配",
        ...     error_code="MISMATCHED_INPUT_LENGTH",
        ...     y_true_length=100,
        ...     y_pred_length=95
        ... )
    """
    pass
