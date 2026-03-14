# API 迁移指南

## 概述

本文档提供从旧版 API (v1.0) 迁移到新版统一策略系统 API (v2.0) 的完整指南。

**重要日期：**
- 弃用开始日期：2026-03-14（v2.0 发布）
- 计划移除日期：2026-09-01
- 迁移建议期限：2026-06-01（3个月迁移期）

---

## 版本管理

### API 版本说明

| 版本 | 状态 | 支持截止日期 | 说明 |
|------|------|--------------|------|
| v1.0 | 已弃用 | 2026-09-01 | 旧的策略配置和动态策略 API |
| v2.0 | 当前版本 | - | 新的统一策略系统 API |

### 如何指定 API 版本

支持三种方式指定 API 版本：

#### 1. 使用 HTTP Header（推荐）
```bash
curl -H "X-API-Version: 2.0" https://api.example.com/api/strategies
```

#### 2. 使用查询参数
```bash
curl https://api.example.com/api/strategies?api_version=2.0
```

#### 3. 默认使用当前版本
如果不指定版本，系统将自动使用当前最新版本 (v2.0)。

---

## 弃用警告识别

当调用已弃用的 API 时，系统会在响应中添加弃用警告信息：

### 响应头警告
```http
HTTP/1.1 200 OK
Warning: 299 - "This API endpoint is deprecated since version 2.0. It will be removed on 2026-09-01. Please use '/api/strategies' instead. Reason: 使用新的统一策略系统"
X-API-Deprecated: true
X-API-Deprecated-Since: 2.0
X-API-Removal-Date: 2026-09-01
X-API-Alternative: /api/strategies
```

### 响应体警告
```json
{
  "code": 200,
  "message": "success",
  "data": {...},
  "deprecation": {
    "deprecated": true,
    "deprecated_since": "2.0",
    "removal_date": "2026-09-01",
    "alternative": "/api/strategies",
    "reason": "使用新的统一策略系统"
  }
}
```

---

## 核心变更

### 架构变更

#### v1.0 架构（已弃用）
- 分离的策略配置 API (`/strategy-configs`)
- 分离的动态策略 API (`/dynamic-strategies`)
- 两套独立的数据模型和业务逻辑

#### v2.0 架构（新版）
- 统一的策略系统 API (`/strategies`)
- 统一的数据模型
- 支持配置驱动和代码驱动两种策略类型
- 改进的安全验证和性能优化

### 响应格式统一

#### 旧版响应格式（不一致）
```json
{
  "success": true,
  "data": {...},
  "meta": {...}
}
```

#### 新版响应格式（统一）
```json
{
  "code": 200,
  "message": "success",
  "data": {...},
  "timestamp": "2026-03-14T12:00:00",
  "request_id": "req_123456",
  "api_version": "2.0",
  "success": true
}
```

---

## API 映射表

### 1. 策略配置 API (`/strategy-configs` → `/strategies`)

#### 获取策略类型

**旧版 (v1.0 - 已弃用):**
```http
GET /api/strategy-configs/types
```

**新版 (v2.0):**
```http
GET /api/strategies/types
```

**变更说明：**
- URL 路径变更
- 响应格式统一
- 增加了更详细的策略类型元数据

---

#### 验证策略配置

**旧版 (v1.0 - 已弃用):**
```http
POST /api/strategy-configs/validate
Content-Type: application/json

{
  "strategy_type": "momentum",
  "config": {
    "lookback_period": 20,
    "threshold": 0.10
  }
}
```

**新版 (v2.0):**
```http
POST /api/strategies/validate
Content-Type: application/json

{
  "strategy_type": "config_driven",
  "config_type": "momentum",
  "config": {
    "lookback_period": 20,
    "threshold": 0.10
  }
}
```

**变更说明：**
- 增加 `strategy_type` 字段（固定为 `"config_driven"`）
- `strategy_type` 重命名为 `config_type`
- 响应格式统一

---

#### 创建策略

**旧版 (v1.0 - 已弃用):**
```http
POST /api/strategy-configs
Content-Type: application/json

{
  "strategy_type": "momentum",
  "config": {...},
  "name": "我的动量策略",
  "description": "20日动量策略"
}
```

