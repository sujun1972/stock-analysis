# ApiResponse 统一响应模型使用指南

## 📋 概述

`ApiResponse` 是 Backend 项目的统一 API 响应模型，基于 Pydantic 构建，提供一致的响应格式和便捷的构造方法。

**特性**:
- ✅ 统一的响应格式
- ✅ 泛型类型支持
- ✅ 自动时间戳
- ✅ 请求追踪 (request_id)
- ✅ **三种状态**: Success/Warning/Error
- ✅ 分页响应支持
- ✅ 与异常系统集成

**相关文档**:
- [Exception Handling Skill](../../.claude/skills/exception-handling.md) - 异常处理指南
- [API Response Skill](../../.claude/skills/api-response.md) - 详细的最佳实践

---

## 🎯 响应格式

### 标准响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {
    // 实际数据
  },
  "timestamp": "2026-02-01T12:00:00.123456",
  "request_id": "req_123456"  // 可选
}
```

### 三种响应状态

| 状态 | HTTP 状态码 | 使用场景 |
|------|------------|----------|
| **Success** | 200, 201 | 操作完全成功 |
| **Warning** | 206 | 操作成功但有需要注意的问题 |
| **Error** | 4xx, 5xx | 操作失败 |

---

## 🚀 基本使用

### 1. 成功响应 (200)

```python
from app.models.api_response import ApiResponse

@router.get("/stocks")
async def get_stocks():
    stocks = await stock_service.list()
    return ApiResponse.success(data=stocks, message="查询成功")
```

**返回**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": [...],
  "timestamp": "2026-02-01T12:00:00"
}
```

### 2. 警告响应 (206) - 新增功能

```python
@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    result = await backtest_service.run(request)

    # 检查数据质量
    if result.data_quality_score < 0.8:
        return ApiResponse.warning(
            data=result.dict(),
            message="回测完成，但数据质量较低",
            warning_code="LOW_DATA_QUALITY",
            quality_score=result.data_quality_score,
            recommendation="建议检查数据源"
        )

    return ApiResponse.success(data=result)
```

**返回**:
```json
{
  "code": 206,
  "message": "回测完成，但数据质量较低",
  "data": {
    "warning_code": "LOW_DATA_QUALITY",
    "quality_score": 0.75,
    "recommendation": "建议检查数据源"
  },
  "timestamp": "2026-02-01T12:00:00"
}
```

### 3. 错误响应 (404)

```python
@router.get("/stocks/{stock_code}")
async def get_stock(stock_code: str):
    stock = await stock_service.get_by_code(stock_code)

    if not stock:
        return ApiResponse.not_found(
            message=f"股票 {stock_code} 不存在",
            data={"stock_code": stock_code}
        )

    return ApiResponse.success(data=stock)
```

**返回**:
```json
{
  "code": 404,
  "message": "股票 000001 不存在",
  "data": {"stock_code": "000001"},
  "timestamp": "2026-02-01T12:00:00"
}
```

### 4. 创建资源响应 (201)

```python
@router.post("/strategies")
async def create_strategy(strategy: StrategyCreate):
    new_strategy = await strategy_service.create(strategy)
    return ApiResponse.created(
        data=new_strategy,
        message="策略创建成功"
    )
```

### 5. 分页响应

```python
@router.get("/stocks")
async def list_stocks(page: int = 1, page_size: int = 20):
    total = await stock_service.count()
    items = await stock_service.list(page=page, page_size=page_size)

    return ApiResponse.paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        message="查询成功"
    )
```

**返回**:
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
  "timestamp": "2026-02-01T12:00:00"
}
```

---

## 📖 所有便捷方法

### 成功响应系列 (2xx)

```python
# 200 OK - 成功
ApiResponse.success(
    data={"key": "value"},
    message="操作成功"
)

# 201 Created - 创建成功
ApiResponse.created(
    data=new_resource,
    message="资源创建成功"
)

# 204 No Content - 无内容（通常用于删除）
ApiResponse.no_content(
    message="删除成功"
)

# 206 Partial Content/Warning - 警告（新增）
ApiResponse.warning(
    data=result,
    message="操作完成，但存在警告",
    warning_code="WARNING_CODE"
)

# 206 Partial Content - 部分内容
ApiResponse.partial_content(
    data=partial_data,
    message="部分数据获取成功"
)
```

### 客户端错误响应系列 (4xx)

```python
# 400 Bad Request - 错误请求
ApiResponse.bad_request(
    message="参数错误",
    data={"field": "stock_code", "error": "格式不正确"}
)

# 401 Unauthorized - 未授权
ApiResponse.unauthorized(
    message="未登录或 Token 过期"
)

