# Backend Exception Handling Skill

**作用**: 指导如何在 Backend 项目（FastAPI 环境）中正确使用统一异常处理系统

**适用范围**: FastAPI 端点开发、异步服务、数据库操作、策略执行

---

## 📚 Backend 异常系统概述

Backend 项目已建立 FastAPI 友好的异常处理系统：
- **基础模块**: `app/core/exceptions.py` (业务异常类)
- **API 异常**: `app/api/error_handler.py` (FastAPI 装饰器)
- **重试机制**: `app/utils/retry.py` (异步/同步重试)
- **响应模型**: `app/models/api_response.py` (统一响应格式)

---

## 🎯 异常类体系

### 1. API 异常类（HTTP 状态码）

这些异常类继承自 `APIError`，用于 FastAPI 端点：

```python
from app.api.error_handler import (
    APIError,              # 基类
    BadRequestError,       # 400 - 错误请求
    NotFoundError,         # 404 - 资源不存在
    ConflictError,         # 409 - 资源冲突
    InternalServerError,   # 500 - 服务器错误
)

# ✅ 示例：抛出 API 异常
raise BadRequestError(
    "股票代码格式不正确",
    details={"stock_code": "ABC", "expected": "6位数字"}
)
```

### 2. 业务异常类（结构化异常）

这些异常类继承自 `BackendError`，支持 error_code 和 context：

```python
from app.core.exceptions import (
    BackendError,              # 业务异常基类
    DataQueryError,            # 数据查询失败
    StrategyExecutionError,    # 策略执行失败
    ValidationError,           # 数据验证失败
    CalculationError,          # 计算错误
    DatabaseError,             # 数据库错误
    ExternalAPIError,          # 外部 API 错误
)

# ✅ 示例：抛出业务异常（推荐）
raise DataQueryError(
    "股票数据查询失败",
    error_code="STOCK_DATA_NOT_FOUND",
    stock_code="000001",
    date_range="2024-01-01至2024-12-31",
    reason="数据库中无此股票记录"
)
```

---

## 🚀 使用指南

### 模式 1: FastAPI 端点 + API 异常

**适用场景**: 快速开发，简单的错误处理

```python
from fastapi import APIRouter
from app.api.error_handler import handle_api_errors, BadRequestError, NotFoundError
from app.models.api_response import ApiResponse

router = APIRouter()

@router.get("/stocks/{stock_code}")
@handle_api_errors
async def get_stock_info(stock_code: str):
    """
    获取股票信息

    装饰器会自动捕获异常并转换为 HTTP 响应
    """
    # 验证参数
    if not stock_code or len(stock_code) != 6:
        raise BadRequestError(
            "股票代码必须是6位数字",
            details={"stock_code": stock_code}
        )

    # 查询数据
    stock = await stock_service.get_by_code(stock_code)
    if not stock:
        raise NotFoundError(
            f"股票 {stock_code} 不存在",
            details={"stock_code": stock_code}
        )

    return ApiResponse.success(data=stock)
```

### 模式 2: 业务异常 + ApiResponse（推荐）

**适用场景**: 需要详细的错误上下文和统一的响应格式

```python
from fastapi import APIRouter
from app.core.exceptions import DataQueryError, ValidationError
from app.models.api_response import ApiResponse

router = APIRouter()

@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """
    运行策略回测

    使用 try-except 手动处理异常，返回 ApiResponse
    """
    try:
        # 数据验证
        if request.start_date >= request.end_date:
            raise ValidationError(
                "开始日期必须早于结束日期",
                error_code="INVALID_DATE_RANGE",
                start_date=str(request.start_date),
                end_date=str(request.end_date)
            )

        # 执行回测
        result = await backtest_service.run(
            strategy=request.strategy,
            start_date=request.start_date,
            end_date=request.end_date
        )

        return ApiResponse.success(
            data=result,
            message="回测完成",
            total_trades=result['total_trades'],
            sharpe_ratio=result['sharpe_ratio']
        )

    except ValidationError as e:
        return ApiResponse.error(
            message=e.message,
            code=400,
            data={
                "error_code": e.error_code,
                **e.context
            }
        )

    except DataQueryError as e:
        return ApiResponse.error(
            message=e.message,
            code=500,
            data={
                "error_code": e.error_code,
                **e.context
            }
        )
```

### 模式 3: 异步重试 + 异常处理

**适用场景**: 外部 API 调用、数据库连接

