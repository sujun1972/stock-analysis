# Backend v3.x → v4.0 迁移指南

**文档版本**: v1.0.0
**创建日期**: 2026-02-09
**适用版本**: v3.x → v4.0.0

---

## 📋 目录

- [迁移概述](#迁移概述)
- [重大变更](#重大变更)
- [API迁移指南](#api迁移指南)
- [代码示例对比](#代码示例对比)
- [常见问题](#常见问题)
- [迁移检查清单](#迁移检查清单)

---

## 迁移概述

### 背景

Backend v4.0 完成了对 Core v6.0 的适配，移除了 Three Layer 架构，引入了全新的统一策略系统。

### 核心变化

1. ❌ **Three Layer API 已移除**
   - `/api/three-layer/*` 端点已不可用
   - 返回 `410 Gone` 状态码

2. ✅ **新增三种策略类型**
   - 预定义策略（Predefined Strategies）
   - 配置驱动策略（Configured Strategies）
   - 动态代码策略（Dynamic Strategies）

3. ✅ **统一回测接口**
   - 新增 `/api/backtest` 端点，支持所有策略类型
   - 更简洁的请求格式

### 迁移工作量评估

| 项目 | 预计工作量 |
|------|----------|
| 前端 API 调用更新 | 2-3 天 |
| 测试用例更新 | 1-2 天 |
| 文档更新 | 0.5 天 |
| 回归测试 | 1 天 |
| **总计** | **4.5-6.5 天** |

---

## 重大变更

### 1. 移除的 API 端点

以下端点已在 v4.0 移除：

| 端点 | 方法 | 状态 | 替代方案 |
|------|------|------|---------|
| `/api/three-layer/selectors` | GET | ❌ 已移除 | `/api/strategy-configs/types` |
| `/api/three-layer/entries` | GET | ❌ 已移除 | 无需替代（预定义策略内置） |
| `/api/three-layer/exits` | GET | ❌ 已移除 | 无需替代（预定义策略内置） |
| `/api/three-layer/validate` | POST | ❌ 已移除 | `/api/dynamic-strategies` |
| `/api/three-layer/backtest` | POST | ❌ 已移除 | `/api/backtest` |

### 2. 新增的 API 端点

#### 策略配置 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/strategy-configs/types` | GET | 获取可用的预定义策略类型 |
| `/api/strategy-configs` | POST | 创建策略配置 |
| `/api/strategy-configs` | GET | 获取配置列表 |
| `/api/strategy-configs/{id}` | GET | 获取配置详情 |
| `/api/strategy-configs/{id}` | PUT | 更新配置 |
| `/api/strategy-configs/{id}` | DELETE | 删除配置 |
| `/api/strategy-configs/{id}/test` | POST | 测试配置 |
| `/api/strategy-configs/validate` | POST | 验证配置参数 |

#### 动态策略 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/dynamic-strategies` | POST | 创建动态策略 |
| `/api/dynamic-strategies` | GET | 获取动态策略列表 |
| `/api/dynamic-strategies/{id}` | GET | 获取动态策略详情 |
| `/api/dynamic-strategies/{id}` | PUT | 更新动态策略 |
| `/api/dynamic-strategies/{id}` | DELETE | 删除动态策略 |
| `/api/dynamic-strategies/{id}/code` | GET | 获取策略代码 |
| `/api/dynamic-strategies/{id}/test` | POST | 测试动态策略 |
| `/api/dynamic-strategies/{id}/validate` | POST | 验证策略代码 |
| `/api/dynamic-strategies/statistics` | GET | 获取策略统计信息 |

#### 统一回测 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/backtest` | POST | 统一回测接口（支持三种策略类型） |

---

## API迁移指南

### 场景 1: 获取可用策略列表

#### 旧方式（v3.x）❌

```http
GET /api/three-layer/selectors
```

```json
{
  "success": true,
  "data": [
    {
      "id": "momentum",
      "name": "动量选股",
      "params": { ... }
    },
    {
      "id": "value",
      "name": "价值选股",
      "params": { ... }
    }
  ]
}
```

#### 新方式（v4.0）✅

```http
GET /api/strategy-configs/types
```

```json
{
  "success": true,
  "data": [
    {
      "type": "momentum",
      "name": "动量策略",
      "description": "选择近期涨幅最大的股票",
      "default_params": {
        "lookback_period": 20,
        "threshold": 0.10,
        "top_n": 20
      }
    },
    {
      "type": "mean_reversion",
      "name": "均值回归策略",
      "description": "选择偏离均值的股票",
      "default_params": {
        "lookback_period": 20,
        "std_threshold": 2.0,
        "top_n": 20
      }
    }
  ]
}
```

**变化说明**:
- 端点路径变更
- 返回的策略类型是完整策略，而非单独的选股器
- 参数结构更清晰

---

### 场景 2: 运行回测

#### 旧方式（v3.x）❌

```http
POST /api/three-layer/backtest
Content-Type: application/json

{
  "selector": {
    "id": "momentum",
    "params": {
      "lookback_period": 20,
      "top_n": 50
    }
  },
  "entry": {
    "id": "immediate",
    "params": {}
  },
  "exit": {
    "id": "fixed_stop_loss",
    "params": {
      "stop_loss_pct": 0.05,
      "take_profit_pct": 0.10
    }
  },
  "stock_pool": ["000001.SZ", "600000.SH"],
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "initial_capital": 1000000
}
```

#### 新方式（v4.0）✅

**方式 1: 使用预定义策略**

```http
POST /api/backtest
Content-Type: application/json

{
  "strategy_type": "predefined",
  "strategy_name": "momentum",
  "strategy_config": {
    "lookback_period": 20,
    "threshold": 0.10,
    "top_n": 50
  },
  "stock_pool": ["000001.SZ", "600000.SH"],
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "initial_capital": 1000000
}
```

**方式 2: 使用配置驱动策略**

```http
# 1. 先创建策略配置
POST /api/strategy-configs
Content-Type: application/json

{
  "strategy_type": "momentum",
  "config": {
    "lookback_period": 20,
    "threshold": 0.10,
    "top_n": 50
  },
  "name": "我的动量策略",
  "description": "优化后的动量策略"
}

# 响应
{
  "success": true,
  "data": {
    "config_id": 123
  }
}

# 2. 使用配置ID运行回测
POST /api/backtest
Content-Type: application/json

{
  "strategy_type": "config",
  "strategy_id": 123,
  "stock_pool": ["000001.SZ", "600000.SH"],
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "initial_capital": 1000000
}
```

**变化说明**:
- 不再需要单独指定 entry 和 exit 策略
- 策略配置更简洁
- 支持保存和复用策略配置

---

### 场景 3: 验证策略参数

#### 旧方式（v3.x）❌

```http
POST /api/three-layer/validate
Content-Type: application/json

{
  "selector": { "id": "momentum", "params": { ... } },
  "entry": { "id": "immediate", "params": {} },
  "exit": { "id": "fixed_stop_loss", "params": { ... } }
}
```

#### 新方式（v4.0）✅

**验证预定义策略配置**

```http
POST /api/strategy-configs/validate
Content-Type: application/json

{
  "strategy_type": "momentum",
  "config": {
    "lookback_period": 20,
    "threshold": 0.10,
    "top_n": 50
  }
}
```

**响应**

```json
{
  "success": true,
  "data": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  }
}
```

**验证动态策略代码**

```http
POST /api/dynamic-strategies/{id}/validate
```

---

## 代码示例对比

### Python 客户端示例

#### 旧方式（v3.x）❌

```python
import requests

# 运行三层架构回测
response = requests.post('http://localhost:8000/api/three-layer/backtest', json={
    'selector': {
        'id': 'momentum',
        'params': {
            'lookback_period': 20,
            'top_n': 50
        }
    },
    'entry': {
        'id': 'immediate',
        'params': {}
    },
    'exit': {
        'id': 'fixed_stop_loss',
        'params': {
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.10
        }
    },
    'stock_pool': ['000001.SZ', '600000.SH'],
    'start_date': '2023-01-01',
    'end_date': '2023-12-31',
    'initial_capital': 1000000
})

result = response.json()
```

#### 新方式（v4.0）✅

```python
import requests

# 使用预定义策略运行回测
response = requests.post('http://localhost:8000/api/backtest', json={
    'strategy_type': 'predefined',
    'strategy_name': 'momentum',
    'strategy_config': {
        'lookback_period': 20,
        'threshold': 0.10,
        'top_n': 50
    },
    'stock_pool': ['000001.SZ', '600000.SH'],
    'start_date': '2023-01-01',
    'end_date': '2023-12-31',
    'initial_capital': 1000000
})

result = response.json()

# 或使用配置驱动策略
response = requests.post('http://localhost:8000/api/backtest', json={
    'strategy_type': 'config',
    'strategy_id': 123,  # 之前保存的配置ID
    'stock_pool': ['000001.SZ', '600000.SH'],
    'start_date': '2023-01-01',
    'end_date': '2023-12-31',
    'initial_capital': 1000000
})

result = response.json()
```

### JavaScript/TypeScript 客户端示例

#### 旧方式（v3.x）❌

```typescript
// 运行三层架构回测
const response = await fetch('http://localhost:8000/api/three-layer/backtest', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    selector: {
      id: 'momentum',
      params: {
        lookback_period: 20,
        top_n: 50
      }
    },
    entry: {
      id: 'immediate',
      params: {}
    },
    exit: {
      id: 'fixed_stop_loss',
      params: {
        stop_loss_pct: 0.05,
        take_profit_pct: 0.10
      }
    },
    stock_pool: ['000001.SZ', '600000.SH'],
    start_date: '2023-01-01',
    end_date: '2023-12-31',
    initial_capital: 1000000
  })
});

const result = await response.json();
```

#### 新方式（v4.0）✅

```typescript
// 使用预定义策略运行回测
const response = await fetch('http://localhost:8000/api/backtest', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    strategy_type: 'predefined',
    strategy_name: 'momentum',
    strategy_config: {
      lookback_period: 20,
      threshold: 0.10,
      top_n: 50
    },
    stock_pool: ['000001.SZ', '600000.SH'],
    start_date: '2023-01-01',
    end_date: '2023-12-31',
    initial_capital: 1000000
  })
});

const result = await response.json();
```

---

## 常见问题

### Q1: 我的旧代码会立即停止工作吗？

**A**: 是的，Three Layer API 在 v4.0 已移除。调用旧端点会返回 `410 Gone` 错误。

```json
{
  "error": "API Deprecated",
  "message": "Three Layer architecture has been removed. Use /api/backtest instead.",
  "migration_guide": "https://docs.example.com/migration-v4"
}
```

### Q2: 如何将旧的 entry/exit 策略映射到新系统？

**A**: 新系统的预定义策略已内置了 entry 和 exit 逻辑。您无需单独配置它们。如果需要自定义 entry/exit 逻辑，请使用动态代码策略。

| 旧组合 | 新策略 |
|-------|--------|
| momentum selector + immediate entry + stop loss exit | `momentum` 预定义策略 |
| value selector + immediate entry + stop loss exit | `mean_reversion` 预定义策略 |
| 自定义组合 | 创建动态代码策略 |

### Q3: 如何迁移自定义的三层架构策略？

**A**: 使用动态代码策略：

```python
# 1. 编写完整的策略类
strategy_code = """
from core.strategies.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def __init__(self, config):
        super().__init__(config)
        # 初始化参数

    def select_stocks(self, market_data, date):
        # 选股逻辑
        pass

    def generate_signals(self, market_data, date):
        # 信号生成逻辑
        pass
"""

# 2. 创建动态策略
response = requests.post('http://localhost:8000/api/dynamic-strategies', json={
    'strategy_name': 'my_custom_strategy',
    'display_name': '我的自定义策略',
    'class_name': 'MyCustomStrategy',
    'generated_code': strategy_code
})

strategy_id = response.json()['data']['strategy_id']

# 3. 运行回测
response = requests.post('http://localhost:8000/api/backtest', json={
    'strategy_type': 'dynamic',
    'strategy_id': strategy_id,
    'stock_pool': ['000001.SZ'],
    'start_date': '2023-01-01',
    'end_date': '2023-12-31'
})
```

### Q4: 新系统的性能如何？

**A**: 新系统性能更优：

| 策略类型 | 性能 | 原因 |
|---------|------|------|
| 预定义策略 | 最快 | 硬编码，无动态加载 |
| 配置驱动策略 | 快 | 从数据库加载参数，有缓存 |
| 动态代码策略 | 中等 | 动态编译，有安全验证 |

### Q5: 如何处理历史回测记录？

**A**: 历史记录仍然保留在旧表中，不受影响。新的回测记录会保存到 `strategy_executions` 表。

### Q6: 前端需要做哪些改动？

**A**: 主要改动点：

1. **更新 API 端点路径**
   - `/api/three-layer/*` → `/api/backtest`, `/api/strategy-configs/*`, etc.

2. **更新请求参数结构**
   - 从 `{selector, entry, exit}` → `{strategy_type, strategy_name/strategy_id, strategy_config}`

3. **更新 UI 组件**
   - 移除 entry/exit 策略选择器
   - 添加策略类型选择器（预定义/配置驱动/动态代码）

4. **更新状态管理**
   - 更新 API 调用逻辑
   - 更新数据模型

预计工作量：2-3 天

---

## 迁移检查清单

### 后端迁移（Backend）

- [x] 移除 Three Layer API 端点
- [x] 新增策略配置 API
- [x] 新增动态策略 API
- [x] 新增统一回测 API
- [x] 更新数据库表结构
- [x] 更新测试用例
- [x] 更新文档

### 前端迁移（Frontend）

- [ ] 更新 API 客户端代码
- [ ] 更新请求参数结构
- [ ] 更新 UI 组件
- [ ] 更新状态管理
- [ ] 更新测试用例
- [ ] 回归测试

### 测试验证

- [ ] 预定义策略回测测试
- [ ] 配置驱动策略回测测试
- [ ] 动态代码策略回测测试
- [ ] API 端点测试
- [ ] 性能测试
- [ ] 用户验收测试

### 部署上线

- [ ] 数据库 Migration
- [ ] 后端部署
- [ ] 前端部署
- [ ] 监控告警配置
- [ ] 生产验证

---

## 获取帮助

### 文档资源

- [Backend README](../README.md) - Backend 项目文档
- [API 参考文档](../api_reference/README.md) - 完整的 API 文档
- [API 使用指南](../api_reference/API_USAGE_GUIDE.md) - API 使用示例
- [Core v6.0 文档](../../../core/docs/README.md) - Core 项目文档

### 技术支持

如有问题，请联系：
- **Email**: quant-team@example.com
- **Slack**: #backend-support
- **GitHub Issues**: https://github.com/your-org/stock-analysis/issues

---

**文档维护**: Backend Team
**最后更新**: 2026-02-09
