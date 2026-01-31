# 统一API返回格式使用指南

## 📋 概述

本指南说明如何在core项目中使用统一的`Response`类构建标准化API。Response类提供一致的返回格式，支持成功、错误和警告三种状态，便于错误处理和元数据传递。

## 🎯 何时使用Response格式

### ✅ 应该使用

- **新的API函数** - 所有新开发的高层API函数
- **特征计算接口** - `calculate_alpha_factors()`, `calculate_technical_indicators()`
- **数据验证函数** - `validate_feature_data()`, `validate_ohlcv_data()`
- **回测接口** - `run_backtest()`, `optimize_parameters()`
- **模型训练接口** - `train_model()`, `evaluate_model()`
- **需要传递元数据** - 执行时间、统计信息、警告消息等

### ❌ 不需要使用

- **底层工具函数** - 简单的计算函数（如`rolling_mean()`）
- **内部辅助函数** - 仅在模块内部使用的函数
- **数据转换函数** - 简单的数据格式转换
- **已有的稳定API** - 除非需要重构

## 📖 基本使用

### 1. 导入Response类

```python
from src.utils.response import Response, ResponseStatus
# 或使用便捷函数
from src.utils.response import success, error, warning
# 或从utils直接导入
from src.utils import Response, success, error, warning
```

### 2. 创建成功响应

```python
def calculate_alpha_factors(data: pd.DataFrame) -> Response:
    """计算Alpha因子

    Returns:
        Response: 包含features DataFrame的成功响应
    """
    start_time = time.time()

    try:
        # 执行计算
        features = AlphaFactors(data).calculate_all_alpha_factors()
        elapsed = time.time() - start_time

        # 返回成功响应，带元数据
        return Response.success(
            data=features,
            message="Alpha因子计算完成",
            n_features=len(features.columns),
            n_samples=len(features),
            elapsed_time=f"{elapsed:.2f}s",
            cache_hit=False
        )
    except Exception as e:
        return Response.error(
            error=f"计算失败: {str(e)}",
            error_code="CALCULATION_ERROR"
        )
```

### 3. 创建错误响应

```python
def validate_stock_code(code: str) -> Response:
    """验证股票代码

    Returns:
        Response: 验证结果
    """
    # 空值检查
    if not code or len(code.strip()) == 0:
        return Response.error(
            error="股票代码不能为空",
            error_code="EMPTY_STOCK_CODE",
            field="stock_code",
            value=code,
            validator="validate_stock_code"
        )

    # 长度检查
    if len(code) != 6:
        return Response.error(
            error=f"股票代码必须是6位数字，实际长度: {len(code)}",
            error_code="INVALID_CODE_LENGTH",
            field="stock_code",
            value=code,
            expected_length=6,
            actual_length=len(code)
        )

    # 验证通过
    return Response.success(
        data={'valid': True, 'code': code},
        message="股票代码验证通过"
    )
```

### 4. 创建警告响应

```python
def process_data_with_fallback(data: pd.DataFrame) -> Response:
    """处理数据，有缺失时使用回退策略

    Returns:
        Response: 处理结果，可能包含警告
    """
    # 检查数据质量
    null_ratio = data.isnull().sum().sum() / (len(data) * len(data.columns))

    # 填充缺失值
    processed = data.fillna(method='ffill')

    # 如果缺失较多，返回警告
    if null_ratio > 0.1:
        return Response.warning(
            message=f"数据存在较多缺失值 ({null_ratio:.1%}), 已使用前向填充",
            data=processed,
            null_ratio=f"{null_ratio:.2%}",
            fill_method="forward",
            original_nulls=int(data.isnull().sum().sum())
        )

    # 正常情况返回成功
    return Response.success(
        data=processed,
        message="数据处理完成",
        null_ratio=f"{null_ratio:.2%}"
    )
```

## 🔍 处理响应

### 基本模式