**新版 (v2.0):**
```http
POST /api/strategies
Content-Type: application/json

{
  "strategy_type": "config_driven",
  "strategy_name": "my_momentum_strategy",
  "display_name": "我的动量策略",
  "description": "20日动量策略",
  "config_type": "momentum",
  "config": {...}
}
```

**变更说明：**
- 增加 `strategy_name` 字段（唯一标识符）
- `name` 重命名为 `display_name`
- 增加 `strategy_type` 字段区分配置驱动和代码驱动
- 统一的响应格式

---

#### 获取策略列表

**旧版 (v1.0 - 已弃用):**
```http
GET /api/strategy-configs?page=1&page_size=20&category=趋势跟踪
```

**新版 (v2.0):**
```http
GET /api/strategies?page=1&page_size=20&strategy_type=config_driven&category=趋势跟踪
```

**变更说明：**
- 增加 `strategy_type` 过滤参数
- 改进的分页响应格式
- 支持更多过滤选项

---

#### 获取策略详情

**旧版 (v1.0 - 已弃用):**
```http
GET /api/strategy-configs/{config_id}
```

**新版 (v2.0):**
```http
GET /api/strategies/{strategy_id}
```

**变更说明：**
- URL 参数从 `config_id` 改为 `strategy_id`
- 响应包含更多元数据（创建时间、更新时间、版本等）

---

#### 更新策略

**旧版 (v1.0 - 已弃用):**
```http
PUT /api/strategy-configs/{config_id}
Content-Type: application/json

{
  "config": {...},
  "is_enabled": true
}
```

**新版 (v2.0):**
```http
PUT /api/strategies/{strategy_id}
Content-Type: application/json

{
  "config": {...},
  "is_enabled": true,
  "version": 2
}
```

**变更说明：**
- 增加版本控制（乐观锁）
- 改进的并发冲突处理

---

#### 删除策略

**旧版 (v1.0 - 已弃用):**
```http
DELETE /api/strategy-configs/{config_id}
```

**新版 (v2.0):**
```http
DELETE /api/strategies/{strategy_id}
```

**变更说明：**
- 软删除机制（标记为 archived）
- 支持 `force=true` 参数进行硬删除

---

### 2. 动态策略 API (`/dynamic-strategies` → `/strategies`)

#### 验证策略代码

**旧版 (v1.0 - 已弃用):**
```http
POST /api/dynamic-strategies/validate
Content-Type: application/json

{
  "class_name": "MyStrategy",
  "generated_code": "class MyStrategy(BaseStrategy): ..."
}
```

**新版 (v2.0):**
```http
POST /api/strategies/validate
Content-Type: application/json

{
  "strategy_type": "code_driven",
  "class_name": "MyStrategy",
  "generated_code": "class MyStrategy(BaseStrategy): ..."
}
```

**变更说明：**
- 增加 `strategy_type` 字段（固定为 `"code_driven"`）
- 改进的安全验证机制
- 更详细的错误信息

---

#### 创建动态策略

**旧版 (v1.0 - 已弃用):**
```http
POST /api/dynamic-strategies
Content-Type: application/json

{
  "strategy_name": "my_strategy",
  "display_name": "我的策略",
  "class_name": "MyStrategy",
  "generated_code": "...",
  "user_prompt": "创建一个动量策略"
}
```

**新版 (v2.0):**
```http
POST /api/strategies
Content-Type: application/json

{
  "strategy_type": "code_driven",
  "strategy_name": "my_strategy",
  "display_name": "我的策略",
  "class_name": "MyStrategy",
  "generated_code": "...",
  "user_prompt": "创建一个动量策略",
  "ai_metadata": {
    "model": "deepseek-coder",
    "prompt": "创建一个动量策略"
  }
}
```

**变更说明：**
- 统一到 `/strategies` 端点
- 增加 `strategy_type` 字段
- AI 相关信息移到 `ai_metadata` 对象中
- 改进的代码哈希和版本管理

---

#### 获取动态策略列表

**旧版 (v1.0 - 已弃用):**
```http
GET /api/dynamic-strategies?page=1&page_size=20
```

**新版 (v2.0):**
```http
GET /api/strategies?page=1&page_size=20&strategy_type=code_driven
```