```python
from app.utils.retry import retry_async
from app.core.exceptions import ExternalAPIError, DatabaseError

@retry_async(
    max_retries=3,
    delay_base=2.0,
    delay_strategy='exponential',
    exceptions=(ExternalAPIError, DatabaseError)
)
async def fetch_stock_data_from_api(stock_code: str):
    """
    从外部 API 获取股票数据（自动重试）

    失败时自动重试 3 次，延迟 2s, 4s, 8s
    """
    try:
        response = await external_api.get_stock_data(stock_code)

        if not response:
            raise ExternalAPIError(
                "API 返回数据为空",
                error_code="EMPTY_RESPONSE",
                stock_code=stock_code,
                api_endpoint="/stock/data"
            )

        return response

    except Exception as e:
        raise ExternalAPIError(
            "外部 API 调用失败",
            error_code="API_REQUEST_FAILED",
            stock_code=stock_code,
            error_message=str(e)
        ) from e
```

---

## ✅ 最佳实践

### 1. 选择合适的异常类

```python
# ✅ 推荐：使用具体的业务异常
raise DataQueryError(
    "股票数据不存在",
    error_code="STOCK_NOT_FOUND",
    stock_code="000001"
)

# ❌ 避免：使用通用异常
raise Exception("股票数据不存在")

# ❌ 避免：使用标准库异常
raise ValueError("股票数据不存在")
```

### 2. 总是提供 error_code

```python
# ✅ 推荐：包含 error_code 和上下文
raise ValidationError(
    "数据验证失败",
    error_code="INVALID_STOCK_CODE",
    stock_code="ABC123",
    expected_format="6位数字"
)

# ❌ 避免：缺少 error_code
raise ValidationError("数据验证失败")
```

### 3. 错误代码命名规范

```python
# ✅ 推荐：大写下划线，语义清晰
"STOCK_NOT_FOUND"
"INVALID_DATE_RANGE"
"DATABASE_CONNECTION_FAILED"
"API_RATE_LIMIT_EXCEEDED"

# ❌ 避免：小写或驼峰
"stockNotFound"
"error1"
"err"
```

### 4. 提供丰富的上下文信息

```python
# ✅ 推荐：详细的上下文
raise DataQueryError(
    "股票数据查询失败",
    error_code="QUERY_FAILED",
    stock_code="000001",
    start_date="2024-01-01",
    end_date="2024-12-31",
    table="stock_daily",
    query_time="2.5s",
    reason="数据库连接超时"
)

# ❌ 避免：缺少上下文
raise DataQueryError("查询失败")
```

---

## 📖 常用场景示例

### 场景 1: 数据验证

```python
from app.core.exceptions import ValidationError

def validate_stock_code(code: str) -> None:
    """验证股票代码"""
    if not code:
        raise ValidationError(
            "股票代码不能为空",
            error_code="EMPTY_STOCK_CODE",
            field="stock_code",
            value=code
        )

    if not code.isdigit() or len(code) != 6:
        raise ValidationError(
            "股票代码必须是6位数字",
            error_code="INVALID_STOCK_CODE_FORMAT",
            stock_code=code,
            expected_format="6位数字",
            actual_value=code
        )
```

### 场景 2: 数据库操作

```python
from app.core.exceptions import DatabaseError
from sqlalchemy.exc import SQLAlchemyError

async def get_stock_by_code(stock_code: str):
    """从数据库获取股票信息"""
    try:
        result = await db.execute(
            select(Stock).where(Stock.code == stock_code)
        )
        return result.scalar_one_or_none()

    except SQLAlchemyError as e:
        raise DatabaseError(
            "数据库查询失败",
            error_code="DB_QUERY_ERROR",
            stock_code=stock_code,
            table="stocks",
            error_message=str(e)
        ) from e
```

### 场景 3: 策略执行

```python
from app.core.exceptions import StrategyExecutionError

async def execute_strategy(strategy_name: str, params: dict):
    """执行交易策略"""
    try:
        strategy = strategy_registry.get(strategy_name)
        if not strategy:
            raise StrategyExecutionError(
                f"策略 {strategy_name} 不存在",
                error_code="STRATEGY_NOT_FOUND",
                strategy_name=strategy_name,
                available_strategies=list(strategy_registry.keys())
            )

        result = await strategy.execute(**params)
        return result

    except Exception as e:
        raise StrategyExecutionError(
            "策略执行失败",
            error_code="STRATEGY_EXECUTION_FAILED",
            strategy_name=strategy_name,
            params=params,
            error_message=str(e)
        ) from e
```

### 场景 4: 外部 API 调用（带重试）

