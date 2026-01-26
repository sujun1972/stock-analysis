## ApiResponse 统一响应模型

### 概述

`ApiResponse` 是一个统一的 API 响应模型，提供一致的响应格式和便捷的构造方法。

### 响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {
    // 实际数据
  },
  "timestamp": "2024-01-26T12:00:00",
  "request_id": "req_123456"  // 可选
}
```

### 基本使用

#### 1. 成功响应

```python
from app.models.api_response import ApiResponse

@router.get("/users")
async def get_users():
    users = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    return ApiResponse.success(data=users)
```

#### 2. 错误响应

```python
@router.get("/user/{user_id}")
async def get_user(user_id: int):
    user = find_user(user_id)
    if not user:
        return ApiResponse.not_found(message=f"User {user_id} not found")
    return ApiResponse.success(data=user)
```

#### 3. 创建资源响应

```python
@router.post("/users")
async def create_user(user: UserCreate):
    new_user = create_user_in_db(user)
    return ApiResponse.created(data=new_user, message="User created successfully")
```

#### 4. 分页响应

```python
@router.get("/users")
async def list_users(page: int = 1, page_size: int = 20):
    users, total = get_users_paginated(page, page_size)
    return ApiResponse.paginated(
        items=users,
        total=total,
        page=page,
        page_size=page_size
    )
```

### 所有便捷方法

#### 成功响应 (2xx)

```python
# 200 OK
ApiResponse.success(data={"key": "value"}, message="success")

# 201 Created
ApiResponse.created(data=new_resource, message="created")

# 204 No Content
ApiResponse.no_content(message="deleted")

# 206 Partial Content
ApiResponse.partial_content(data=partial_data, message="partial success")
```

#### 客户端错误响应 (4xx)

```python
# 400 Bad Request
ApiResponse.bad_request(message="Invalid parameters")

# 401 Unauthorized
ApiResponse.unauthorized(message="Authentication required")

# 403 Forbidden
ApiResponse.forbidden(message="Permission denied")

# 404 Not Found
ApiResponse.not_found(message="Resource not found")

# 409 Conflict
ApiResponse.conflict(message="Resource already exists")
```

#### 服务器错误响应 (5xx)

```python
# 500 Internal Server Error
ApiResponse.internal_error(message="Server error")

# 自定义状态码
ApiResponse.error(message="Custom error", code=503)
```

### 泛型支持

```python
from typing import List
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str

@router.get("/users", response_model=ApiResponse[List[User]])
async def get_users():
    users = [User(id=1, name="Alice")]
    return ApiResponse.success(data=users)
```

### 向后兼容

如果需要直接返回字典格式：

```python
from app.models.api_response import success_response, error_response

@router.get("/old-endpoint")
async def old_endpoint():
    # 返回字典而不是 Pydantic 模型
    return success_response(data={"key": "value"})

@router.get("/error")
async def error_endpoint():
    return error_response(message="Something went wrong", code=500)
```

### 与错误处理装饰器配合

```python
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse

@router.get("/data")
@handle_api_errors
async def get_data():
    # 装饰器自动处理异常
    # 这里只需要返回成功的情况
    data = await fetch_data()
    return ApiResponse.success(data=data)
```

### 请求追踪

```python
from fastapi import Request
import uuid

@router.get("/tracked")
async def tracked_endpoint(request: Request):
    request_id = str(uuid.uuid4())

    # 业务逻辑
    data = process_request()

    return ApiResponse.success(
        data=data,
        request_id=request_id
    )
```

### 最佳实践

#### 1. 使用类型注解

```python
from app.models.api_response import ApiResponse
from typing import Dict, List

@router.get("/users", response_model=ApiResponse[List[Dict]])
async def get_users():
    return ApiResponse.success(data=[...])
```

#### 2. 一致的消息格式

```python
# Good
ApiResponse.success(message="Users retrieved successfully")
ApiResponse.error(message="Failed to retrieve users", code=500)

# Bad
ApiResponse.success(message="ok")  # 不够描述性
ApiResponse.error(message="error")  # 不够具体
```

#### 3. 合理使用状态码

```python
# 创建资源
@router.post("/users")
async def create_user(user: UserCreate):
    return ApiResponse.created(data=new_user)  # 201

# 删除资源
@router.delete("/users/{id}")
async def delete_user(id: int):
    delete_from_db(id)
    return ApiResponse.no_content()  # 204

# 部分成功
@router.post("/batch")
async def batch_process(items: List[Item]):
    results = process_items(items)
    if results['failed'] > 0:
        return ApiResponse.partial_content(data=results)  # 206
    return ApiResponse.success(data=results)  # 200
```

#### 4. 错误详情

```python
@router.post("/validate")
async def validate_data(data: DataModel):
    errors = validate(data)
    if errors:
        return ApiResponse.bad_request(
            message="Validation failed",
            data={"errors": errors}  # 提供详细错误信息
        )
    return ApiResponse.success(data={"valid": True})
```

### 迁移现有代码

#### Before (手动构造字典)

```python
@router.get("/old")
async def old_endpoint():
    try:
        data = fetch_data()
        return {
            "code": 200,
            "message": "success",
            "data": data
        }
    except Exception as e:
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }
```

#### After (使用 ApiResponse)

```python
@router.get("/new")
@handle_api_errors  # 错误处理由装饰器负责
async def new_endpoint():
    data = fetch_data()
    return ApiResponse.success(data=data)
```

### 测试

```python
import pytest
from app.models.api_response import ApiResponse

def test_success_response():
    response = ApiResponse.success(data={"key": "value"})
    assert response.code == 200
    assert response.message == "success"
    assert response.data == {"key": "value"}

def test_error_response():
    response = ApiResponse.not_found(message="User not found")
    assert response.code == 404
    assert response.message == "User not found"
    assert response.data is None

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
```

### FastAPI 集成

```python
from fastapi import FastAPI, HTTPException
from app.models.api_response import ApiResponse
from app.api.error_handler import handle_api_errors

app = FastAPI()

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return ApiResponse.error(
        message=exc.detail,
        code=exc.status_code
    )

@app.get("/example")
@handle_api_errors
async def example():
    return ApiResponse.success(data={"example": "data"})
```
