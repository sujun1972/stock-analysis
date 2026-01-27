"""
评估模块装饰器
"""
import numpy as np
from functools import wraps
from loguru import logger

from .exceptions import InvalidInputError, InsufficientDataError


def validate_input_arrays(func):
    """
    验证输入数组的装饰器
    - 检查是否为 None
    - 检查长度是否一致
    - 检查是否有足够的数据
    """
    @wraps(func)
    def wrapper(self, predictions: np.ndarray, actual_returns: np.ndarray, *args, **kwargs):
        # 检查 None
        if predictions is None or actual_returns is None:
            raise InvalidInputError("预测值或实际收益率为 None")

        # 转换为 numpy 数组
        predictions = np.asarray(predictions)
        actual_returns = np.asarray(actual_returns)

        # 检查长度
        if len(predictions) != len(actual_returns):
            raise InvalidInputError(
                f"预测值和实际收益率长度不一致: {len(predictions)} vs {len(actual_returns)}"
            )

        # 检查数据量
        if len(predictions) == 0:
            raise InsufficientDataError("输入数据为空")

        return func(self, predictions, actual_returns, *args, **kwargs)

    return wrapper


def safe_compute(metric_name: str, default_value=np.nan):
    """
    安全计算装饰器，捕获并记录异常

    Args:
        metric_name: 指标名称
        default_value: 出错时的默认返回值
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # 只对数值类型检查 NaN 和 Inf
                if isinstance(result, (int, float, np.number)):
                    if np.isnan(result) or np.isinf(result):
                        logger.warning(f"{metric_name} 计算结果为 NaN 或 Inf")
                return result
            except Exception as e:
                logger.error(f"计算 {metric_name} 时出错: {str(e)}")
                return default_value
        return wrapper
    return decorator
