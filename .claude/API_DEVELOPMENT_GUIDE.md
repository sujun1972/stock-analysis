# API 开发规范指南

## 概述

本文档规范了项目中 Backend API 和 Frontend 数据交互的标准格式和最佳实践。

---

## Backend API 响应格式

### 统一使用 ApiResponse

**所有 API 端点必须使用 `ApiResponse` 类包装响应**，不允许直接返回字典或 Pydantic 模型。

```python
from app.models.api_response import ApiResponse

# ✅ 正确
return ApiResponse.success(data=result, message="操作成功")

# ❌ 错误
return {"success": True, "data": result}
return result  # 直接返回 Pydantic 模型
```

### ApiResponse 方法

#### 1. 成功响应 (200)

```python
return ApiResponse.success(
    data={"key": "value"},
    message="操作成功"
)
```

#### 2. 创建成功 (201)

```python
return ApiResponse.created(
    data={"id": new_id},
    message="资源创建成功"
)
```

#### 3. 分页响应 (200)

```python
return ApiResponse.paginated(
    items=items_list,
    total=total_count,
    page=current_page,
    page_size=page_size,
    message=f"成功获取第 {current_page} 页，共 {total_count} 条记录"
)
```

#### 4. 错误响应 (400/404/500等)

```python
return ApiResponse.error(
    message="错误描述",
    code=400,
    data={"details": "..."}  # 可选
)
```

#### 5. 部分成功 (206)

```python
return ApiResponse.partial_content(
    data={"processed": 80, "failed": 20},
    message="部分数据处理成功"
)
```

### 端点装饰器规范

**移除冗余的类型注解**，让 FastAPI 自动处理序列化：

```python
# ❌ 错误 - 会导致验证错误
@router.get("/items", response_model=List[Item])
async def get_items() -> Dict[str, Any]:
    return ApiResponse.success(data=items)

# ✅ 正确 - 让 FastAPI 自动序列化
@router.get("/items")
async def get_items():
    return ApiResponse.success(data=items)
```

---

## Frontend 数据解析

### 基本响应解析

```typescript
const response = await apiClient.get('/api/xxx') as any

// 检查响应码
if (response?.code === 200) {
  const data = response.data
  // 使用数据
} else {
  toast.error(response.message || '操作失败')
}
```

### 分页数据解析

```typescript
const response = await apiClient.get('/api/xxx', { params }) as any

if (response?.code === 200 && response.data) {
  // 解构分页数据
  const { items, total, page, page_size, total_pages } = response.data

  setItems(items)
  setTotal(total)
  setCurrentPage(page)
  setTotalPages(total_pages)
}
```

### 错误处理模式

```typescript
try {
  const response = await apiClient.get('/api/xxx') as any

  if (response?.code !== 200) {
    logger.error('API请求失败', response)
    toast.error(response.message || '操作失败')
    return
  }

  // 处理成功响应
  const data = response.data
  // ...

} catch (error: any) {
  logger.error('API调用异常', error)
  toast.error(error.response?.data?.message || error.message)
}
```

---

## 数字格式化最佳实践

### 后端：自动清理 NaN/Inf

`ApiResponse` 会自动调用 `sanitize_float_values()` 清理数据中的 NaN 和 Inf 值，防止 JSON 序列化错误。

### 前端：防御性格式化

**永远不要直接使用 `.toFixed()`**，使用安全的格式化函数：

```typescript
// ✅ 正确 - 安全的格式化函数
const safeFormatNumber = (value: any, decimals: number = 2): string => {
  if (value === null || value === undefined || value === '') return '-'
  const num = typeof value === 'number' ? value : parseFloat(value)
  return isNaN(num) ? '-' : num.toFixed(decimals)
}

// 使用
<span>{safeFormatNumber(item.price, 2)}</span>

// ❌ 错误 - 不安全
<span>{item.price?.toFixed(2)}</span>  // 如果 price 是 null 会报错
```

---

## 常见错误及解决方案

### 错误 1: 检查 success 字段

```typescript
// ❌ 错误
if (response.success) { ... }

// ✅ 正确
if (response.code === 200) { ... }
```

### 错误 2: 双重嵌套访问 data

```typescript
// ❌ 错误
const items = response.data.data

// ✅ 正确
const items = response.data.items  // 分页响应
const data = response.data         // 普通响应
```

### 错误 3: 期望 meta 字段

```typescript
// ❌ 错误
const total = response.meta.total

// ✅ 正确
const total = response.data.total
```

### 错误 4: 直接使用 toFixed

```typescript
// ❌ 错误 - 可能抛出异常
const formatted = value.toFixed(2)

// ✅ 正确 - 安全处理
const formatted = safeFormatNumber(value, 2)
```

---

## 开发检查清单

### Backend 新端点

- [ ] 使用 `ApiResponse` 包装所有响应
- [ ] 移除 `response_model=Dict[str, Any]`
- [ ] 移除 `-> Dict[str, Any]` 返回类型注解
- [ ] 使用合适的 ApiResponse 方法（success/paginated/error等）
- [ ] 添加有意义的 message

### Frontend 新页面

- [ ] 使用 `response.code === 200` 检查成功
- [ ] 分页数据从 `response.data.items` 获取
- [ ] 分页信息从 `response.data` 获取（total, page, page_size, total_pages）
- [ ] 使用 `safeFormatNumber` 格式化数字
- [ ] 添加适当的错误处理和日志

### 代码审查要点

- [ ] 无直接返回字典或模型
- [ ] 无 `response.success` 检查
- [ ] 无双重嵌套 `data.data` 访问
- [ ] 无不安全的 `.toFixed()` 调用
- [ ] 统一的错误处理模式

---

## 参考资源

- ApiResponse 源码: `backend/app/models/api_response.py`
- API 迁移指南: `.claude/guides/API_RESPONSE_MIGRATION_GUIDE.md`
- 修复案例: `.claude/fixes/`

---

**最后更新**: 2026-03-15
