# API 统一响应格式规范

## 概述

本文档定义了 Backend API 的统一响应格式规范，确保所有 API 端点返回一致的数据结构。

**版本:** 2.0
**生效日期:** 2026-03-14
**适用范围:** 所有 `/api/*` 端点

---

## 核心原则

1. **一致性**: 所有 API 响应使用相同的顶层结构
2. **可预测性**: 客户端可以依赖固定的字段和数据类型
3. **完整性**: 提供足够的元数据支持调试和追踪
4. **扩展性**: 支持版本演进和功能扩展

---

## 标准响应格式

### 基本结构

```typescript
interface ApiResponse<T> {
  code: number;              // HTTP 状态码
  message: string;           // 响应消息
  data: T | null;           // 响应数据（泛型）
  timestamp: string;         // 响应时间戳 (ISO 8601)
  success: boolean;          // 便捷成功标识
  request_id?: string;       // 请求追踪 ID（可选）
  api_version?: string;      // API 版本号（可选）
  deprecation?: DeprecationWarning;  // 弃用警告（可选）
}
```

### 字段说明

#### 必需字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `code` | `number` | HTTP 状态码 | `200`, `400`, `500` |
| `message` | `string` | 简短的响应消息 | `"success"`, `"参数错误"` |
| `data` | `T \| null` | 实际的响应数据，泛型类型 | `{...}`, `null` |
| `timestamp` | `string` | 响应生成时间 (ISO 8601) | `"2026-03-14T12:00:00"` |
| `success` | `boolean` | 请求是否成功 (`code < 400`) | `true`, `false` |

#### 可选字段

| 字段 | 类型 | 说明 | 何时出现 |
|------|------|------|----------|
| `request_id` | `string` | 请求唯一标识符 | 用于追踪和调试 |
| `api_version` | `string` | API 版本号 | 明确标识使用的 API 版本 |
| `deprecation` | `DeprecationWarning` | 弃用警告信息 | 调用已弃用的端点时 |

---

## 响应类型

### 1. 成功响应

#### 1.1 标准成功 (200 OK)

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "user_id": "123",
    "username": "john_doe"
  },
  "timestamp": "2026-03-14T12:00:00",
  "success": true
}
```

**使用场景:** 查询操作成功、更新操作成功

**Python 示例:**
```python
from app.models.api_response import ApiResponse

return ApiResponse.success(
    data={"user_id": "123", "username": "john_doe"}
)
```

#### 1.2 创建成功 (201 Created)

```json
{
  "code": 201,
  "message": "created",
  "data": {
    "strategy_id": "abc123",
    "created_at": "2026-03-14T12:00:00"
  },
  "timestamp": "2026-03-14T12:00:00",
  "success": true
}
```

**使用场景:** 资源创建成功（POST 请求）

**Python 示例:**
```python
return ApiResponse.created(
    data={"strategy_id": "abc123", "created_at": "..."}
)
```

#### 1.3 无内容 (204 No Content)

```json
{
  "code": 204,
  "message": "no content",
  "data": null,
  "timestamp": "2026-03-14T12:00:00",
  "success": true
}
```

**使用场景:** 删除操作成功、更新操作成功但无返回数据

**Python 示例:**
```python
return ApiResponse.no_content()
```

#### 1.4 部分内容/警告 (206 Partial Content)

```json
{
  "code": 206,
  "message": "数据质量较低，请注意风险",
  "data": {
    "result": {...},
    "warning_code": "LOW_QUALITY",
    "quality_score": 0.75
  },
  "timestamp": "2026-03-14T12:00:00",
  "success": true
}
```

**使用场景:** 操作成功但存在警告、部分数据可用

**Python 示例:**
```python
return ApiResponse.warning(
    data={"result": {...}},
    message="数据质量较低，请注意风险",
    warning_code="LOW_QUALITY",
    quality_score=0.75
)
```

---

### 2. 分页响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {"id": 1, "name": "Item 1"},
      {"id": 2, "name": "Item 2"}
    ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  },
  "timestamp": "2026-03-14T12:00:00",
  "success": true
}
```

**分页数据结构:**

| 字段 | 类型 | 说明 |
|------|------|------|
| `items` | `array` | 当前页的数据列表 |
| `total` | `number` | 总记录数 |
| `page` | `number` | 当前页码（从 1 开始） |
| `page_size` | `number` | 每页大小 |
| `total_pages` | `number` | 总页数 |

