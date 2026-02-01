# Backend API Response Skill

**作用**: 指导如何在 Backend 项目中使用统一的 `ApiResponse` 类构建标准化 FastAPI 响应

**适用范围**: 所有 FastAPI 端点开发、API 重构、数据查询接口

---

## 📋 概述

Backend 项目使用基于 Pydantic 的 `ApiResponse` 类提供统一的 API 响应格式，支持：
- ✅ 成功、错误、警告三种状态
- ✅ 泛型数据类型支持
- ✅ 自动时间戳
- ✅ 请求 ID 追踪
- ✅ 分页响应支持
- ✅ 与异常系统集成

---

## 🎯 何时使用 ApiResponse

### ✅ 应该使用

- **所有 FastAPI 端点** - 保持响应格式一致性
- **数据查询接口** - `GET /stocks`, `GET /backtest/results`
- **策略执行接口** - `POST /backtest`, `POST /strategies/run`
- **数据验证接口** - 返回验证结果和错误详情
- **需要传递元数据** - 执行时间、统计信息、警告消息等

### ❌ 不需要使用

- **文件下载端点** - 返回 StreamingResponse
- **WebSocket 连接** - 实时数据流
- **重定向响应** - RedirectResponse
- **健康检查端点** - 简单的 `{"status": "ok"}`

---

## 📖 基本使用

### 1. 导入 ApiResponse

```python
from app.models.api_response import ApiResponse

# 或使用便捷函数
from app.models.api_response import success_response, error_response, paginated_response
```

### 2. 创建成功响应

```python
from fastapi import APIRouter
from app.models.api_response import ApiResponse

router = APIRouter()

@router.get("/stocks/{stock_code}")
async def get_stock(stock_code: str):
    """获取股票信息"""
    stock = await stock_service.get_by_code(stock_code)

    return ApiResponse.success(
        data=stock,
        message="查询成功"
    )

# 返回格式:
# {
#   "code": 200,
#   "message": "查询成功",
#   "data": {...},
#   "timestamp": "2026-02-01T10:00:00"
# }
```

### 3. 创建错误响应

```python
@router.get("/stocks/{stock_code}")
async def get_stock(stock_code: str):
    """获取股票信息"""
    stock = await stock_service.get_by_code(stock_code)

    if not stock:
        return ApiResponse.not_found(
            message=f"股票 {stock_code} 不存在",
            data={"stock_code": stock_code}
        )

    return ApiResponse.success(data=stock)

# 返回格式:
# {
#   "code": 404,
#   "message": "股票 000001 不存在",
#   "data": {"stock_code": "000001"},
#   "timestamp": "2026-02-01T10:00:00"
# }
```

### 4. 创建警告响应

```python
@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """运行回测"""
    result = await backtest_service.run(request)

    # 检查数据质量
    if result.data_quality_score < 0.8:
        return ApiResponse.warning(
            data=result.dict(),
            message="回测完成，但数据质量较低",
            warning_code="LOW_DATA_QUALITY",
            data_quality_score=result.data_quality_score,
            issues=["缺失值过多", "异常值检测到"]
        )

    return ApiResponse.success(data=result)

# 返回格式:
# {
#   "code": 206,
#   "message": "回测完成，但数据质量较低",
#   "data": {
#       "warning_code": "LOW_DATA_QUALITY",
#       "data_quality_score": 0.75,
#       "issues": ["缺失值过多", "异常值检测到"]
#   },
#   "timestamp": "2026-02-01T10:00:00"
# }
```

---

## 🚀 ApiResponse 方法速查

### 成功响应系列

```python
# 200 - 成功
ApiResponse.success(
    data={"key": "value"},
    message="操作成功"
)

# 201 - 创建成功
ApiResponse.created(
    data={"id": 123, "name": "新策略"},
    message="策略创建成功"
)

# 204 - 无内容
ApiResponse.no_content(
    message="删除成功"
)

# 206 - 部分内容/警告
ApiResponse.partial_content(
    data={"items": [...]},
    message="部分数据获取成功"
)

# NEW: 警告响应（扩展功能）
ApiResponse.warning(
    data=result,
    message="操作完成，但存在警告",
    warning_code="DATA_QUALITY_LOW"
)
```

