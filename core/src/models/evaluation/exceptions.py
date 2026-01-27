"""
评估模块异常类定义
"""


class EvaluationError(Exception):
    """评估过程错误基类"""
    pass


class InsufficientDataError(EvaluationError):
    """数据不足错误"""
    pass


class InvalidInputError(EvaluationError):
    """无效输入错误"""
    pass
