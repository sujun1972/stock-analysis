# Backend API 模块化重构技能

## 概述
此技能用于重构大型 Backend API 端点文件，将单一文件拆分为模块化的包结构，提升代码可维护性。

## 适用场景
- 单个 API 端点文件超过 500 行
- 文件包含多个功能域（查询、同步、分析等）
- 端点数量超过 10 个
- 需要提升代码可读性和可维护性

## 重构策略

### 1. 模块化拆分原则
按功能域将单一文件拆分为多个模块：

```
# 重构前
endpoints/resource.py (1000+ 行) - 单一文件

# 重构后
endpoints/resource/
├── __init__.py          # 路由聚合
├── schemas.py           # Pydantic 数据模型
├── query.py             # 查询类端点 (GET)
├── mutation.py          # 修改类端点 (POST/PUT/DELETE)
├── sync.py              # 数据同步端点
└── analysis.py          # 分析类端点
```

### 2. 文件职责划分

#### schemas.py
- 定义所有 Pydantic 请求/响应模型
- 集中管理数据验证规则
- 便于复用和维护

```python
"""
资源相关的 Pydantic Schema 定义

定义所有请求和响应的数据模型，用于参数验证和文档生成。
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class ResourceQuery(BaseModel):
    """资源查询参数"""
    page: int = Field(1, ge=1, description="页码")
    limit: int = Field(20, ge=1, le=100, description="每页数量")
```

#### query.py
- 只读操作 (GET 请求)
- 不涉及数据修改
- 可供普通用户访问

```python
"""
资源查询端点

包含所有查询类端点，不涉及数据修改。
"""

from fastapi import APIRouter, Query, Depends
from app.services.resource_service import ResourceService

router = APIRouter()
service = ResourceService()

@router.get("/list")
async def get_resource_list(
    page: int = Query(1, ge=1),
    current_user = Depends(get_current_active_user)
):
    """查询资源列表"""
    return await service.get_list(page=page)
```

#### sync.py
- 数据同步相关端点
- 任务状态查询
- 通常需要管理员权限

```python
"""
资源同步端点

包含数据同步和任务管理相关的端点。
"""

from fastapi import APIRouter, Depends
from app.core.dependencies import require_admin

router = APIRouter()

@router.post("/sync")
async def sync_resource(
    current_user = Depends(require_admin)
):
    """手动触发同步"""
    # 实现同步逻辑
```

#### __init__.py
- 路由聚合入口
- 统一注册子路由
- 定义路由前缀和标签

```python
"""
资源 API 端点包

将原有的 resource.py 拆分为多个模块化文件。
"""

from fastapi import APIRouter
from . import query, sync, analysis

router = APIRouter()

# 注册子路由
router.include_router(query.router, tags=["resource-query"])
router.include_router(sync.router, tags=["resource-sync"])
router.include_router(analysis.router, prefix="/analysis", tags=["resource-analysis"])

__all__ = ["router"]
```

### 3. 重构步骤

1. **创建目录结构**
   ```bash
   mkdir backend/app/api/endpoints/resource
   ```

2. **创建 schemas.py**
   - 提取所有 Pydantic 模型
   - 按功能分组（查询、同步、分析等）

3. **按功能域拆分端点**
   - 创建 query.py、sync.py 等文件
   - 复制相关的路由处理函数
   - 导入必要的依赖

4. **创建 __init__.py**
   - 导入所有子模块
   - 注册子路由
   - 设置合适的 prefix 和 tags

5. **备份原文件**
   ```bash
   mv resource.py resource.py.backup
   ```

6. **测试验证**
   ```bash
   # 验证导入
   docker-compose exec backend python -c "from app.api.endpoints import resource; print(len(resource.router.routes))"

   # 测试 API
   curl http://localhost:8000/api/resource/list
   ```

7. **删除备份文件**
   ```bash
   rm resource.py.backup
   ```

## 实际案例：sentiment 模块重构

### 重构前
- `sentiment.py`: 1018 行，22 个端点

### 重构后
| 文件 | 行数 | 端点数 | 职责 |
|------|------|--------|------|
| `__init__.py` | 31 | - | 路由聚合 |
| `schemas.py` | 168 | - | 数据模型 |
| `query.py` | 315 | 9 | 查询端点 |
| `sync.py` | 426 | 5 | 同步和任务管理 |
| `cycle.py` | 228 | 6 | 情绪周期分析 |
| `ai_analysis.py` | 123 | 2 | AI 分析 |

### 路由注册
```python
# sentiment/__init__.py
router.include_router(query.router, tags=["sentiment-query"])
router.include_router(sync.router, tags=["sentiment-sync"])
router.include_router(cycle.router, prefix="/cycle", tags=["sentiment-cycle"])
router.include_router(ai_analysis.router, prefix="/ai-analysis", tags=["sentiment-ai"])
```

### API 路径映射
- `/api/sentiment/*` → query.router
- `/api/sentiment/sync/*` → sync.router
- `/api/sentiment/cycle/*` → cycle.router
- `/api/sentiment/ai-analysis/*` → ai_analysis.router

## 注意事项

### 向后兼容性
- ✅ 所有 API 路径保持不变
- ✅ 响应格式保持不变
- ✅ 功能完全一致

### 代码规范
- ✅ 每个文件保持在 300-500 行以内
- ✅ 相关功能聚合在一起
- ✅ 清晰的模块文档注释
- ✅ 统一的导入顺序（标准库 → 第三方 → 本地）

### 测试要点
- ✅ 验证所有端点路径正确
- ✅ 验证路由数量一致
- ✅ 验证依赖注入正常
- ✅ 验证权限控制有效

## 优势总结

1. **更好的代码组织**
   - 单一职责，降低复杂度
   - 易于定位和修改

2. **提升可维护性**
   - 文件更小，易于理解
   - 减少合并冲突

3. **便于团队协作**
   - 模块化开发
   - 并行开发不同功能

4. **符合架构规范**
   - 遵循 Backend 三层架构
   - API 层保持简洁

## 参考文档
- [CLAUDE.md - Backend 架构规范](../../../CLAUDE.md#backend-架构规范)
- [FastAPI 文档 - 大型应用](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
