"""
数据加载API - 使用统一返回格式

提供高层API接口用于数据加载、验证和清洗，返回标准化的Response对象。

该模块封装了数据管理相关功能，并使用统一的Response格式返回结果，
便于错误处理和元信息传递。

Examples:
    >>> from src.api.data_api import load_stock_data, validate_stock_data, clean_stock_data
    >>>
    >>> # 加载股票数据
    >>> response = load_stock_data('000001', '20240101', '20241231')
    >>> if response.is_success():
    ...     data = response.data
    ...     print(f"加载了 {response.metadata['n_records']} 条记录")
    ... else:
    ...     print(f"错误: {response.error_message}")
    >>>
    >>> # 验证数据质量
    >>> response = validate_stock_data(data)
    >>> if response.is_success():
    ...     print("数据质量良好")
    >>> elif response.is_warning():
    ...     print(f"警告: {response.message}")
    >>>
    >>> # 清洗数据
    >>> response = clean_stock_data(data, '000001')
    >>> if response.is_success():
    ...     cleaned_data = response.data
    ...     print(f"清洗统计: {response.metadata['cleaning_stats']}")
"""
import time
import pandas as pd
from typing import Optional
from loguru import logger

# Lazy imports to avoid dependency issues
# from src.data_pipeline.data_loader import DataLoader
# from src.data.data_validator import DataValidator
# from src.data.data_cleaner import DataCleaner
from src.utils.response import Response
from src.exceptions import (
    DataError,
    DataNotFoundError,
    DataValidationError
)


def load_stock_data(
    symbol: str,
    start_date: str,
    end_date: str,
    validate: bool = True
) -> Response:
    """加载股票数据（使用统一返回格式）

    从数据库加载指定股票的历史行情数据，支持自动验证。

    Args:
        symbol: 股票代码（如'000001'）
        start_date: 开始日期（格式：YYYYMMDD）
        end_date: 结束日期（格式：YYYYMMDD）
        validate: 是否自动验证数据质量，默认True

    Returns:
        Response对象:
            - 成功: data包含OHLCV DataFrame, metadata包含统计信息
            - 失败: error包含错误消息, error_code标识错误类型

    Examples:
        >>> # 加载股票数据
        >>> resp = load_stock_data('000001', '20240101', '20241231')
        >>> if resp.is_success():
        ...     data = resp.data
        ...     print(f"加载 {resp.metadata['n_records']} 条记录")
        ...     print(f"日期范围: {resp.metadata['date_range']}")

        >>> # 加载并跳过验证
        >>> resp = load_stock_data('000001', '20240101', '20241231', validate=False)
        >>> if resp.is_success():
        ...     data = resp.data
    """
    # 参数验证（在导入之前，避免不必要的依赖加载）
    if not symbol or not symbol.strip():
        return Response.error(
            error="股票代码不能为空",
            error_code="EMPTY_SYMBOL",
            symbol=symbol
        )

    if not start_date or not end_date:
        return Response.error(
            error="开始日期和结束日期不能为空",
            error_code="EMPTY_DATE",
            start_date=start_date,
            end_date=end_date
        )

    # 验证日期格式
    if len(start_date) != 8 or len(end_date) != 8:
        return Response.error(
            error="日期格式错误，应为YYYYMMDD格式",
            error_code="INVALID_DATE_FORMAT",
            start_date=start_date,
            end_date=end_date
        )

    start_time = time.time()

    try:
        # Lazy import to avoid dependency issues
        from src.data_pipeline.data_loader import DataLoader
        from src.data.data_validator import DataValidator

        # 加载数据
        logger.info(f"开始加载股票数据: {symbol} ({start_date} ~ {end_date})")
        loader = DataLoader()

        df = loader.load_data(symbol, start_date, end_date)

        if df is None or df.empty:
            return Response.error(
                error=f"未找到股票数据: {symbol}",
                error_code="DATA_NOT_FOUND",
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )

        elapsed_time = time.time() - start_time

        # 统计信息
        n_records = len(df)
        date_range = f"{df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}"
        columns = list(df.columns)

        # 自动验证数据质量
        validation_result = None
        if validate:
            validator = DataValidator(df)
            validation_result = validator.validate_all(strict_mode=False)

            # 如果验证失败，返回警告
            if not validation_result['passed']:
                return Response.warning(
                    message=f"数据加载完成，但存在质量问题（错误: {validation_result['summary']['error_count']}）",
                    data=df,
                    symbol=symbol,
                    n_records=n_records,
                    date_range=date_range,
                    columns=columns,
                    elapsed_time=f"{elapsed_time:.2f}s",
                    validation_errors=validation_result['errors'],
                    validation_warnings=validation_result['warnings']
                )

        # 成功返回
        metadata = {
            'symbol': symbol,
            'n_records': n_records,
            'date_range': date_range,
            'columns': columns,
            'elapsed_time': f"{elapsed_time:.2f}s"
        }

        if validation_result:
            metadata['validation_passed'] = validation_result['passed']
            metadata['validation_warnings'] = len(validation_result['warnings'])

        return Response.success(
            data=df,
            message=f"成功加载股票数据: {symbol}",
            **metadata
        )

    except DataNotFoundError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"股票数据未找到: {symbol}")
        return Response.error(
            error=str(e),
            error_code="DATA_NOT_FOUND",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            elapsed_time=f"{elapsed_time:.2f}s"
        )

    except DataError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"数据加载失败: {e}")
        return Response.error(
            error=str(e),
            error_code="DATA_LOAD_ERROR",
            symbol=symbol,
            elapsed_time=f"{elapsed_time:.2f}s"
        )

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.exception("数据加载发生未预期错误")
        return Response.error(
            error=f"数据加载失败: {str(e)}",
            error_code="UNEXPECTED_ERROR",
            exception_type=type(e).__name__,
            symbol=symbol,
            elapsed_time=f"{elapsed_time:.2f}s"
        )