**变更说明：**
- 统一端点，使用 `strategy_type` 过滤
- 支持更多过滤和排序选项

---

#### 其他端点

所有其他端点（获取详情、更新、删除等）都遵循相同的迁移模式：

- `/dynamic-strategies/{strategy_id}` → `/strategies/{strategy_id}`
- 增加 `strategy_type` 区分
- 统一的响应格式

---

## 迁移步骤

### 第一阶段：评估和准备（1-2周）

1. **审计现有集成**
   - 列出所有调用旧 API 的客户端
   - 识别使用的端点和频率
   - 评估迁移影响范围

2. **测试新 API**
   - 在测试环境中调用新 API
   - 验证功能一致性
   - 测试边缘情况

3. **更新文档**
   - 更新内部 API 调用文档
   - 更新客户端集成指南

### 第二阶段：实施迁移（4-6周）

1. **并行运行**
   - 同时调用新旧 API
   - 比较响应结果
   - 逐步切换流量

2. **代码更新**
   - 更新 API 客户端库
   - 更新请求/响应处理逻辑
   - 更新错误处理

3. **监控和日志**
   - 添加迁移监控指标
   - 记录 API 调用日志
   - 设置告警

### 第三阶段：验证和清理（2-4周）

1. **验证迁移**
   - 100% 流量切换到新 API
   - 验证所有功能正常
   - 性能测试

2. **清理旧代码**
   - 移除旧 API 调用
   - 清理兼容性代码
   - 更新配置

---

## 迁移示例

### Python 客户端迁移示例

#### 旧版代码
```python
import requests

# 创建策略配置
response = requests.post(
    "https://api.example.com/api/strategy-configs",
    json={
        "strategy_type": "momentum",
        "config": {"lookback_period": 20, "threshold": 0.10},
        "name": "我的动量策略"
    }
)

if response.json()["success"]:
    config_id = response.json()["data"]["config_id"]
```

#### 新版代码
```python
import requests

# 创建策略（统一 API）
response = requests.post(
    "https://api.example.com/api/strategies",
    headers={"X-API-Version": "2.0"},
    json={
        "strategy_type": "config_driven",
        "strategy_name": "my_momentum_strategy",
        "display_name": "我的动量策略",
        "config_type": "momentum",
        "config": {"lookback_period": 20, "threshold": 0.10}
    }
)

data = response.json()
if data["code"] == 201:  # HTTP 201 Created
    strategy_id = data["data"]["strategy_id"]
```

### JavaScript 客户端迁移示例

#### 旧版代码
```javascript
// 获取策略列表
const response = await fetch('/api/strategy-configs?page=1&page_size=20');
const result = await response.json();

if (result.success) {
  const configs = result.data;
}
```

#### 新版代码
```javascript
// 获取策略列表（统一 API）
const response = await fetch('/api/strategies?page=1&page_size=20&strategy_type=config_driven', {
  headers: {
    'X-API-Version': '2.0'
  }
});
const result = await response.json();

if (result.code === 200) {
  const strategies = result.data.items;
  const total = result.data.total;
}
```

---

## 错误处理变更

### 旧版错误响应
```json
{
  "success": false,
  "error": "策略不存在",
  "error_code": "STRATEGY_NOT_FOUND"
}
```

### 新版错误响应（统一格式）
```json
{
  "code": 404,
  "message": "策略不存在",
  "data": {
    "error_code": "STRATEGY_NOT_FOUND",
    "details": "Strategy with ID 'abc123' not found"
  },
  "timestamp": "2026-03-14T12:00:00",
  "success": false
}
```

**处理建议：**
- 使用 `code` 字段判断 HTTP 状态
- 使用 `success` 字段快速判断是否成功
- 从 `data.error_code` 获取详细错误代码

---

## 常见问题 (FAQ)

### Q1: 我可以继续使用旧 API 多久？
**A:** 旧 API 将支持到 2026-09-01。我们强烈建议在 2026-06-01 之前完成迁移。

### Q2: 新旧 API 可以同时使用吗？
**A:** 可以。在迁移期间，您可以同时使用新旧 API。但建议尽快完全迁移到新 API。