### 错误响应系列

```python
# 400 - 错误请求
ApiResponse.bad_request(
    message="参数错误",
    data={"field": "stock_code", "error": "格式不正确"}
)

# 401 - 未授权
ApiResponse.unauthorized(
    message="未登录或 Token 过期"
)

# 403 - 禁止访问
ApiResponse.forbidden(
    message="权限不足"
)

# 404 - 资源不存在
ApiResponse.not_found(
    message="股票不存在",
    data={"stock_code": "000001"}
)

# 409 - 资源冲突
ApiResponse.conflict(
    message="策略名称已存在",
    data={"name": "动量策略"}
)

# 500 - 服务器错误
ApiResponse.internal_error(
    message="服务器内部错误",
    data={"error_id": 12345}
)

# 自定义状态码
ApiResponse.error(
    message="自定义错误",
    code=422,
    data={"details": "..."}
)
```

### 分页响应

```python
@router.get("/stocks")
async def list_stocks(page: int = 1, page_size: int = 20):
    """获取股票列表（分页）"""
    total = await stock_service.count()
    items = await stock_service.list(page=page, page_size=page_size)

    return ApiResponse.paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        message="查询成功"
    )

# 返回格式:
# {
#   "code": 200,
#   "message": "查询成功",
#   "data": {
#       "items": [...],
#       "total": 1000,
#       "page": 1,
#       "page_size": 20,
#       "total_pages": 50
#   },
#   "timestamp": "2026-02-01T10:00:00"
# }
```

---

## 💡 最佳实践

### 1. 提供有意义的 message

```python
# ✅ 推荐：清晰的消息
ApiResponse.success(
    data=result,
    message="回测完成，共执行 150 笔交易"
)

# ❌ 避免：无意义的消息
ApiResponse.success(data=result, message="success")
```

### 2. 错误时提供详细信息

```python
# ✅ 推荐：包含 error_code 和上下文
return ApiResponse.error(
    message="股票数据查询失败",
    code=500,
    data={
        "error_code": "QUERY_FAILED",
        "stock_code": "000001",
        "date_range": "2024-01-01至2024-12-31",
        "reason": "数据库连接超时"
    }
)

# ❌ 避免：信息不足
return ApiResponse.error(message="查询失败", code=500)
```

### 3. 成功时传递有用的元数据

```python
# ✅ 推荐：包含统计信息
return ApiResponse.success(
    data=features,
    message="特征计算完成",
    n_features=125,
    n_samples=1000,
    null_ratio="2.5%",
    elapsed_time="3.2s"
)
```

### 4. 合理使用警告状态

```python
# ✅ 推荐：操作完成但有问题时使用警告
if data_quality < 0.8:
    return ApiResponse.warning(
        data=result,
        message="数据处理完成，但质量较低",
        warning_code="LOW_QUALITY",
        quality_score=data_quality
    )

# ❌ 避免：完全忽略问题或直接报错
```

---

## 🔄 与异常系统集成

### 模式 1: 手动捕获异常

```python
from app.core.exceptions import DataQueryError, ValidationError
from app.models.api_response import ApiResponse

@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    try:
        result = await backtest_service.run(request)
        return ApiResponse.success(data=result)

    except ValidationError as e:
        return ApiResponse.bad_request(
            message=e.message,
            data={
                "error_code": e.error_code,
                **e.context
            }
        )

    except DataQueryError as e:
        return ApiResponse.internal_error(
            message=e.message,
            data={
                "error_code": e.error_code,
                **e.context
            }
        )
```

### 模式 2: 使用装饰器 + ApiResponse

```python
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse

@router.get("/stocks/{stock_code}")
@handle_api_errors
async def get_stock(stock_code: str):
    """
    装饰器会自动捕获异常转换为 HTTP 响应
    成功时返回 ApiResponse
    """
    stock = await stock_service.get_by_code(stock_code)
    return ApiResponse.success(data=stock)
```

---

## 🎨 实际示例

### 示例 1: 数据查询 API

