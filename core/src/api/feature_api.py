"""
特征计算API - 使用统一返回格式

提供高层API接口用于特征计算，返回标准化的Response对象。

该模块封装了特征计算相关功能，并使用统一的Response格式返回结果，
便于错误处理和元信息传递。

Examples:
    >>> from src.api.feature_api import calculate_alpha_factors, calculate_technical_indicators
    >>>
    >>> # 计算Alpha因子
    >>> response = calculate_alpha_factors(data)
    >>> if response.is_success():
    ...     features = response.data
    ...     print(f"计算了 {response.metadata['n_features']} 个因子")
    ... else:
    ...     print(f"错误: {response.error}")
"""
import time
import pandas as pd
from typing import Optional

from src.features.alpha_factors import AlphaFactors
from src.features.technical_indicators import TechnicalIndicators
from src.utils.response import Response
from src.exceptions import (
    FeatureCalculationError,
    DataValidationError
)
from loguru import logger


def calculate_alpha_factors(
    data: pd.DataFrame,
    factor_names: Optional[list] = None,
    cache: bool = True
) -> Response:
    """计算Alpha因子（使用统一返回格式）

    Args:
        data: 股票OHLCV数据
        factor_names: 要计算的因子名称列表，None表示计算所有因子
        cache: 是否使用缓存

    Returns:
        Response对象:
            - 成功: data包含因子DataFrame, metadata包含统计信息
            - 失败: error包含错误消息, error_code标识错误类型

    Examples:
        >>> # 计算所有因子
        >>> resp = calculate_alpha_factors(stock_data)
        >>> if resp.is_success():
        ...     factors = resp.data
        ...     print(f"耗时: {resp.metadata['elapsed_time']}")

        >>> # 计算指定因子
        >>> resp = calculate_alpha_factors(
        ...     stock_data,
        ...     factor_names=['MOM_20', 'RSI_14']
        ... )
    """
    start_time = time.time()

    try:
        # 数据验证
        if data is None or data.empty:
            return Response.error(
                error="输入数据为空",
                error_code="EMPTY_DATA",
                input_type=type(data).__name__
            )

        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = set(required_columns) - set(data.columns)
        if missing_columns:
            return Response.error(
                error=f"缺少必需的列: {missing_columns}",
                error_code="MISSING_COLUMNS",
                required_columns=required_columns,
                available_columns=list(data.columns),
                missing_columns=list(missing_columns)
            )

        # 计算因子
        logger.info(f"开始计算Alpha因子, 数据行数: {len(data)}")
        alpha_calculator = AlphaFactors(data)

        if factor_names is None:
            # 计算所有因子
            features = alpha_calculator.calculate_all_alpha_factors()
        else:
            # 计算指定因子
            features = pd.DataFrame(index=data.index)
            for factor_name in factor_names:
                try:
                    factor_method = getattr(alpha_calculator, f'calculate_{factor_name.lower()}', None)
                    if factor_method:
                        features[factor_name] = factor_method()
                    else:
                        logger.warning(f"未找到因子计算方法: {factor_name}")
                except Exception as e:
                    logger.warning(f"计算因子 {factor_name} 失败: {str(e)}")

        elapsed_time = time.time() - start_time

        # 统计信息
        n_features = len(features.columns)
        n_samples = len(features)
        null_ratio = features.isnull().sum().sum() / (n_features * n_samples) if n_features * n_samples > 0 else 0

        # 检查是否有警告
        if null_ratio > 0.1:  # 超过10%的空值
            return Response.warning(
                message=f"计算完成，但存在较多空值 ({null_ratio:.1%})",
                data=features,
                n_features=n_features,
                n_samples=n_samples,
                null_ratio=f"{null_ratio:.2%}",
                elapsed_time=f"{elapsed_time:.2f}s",
                cache_enabled=cache
            )

        return Response.success(
            data=features,
            message="Alpha因子计算完成",
            n_features=n_features,
            n_samples=n_samples,
            null_ratio=f"{null_ratio:.2%}",
            elapsed_time=f"{elapsed_time:.2f}s",
            cache_enabled=cache
        )

    except FeatureCalculationError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"特征计算失败: {e.message}")
        return Response.error(
            error=e.message,
            error_code=e.error_code,
            elapsed_time=f"{elapsed_time:.2f}s",
            **e.context
        )

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.exception("Alpha因子计算发生未预期错误")
        return Response.error(
            error=f"计算失败: {str(e)}",
            error_code="UNEXPECTED_ERROR",
            exception_type=type(e).__name__,
            elapsed_time=f"{elapsed_time:.2f}s"
        )