```python
# 调用API
response = calculate_alpha_factors(stock_data)

# 检查状态并处理
if response.is_success():
    features = response.data
    print(f"✓ 成功: {response.message}")
    print(f"  计算了 {response.metadata['n_features']} 个因子")
    print(f"  耗时: {response.metadata['elapsed_time']}")

elif response.is_warning():
    features = response.data  # 警告状态仍有数据
    print(f"⚠ 警告: {response.message}")
    for key, value in response.metadata.items():
        print(f"  {key}: {value}")

else:  # is_error()
    print(f"✗ 错误: {response.error_message}")
    print(f"  错误代码: {response.error_code}")
    # 输出上下文信息
    for key, value in response.metadata.items():
        print(f"  {key}: {value}")
```

### 链式调用模式

```python
def full_pipeline(stock_code: str) -> Response:
    """完整的数据处理流程"""

    # 步骤1: 获取数据
    data_response = fetch_stock_data(stock_code)
    if not data_response.is_success():
        return data_response  # 直接返回错误

    # 步骤2: 计算特征
    feature_response = calculate_features(data_response.data)
    if not feature_response.is_success():
        return feature_response  # 直接返回错误

    # 步骤3: 运行回测
    backtest_response = run_backtest(feature_response.data)

    # 返回最终结果
    return backtest_response
```

## 💡 最佳实践

### 1. 一致的错误代码命名

使用大写下划线命名，语义清晰：

```python
# ✅ 好的做法
Response.error(error="...", error_code="DATA_VALIDATION_ERROR")
Response.error(error="...", error_code="FILE_NOT_FOUND")
Response.error(error="...", error_code="API_REQUEST_TIMEOUT")
Response.error(error="...", error_code="INSUFFICIENT_DATA")

# ❌ 不好的做法
Response.error(error="...", error_code="error1")
Response.error(error="...", error_code="err")
Response.error(error="...", error_code="dataValidationError")
```

### 2. 提供丰富的元数据

元数据帮助调试和监控：

```python
# ✅ 好的做法
Response.success(
    data=results,
    message="回测完成",
    strategy="MomentumStrategy",
    period="2024-01-01至2024-12-31",
    total_trades=150,
    sharpe_ratio=1.52,
    max_drawdown=-0.15,
    execution_time="5.2s"
)

# ❌ 不好的做法
Response.success(data=results)  # 缺少有用信息
```

### 3. 错误时提供上下文

帮助定位问题：

```python
# ✅ 好的做法
Response.error(
    error="API请求失败",
    error_code="API_REQUEST_FAILED",
    provider="akshare",
    stock_code="000001",
    url="https://api.example.com/stock/000001",
    retry_count=3,
    last_error="Connection timeout",
    status_code=504
)

# ❌ 不好的做法
Response.error(error="请求失败")  # 信息不足
```

### 4. 合理使用警告状态

当操作完成但有需要注意的情况时使用警告：

```python
# ✅ 好的做法
if data_quality_score < 0.8:
    return Response.warning(
        message="数据质量较低，结果可能不可靠",
        data=results,
        quality_score=data_quality_score,
        issues=["缺失值过多", "异常值检测到"],
        recommendation="建议检查数据源"
    )

# ❌ 不好的做法
# 要么完全忽略质量问题，要么直接报错
```

### 5. 消息应该人类可读

```python
# ✅ 好的做法
Response.error(
    error="数据时间范围不足，需要至少120个交易日，实际只有45��",
    error_code="INSUFFICIENT_DATA_RANGE"
)

# ❌ 不好的做法
Response.error(
    error="err: data < 120",  # 不够清晰
    error_code="ERR001"
)
```

## 🎨 实际示例

### 示例1: 特征计算API