```python
from app.utils.retry import retry_async
from app.core.exceptions import ExternalAPIError

@retry_async(
    max_retries=3,
    delay_base=2.0,
    delay_strategy='exponential',
    exceptions=(ExternalAPIError,)
)
async def fetch_realtime_price(stock_code: str):
    """获取实时股价（带重试）"""
    try:
        response = await http_client.get(
            f"https://api.example.com/price/{stock_code}"
        )

        if response.status_code == 429:
            raise ExternalAPIError(
                "API 调用频率超限",
                error_code="RATE_LIMIT_EXCEEDED",
                stock_code=stock_code,
                retry_after=response.headers.get("Retry-After", 60)
            )

        if response.status_code != 200:
            raise ExternalAPIError(
                "API 请求失败",
                error_code="API_REQUEST_FAILED",
                stock_code=stock_code,
                status_code=response.status_code
            )

        return response.json()

    except Exception as e:
        if isinstance(e, ExternalAPIError):
            raise
        raise ExternalAPIError(
            "外部 API 调用异常",
            error_code="API_EXCEPTION",
            stock_code=stock_code,
            error_message=str(e)
        ) from e
```

---

## 🔧 创建自定义异常类

如果需要创建新的业务异常类：

```python
# app/core/exceptions.py

from app.core.exceptions import BackendError

class MyCustomError(BackendError):
    """
    自定义业务异常

    继承自 BackendError，自动获得 error_code 和 context 支持

    Examples:
        >>> raise MyCustomError(
        ...     "自定义错误消息",
        ...     error_code="CUSTOM_ERROR",
        ...     custom_field="value"
        ... )
    """
    pass
```

---

## 📋 快速参考

### 异常类速查表

| 场景 | 异常类 | HTTP 状态码 | 错误代码示例 |
|------|--------|------------|-------------|
| 参数错误 | `BadRequestError` | 400 | `INVALID_PARAMETER` |
| 参数验证失败 | `ValidationError` | 400 | `VALIDATION_FAILED` |
| 资源不存在 | `NotFoundError` | 404 | `RESOURCE_NOT_FOUND` |
| 数据不存在 | `DataQueryError` | 404 | `DATA_NOT_FOUND` |
| 资源冲突 | `ConflictError` | 409 | `RESOURCE_CONFLICT` |
| 数据库错误 | `DatabaseError` | 500 | `DB_ERROR` |
| 策略执行失败 | `StrategyExecutionError` | 500 | `STRATEGY_FAILED` |
| 外部 API 错误 | `ExternalAPIError` | 500 | `API_ERROR` |
| 计算错误 | `CalculationError` | 500 | `CALCULATION_ERROR` |

### 装饰器和工具速查

| 工具 | 用途 | 适用场景 |
|------|------|----------|
| `@handle_api_errors` | 自动捕获异常转 HTTP 响应 | FastAPI 异步端点 |
| `@handle_api_errors_sync` | 同上（同步版本） | FastAPI 同步端点 |
| `retry_async()` | 异步函数重试 | 外部 API、数据库连接 |
| `retry_sync()` | 同步函数重试 | 同步操作重试 |

---

## 🎯 与 ApiResponse 集成

推荐模式：

```python
from app.models.api_response import ApiResponse
from app.core.exceptions import DataQueryError, ValidationError

async def my_api_endpoint(request: Request):
    try:
        # 业务逻辑
        result = await service.do_something(request)

        return ApiResponse.success(
            data=result,
            message="操作成功"
        )

    except ValidationError as e:
        return ApiResponse.error(
            message=e.message,
            code=400,
            data={"error_code": e.error_code, **e.context}
        )

    except DataQueryError as e:
        return ApiResponse.error(
            message=e.message,
            code=500,
            data={"error_code": e.error_code, **e.context}
        )
```

---

## 🚦 决策树：何时使用哪种异常

```
是否是 FastAPI 端点？
├─ 是 → 是否需要详细的错误上下文？
│      ├─ 是 → 使用业务异常 + try-except + ApiResponse
│      └─ 否 → 使用 @handle_api_errors + API 异常
│
└─ 否 → 是否是外部调用（API/DB）？
       ├─ 是 → 使用业务异常 + retry_async/retry_sync
       └─ 否 → 使用业务异常 + 在上层捕获
```

---

## 🎓 总结

1. **优先使用业务异常类**（`BackendError` 系列），提供 error_code 和 context
2. **FastAPI 端点**使用 `@handle_api_errors` 或手动 try-except
3. **外部调用**使用 `retry_async/retry_sync` 自动重试
4. **总是提供 error_code**，便于监控和调试
5. **添加丰富的 context**，帮助定位问题
6. **与 ApiResponse 集成**，返回统一的响应格式

---

**版本**: 1.0.0
**创建日期**: 2026-02-01
**维护者**: Stock Analysis Team
