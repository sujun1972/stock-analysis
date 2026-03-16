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

**重要：直接返回 ApiResponse 对象，FastAPI 会自动序列化**

#### 1. 成功响应 (200)

```python
@router.get("/items", response_model=ApiResponse)
async def get_items():
    return ApiResponse.success(
        data={"key": "value"},
        message="操作成功"
    )
```

#### 2. 创建成功 (201)

```python
@router.post("/items", response_model=ApiResponse)
async def create_item():
    return ApiResponse.created(
        data={"id": new_id},
        message="资源创建成功"
    )
```

#### 3. 分页响应 (200)

```python
@router.get("/items", response_model=ApiResponse)
async def get_items():
    return ApiResponse.success(
        data={
            "items": items_list,
            "pagination": {
                "total": total_count,
                "page": current_page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }
    )
```

#### 4. 错误响应 (400/404/500等)

```python
# 注意：错误响应通常通过 HTTPException 抛出，不直接返回
raise HTTPException(status_code=400, detail="错误描述")

# 或者在异常处理器中使用 ApiResponse
return ApiResponse.error(
    message="错误描述",
    code=400,
    data={"details": "..."}  # 可选
)
```

#### 5. 部分成功 (206)

```python
@router.post("/batch", response_model=ApiResponse)
async def batch_process():
    return ApiResponse.partial_content(
        data={"processed": 80, "failed": 20},
        message="部分数据处理成功"
    )
```

### 端点装饰器规范

**必须使用 `response_model=ApiResponse`**，让 FastAPI 正确序列化响应：

```python
# ❌ 错误 - 会导致 Pydantic 验证错误
@router.get("/items", response_model=dict)
async def get_items():
    return ApiResponse.success(data=items)

# ❌ 错误 - 缺少 response_model
@router.get("/items")
async def get_items():
    return ApiResponse.success(data=items).to_dict()

# ✅ 正确 - 使用 response_model=ApiResponse
@router.get("/items", response_model=ApiResponse)
async def get_items():
    return ApiResponse.success(data=items)
```

**常见错误：**

```python
# ❌ 错误 - response_model=dict 无法序列化 ApiResponse 对象
@router.get("/items", response_model=dict)

# ❌ 错误 - 使用错误的导入路径
from app.utils.response import ApiResponse  # 不存在

# ❌ 错误 - 返回字典而不是 ApiResponse 对象
@router.get("/items", response_model=ApiResponse)
async def get_items():
    return {"code": 200, "data": items}

# ✅ 正确 - 完整示例
from app.models.api_response import ApiResponse

@router.get("/items", response_model=ApiResponse)
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

### 错误 3: 期望 meta 字段在顶层

```typescript
// ❌ 错误 - meta 不在顶层
const total = response.meta.total

// ✅ 正确 - meta 在 data 下
const total = response.data.meta.total
```

**常见场景**：分页数据结构
```typescript
// 后端返回
return ApiResponse.success(data={
    "items": result['items'],
    "meta": result['meta']
})

// 前端正确解析
if (response?.code === 200 && response.data) {
  setStrategies(response.data.items || [])
  if (response.data.meta) {
    setTotalPages(response.data.meta.total_pages || 1)
    setTotalCount(response.data.meta.total || 0)
  }
}
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

- [ ] 使用正确的导入：`from app.models.api_response import ApiResponse`
- [ ] **装饰器必须使用 `response_model=ApiResponse`**
- [ ] **直接返回 ApiResponse 对象，不要调用 `.to_dict()`**
- [ ] 不要使用 `response_model=dict` 或 `response_model=Dict[str, Any]`
- [ ] 使用合适的 ApiResponse 方法（success/error等）
- [ ] 添加有意义的 message
- [ ] 对于分页响应，将 items 和 pagination 放在 data 字段中

### Frontend 新页面

- [ ] 使用 `response.code === 200` 检查成功
- [ ] 分页数据从 `response.data.items` 获取
- [ ] 分页信息从 `response.data` 获取（total, page, page_size, total_pages）
- [ ] 使用 `safeFormatNumber` 格式化数字
- [ ] 添加适当的错误处理和日志

### 代码审查要点