**Python 示例:**
```python
return ApiResponse.paginated(
    items=[...],
    total=100,
    page=1,
    page_size=20
)
```

---

### 3. 错误响应

#### 3.1 客户端错误 (4xx)

##### 400 Bad Request（参数错误）

```json
{
  "code": 400,
  "message": "参数验证失败",
  "data": {
    "error_code": "VALIDATION_ERROR",
    "details": [
      {
        "field": "email",
        "message": "邮箱格式不正确"
      },
      {
        "field": "age",
        "message": "年龄必须大于 0"
      }
    ]
  },
  "timestamp": "2026-03-14T12:00:00",
  "success": false
}
```

**Python 示例:**
```python
return ApiResponse.bad_request(
    message="参数验证失败",
    data={
        "error_code": "VALIDATION_ERROR",
        "details": [...]
    }
)
```

##### 401 Unauthorized（未授权）

```json
{
  "code": 401,
  "message": "未授权访问",
  "data": {
    "error_code": "UNAUTHORIZED",
    "details": "Token 已过期或无效"
  },
  "timestamp": "2026-03-14T12:00:00",
  "success": false
}
```

**Python 示例:**
```python
return ApiResponse.unauthorized(
    message="未授权访问",
    data={"error_code": "UNAUTHORIZED", "details": "Token 已过期或无效"}
)
```

##### 403 Forbidden（禁止访问）

```json
{
  "code": 403,
  "message": "权限不足",
  "data": {
    "error_code": "FORBIDDEN",
    "required_permission": "admin"
  },
  "timestamp": "2026-03-14T12:00:00",
  "success": false
}
```

##### 404 Not Found（资源不存在）

```json
{
  "code": 404,
  "message": "资源不存在",
  "data": {
    "error_code": "RESOURCE_NOT_FOUND",
    "resource_type": "strategy",
    "resource_id": "abc123"
  },
  "timestamp": "2026-03-14T12:00:00",
  "success": false
}
```

**Python 示例:**
```python
return ApiResponse.not_found(
    message="策略不存在",
    data={
        "error_code": "RESOURCE_NOT_FOUND",
        "resource_type": "strategy",
        "resource_id": "abc123"
    }
)
```

##### 409 Conflict（资源冲突）

```json
{
  "code": 409,
  "message": "资源已存在",
  "data": {
    "error_code": "RESOURCE_CONFLICT",
    "conflicting_field": "strategy_name",
    "existing_id": "xyz789"
  },
  "timestamp": "2026-03-14T12:00:00",
  "success": false
}
```

#### 3.2 服务器错误 (5xx)

##### 500 Internal Server Error

```json
{
  "code": 500,
  "message": "服务器内部错误",
  "data": {
    "error_code": "INTERNAL_ERROR",
    "details": "数据库连接失败"
  },
  "timestamp": "2026-03-14T12:00:00",
  "success": false,
  "request_id": "req_abc123"
}
```

**Python 示例:**
```python
return ApiResponse.internal_error(
    message="服务器内部错误",
    data={"error_code": "INTERNAL_ERROR", "details": "..."},
    request_id="req_abc123"
)
```

---

### 4. 带版本信息的响应

```json
{
  "code": 200,
  "message": "success",
  "data": {...},
  "timestamp": "2026-03-14T12:00:00",
  "success": true,
  "api_version": "2.0"
}
```

**自动添加:** API 版本中间件会自动在响应中添加版本信息

---

### 5. 带弃用警告的响应

```json
{
  "code": 200,
  "message": "success",
  "data": {...},
  "timestamp": "2026-03-14T12:00:00",
  "success": true,
  "deprecation": {
    "deprecated": true,
    "deprecated_since": "2.0",
    "removal_date": "2026-09-01",
    "alternative": "/api/strategies",
    "reason": "使用新的统一策略系统"
  }
}
```

**自动添加:** 使用 `@deprecated` 装饰器的端点会自动添加弃用警告

---

## HTTP 状态码规范

### 成功状态码 (2xx)