def validate_stock_data(
    data: pd.DataFrame,
    strict_mode: bool = False,
    required_fields: Optional[list] = None
) -> Response:
    """验证股票数据质量（使用统一返回格式）

    对股票OHLCV数据进行全面的质量检查，包括必需字段、数据类型、
    价格逻辑、日期连续性、数值范围和缺失值等。

    Args:
        data: 待验证的股票数据DataFrame
        strict_mode: 严格模式，警告也视为失败，默认False
        required_fields: 必需字段列表，None表示使用默认['close']

    Returns:
        Response对象:
            - 成功: 数据质量良好，metadata包含详细统计
            - 警告: 数据可用但有问题，metadata包含警告信息
            - 错误: 数据质量严重问题，无法使用

    Examples:
        >>> # 验证数据质量
        >>> resp = validate_stock_data(data)
        >>> if resp.is_success():
        ...     print("数据质量良好")
        >>> elif resp.is_warning():
        ...     print(f"警告: {resp.message}")
        ...     print(f"警告数量: {resp.metadata['warning_count']}")
        >>> else:
        ...     print(f"错误: {resp.error_message}")

        >>> # 严格模式验证
        >>> resp = validate_stock_data(data, strict_mode=True)

        >>> # 指定必需字段
        >>> resp = validate_stock_data(data, required_fields=['open', 'high', 'low', 'close', 'volume'])
    """
    try:
        # Lazy import to avoid dependency issues
        from src.data.data_validator import DataValidator

        # 基本检查
        if data is None or data.empty:
            return Response.error(
                error="数据为空，无法验证",
                error_code="EMPTY_DATA"
            )

        logger.info(f"开始验证数据质量: {len(data)} 行 x {len(data.columns)} 列")

        # 创建验证器并执行验证
        validator = DataValidator(
            data,
            required_fields=required_fields
        )

        validation_results = validator.validate_all(
            strict_mode=strict_mode,
            allow_date_gaps=True,
            max_missing_rate=0.5
        )

        # 解析验证结果
        passed = validation_results['passed']
        errors = validation_results['errors']
        warnings = validation_results['warnings']
        stats = validation_results.get('stats', {})
        summary = validation_results.get('summary', {})

        # 构建元数据
        metadata = {
            'n_records': summary.get('total_records', len(data)),
            'n_columns': summary.get('total_columns', len(data.columns)),
            'error_count': summary.get('error_count', len(errors)),
            'warning_count': summary.get('warning_count', len(warnings)),
            'strict_mode': strict_mode
        }

        # 添加详细统计
        if 'missing_values' in stats:
            metadata['missing_values'] = stats['missing_values']

        if 'duplicate_records' in stats:
            metadata['duplicate_count'] = stats['duplicate_records']

        if 'price_logic_errors' in stats:
            metadata['price_logic_errors'] = stats['price_logic_errors']

        # 根据结果返回不同状态
        if not passed:
            return Response.error(
                error="数据质量验证失败",
                error_code="DATA_VALIDATION_FAILED",
                errors=errors,
                warnings=warnings,
                **metadata
            )

        elif warnings:
            return Response.warning(
                message=f"数据质量验证通过，但存在 {len(warnings)} 个警告",
                data={'passed': True},
                warnings=warnings,
                **metadata
            )

        else:
            return Response.success(
                data={'passed': True},
                message="数据质量验证完全通过",
                **metadata
            )

    except DataValidationError as e:
        logger.error(f"数据验证失败: {e}")
        return Response.error(
            error=str(e),
            error_code="VALIDATION_ERROR"
        )

    except Exception as e:
        logger.exception("数据验证发生未预期错误")
        return Response.error(
            error=f"验证失败: {str(e)}",
            error_code="UNEXPECTED_ERROR",
            exception_type=type(e).__name__
        )


