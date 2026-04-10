# Backend API 权限控制文档

## 📋 权限体系

本项目实现了三级权限控制体系：

### 权限级别

| 权限级别 | 说明 | 实现方式 |
|---------|------|---------|
| 🌍 **公开 (Public)** | 无需登录即可访问 | 无依赖注入 |
| 👤 **普通用户 (User)** | 需要登录且账户活跃 | `Depends(get_current_active_user)` |
| 🔐 **管理员 (Admin)** | 需要管理员或超级管理员角色 | `Depends(require_admin)` |

### 用户角色

系统支持以下用户角色（`users.role` 字段）：

- `trial_user` - 试用用户（默认注册角色）
- `normal_user` - 普通用户
- `vip_user` - VIP用户
- `admin` - 管理员
- `super_admin` - 超级管理员

---

## 🔧 实现方式

### 1. 普通用户权限

```python
from fastapi import Depends
from app.core.dependencies import get_current_active_user
from app.models.user import User

@router.post("/some-endpoint")
async def some_function(
    param: str,
    current_user: User = Depends(get_current_active_user)
):
    """需要登录的端点"""
    # current_user 包含当前登录用户的完整信息
    # 可以通过 current_user.id, current_user.role 等访问用户属性
    pass
```

**验证逻辑**：
1. ✅ JWT Token 有效性
2. ✅ 用户存在于数据库
3. ✅ 账户状态为活跃 (`is_active=True`)

**适用角色**: 所有角色（trial_user, normal_user, vip_user, admin, super_admin）

### 2. 管理员权限

```python
from fastapi import Depends
from app.core.dependencies import require_admin
from app.models.user import User

@router.post("/admin-endpoint")
async def admin_function(
    param: str,
    current_user: User = Depends(require_admin)
):
    """需要管理员权限的端点"""
    # 只有 admin 或 super_admin 角色可以访问
    pass
```

**验证逻辑**：
1. ✅ 继承 `get_current_active_user` 的所有验证
2. ✅ 角色必须是 `admin` 或 `super_admin`

**适用角色**: 仅限 admin, super_admin

### 3. 公开接口

```python
@router.get("/public-endpoint")
async def public_function(param: str):
    """公开接口，无需登录"""
    pass
```

**无需任何验证**，任何人都可访问。

---

## 📊 权限分配原则

### 公开接口 (Public)

- 用户注册、登录、Token刷新
- 股票基础信息查询（列表、详情）
- 概念板块信息查询
- 市场状态、交易时段查询
- 策略列表浏览（策略库公开展示）
- 可用特征列表

### 普通用户权限 (User)

- 个人资料管理（查看、修改、密码修改）
- 股票数据查询（日线、分时、批量查询）
- 策略管理（创建、修改、删除、测试）
- 策略发布申请、撤回
- 回测执行（同步、异步、并行）
- 机器学习（训练、预测、实验管理）
- 市场情绪数据查询
- 特征计算与选择
- AI策略生成

### 管理员权限 (Admin)

- 用户管理（增删改查、配额管理）
- 数据下载与同步
- 概念数据同步
- 定时任务管理
- 系统配置管理
- 策略审核（批准、拒绝、下架）
- LLM日志查看与分析
- 提示词模板管理
- AI提供商配置

---

## 🚨 错误处理

### 401 Unauthorized - 未登录或Token无效

```json
{
  "detail": "Could not validate credentials"
}
```

**原因**：
- 未提供 Authorization header
- Token 过期
- Token 格式错误
- Token 签名无效

**解决方案**：
- 跳转到登录页面
- 使用 refresh token 刷新 access token

### 403 Forbidden - 权限不足

```json
{
  "detail": "需要管理员权限"
}
```

**原因**：
- 普通用户访问管理员端点
- 账户被禁用 (`is_active=False`)

**解决方案**：
- 提示用户权限不足
- 隐藏无权限访问的UI元素

---

## 🔐 安全最佳实践

### 1. Token 管理

```typescript
// 前端示例
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});

// 拦截器处理401
apiClient.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      // 尝试刷新token
      const newToken = await refreshAccessToken();
      if (newToken) {
        // 重试请求
        error.config.headers['Authorization'] = `Bearer ${newToken}`;
        return apiClient.request(error.config);
      }
      // 刷新失败，跳转登录
      router.push('/login');
    }
    return Promise.reject(error);
  }
);
```

### 2. 权限检查

```typescript
// 前端权限检查
function hasPermission(userRole: string, requiredRole: 'user' | 'admin'): boolean {
  if (requiredRole === 'user') {
    return ['trial_user', 'normal_user', 'vip_user', 'admin', 'super_admin'].includes(userRole);
  }
  if (requiredRole === 'admin') {
    return ['admin', 'super_admin'].includes(userRole);
  }
  return false;
}

// 条件渲染
{hasPermission(user.role, 'admin') && (
  <AdminPanel />
)}
```

### 3. 数据隔离

对于用户私有数据（如回测历史、训练任务），后端应该自动过滤：

```python
@router.get("/backtest-history")
async def get_backtest_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 自动过滤为当前用户的数据
    executions = db.query(StrategyExecution).filter(
        StrategyExecution.user_id == current_user.id
    ).all()
    return executions
```

---

## 📝 权限迁移指南

### 为已有端点添加权限

1. **导入依赖**：
```python
from fastapi import Depends
from app.core.dependencies import get_current_active_user, require_admin
from app.models.user import User
```

2. **添加参数**：
```python
# 普通用户权限
async def my_endpoint(
    param: str,
    current_user: User = Depends(get_current_active_user)
):
    pass

# 管理员权限
async def admin_endpoint(
    param: str,
    current_user: User = Depends(require_admin)
):
    pass
```

3. **使用用户信息**（可选）：
```python
async def create_strategy(
    data: StrategyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 自动关联创建者
    strategy = Strategy(
        **data.dict(),
        created_by=current_user.id,
        creator_name=current_user.username
    )
    db.add(strategy)
    db.commit()
    return strategy
```

---

## 🧪 测试

### 单元测试示例

```python
# tests/test_permissions.py
import pytest
from fastapi.testclient import TestClient

def test_public_endpoint_without_auth(client: TestClient):
    """公开端点无需认证"""
    response = client.get("/api/stocks/list")
    assert response.status_code == 200

def test_protected_endpoint_without_auth(client: TestClient):
    """受保护端点需要认证"""
    response = client.post("/api/backtest/run")
    assert response.status_code == 401

def test_protected_endpoint_with_user_token(client: TestClient, user_token: str):
    """普通用户可以访问用户端点"""
    headers = {"Authorization": f"Bearer {user_token}"}
    response = client.get("/api/profile", headers=headers)
    assert response.status_code == 200

def test_admin_endpoint_with_user_token(client: TestClient, user_token: str):
    """普通用户不能访问管理员端点"""
    headers = {"Authorization": f"Bearer {user_token}"}
    response = client.get("/api/users", headers=headers)
    assert response.status_code == 403

def test_admin_endpoint_with_admin_token(client: TestClient, admin_token: str):
    """管理员可以访问管理员���点"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/users", headers=headers)
    assert response.status_code == 200
```

---

## 📚 相关文档

- [认证系统文档](./AUTH_SYSTEM.md) - JWT认证实现细节
- [用户管理文档](./USER_MANAGEMENT.md) - 用户角色与配额管理
- [API开发指南](./API_DEVELOPMENT.md) - API端点开发规范

---

**最后更新**: 2026-03-14
**维护者**: Backend Team
