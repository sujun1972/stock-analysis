"""
Pytest配置文件

确保测试可以正确导入src模块，并提供Response对象测试辅助函数
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent.parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# ============================================================================
# Response对象测试辅助函数
# ============================================================================

def unwrap_response(response):
    """
    解包Response对象，返回data

    用于简化测试中Response对象的处理，自动验证操作是否成功并提取数据。

    Args:
        response: Response对象

    Returns:
        response.data的内容

    Raises:
        AssertionError: 如果Response表示失败

    Example:
        >>> loaded_df = unwrap_response(storage.load_features('000001', 'alpha'))
        >>> # 等价于:
        >>> # response = storage.load_features('000001', 'alpha')
        >>> # assert response.is_success(), f"操作失败: {response.error_message}"
        >>> # loaded_df = response.data
    """
    assert response.is_success(), f"操作失败: {response.error_message}"
    return response.data


def unwrap_prepare_data(response):
    """
    解包prepare_data的Response对象，返回拆分后的数据集元组

    专门用于ModelTrainer.prepare_data()方法的返回值处理。

    Args:
        response: prepare_data返回的Response对象

    Returns:
        (X_train, y_train, X_valid, y_valid, X_test, y_test): 拆分后的训练、验证和测试数据集

    Raises:
        AssertionError: 如果Response表示失败

    Example:
        >>> X_train, y_train, X_valid, y_valid, X_test, y_test = unwrap_prepare_data(
        ...     trainer.prepare_data(df, feature_cols, target_col)
        ... )
    """
    assert response.is_success(), f"数据准备失败: {response.error_message}"
    data = response.data
    return (
        data['X_train'], data['y_train'],
        data['X_valid'], data['y_valid'],
        data['X_test'], data['y_test']
    )