| 状态码 | 名称 | 使用场景 | 示例 |
|--------|------|----------|------|
| 200 | OK | 查询成功、更新成功 | 获取用户信息、更新策略 |
| 201 | Created | 创建资源成功 | 创建新策略、注册新用户 |
| 204 | No Content | 操作成功但无内容返回 | 删除策略、清空缓存 |
| 206 | Partial Content | 部分成功或带警告 | 数据质量低、批量操作部分失败 |

### 客户端错误 (4xx)

| 状态码 | 名称 | 使用场景 | 示例 |
|--------|------|----------|------|
| 400 | Bad Request | 参数错误、验证失败 | 邮箱格式错误、缺少必需参数 |
| 401 | Unauthorized | 未登录或 Token 无效 | Token 过期、未提供认证信息 |
| 403 | Forbidden | 权限不足 | 普通用户访问管理员接口 |
| 404 | Not Found | 资源不存在 | 策略 ID 不存在、用户不存在 |
| 409 | Conflict | 资源冲突 | 用户名已存在、策略名重复 |
| 429 | Too Many Requests | 请求频率限制 | API 调用超过限额 |

### 服务器错误 (5xx)

| 状态码 | 名称 | 使用场景 | 示例 |
|--------|------|----------|------|
| 500 | Internal Server Error | 服务器内部错误 | 数据库错误、未捕获的异常 |
| 502 | Bad Gateway | 外部服务错误 | 调用 Tushare API 失败 |
| 503 | Service Unavailable | 服务不可用 | 数据库连接超时、Redis 不可用 |
| 504 | Gateway Timeout | 外部服务超时 | 调用 LLM API 超时 |

---

## 错误代码规范

### 错误代码格式

```
<CATEGORY>_<SPECIFIC_ERROR>
```

例如：`VALIDATION_ERROR`, `DATABASE_CONNECTION_ERROR`

### 标准错误代码

| 错误代码 | HTTP 状态码 | 说明 |
|----------|-------------|------|
| `VALIDATION_ERROR` | 400 | 参数验证失败 |
| `MISSING_REQUIRED_FIELD` | 400 | 缺少必需字段 |
| `INVALID_FORMAT` | 400 | 格式不正确 |
| `UNAUTHORIZED` | 401 | 未授权 |
| `TOKEN_EXPIRED` | 401 | Token 已过期 |
| `FORBIDDEN` | 403 | 权限不足 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 |
| `RESOURCE_CONFLICT` | 409 | 资源冲突 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `DATABASE_ERROR` | 500 | 数据库错误 |
| `EXTERNAL_API_ERROR` | 502 | 外部 API 错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |
| `TIMEOUT_ERROR` | 504 | 超时错误 |

---

## 使用指南

### 在端点中使用

#### 方式 1: 使用 ApiResponse 类（推荐）

```python
from fastapi import APIRouter
from app.models.api_response import ApiResponse

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await get_user_from_db(user_id)

    if not user:
        return ApiResponse.not_found(
            message="用户不存在",
            data={"error_code": "USER_NOT_FOUND", "user_id": user_id}
        )

    return ApiResponse.success(data=user)
```

#### 方式 2: 使用便捷函数

```python
from app.models.api_response import success_response, error_response

@router.post("/strategies")
async def create_strategy(data: dict):
    try:
        strategy_id = await create_strategy_in_db(data)
        return success_response(
            data={"strategy_id": strategy_id},
            message="策略创建成功"
        )
    except ValueError as e:
        return error_response(
            message=str(e),
            code=400,
            data={"error_code": "VALIDATION_ERROR"}
        )
```

#### 方式 3: 直接返回 ApiResponse 对象

```python
@router.get("/strategies")
async def list_strategies(page: int = 1, page_size: int = 20):
    strategies = await get_strategies_from_db(page, page_size)
    total = await get_total_count()

    return ApiResponse.paginated(
        items=strategies,
        total=total,
        page=page,
        page_size=page_size
    )
```

### 错误处理最佳实践

#### 使用 @handle_api_errors 装饰器

```python
from app.api.error_handler import handle_api_errors
from app.core.exceptions import DataNotFoundError

@router.get("/strategies/{strategy_id}")
@handle_api_errors
async def get_strategy(strategy_id: str):
    # 如果抛出异常，装饰器会自动转换为标准响应
    strategy = await get_strategy_or_raise(strategy_id)
    return ApiResponse.success(data=strategy)

async def get_strategy_or_raise(strategy_id: str):
    strategy = await db.get(strategy_id)
    if not strategy:
        raise DataNotFoundError(f"Strategy {strategy_id} not found")
    return strategy
```