- [ ] 所有端点装饰器使用 `response_model=ApiResponse`
- [ ] 直接返回 ApiResponse 对象（不调用 `.to_dict()`）
- [ ] 使用正确的导入路径 `app.models.api_response`
- [ ] 无 `response_model=dict` 配置
- [ ] 无直接返回字典
- [ ] 无 `response.success` 检查（前端）
- [ ] 无双重嵌套 `data.data` 访问（前端）
- [ ] 无不安全的 `.toFixed()` 调用（前端）
- [ ] 统一的错误处理模式

---

## 参考资源

- ApiResponse 源码: `backend/app/models/api_response.py`
- API 迁移指南: `.claude/guides/API_RESPONSE_MIGRATION_GUIDE.md`
- 修复案例: `.claude/fixes/`

---

## 已完成的迁移工作

### Backend (已完成)
- ✅ 统一 48 个 API 端点使用 ApiResponse 格式
- ✅ 涉及 10 个文件: auth.py, profile.py, premarket.py, concepts.py, sync.py, system_logs.py, experiment.py, ml.py, scheduler.py, notification_channels.py
- ✅ 提交: `4109660` - refactor(api): 统一所有API端点使用ApiResponse标准格式

### Admin 项目 (已完成)
- ✅ 修复 5 个核心文件的 API 响应解析
- ✅ 文件: auth-store.ts, notification-channels/page.tsx, logs/system/page.tsx, strategies/pending-review/page.tsx, strategies/[id]/review/page.tsx
- ✅ 提交: `ffbf5ed` - fix(admin): 适配后端 API 响应格式标准化 (ApiResponse)

### Frontend 项目 (已完成)
- ✅ 修复 3 个核心文件的 API 响应解析
- ✅ 文件: auth-store.ts, settings/notifications/page.tsx, profile/page.tsx
- ✅ 提交: `fcc16cf` - fix(frontend): 适配后端 API 响应格式标准化 (ApiResponse)

### 遗留工作
- ⚠️ 其他页面可能仍需适配（非核心功能页面）
- 📝 建议在发现问题时逐步修复

---

## 修复记录

### 2026-03-16 (1): 修复 response_model 配置错误

**问题**：
- `llm_logs.py` 和 `system_logs.py` 中使用 `response_model=dict`
- 导致 FastAPI 尝试将 `ApiResponse` 对象验证为 dict 时抛出 500 错误
- 错误信息: `Input should be a valid dictionary`

**修复**：
- 将所有 `response_model=dict` 改为 `response_model=ApiResponse`
- 受影响文件：
  - `backend/app/api/endpoints/llm_logs.py` (1 个端点)
  - `backend/app/api/endpoints/system_logs.py` (3 个端点)

**重要提醒**：
- ✅ **正确**: `@router.get("/list", response_model=ApiResponse)`
- ❌ **错误**: `@router.get("/list", response_model=dict)`
- 直接返回 `ApiResponse` 对象，FastAPI 会自动序列化
- 不需要调用 `.to_dict()`

---

### 2026-03-16 (2): 修复 Admin 分页数据解析错误

**问题**：
- `/strategies/pending-review` 页面报错: `strategies.map is not a function`
- 前端错误地将 `response.data` (对象) 当作数组使用
- 后端返回格式: `{code: 200, data: {items: [...], meta: {...}}}`

**根本原因**：
- 前端期望 `response.data` 是数组，但实际是包含 `items` 和 `meta` 的对象
- 分页信息位置错误：使用 `response.meta` 而非 `response.data.meta`

**修复**：
```typescript
// ❌ 错误
setStrategies(response.data)
if (response.meta) {
  setTotalPages(response.meta.total_pages || 1)
}

// ✅ 正确
setStrategies(response.data.items || [])
if (response.data.meta) {
  setTotalPages(response.data.meta.total_pages || 1)
}
```

**受影响文件**：
- `admin/app/(dashboard)/strategies/pending-review/page.tsx`

**关键点**：
- 分页数据中，数组在 `response.data.items`
- 分页信息在 `response.data.meta`，不在顶层 `response.meta`
- 始终添加 `|| []` 作为默认值，防止 undefined

---

**最后更新**: 2026-03-16 (修复 Admin 分页数据解析错误)
