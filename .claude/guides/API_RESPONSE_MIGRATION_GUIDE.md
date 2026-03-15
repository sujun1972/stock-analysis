# API 响应格式统一迁移指南

## 概述

本项目已完成从混合响应格式到统一 `ApiResponse` 格式的全面迁移。本文档说明：
- 标准的 API 响应格式
- 前端如何正确解析响应
- 常见错误及解决方案

---

## 标准响应格式

### 成功响应

```json
{
  "code": 200,
  "message": "操作成功的描述",
  "data": { ... },
  "timestamp": "2026-03-15T20:00:00.123456",
  "request_id": null,
  "api_version": null,
  "deprecation": null
}
```

### 分页响应

```json
{
  "code": 200,
  "message": "成功获取第 X 页，共 Y 个XXX",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  },
  "timestamp": "..."
}
```

### 错误响应

```json
{
  "code": 400,
  "message": "错误描述",
  "data": { "details": "..." },
  "timestamp": "..."
}
```

---

## Frontend 解析最佳实践

### 基本响应解析

```typescript
const response = await apiClient.get('/api/xxx') as any

if (response?.code === 200) {
  const data = response.data
  // 使用 data
} else {
  console.error(response.message)
}
```

### 分页数据解析

```typescript
const response = await apiClient.get('/api/xxx', { params }) as any

if (response?.code === 200 && response.data) {
  const { items, total, page, page_size, total_pages } = response.data

  setItems(items)
  setTotal(total)
  setCurrentPage(page)
  setTotalPages(total_pages)
}
```

### 错误处理

```typescript
try {
  const response = await apiClient.get('/api/xxx') as any

  if (response?.code !== 200) {
    toast.error(response.message || '操作失败')
    return
  }

  // 处理成功响应
} catch (error: any) {
  logger.error('API调用失败', error)
  toast.error(error.response?.data?.message || error.message)
}
```

---

## 常见错误模式

### ❌ 错误 1: 检查 success 字段

```typescript
// ❌ 错误 - ApiResponse 没有 success 字段
if (response.success) { ... }

// ✅ 正确
if (response.code === 200) { ... }
```

### ❌ 错误 2: 双重嵌套访问

```typescript
// ❌ 错误
const items = response.data.data

// ✅ 正确
const items = response.data.items  // 对于分页响应
const data = response.data         // 对于普通响应
```

### ❌ 错误 3: 期望 meta 字段

```typescript
// ❌ 错误 - 没有单独的 meta 字段
const total = response.meta.total

// ✅ 正确
const total = response.data.total
```

---

## Backend ApiResponse 使用

### 成功响应

```python
from app.models.api_response import ApiResponse

# 简单成功
return ApiResponse.success(
    data={"key": "value"},
    message="操作成功"
)

# 分页响应
return ApiResponse.paginated(
    items=items,
    total=total,
    page=page,
    page_size=page_size,
    message=f"成功获取第 {page} 页，共 {total} 条记录"
)

# 创建成功 (201)
return ApiResponse.created(
    data={"id": new_id},
    message="创建成功"
)
```

### 错误响应

```python
# 客户端错误 (400)
return ApiResponse.error(
    message="参数错误",
    code=400,
    data={"field": "error details"}
)

# 服务器错误 (500)
return ApiResponse.error(
    message="服务器内部错误",
    code=500
)
```

### 部分成功 (206)

```python
return ApiResponse.partial_content(
    data={"processed": 50, "failed": 10},
    message="部分数据处理成功"
)
```

---

## 迁移检查清单

### Backend 端点检查

- [ ] 移除 `response_model=Dict[str, Any]`
- [ ] 移除 `-> Dict[str, Any]` 返回类型注解
- [ ] 使用 `ApiResponse.success()` 或 `ApiResponse.paginated()`
- [ ] 确保所有端点返回统一格式

### Frontend 页面检查

- [ ] 检查 `response.code === 200` 而非 `response.success`
- [ ] 分页数据从 `response.data.items` 获取
- [ ] 分页信息从 `response.data` 直接获取
- [ ] 添加适当的错误处理

---

## 已修复的问题

### 1. AI Strategy API (2026-03-15)
- 修复了 8 个 AI 策略相关端点
- 前端页面: `sentiment/ai-analysis`, `sentiment/premarket`
- 详见: [AI_STRATEGY_API_FIX.md](../AI_STRATEGY_API_FIX.md)

### 2. 策略列表页面 (2026-03-15)
- 修复了策略列表数据解析错误
- 修复了用户列表数据解析错误
- 详见: [STRATEGIES_PAGE_FIX.md](../STRATEGIES_PAGE_FIX.md)

### 3. Frontend toFixed 错误 (2026-03-15)
- 修复了情绪数据页面的数字格式化错误
- 添加了 `safeFormatNumber` 工具函数
- 详见: [FRONTEND_FIX_TOFIX_ERROR.md](../FRONTEND_FIX_TOFIX_ERROR.md)

---

## 参考资源

- ApiResponse 源码: `backend/app/models/api_response.py`
- API 客户端: `admin/lib/api-client.ts`
- 前端类型定义: `admin/types/api.ts`
