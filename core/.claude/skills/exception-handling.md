# Exception Handling Skill

**作用**: 指导如何在core项目中正确使用统一异常处理系统

**适用范围**: 所有新代码开发、代码重构、错误处理改进

---

## 📚 统一异常系统概述

core项目已建立完整的异常处理系统：
- **基础模块**: `src/exceptions.py` (30+异常类)
- **工具模块**: `src/utils/error_handling.py` (4个装饰器)
- **已迁移模块**: Providers、Features、Models、Utils (24个异常类)

---

## 🎯 使用原则

### 1. 选择合适的异常类

**按业务领域选择异常基类**:

```python
# ✅ 数据相关 - 使用 DataError 系列
from src.exceptions import (
    DataError,              # 数据相关异常基类
    DataNotFoundError,      # 数据不存在
    DataValidationError,    # 数据验证失败
    DataProviderError,      # 数据提供者错误
    InsufficientDataError,  # 数据不足
)

# ✅ 特征工程 - 使用 FeatureError 系列
from src.exceptions import (
    FeatureError,              # 特征相关基类
    FeatureCalculationError,   # 特征计算错误
    FeatureStorageError,       # 特征存储错误
    FeatureCacheError,         # 特征缓存错误
)

# ✅ 模型相关 - 使用 ModelError 系列
from src.exceptions import (
    ModelError,              # 模型相关基类
    ModelTrainingError,      # 模型训练错误
    ModelPredictionError,    # 模型预测错误
    ModelNotFoundError,      # 模型不存在
    ModelValidationError,    # 模型验证错误
)

# ✅ 策略和回测 - 使用 StrategyError/BacktestError
from src.exceptions import (
    StrategyError,           # 策略相关基类
    SignalGenerationError,   # 信号生成错误
    BacktestError,           # 回测相关基类
    BacktestExecutionError,  # 回测执行错误
)

# ✅ 配置相关 - 使用 ConfigError 系列
from src.exceptions import (
    ConfigError,                # 配置相关基类
    ConfigValidationError,      # 配置验证错误
    ConfigFileNotFoundError,    # 配置文件不存在
)

# ✅ 风险管理 - 使用 RiskManagementError 系列
from src.exceptions import (
    RiskManagementError,      # 风险管理基类
    RiskLimitExceededError,   # 风险限制超出
    DrawdownExceededError,    # 回撤超限
)

# ✅ 数据库相关 - 使用 DatabaseError 系列
from src.exceptions import (
    DatabaseError,              # 数据库基类
    DatabaseConnectionError,    # 连接错误
    QueryError,                 # 查询错误
)
```

### 2. 正确抛出异常

**推荐用法** (使用error_code和context):

```python
# ✅ 完整示例：包含错误代码和上下文
raise DataValidationError(
    "股票代码格式不正确",
    error_code="INVALID_STOCK_CODE",
    stock_code="ABC123",
    expected_format="6位数字",
    actual_format="字母+数字"
)

# ✅ 特征计算错误
raise FeatureCalculationError(
    "MA计算失败，数据点不足",
    error_code="INSUFFICIENT_DATA_FOR_MA",
    feature_name="MA_20",
    required_points=20,
    actual_points=10,
    stock_code="000001"
)

# ✅ 模型训练错误
raise ModelTrainingError(
    "LightGBM训练失败",
    error_code="TRAINING_FAILED",
    model_type="LightGBM",
    n_samples=1000,
    n_features=125,
    reason="数据包含NaN值"
)

# ✅ 数据提供者错误（AkShare）
from src.providers.akshare.exceptions import AkShareDataError
raise AkShareDataError(
    "获取股票历史数据失败",
    error_code="AKSHARE_API_ERROR",
    stock_code="000001",
    start_date="2024-01-01",
    end_date="2024-12-31",
    api_function="stock_zh_a_hist"
)
```

**兼容旧代码** (仍然支持):

```python
# ✅ 简单用法（向后兼容）
raise DataValidationError("数据验证失败")
```

### 3. 使用错误处理装饰器

```python
from src.utils.error_handling import handle_errors, retry_on_error, log_errors

# ✅ 示例1: 捕获异常并返回默认值
@handle_errors(DataProviderError, default_return=pd.DataFrame())
def fetch_stock_data(stock_code: str) -> pd.DataFrame:
    """获取股票数据，失败时返回空DataFrame"""
    return provider.get_daily_data(stock_code)

# ✅ 示例2: 自动重试（带指数退避）
@retry_on_error(
    max_attempts=3,
    delay=1.0,
    backoff_factor=2.0,
    exception_class=(DataProviderError, ConnectionError)
)
def fetch_data_with_retry(stock_code: str):
    """自动重试3次，延迟1s, 2s, 4s"""
    return provider.get_daily_data(stock_code)

# ✅ 示例3: 记录错误日志
@log_errors(log_level="error", include_args=True)
def critical_calculation(data: pd.DataFrame):
    """关键计算，记录详细错误信息"""
    return complex_operation(data)

# ✅ 示例4: 组合使用多个装饰器
@retry_on_error(max_attempts=3, delay=1.0)
@handle_errors(DataProviderError, default_return=pd.DataFrame())
def robust_fetch(stock_code: str):
    """先重试，再捕获异常"""
    return provider.get_daily_data(stock_code)
```