---

## 客户端使用示例

### JavaScript/TypeScript

```typescript
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T | null;
  timestamp: string;
  success: boolean;
  request_id?: string;
  api_version?: string;
  deprecation?: DeprecationWarning;
}

async function fetchStrategy(strategyId: string): Promise<Strategy> {
  const response = await fetch(`/api/strategies/${strategyId}`, {
    headers: {
      'X-API-Version': '2.0'
    }
  });

  const result: ApiResponse<Strategy> = await response.json();

  if (!result.success) {
    throw new Error(result.message);
  }

  // 检查弃用警告
  if (result.deprecation) {
    console.warn(`API Deprecated: ${result.deprecation.alternative}`);
  }

  return result.data!;
}
```

### Python

```python
import requests
from typing import TypeVar, Generic, Optional

T = TypeVar('T')

class ApiResponse(Generic[T]):
    code: int
    message: str
    data: Optional[T]
    success: bool

    @classmethod
    def from_response(cls, response: requests.Response):
        json_data = response.json()
        return cls(**json_data)

def get_strategy(strategy_id: str) -> dict:
    response = requests.get(
        f"https://api.example.com/api/strategies/{strategy_id}",
        headers={"X-API-Version": "2.0"}
    )

    result = ApiResponse.from_response(response)

    if not result.success:
        raise Exception(result.message)

    return result.data
```

---

## 迁移指南

### 从旧格式迁移

#### 旧格式
```json
{
  "success": true,
  "data": {...},
  "meta": {...}
}
```

#### 新格式
```json
{
  "code": 200,
  "message": "success",
  "data": {...},
  "timestamp": "2026-03-14T12:00:00",
  "success": true
}
```

#### 客户端兼容性处理

```javascript
function normalizeResponse(response) {
  // 兼容旧格式
  if (response.success !== undefined && response.code === undefined) {
    return {
      code: response.success ? 200 : 500,
      message: response.success ? "success" : "error",
      data: response.data,
      success: response.success
    };
  }
  return response;
}
```

---

## 常见问题

### Q: 为什么同时有 `code` 和 `success` 字段？

**A:** `code` 提供精确的 HTTP 状态码，`success` 提供快速的布尔判断。这样客户端可以灵活选择：
```javascript
// 方式 1: 使用 success
if (response.success) { ... }

// 方式 2: 使用 code
if (response.code === 200) { ... }
```

### Q: 什么时候应该使用 206 状态码？

**A:** 当操作成功但存在需要注意的警告时。例如：
- 数据质量较低
- 批量操作部分失败
- 使用了降级方案

### Q: `data` 可以是什么类型？

**A:** `data` 是泛型字段，可以是：
- 对象 `{...}`
- 数组 `[...]`
- 字符串 `"..."`
- 数字 `123`
- `null`

### Q: 错误响应中 `data` 应该包含什么？

**A:** 建议包含：
- `error_code`: 标准错误代码
- `details`: 详细错误信息
- 其他上下文信息（如字段名、资源 ID）

---

## 附录

### A. 完整的 TypeScript 类型定义

```typescript
// 弃用警告
interface DeprecationWarning {
  deprecated: true;
  deprecated_since: string;
  removal_date?: string;
  alternative?: string;
  reason?: string;
}

// API 响应
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T | null;
  timestamp: string;
  success: boolean;
  request_id?: string;
  api_version?: string;
  deprecation?: DeprecationWarning;
}

// 分页数据
interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// 错误详情
interface ErrorDetails {
  error_code: string;
  details?: string | object;
  [key: string]: any;
}
```

### B. Python Pydantic 模型

```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")

class DeprecationWarning(BaseModel):
    deprecated: bool = True
    deprecated_since: str
    removal_date: Optional[str] = None
    alternative: Optional[str] = None
    reason: Optional[str] = None

class ApiResponse(BaseModel, Generic[T]):
    code: int
    message: str
    data: Optional[T] = None
    timestamp: str
    success: bool
    request_id: Optional[str] = None
    api_version: Optional[str] = None
    deprecation: Optional[DeprecationWarning] = None
```

---

**文档版本:** 2.0
**最后更新:** 2026-03-14
**维护者:** Backend API Team