# 403 Forbidden - 禁止访问
ApiResponse.forbidden(
    message="权限不足"
)

# 404 Not Found - 资源不存在
ApiResponse.not_found(
    message="资源不存在",
    data={"resource_id": "123"}
)

# 409 Conflict - 资源冲突
ApiResponse.conflict(
    message="资源已存在",
    data={"name": "动量策略"}
)
```

### 服务器错误响应系列 (5xx)

```python
# 500 Internal Server Error - 服务器内部错误
ApiResponse.internal_error(
    message="服务器内部错误",
    data={"error_id": 12345}
)

# 自定义状态码
ApiResponse.error(
    message="自定义错误",
    code=503,
    data={"details": "..."}
)
```

---

## 🔄 与异常系统集成

### 模式 1: 使用装饰器（推荐简单场景）

```python
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse

@router.get("/stocks/{stock_code}")
@handle_api_errors
async def get_stock(stock_code: str):
    """
    装饰器会自动捕获异常并转换为 HTTP 响应
    """
    stock = await stock_service.get_by_code(stock_code)
    return ApiResponse.success(data=stock)
```

### 模式 2: 手动异常处理（推荐复杂场景）

```python
from app.core.exceptions import DataQueryError, ValidationError
from app.models.api_response import ApiResponse

@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
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
        result = await backtest_service.run(request)

        return ApiResponse.success(
            data=result,
            message="回测完成",
            total_trades=result['total_trades']
        )

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

---

## 💡 最佳实践

### 1. 提供有意义的 message

```python
# ✅ 推荐：清晰描述性的消息
ApiResponse.success(
    data=result,
    message="回测完成，共执行 150 笔交易"
)

# ❌ 避免：模糊的消息
ApiResponse.success(data=result, message="ok")
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

### 3. 合理使用警告状态

**何时使用 warning**:
- 数据质量较低但可用
- 部分数据缺失但已填充
- 使用了降级方案
- 结果可能不可靠

```python
# ✅ 推荐：数据质量问题时使用警告
if null_ratio > 0.1:
    return ApiResponse.warning(
        data=processed_data,
        message="数据处理完成，但存在较多缺失值",
        warning_code="HIGH_NULL_RATIO",
        null_ratio=f"{null_ratio:.2%}",
        fill_method="forward_fill"
    )

# ❌ 避免：完全忽略问题或直接报错
```

### 4. 合理使用状态码

```python
# ✅ 创建资源使用 201
@router.post("/strategies")
async def create_strategy(strategy: StrategyCreate):
    new_strategy = await service.create(strategy)
    return ApiResponse.created(data=new_strategy)  # 201

# ✅ 删除资源使用 204
@router.delete("/strategies/{id}")
async def delete_strategy(id: int):
    await service.delete(id)
    return ApiResponse.no_content()  # 204

# ✅ 部分成功使用 206
@router.post("/batch")
async def batch_process(items: List[Item]):
    results = await service.process(items)
    if results['failed'] > 0:
        return ApiResponse.partial_content(data=results)  # 206
    return ApiResponse.success(data=results)  # 200
```

### 5. 添加有用的元数据

```python
# ✅ 推荐：包含统计信息和执行时间
return ApiResponse.success(
    data=features,
    message="特征计算完成",
    n_features=125,
    n_samples=1000,
    null_ratio="2.5%",
    elapsed_time="3.2s",
    cache_hit=False
)
```

---

## 🎨 高级用法

### 泛型类型支持

```python
from typing import List, Dict
from pydantic import BaseModel

class Stock(BaseModel):
    code: str
    name: str
    price: float

@router.get("/stocks", response_model=ApiResponse[List[Stock]])
async def get_stocks():
    stocks = await stock_service.list()
    return ApiResponse.success(data=stocks)
```

### 请求追踪

```python
from fastapi import Request
import uuid

@router.get("/tracked")
async def tracked_endpoint(request: Request):
    # 生成或从请求头获取 request_id
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    # 业务逻辑
    data = await service.process()

    return ApiResponse.success(
        data=data,
        message="处理完成",
        request_id=request_id
    )
```

### 向后兼容的字典格式

如果某些旧代码需要字典而非 Pydantic 模型：

```python
from app.models.api_response import (
    success_response,
    error_response,
    warning_response,  # 新增
    paginated_response
)

@router.get("/old-endpoint")
async def old_endpoint():
    # 返回字典而不是 Pydantic 模型
    return success_response(data={"key": "value"})

@router.get("/warning-endpoint")
async def warning_endpoint():
    # 返回警告字典
    return warning_response(
        data={"result": "..."},
        message="操作完成，但存在警告",
        warning_code="LOW_QUALITY"
    )