### Q3: 如何识别我正在使用的是旧 API？
**A:** 检查响应头中的 `X-API-Deprecated` 和 `Warning` 字段，或检查响应体中的 `deprecation` 对象。

### Q4: 新 API 向后兼容吗？
**A:** 新 API 在功能上兼容旧 API，但请求/响应格式有变化。需要更新客户端代码。

### Q5: 迁移后性能会提升吗？
**A:** 是的。新 API 采用了优化的架构，包括：
- 改进的数据库查询
- 更好的缓存机制
- 减少的网络开销

### Q6: 如何处理现有的策略配置 ID？
**A:** 旧的 `config_id` 将自动映射到新的 `strategy_id`。您可以使用相同的 ID 访问策略。

### Q7: 需要更新数据库吗？
**A:** 不需要。数据库迁移已在服务端完成。客户端只需更新 API 调用。

### Q8: 测试环境在哪里？
**A:** 测试环境地址：`https://api-test.example.com`（使用相同的认证凭据）

---

## 支持和帮助

### 获取帮助

- **技术支持邮箱:** api-support@example.com
- **开发者论坛:** https://forum.example.com/api
- **API 文档:** https://docs.example.com/api/v2
- **Swagger UI:** https://api.example.com/api/docs

### 报告问题

如果在迁移过程中遇到问题，请提供以下信息：

1. 使用的 API 端点
2. 请求示例
3. 预期结果 vs 实际结果
4. 错误消息（如有）
5. 请求 ID（从响应头 `X-Request-ID` 获取）

---

## 附录

### A. 完整 API 映射表

| 旧 API (v1.0) | 新 API (v2.0) | 说明 |
|---------------|---------------|------|
| `GET /strategy-configs/types` | `GET /strategies/types` | 获取策略类型 |
| `POST /strategy-configs/validate` | `POST /strategies/validate` | 验证配置 |
| `POST /strategy-configs` | `POST /strategies` | 创建策略 |
| `GET /strategy-configs` | `GET /strategies?strategy_type=config_driven` | 获取列表 |
| `GET /strategy-configs/{id}` | `GET /strategies/{id}` | 获取详情 |
| `PUT /strategy-configs/{id}` | `PUT /strategies/{id}` | 更新策略 |
| `DELETE /strategy-configs/{id}` | `DELETE /strategies/{id}` | 删除策略 |
| `POST /dynamic-strategies/validate` | `POST /strategies/validate` | 验证代码 |
| `POST /dynamic-strategies` | `POST /strategies` | 创建动态策略 |
| `GET /dynamic-strategies` | `GET /strategies?strategy_type=code_driven` | 获取列表 |
| `GET /dynamic-strategies/{id}` | `GET /strategies/{id}` | 获取详情 |
| `PUT /dynamic-strategies/{id}` | `PUT /strategies/{id}` | 更新策略 |
| `DELETE /dynamic-strategies/{id}` | `DELETE /strategies/{id}` | 删除策略 |

### B. 字段映射表

| 旧字段名 | 新字段名 | 变更说明 |
|----------|----------|----------|
| `success` | `code` + `success` | 增加 HTTP 状态码 |
| `error` | `message` | 统一使用 message |
| `data` | `data` | 无变化 |
| - | `timestamp` | 新增响应时间戳 |
| - | `request_id` | 新增请求追踪 ID |
| - | `api_version` | 新增 API 版本号 |
| `name` | `display_name` | 重命名，更语义化 |
| - | `strategy_name` | 新增唯一标识符 |
| `strategy_type` | `config_type` | 配置驱动策略的类型字段 |

### C. HTTP 状态码变更

| 场景 | 旧版 | 新版 | 说明 |
|------|------|------|------|
| 成功 | 200 | 200 | 无变化 |
| 创建成功 | 200 | 201 | 更符合 RESTful 规范 |
| 参数错误 | 400 | 400 | 无变化 |
| 未授权 | 401 | 401 | 无变化 |
| 资源不存在 | 404 | 404 | 无变化 |
| 服务器错误 | 500 | 500 | 无变化 |

---

## 变更日志

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | 2026-03-14 | 初始版本，发布迁移指南 |

---

**最后更新:** 2026-03-14
**文档版本:** 1.0
**维护者:** Backend API Team