### 4. 安全执行函数

```python
from src.utils.error_handling import safe_execute

# ✅ 临时安全执行
result = safe_execute(
    risky_function,
    arg1, arg2,
    default_return=None,
    exception_class=Exception,
    log_error=True
)
```

---

## 🚫 错误示例（避免）

```python
# ❌ 错误1: 使用通用Exception
raise Exception("出错了")  # 太宽泛，不利于错误分类

# ❌ 错误2: 使用标准ValueError但应该用业务异常
raise ValueError("股票代码不能为空")  # 应该用 DataValidationError

# ❌ 错误3: 缺少错误代码和上下文
raise DataValidationError("验证失败")  # 应该添加error_code和context

# ❌ 错误4: 不遵循异常层次结构
raise StockAnalysisError("特征计算失败")  # 应该用 FeatureCalculationError
```

---

## ✅ 正确示例（推荐）

### 示例1: 数据验证

```python
def validate_stock_code(code: str) -> None:
    """验证股票代码格式"""
    if not code:
        raise DataValidationError(
            "股票代码不能为空",
            error_code="EMPTY_STOCK_CODE",
            field="stock_code",
            value=code
        )

    if not code.isdigit() or len(code) != 6:
        raise DataValidationError(
            "股票代码格式不正确",
            error_code="INVALID_STOCK_CODE_FORMAT",
            stock_code=code,
            expected_format="6位数字",
            actual_format=f"{len(code)}位，包含非数字字符" if not code.isdigit() else f"{len(code)}位数字"
        )
```

### 示例2: 特征计算

```python
from src.exceptions import FeatureCalculationError, InsufficientDataError

def calculate_ma(data: pd.DataFrame, period: int) -> pd.Series:
    """计算移动平均线"""
    if len(data) < period:
        raise InsufficientDataError(
            f"数据点不足，无法计算MA{period}",
            error_code="INSUFFICIENT_DATA_FOR_MA",
            indicator="MA",
            period=period,
            required_points=period,
            actual_points=len(data)
        )

    try:
        return data['close'].rolling(window=period).mean()
    except Exception as e:
        raise FeatureCalculationError(
            f"MA{period}计算失败",
            error_code="MA_CALCULATION_ERROR",
            period=period,
            data_shape=data.shape,
            reason=str(e)
        ) from e
```

### 示例3: 模型训练

```python
from src.exceptions import ModelTrainingError, ModelValidationError

def train_model(X: pd.DataFrame, y: pd.Series, model_type: str = 'lightgbm'):
    """���练模型"""
    # 数据验证
    if X.isnull().any().any():
        raise ModelTrainingError(
            "训练数据包含NaN值",
            error_code="TRAINING_DATA_CONTAINS_NAN",
            model_type=model_type,
            nan_columns=X.columns[X.isnull().any()].tolist(),
            total_nan_count=X.isnull().sum().sum()
        )

    # 模型训练
    try:
        model = LightGBMModel(**params)
        model.fit(X, y)
    except Exception as e:
        raise ModelTrainingError(
            "模型训练过程失败",
            error_code="MODEL_FIT_ERROR",
            model_type=model_type,
            n_samples=len(X),
            n_features=X.shape[1],
            error_message=str(e)
        ) from e

    # 模型验证
    if model.feature_importances_.sum() == 0:
        raise ModelValidationError(
            "模型特征重要性全为0，训练可能失败",
            error_code="ZERO_FEATURE_IMPORTANCE",
            model_type=model_type,
            n_features=len(model.feature_importances_)
        )

    return model
```

### 示例4: API调用重试