def calculate_technical_indicators(
    data: pd.DataFrame,
    indicators: Optional[list] = None
) -> Response:
    """计算技术指标（使用统一返回格式）

    Args:
        data: 股票OHLCV数据
        indicators: 要计算的指标列表，None表示计算所有指标

    Returns:
        Response对象:
            - 成功: data包含添加了指标的DataFrame
            - 失败: error包含错误消息

    Examples:
        >>> # 计算所有技术指标
        >>> resp = calculate_technical_indicators(stock_data)
        >>> if resp.is_success():
        ...     data_with_indicators = resp.data
        ...     print(f"添加了 {resp.metadata['n_indicators']} 个指标")

        >>> # 计算指定指标
        >>> resp = calculate_technical_indicators(
        ...     stock_data,
        ...     indicators=['MA', 'MACD', 'RSI']
        ... )
    """
    start_time = time.time()

    try:
        # 数据验证
        if data is None or data.empty:
            return Response.error(
                error="输入数据为空",
                error_code="EMPTY_DATA"
            )

        # 计算指标
        logger.info(f"开始计算技术指标, 数据行数: {len(data)}")
        tech_calculator = TechnicalIndicators(data.copy())

        original_columns = len(data.columns)

        if indicators is None:
            # 计算所有指标
            result = tech_calculator.add_all_indicators()
        else:
            # 计算指定指标
            result = data.copy()
            for indicator in indicators:
                try:
                    method_name = f'add_{indicator.lower()}'
                    indicator_method = getattr(tech_calculator, method_name, None)
                    if indicator_method:
                        result = indicator_method()
                    else:
                        logger.warning(f"未找到指标计算方法: {indicator}")
                except Exception as e:
                    logger.warning(f"计算指标 {indicator} 失败: {str(e)}")

        elapsed_time = time.time() - start_time

        # 统计信息
        new_columns = len(result.columns)
        n_indicators = new_columns - original_columns

        return Response.success(
            data=result,
            message="技术指标计算完成",
            n_indicators=n_indicators,
            original_columns=original_columns,
            total_columns=new_columns,
            elapsed_time=f"{elapsed_time:.2f}s"
        )

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.exception("技术指标计算发生错误")
        return Response.error(
            error=f"计算失败: {str(e)}",
            error_code="INDICATOR_CALCULATION_ERROR",
            exception_type=type(e).__name__,
            elapsed_time=f"{elapsed_time:.2f}s"
        )


def validate_feature_data(data: pd.DataFrame) -> Response:
    """验证特征数据质量

    Args:
        data: 特征数据

    Returns:
        Response对象:
            - 成功: 数据质量良好
            - 警告: 数据质量有问题但可用
            - 错误: 数据质量严重问题

    Examples:
        >>> resp = validate_feature_data(features)
        >>> if resp.is_success():
        ...     print("数据质量良好")
        >>> elif resp.is_warning():
        ...     print(f"警告: {resp.message}")
        >>> else:
        ...     print(f"错误: {resp.error}")
    """
    try:
        if data is None or data.empty:
            return Response.error(
                error="数据为空",
                error_code="EMPTY_DATA"
            )

        issues = []
        warnings = []

        # 检查空值
        null_counts = data.isnull().sum()
        total_nulls = null_counts.sum()
        null_ratio = total_nulls / (len(data) * len(data.columns)) if len(data) * len(data.columns) > 0 else 0

        if null_ratio > 0.5:
            issues.append(f"空值比例过高: {null_ratio:.1%}")
        elif null_ratio > 0.1:
            warnings.append(f"存在一定比例空值: {null_ratio:.1%}")

        # 检查无穷值
        inf_count = 0
        for col in data.select_dtypes(include=['float', 'int']).columns:
            inf_count += data[col].isin([float('inf'), float('-inf')]).sum()

        if inf_count > 0:
            issues.append(f"存在 {inf_count} 个无穷值")

        # 检查常数列
        constant_cols = [col for col in data.columns if data[col].nunique() <= 1]
        if len(constant_cols) > 0:
            warnings.append(f"存在 {len(constant_cols)} 个常数列")

        # 检查数据类型
        non_numeric_cols = data.select_dtypes(exclude=['number']).columns.tolist()
        if len(non_numeric_cols) > 0:
            warnings.append(f"存在 {len(non_numeric_cols)} 个非数值列")

        # 返回结果
        if issues:
            return Response.error(
                error="数据质量检查失败",
                error_code="DATA_QUALITY_ERROR",
                issues=issues,
                warnings=warnings,
                null_ratio=f"{null_ratio:.2%}",
                inf_count=inf_count,
                constant_columns=constant_cols,
                non_numeric_columns=non_numeric_cols
            )
        elif warnings:
            return Response.warning(
                message="数据质量检查通过，但存在一些警告",
                data={'passed': True},
                warnings=warnings,
                null_ratio=f"{null_ratio:.2%}",
                constant_columns=constant_cols,
                non_numeric_columns=non_numeric_cols
            )
        else:
            return Response.success(
                data={'passed': True},
                message="数据质量检查通过",
                null_ratio=f"{null_ratio:.2%}",
                n_features=len(data.columns),
                n_samples=len(data)
            )

    except Exception as e:
        logger.exception("数据验证发生错误")
        return Response.error(
            error=f"验证失败: {str(e)}",
            error_code="VALIDATION_ERROR",
            exception_type=type(e).__name__
        )