```python
import time
import pandas as pd
from src.utils.response import Response
from src.features.alpha_factors import AlphaFactors
from src.exceptions import FeatureCalculationError

def calculate_alpha_factors(
    data: pd.DataFrame,
    factor_names: list = None
) -> Response:
    """计算Alpha因子

    Args:
        data: OHLCV数据
        factor_names: 要计算的因子列表，None表示全部

    Returns:
        Response: 包含因子DataFrame和元数据的响应
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

        required = ['open', 'high', 'low', 'close', 'volume']
        missing = set(required) - set(data.columns)
        if missing:
            return Response.error(
                error=f"缺少必需的列: {missing}",
                error_code="MISSING_COLUMNS",
                required_columns=required,
                missing_columns=list(missing),
                available_columns=list(data.columns)
            )

        # 计算因子
        calculator = AlphaFactors(data)
        if factor_names is None:
            features = calculator.calculate_all_alpha_factors()
        else:
            features = calculator.calculate_factors(factor_names)

        elapsed = time.time() - start_time

        # 检查数据质量
        null_ratio = features.isnull().sum().sum() / features.size

        if null_ratio > 0.1:
            return Response.warning(
                message=f"计算完成，但存在较多空值 ({null_ratio:.1%})",
                data=features,
                n_features=len(features.columns),
                n_samples=len(features),
                null_ratio=f"{null_ratio:.2%}",
                elapsed_time=f"{elapsed:.2f}s"
            )

        return Response.success(
            data=features,
            message="Alpha因子计算完成",
            n_features=len(features.columns),
            n_samples=len(features),
            null_ratio=f"{null_ratio:.2%}",
            elapsed_time=f"{elapsed:.2f}s"
        )

    except FeatureCalculationError as e:
        return Response.error(
            error=e.message,
            error_code=e.error_code,
            elapsed_time=f"{time.time() - start_time:.2f}s",
            **e.context
        )
    except Exception as e:
        return Response.error(
            error=f"未预期的错误: {str(e)}",
            error_code="UNEXPECTED_ERROR",
            exception_type=type(e).__name__,
            elapsed_time=f"{time.time() - start_time:.2f}s"
        )
```

### 示例2: 数据验证API

```python
from src.utils.response import Response

def validate_feature_data(data: pd.DataFrame) -> Response:
    """验证特征数据质量

    Args:
        data: 特征数据

    Returns:
        Response: 验证结果（success/warning/error）
    """
    if data is None or data.empty:
        return Response.error(
            error="数据为空",
            error_code="EMPTY_DATA"
        )

    issues = []
    warnings = []

    # 检查空值
    null_ratio = data.isnull().sum().sum() / data.size
    if null_ratio > 0.5:
        issues.append(f"空值比例过高: {null_ratio:.1%}")
    elif null_ratio > 0.1:
        warnings.append(f"存在一定比例空值: {null_ratio:.1%}")

    # 检查无穷值
    inf_count = data.isin([float('inf'), float('-inf')]).sum().sum()
    if inf_count > 0:
        issues.append(f"存在 {inf_count} 个无穷值")

    # 检查常数列
    constant_cols = [col for col in data.columns if data[col].nunique() <= 1]
    if len(constant_cols) > 0:
        warnings.append(f"存在 {len(constant_cols)} 个常数列")

    # 返回结果
    if issues:
        return Response.error(
            error="数据质量检查失败",
            error_code="DATA_QUALITY_ERROR",
            issues=issues,
            warnings=warnings,
            null_ratio=f"{null_ratio:.2%}",
            inf_count=inf_count,
            constant_columns=constant_cols
        )
    elif warnings:
        return Response.warning(
            message="数据质量检查通过，但存在警告",
            data={'passed': True},
            warnings=warnings,
            null_ratio=f"{null_ratio:.2%}",
            constant_columns=constant_cols
        )
    else:
        return Response.success(
            data={'passed': True},
            message="数据质量检查通过",
            null_ratio=f"{null_ratio:.2%}",
            n_features=len(data.columns),
            n_samples=len(data)
        )
```

### 示例3: 回测API