def clean_stock_data(
    data: pd.DataFrame,
    symbol: str = 'unknown',
    fix_ohlc: bool = True,
    add_features: bool = False
) -> Response:
    """清洗股票数据（使用统一返回格式）

    对股票数据进行清洗处理，包括移除重复值、处理缺失值、移除异常值、
    修复OHLC逻辑等。

    Args:
        data: 待清洗的股票数据DataFrame
        symbol: 股票代码（用于日志），默认'unknown'
        fix_ohlc: 是否修复OHLC逻辑，默认True
        add_features: 是否添加基础特征（涨跌幅、振幅等），默认False

    Returns:
        Response对象:
            - 成功: data包含清洗后的DataFrame, metadata包含清洗统计
            - 警告: 清洗完成但移除了较多数据
            - 失败: 清洗失败或数据质量太差

    Examples:
        >>> # 清洗股票数据
        >>> resp = clean_stock_data(data, '000001')
        >>> if resp.is_success():
        ...     cleaned = resp.data
        ...     stats = resp.metadata['cleaning_stats']
        ...     print(f"原始行数: {stats['total_rows']}")
        ...     print(f"清洗后行数: {stats['final_rows']}")

        >>> # 清洗并修复OHLC + 添加特征
        >>> resp = clean_stock_data(data, '000001', fix_ohlc=True, add_features=True)

        >>> # 检查是否有警告
        >>> if resp.is_warning():
        ...     print(f"警告: {resp.message}")
        ...     print(f"移除比例: {resp.metadata['removal_rate']}")
    """
    start_time = time.time()

    try:
        # Lazy import to avoid dependency issues
        from src.data.data_cleaner import DataCleaner

        # 基本检查
        if data is None or data.empty:
            return Response.error(
                error="数据为空，无法清洗",
                error_code="EMPTY_DATA",
                symbol=symbol
            )

        logger.info(f"开始清洗数据: {symbol}, 原始行数 {len(data)}")

        original_rows = len(data)
        original_columns = len(data.columns)

        # 创建清洗器并清洗数据
        cleaner = DataCleaner(verbose=False)
        cleaned_data = cleaner.clean_price_data(data, symbol)

        # 修复OHLC逻辑
        if fix_ohlc and all(col in cleaned_data.columns for col in ['open', 'high', 'low', 'close']):
            cleaned_data = cleaner.validate_ohlc(cleaned_data, fix=True)

        # 添加基础特征
        if add_features:
            cleaned_data = cleaner.add_basic_features(cleaned_data)

        elapsed_time = time.time() - start_time

        # 获取清洗统计
        cleaning_stats = cleaner.get_stats()
        final_rows = len(cleaned_data)
        final_columns = len(cleaned_data.columns)
        removal_rate = (original_rows - final_rows) / original_rows if original_rows > 0 else 0

        # 构建元数据
        metadata = {
            'symbol': symbol,
            'original_rows': original_rows,
            'original_columns': original_columns,
            'final_rows': final_rows,
            'final_columns': final_columns,
            'rows_removed': original_rows - final_rows,
            'removal_rate': f"{removal_rate:.2%}",
            'cleaning_stats': cleaning_stats,
            'ohlc_fixed': fix_ohlc,
            'features_added': add_features,
            'elapsed_time': f"{elapsed_time:.2f}s"
        }

        # 检查是否移除了过多数据
        if removal_rate > 0.3:  # 超过30%
            return Response.warning(
                message=f"数据清洗完成，但移除了 {removal_rate:.1%} 的数据",
                data=cleaned_data,
                **metadata
            )

        # 检查清洗后数据是否太少
        if final_rows < 10:
            return Response.warning(
                message=f"数据清洗完成，但剩余数据仅有 {final_rows} 行",
                data=cleaned_data,
                **metadata
            )

        # 成功返回
        return Response.success(
            data=cleaned_data,
            message=f"数据清洗完成: {symbol}",
            **metadata
        )

    except DataError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"数据清洗失败: {e}")
        return Response.error(
            error=str(e),
            error_code="DATA_CLEANING_ERROR",
            symbol=symbol,
            elapsed_time=f"{elapsed_time:.2f}s"
        )

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.exception("数据清洗发生未预期错误")
        return Response.error(
            error=f"清洗失败: {str(e)}",
            error_code="UNEXPECTED_ERROR",
            exception_type=type(e).__name__,
            symbol=symbol,
            elapsed_time=f"{elapsed_time:.2f}s"
        )