```python
from fastapi import APIRouter, Query
from app.models.api_response import ApiResponse
from app.core.exceptions import ValidationError

router = APIRouter()

@router.get("/stocks/{stock_code}/history")
async def get_stock_history(
    stock_code: str,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD")
):
    """
    获取股票历史数据

    Returns:
        ApiResponse: 包含历史数据的响应
    """
    try:
        # 验证日期格式
        from datetime import datetime
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        if start >= end:
            raise ValidationError(
                "开始日期必须早于结束日期",
                error_code="INVALID_DATE_RANGE",
                start_date=start_date,
                end_date=end_date
            )

        # 查询数据
        data = await stock_service.get_history(
            stock_code=stock_code,
            start_date=start,
            end_date=end
        )

        if not data:
            return ApiResponse.not_found(
                message=f"股票 {stock_code} 在指定日期范围内无数据",
                data={
                    "stock_code": stock_code,
                    "start_date": start_date,
                    "end_date": end_date
                }
            )

        return ApiResponse.success(
            data=data,
            message="查询成功",
            stock_code=stock_code,
            n_records=len(data),
            date_range=f"{start_date} 至 {end_date}"
        )

    except ValidationError as e:
        return ApiResponse.bad_request(
            message=e.message,
            data={"error_code": e.error_code, **e.context}
        )

    except Exception as e:
        return ApiResponse.internal_error(
            message="数据查询失败",
            data={"error": str(e)}
        )
```

### 示例 2: 策略回测 API

```python
from fastapi import APIRouter
from app.models.api_response import ApiResponse
from app.schemas.backtest import BacktestRequest, BacktestResult
import time

router = APIRouter()

@router.post("/backtest", response_model=ApiResponse[BacktestResult])
async def run_backtest(request: BacktestRequest):
    """
    运行策略回测

    Returns:
        ApiResponse[BacktestResult]: 回测结果
    """
    start_time = time.time()

    try:
        # 执行回测
        result = await backtest_service.run(
            strategy=request.strategy,
            stock_codes=request.stock_codes,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital
        )

        elapsed = time.time() - start_time

        # 检查结果质量
        if result.total_trades < 10:
            return ApiResponse.warning(
                data=result.dict(),
                message="回测完成，但交易次数过少，结果可能不可靠",
                warning_code="INSUFFICIENT_TRADES",
                total_trades=result.total_trades,
                min_recommended=30,
                elapsed_time=f"{elapsed:.2f}s"
            )

        return ApiResponse.success(
            data=result.dict(),
            message="回测完成",
            strategy=request.strategy,
            total_trades=result.total_trades,
            sharpe_ratio=result.sharpe_ratio,
            max_drawdown=result.max_drawdown,
            elapsed_time=f"{elapsed:.2f}s"
        )

    except Exception as e:
        return ApiResponse.internal_error(
            message="回测执行失败",
            data={
                "error": str(e),
                "strategy": request.strategy,
                "elapsed_time": f"{time.time() - start_time:.2f}s"
            }
        )
```

### 示例 3: 分页列表 API

```python
from fastapi import APIRouter, Query
from app.models.api_response import ApiResponse

router = APIRouter()

@router.get("/strategies")
async def list_strategies(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: str = Query(None, description="策略状态过滤")
):
    """
    获取策略列表（分页）

    Returns:
        ApiResponse: 分页的策略列表
    """
    # 构建查询条件
    filters = {}
    if status:
        filters['status'] = status

    # 查询总数和数据
    total = await strategy_service.count(filters)
    items = await strategy_service.list(
        page=page,
        page_size=page_size,
        filters=filters
    )

    return ApiResponse.paginated(
        items=[item.dict() for item in items],
        total=total,
        page=page,
        page_size=page_size,
        message="查询成功"
    )
```

### 示例 4: 数据验证 API