```python
from src.utils.response import Response
from src.backtest import BacktestEngine
from src.strategies import MomentumStrategy

def run_backtest(
    prices: pd.DataFrame,
    features: pd.DataFrame,
    strategy_name: str = 'momentum',
    **strategy_params
) -> Response:
    """运行策略回测

    Args:
        prices: 价格数据
        features: 特征数据
        strategy_name: 策略名称
        **strategy_params: 策略参数

    Returns:
        Response: 回测结果和性能指标
    """
    start_time = time.time()

    try:
        # 创建策略
        if strategy_name == 'momentum':
            strategy = MomentumStrategy(**strategy_params)
        else:
            return Response.error(
                error=f"不支持的策略: {strategy_name}",
                error_code="UNSUPPORTED_STRATEGY",
                strategy_name=strategy_name,
                available_strategies=['momentum', 'mean_reversion', 'multi_factor']
            )

        # 生成信号
        signals = strategy.generate_signals(prices, features)

        # 运行回测
        engine = BacktestEngine(initial_capital=1_000_000)
        results = engine.backtest_long_only(signals, prices)

        elapsed = time.time() - start_time

        # 检查结果质量
        if results['total_trades'] < 10:
            return Response.warning(
                message="回测完成，但交易次数过少，结果可能不可靠",
                data=results,
                total_trades=results['total_trades'],
                min_recommended_trades=30,
                elapsed_time=f"{elapsed:.2f}s"
            )

        return Response.success(
            data=results,
            message="回测完成",
            strategy=strategy_name,
            period=f"{prices.index[0]} 至 {prices.index[-1]}",
            total_trades=results['total_trades'],
            sharpe_ratio=results['sharpe_ratio'],
            annualized_return=results['annualized_return'],
            max_drawdown=results['max_drawdown'],
            elapsed_time=f"{elapsed:.2f}s"
        )

    except Exception as e:
        return Response.error(
            error=f"回测失败: {str(e)}",
            error_code="BACKTEST_ERROR",
            strategy=strategy_name,
            exception_type=type(e).__name__,
            elapsed_time=f"{time.time() - start_time:.2f}s"
        )
```

## 📊 转换为字典（用于JSON API）

```python
# API endpoint示例
from flask import jsonify

@app.route('/api/features/<stock_code>')
def get_features(stock_code):
    # 获取数据
    data = fetch_data(stock_code)

    # 计算特征
    response = calculate_alpha_factors(data)

    # 转换为字典并返回JSON
    return jsonify(response.to_dict())

# 返回格式:
# {
#   "status": "success",
#   "message": "Alpha因子计算完成",
#   "data": {...},
#   "metadata": {
#     "n_features": 125,
#     "elapsed_time": "2.5s"
#   }
# }
```

## 🔄 与异常系统集成

Response类与异常系统完美配合：

```python
from src.utils.response import Response
from src.utils.error_handling import handle_errors, retry_on_error
from src.exceptions import DataProviderError, FeatureCalculationError

@retry_on_error(max_attempts=3, delay=1.0)
def fetch_stock_data(code: str) -> Response:
    """获取股票数据（带重试）"""
    try:
        data = provider.get_daily_data(code)
        return Response.success(
            data=data,
            message="数据获取成功",
            stock_code=code,
            n_records=len(data)
        )
    except DataProviderError as e:
        return Response.error(
            error=e.message,
            error_code=e.error_code,
            **e.context
        )

# 使用
response = fetch_stock_data("000001")
if response.is_success():
    data = response.data
```

## 📝 检查清单

在编写API时，确保：

- [ ] 导入了Response类
- [ ] 函数返回类型标注为`-> Response`
- [ ] 成功情况使用`Response.success()`
- [ ] 错误情况使用`Response.error()`，包含error_code
- [ ] 警告情况使用`Response.warning()`
- [ ] 提供了有意义的message
- [ ] 添加了有用的元数据（执行时间、统计信息等）
- [ ] 错误时提供了足够的上下文信息
- [ ] 错误代码使用大写下划线命名
- [ ] 编写了测试用例验证各种响应状态

## 🚀 下一步

1. 查看现有API示例: `src/api/feature_api.py`
2. 查看单元测试: `tests/unit/utils/test_response.py`
3. 参考异常处理skill: `.claude/skills/exception-handling.md`
4. 开始将现有API逐步迁移到Response格式

## 📚 相关资源

- Response类源码: `src/utils/response.py`
- API示例: `src/api/feature_api.py`
- 异常系统: `src/exceptions.py`
- 错误处理工具: `src/utils/error_handling.py`

---

**版本**: 1.0.0
**创建日期**: 2026-01-31
**维护者**: Stock Analysis Team