```

---

## 🧪 测试示例

### 单元测试

```python
import pytest
from app.models.api_response import ApiResponse

def test_success_response():
    response = ApiResponse.success(data={"key": "value"})
    assert response.code == 200
    assert response.message == "success"
    assert response.data == {"key": "value"}
    assert response.timestamp is not None

def test_error_response():
    response = ApiResponse.not_found(message="User not found")
    assert response.code == 404
    assert response.message == "User not found"
    assert response.data is None

def test_warning_response():
    response = ApiResponse.warning(
        data={"result": "ok"},
        message="操作完成，但有警告",
        warning_code="LOW_QUALITY",
        quality_score=0.75
    )
    assert response.code == 206
    assert response.message == "操作完成，但有警告"
    assert response.data["warning_code"] == "LOW_QUALITY"
    assert response.data["quality_score"] == 0.75

def test_paginated_response():
    response = ApiResponse.paginated(
        items=[1, 2, 3],
        total=100,
        page=1,
        page_size=3
    )
    assert response.code == 200
    assert response.data['total'] == 100
    assert response.data['total_pages'] == 34
    assert len(response.data['items']) == 3
```

### 集成测试（FastAPI TestClient）

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_stock_success():
    response = client.get("/api/v1/stocks/000001")
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == 200
    assert data["message"] == "查询成功"
    assert "data" in data
    assert "timestamp" in data

def test_get_stock_not_found():
    response = client.get("/api/v1/stocks/999999")
    assert response.status_code == 404

    data = response.json()
    assert data["code"] == 404
    assert "不存在" in data["message"]
```

---

## 🔧 FastAPI 全局集成

### 全局异常处理器

```python
from fastapi import FastAPI, HTTPException
from app.models.api_response import ApiResponse

app = FastAPI()

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return ApiResponse.error(
        message=exc.detail,
        code=exc.status_code
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # 记录错误日志
    logger.error(f"未捕获的异常: {exc}", exc_info=True)

    return ApiResponse.internal_error(
        message="服务器内部错误",
        data={"error_id": id(exc)}
    )
```

---

## 🔄 迁移现有代码

### Before（手动构造字典）

```python
@router.get("/old")
async def old_endpoint():
    try:
        data = await fetch_data()
        return {
            "code": 200,
            "message": "success",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }
```

### After（使用 ApiResponse + 装饰器）

```python
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse

@router.get("/new")
@handle_api_errors  # 错误处理由装饰器负责
async def new_endpoint():
    data = await fetch_data()
    return ApiResponse.success(data=data)
```

---

## 📋 快速参考

### 常用方法速查表

| 方法 | 状态码 | 使用场景 |
|------|--------|----------|
| `success()` | 200 | 成功响应 |
| `created()` | 201 | 创建资源成功 |
| `no_content()` | 204 | 删除成功/无内容 |
| `warning()` | 206 | 警告响应（新增） |
| `partial_content()` | 206 | 部分内容 |
| `bad_request()` | 400 | 参数错误 |
| `unauthorized()` | 401 | 未授权 |
| `forbidden()` | 403 | 权限不足 |
| `not_found()` | 404 | 资源不存在 |
| `conflict()` | 409 | 资源冲突 |
| `internal_error()` | 500 | 服务器错误 |
| `error()` | 自定义 | 自定义错误 |
| `paginated()` | 200 | 分页响应 |

### 便捷函数速查表

| 函数 | 返回类型 | 用途 |
|------|----------|------|
| `success_response()` | Dict | 成功响应字典 |
| `error_response()` | Dict | 错误响应字典 |
| `warning_response()` | Dict | 警告响应字典（新增） |
| `paginated_response()` | Dict | 分页响应字典 |

---

## 🔗 相关资源

### 文档
- [API Response Skill](../../.claude/skills/api-response.md) - 详细的使用指南和最佳实践
- [Exception Handling Skill](../../.claude/skills/exception-handling.md) - 异常处理指南
- [API Reference](../api_reference/README.md) - API 端点参考文档

### 代码
- [app/models/api_response.py](../../app/models/api_response.py) - ApiResponse 源码
- [app/core/exceptions.py](../../app/core/exceptions.py) - 业务异常类
- [app/api/error_handler.py](../../app/api/error_handler.py) - 错误处理装饰器

### 示例
参考现有 API 端点：
- `app/api/v1/stocks.py` - 股票数据查询 API
- `app/api/v1/backtest.py` - 回测执行 API
- `app/api/v1/strategies.py` - 策略管理 API

---

**版本**: 2.0.0 (新增 warning 支持)
**最后更新**: 2026-02-01
**维护者**: Stock Analysis Team