```python
from fastapi import APIRouter
from app.models.api_response import ApiResponse
from app.schemas.validation import DataValidationRequest

router = APIRouter()

@router.post("/validate/features")
async def validate_features(request: DataValidationRequest):
    """
    验证特征数据质量

    Returns:
        ApiResponse: 验证结果（success/warning/error）
    """
    validation_result = await validator.validate(request.data)

    issues = validation_result.get('issues', [])
    warnings = validation_result.get('warnings', [])

    # 有严重问题
    if issues:
        return ApiResponse.bad_request(
            message="数据验证失败",
            data={
                "error_code": "VALIDATION_FAILED",
                "issues": issues,
                "warnings": warnings
            }
        )

    # 有警告但可以继续
    if warnings:
        return ApiResponse.warning(
            data={"passed": True},
            message="数据验证通过，但存在警告",
            warning_code="VALIDATION_WARNING",
            warnings=warnings
        )

    # 完全通过
    return ApiResponse.success(
        data={"passed": True},
        message="数据验证通过",
        n_records=len(request.data),
        n_features=validation_result.get('n_features')
    )
```

---

## 📊 响应格式规范

### 标准成功响应

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "key": "value"
  },
  "timestamp": "2026-02-01T10:00:00.123456"
}
```

### 标准错误响应

```json
{
  "code": 400,
  "message": "参数错误",
  "data": {
    "error_code": "INVALID_PARAMETER",
    "field": "stock_code",
    "expected": "6位数字",
    "actual": "ABC123"
  },
  "timestamp": "2026-02-01T10:00:00.123456"
}
```

### 标准警告响应

```json
{
  "code": 206,
  "message": "操作完成，但存在警告",
  "data": {
    "warning_code": "LOW_DATA_QUALITY",
    "quality_score": 0.75,
    "issues": ["缺失值过多"]
  },
  "timestamp": "2026-02-01T10:00:00.123456"
}
```

### 分页响应

```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "items": [...],
    "total": 1000,
    "page": 1,
    "page_size": 20,
    "total_pages": 50
  },
  "timestamp": "2026-02-01T10:00:00.123456"
}
```

---

## 📝 检查清单

在编写 API 时，确保：

- [ ] 导入了 `ApiResponse` 类
- [ ] 使用了合适的响应方法（success/error/warning）
- [ ] 提供了有意义的 `message`
- [ ] 错误响应包含 `error_code`
- [ ] 添加了有用的元数据（统计信息、执行时间等）
- [ ] 错误时提供了足够的上下文信息
- [ ] 考虑了数据质量问题，使用 `warning` 状态
- [ ] 分页接口使用 `ApiResponse.paginated()`
- [ ] 响应模型使用了泛型类型提示（可选）

---

## 🚀 扩展功能

### ApiResponse 新增的 warning 方法

```python
# app/models/api_response.py 中新增

@classmethod
def warning(
    cls,
    data: Optional[T] = None,
    message: str = "warning",
    warning_code: Optional[str] = None,
    **metadata
) -> "ApiResponse[T]":
    """
    创建警告响应 (206 Partial Content)

    用于操作成功但存在需要注意的情况

    Args:
        data: 响应数据
        message: 警告消息
        warning_code: 警告代码
        **metadata: 其他元数据

    Returns:
        ApiResponse: 警告响应对象
    """
    response_data = data if data is not None else {}

    # 将 warning_code 和 metadata 合并到 data 中
    if isinstance(response_data, dict):
        if warning_code:
            response_data["warning_code"] = warning_code
        response_data.update(metadata)

    return cls(
        code=206,
        message=message,
        data=response_data
    )
```

---

## 🎓 总结

1. **统一使用 ApiResponse**，保持响应格式一致性
2. **提供有意义的 message**，便于调试和用户理解
3. **错误时包含 error_code 和上下文**，帮助定位问题
4. **成功时添加元数据**，提供更多有用信息
5. **合理使用 warning 状态**，处理部分成功的情况
6. **分页接口使用 paginated 方法**，自动计算总页数
7. **与异常系统集成**，统一错误处理流程

---

## 📚 相关资源

- ApiResponse 源码: [app/models/api_response.py](backend/app/models/api_response.py)
- 异常处理 Skill: [exception-handling.md](exception-handling.md)
- API 错误处理: [app/api/error_handler.py](backend/app/api/error_handler.py)
- 文档: [backend/app/models/README_API_RESPONSE.md](backend/app/models/README_API_RESPONSE.md)

---

**版本**: 1.0.0
**创建日期**: 2026-02-01
**维护者**: Stock Analysis Team