```python
from src.providers.akshare.exceptions import AkShareDataError, AkShareRateLimitError
from src.utils.error_handling import retry_on_error

@retry_on_error(
    max_attempts=3,
    delay=1.0,
    backoff_factor=2.0,
    exception_class=(AkShareDataError, AkShareRateLimitError)
)
def fetch_stock_data_robust(stock_code: str, start_date: str, end_date: str):
    """健壮的数据获取（自动重试）"""
    try:
        data = ak.stock_zh_a_hist(
            symbol=stock_code,
            start_date=start_date,
            end_date=end_date
        )

        if data.empty:
            raise AkShareDataError(
                "返回数据为空",
                error_code="EMPTY_DATA",
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date
            )

        return data

    except Exception as e:
        if "频率限制" in str(e) or "rate limit" in str(e).lower():
            raise AkShareRateLimitError(
                "API调用频率超限",
                error_code="RATE_LIMIT_EXCEEDED",
                stock_code=stock_code,
                retry_after=60
            )
        else:
            raise AkShareDataError(
                "数据获取失败",
                error_code="API_ERROR",
                stock_code=stock_code,
                error_message=str(e)
            ) from e
```

---

## 📖 异常捕获和处理

### 基本捕获

```python
from src.exceptions import DataProviderError
from loguru import logger

try:
    data = fetch_stock_data("000001")
except DataProviderError as e:
    # 访问错误信息
    logger.error(f"错误类型: {e.__class__.__name__}")
    logger.error(f"错误代码: {e.error_code}")
    logger.error(f"错误消息: {e.message}")
    logger.error(f"上下文: {e.context}")

    # 结构化输出
    error_dict = e.to_dict()
    logger.error(f"结构化错误: {error_dict}")
```

### 分层捕获

```python
try:
    result = complex_operation()
except FeatureCalculationError as e:
    # 特征计算错误
    logger.error(f"特征计算失败: {e.message}", **e.context)
except ModelTrainingError as e:
    # 模型训练错误
    logger.error(f"模型训练失败: {e.message}", **e.context)
except StockAnalysisError as e:
    # 其他所有业务异常
    logger.error(f"操作失败: {e.message}", **e.context)
except Exception as e:
    # 未预期的系统异常
    logger.exception(f"未知错误: {str(e)}")
```

---

## 🔧 创建自定义异常类

如果需要创建新的异常类，遵循以下模式：

```python
from src.exceptions import StockAnalysisError, FeatureError

# ✅ 示例：创建新的业务异常
class MyCustomError(FeatureError):
    """自定义特征错误

    继承自FeatureError，自动获得error_code和context支持。

    Examples:
        >>> raise MyCustomError(
        ...     "自定义错误消息",
        ...     error_code="CUSTOM_ERROR",
        ...     custom_field="value"
        ... )
    """
    pass

# ✅ 示例：带特殊属性的异常（参考TushareRateLimitError）
class MySpecialError(StockAnalysisError):
    """带特殊属性的异常"""

    def __init__(self, message: str, error_code: str = None,
                 special_attr: int = 0, **context):
        context['special_attr'] = special_attr
        super().__init__(message, error_code=error_code, **context)

    @property
    def special_attr(self) -> int:
        """向后兼容属性"""
        return self.context.get('special_attr', 0)
```

---

## 📋 快速参考

### 常用异常类速查

| 场景 | 异常类 | 错误代码示例 |
|------|--------|-------------|
| 数据不存在 | `DataNotFoundError` | `DATA_NOT_FOUND` |
| 数据验证失败 | `DataValidationError` | `INVALID_INPUT` |
| 数据不足 | `InsufficientDataError` | `INSUFFICIENT_DATA` |
| API调用失败 | `DataProviderError` | `API_ERROR` |
| 特征计算失败 | `FeatureCalculationError` | `FEATURE_CALC_ERROR` |
| 模型训练失败 | `ModelTrainingError` | `TRAINING_FAILED` |
| 模型不存在 | `ModelNotFoundError` | `MODEL_NOT_FOUND` |
| 配置错误 | `ConfigValidationError` | `INVALID_CONFIG` |
| 数据库连接失败 | `DatabaseConnectionError` | `DB_CONNECTION_FAILED` |
| 风险限制超出 | `RiskLimitExceededError` | `RISK_LIMIT_EXCEEDED` |

### 装饰器速查

| 装饰器 | 用途 | 适用场景 |
|--------|------|----------|
| `@handle_errors()` | 捕获异常返回默认值 | 容错处理 |
| `@retry_on_error()` | 自动重试 | 网络请求、API调用 |
| `@log_errors()` | 记录错误日志 | 关键操作 |
| `safe_execute()` | 临时安全执行 | 一次性操作 |

---

## 🎯 总结

1. **优先使用业务异常类**，而非Python标准异常
2. **总是提供error_code**，便于错误分类和监控
3. **添加丰富的context信息**，便于调试
4. **使用装饰器简化错误处理**，提高代码可读性
5. **遵循异常层次结构**，使用最具体的异常类
6. **向后兼容**，新老代码都能正常工作

---

**版本**: 1.0
**更新日期**: 2026-01-31
**维护者**: Stock Analysis Team
