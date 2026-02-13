# 离场策略前后端集成方案

> 版本: v1.0.0
> 创建时间: 2026-02-13
> 作者: Claude AI

## 📋 概述

本方案实现了离场策略在前端策略管理页面的展示和管理，同时**禁止单独回测**（因为离场策略必须配合入场策略使用）。

---

## 🎯 核心设计原则

### 1. **数据模型设计**

在 `Strategy` 类型中新增 `strategy_type` 字段：

```typescript
export interface Strategy {
  // ... 其他字段
  strategy_type: 'entry' | 'exit'  // 新增：策略类型
  // ...
}
```

- `'entry'`: 入场策略（可以单独回测）
- `'exit'`: 离场策略（**不能单独回测**，需配合入场策略）

### 2. **前端展示逻辑**

在策略卡片中：
- ✅ 显示"离场策略"标识（Badge）
- ✅ 禁用回测按钮并显示提示文字
- ✅ 保留其他功能（查看代码、编辑、克隆、删除）

---

## 📁 文件修改清单

### 1. 前端类型定义

**文件**: `frontend/src/types/strategy.ts`

```diff
export interface Strategy {
  source_type: 'builtin' | 'ai' | 'custom'
+ strategy_type: 'entry' | 'exit'  // 新增
  // ...
}

export interface CreateStrategyRequest {
  source_type: 'builtin' | 'ai' | 'custom'
+ strategy_type: 'entry' | 'exit'  // 新增
  // ...
}
```

### 2. 前端策略卡片组件

**文件**: `frontend/src/components/strategies/StrategyCard.tsx`

```typescript
// 判断是否为离场策略
const isExitStrategy = strategy.strategy_type === 'exit'

// 显示离场策略标识
{isExitStrategy && (
  <Badge variant="secondary" className="text-xs">
    离场策略
  </Badge>
)}

// 禁用回测按钮
{onBacktest && isExitStrategy && (
  <Button size="sm" disabled title="离场策略需要配合入场策略使用，不能单独回测">
    <Play className="mr-1 h-3 w-3" />
    不可回测
  </Button>
)}
```

### 3. 后端数据库 Schema

**需要添加的列**:

```sql
-- PostgreSQL / MySQL
ALTER TABLE strategies
ADD COLUMN strategy_type VARCHAR(10) DEFAULT 'entry';

-- 创建索引（可选）
CREATE INDEX idx_strategies_strategy_type ON strategies(strategy_type);
```

**字段说明**:
- 类型: `VARCHAR(10)` 或 `ENUM('entry', 'exit')`
- 默认值: `'entry'`（向后兼容）
- NOT NULL

### 4. 离场策略初始化脚本

**文件**: `core/scripts/init_exit_strategies.py`

包含4个内置离场策略：
1. **止损策略** (StopLossExitStrategy)
2. **止盈策略** (TakeProfitExitStrategy)
3. **移动止损策略** (TrailingStopExitStrategy)
4. **持仓时长策略** (HoldingPeriodExitStrategy)

---

## 🚀 部署步骤

### Step 1: 数据库迁移

```sql
-- 1. 添加 strategy_type 列
ALTER TABLE strategies
ADD COLUMN strategy_type VARCHAR(10) DEFAULT 'entry';

-- 2. 验证列已添加
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'strategies' AND column_name = 'strategy_type';
```

### Step 2: 初始化离场策略

```bash
cd /Volumes/MacDriver/stock-analysis/core

# 1. 编辑脚本，取消注释数据库写入代码
vim scripts/init_exit_strategies.py

# 2. 运行初始化脚本
./venv/bin/python scripts/init_exit_strategies.py
```

### Step 3: 更新后端API（如需）

确保后端API支持 `strategy_type` 字段的读写：

```python
# backend/app/models/strategy.py
class Strategy(Base):
    __tablename__ = "strategies"
    # ...
    strategy_type = Column(String(10), default='entry')  # 新增
```

```python
# backend/app/schemas/strategy.py
class StrategyCreate(BaseModel):
    # ...
    strategy_type: str = 'entry'  # 新增

class StrategyResponse(BaseModel):
    # ...
    strategy_type: str  # 新增
```

### Step 4: 前端部署

```bash
cd /Volumes/MacDriver/stock-analysis/frontend

# 重新构建前端
npm run build

# 或启动开发服务器
npm run dev
```

---

## 🎨 前端展示效果

### 策略卡片对比

#### 入场策略卡片（可回测）
```
┌─────────────────────────────────────┐
│ 动量策略              [内置] [已验证] │
│ 基于价格动量的入场策略               │
│                                     │
│ [momentum] [入场]                   │
│ 风险等级: 中等风险    使用次数: 15   │
│                                     │
│ [查看代码] [回测] [克隆]             │  ← 可回测
└─────────────────────────────────────┘
```

#### 离场策略卡片（不可回测）
```
┌─────────────────────────────────────┐
│ 止损离场策略 [离场策略] [内置] [已验证] │  ← 标识
│ 当亏损超过指定比例时触发离场         │
│                                     │
│ [stop_loss] [风控] [离场]           │
│ 风险等级: 安全        使用次数: 8    │
│                                     │
│ [查看代码] [不可回测] [克隆]         │  ← 禁用回测
└─────────────────────────────────────┘
```

---

## 🔧 API 端点说明

### GET /api/strategies

**响应示例**:

```json
{
  "data": [
    {
      "id": 1,
      "name": "momentum_strategy",
      "display_name": "动量策略",
      "strategy_type": "entry",  // 入场策略
      "source_type": "builtin",
      // ...
    },
    {
      "id": 10,
      "name": "stop_loss",
      "display_name": "止损离场策略",
      "strategy_type": "exit",  // 离场策略
      "source_type": "builtin",
      // ...
    }
  ]
}
```

### POST /api/strategies

**请求体**:

```json
{
  "name": "custom_exit",
  "display_name": "自定义离场策略",
  "code": "...",
  "class_name": "CustomExitStrategy",
  "source_type": "custom",
  "strategy_type": "exit",  // 必须指定
  "category": "custom_exit",
  "description": "自定义的离场逻辑"
}
```

---

## 📊 内置离场策略详情

### 1. 止损策略 (StopLossExitStrategy)

**参数**:
- `stop_loss_pct`: 止损比例（默认 10%）
- `priority`: 优先级（默认 10，风控级别）

**触发条件**:
```python
if 亏损 > stop_loss_pct:
    触发离场
```

### 2. 止盈策略 (TakeProfitExitStrategy)

**参数**:
- `take_profit_pct`: 止盈比例（默认 20%）
- `priority`: 优先级（默认 8）

**触发条件**:
```python
if 盈利 > take_profit_pct:
    触发离场
```

### 3. 移动止损策略 (TrailingStopExitStrategy)

**参数**:
- `trailing_stop_pct`: 移动止损比例（默认 5%）
- `priority`: 优先级（默认 9，风控级别）

**触发条件**:
```python
if (当前价格 - 最高价) / 最高价 < -trailing_stop_pct:
    触发离场
```

### 4. 持仓时长策略 (HoldingPeriodExitStrategy)

**参数**:
- `max_holding_days`: 最大持仓天数（默认 30天）
- `priority`: 优先级（默认 3）

**触发条件**:
```python
if 持仓天数 >= max_holding_days:
    触发离场
```

---

## 🔐 权限和限制

### 前端限制

| 操作 | 入场策略 | 离场策略 |
|------|---------|---------|
| 查看代码 | ✅ | ✅ |
| 编辑参数 | ✅ | ✅ |
| 克隆 | ✅ | ✅ |
| 删除 | ✅（自定义/AI） | ✅（自定义/AI） |
| **单独回测** | ✅ | ❌ **禁止** |

### 回测限制说明

**离场策略不能单独回测的原因**:
1. 离场策略需要**已有持仓**才能工作
2. 没有入场策略就无法建立持仓
3. 必须在 `backtest_ml_strategy()` 中配合 `MLEntry` 使用

**正确使用方式**:

```python
from src.ml.ml_entry import MLEntry
from src.ml.exit_strategy import create_default_exit_manager

# 入场策略
ml_entry = MLEntry(model_path='...', ...)

# 离场策略
exit_manager = create_default_exit_manager()

# 回测（两者结合）
engine.backtest_ml_strategy(
    ml_entry=ml_entry,
    exit_manager=exit_manager,  # 离场策略
    ...
)
```

---

## 🧪 测试验证

### 测试清单

- [ ] 数据库 `strategy_type` 列已添加
- [ ] 4个内置离场策略已初始化
- [ ] 前端策略列表能正确显示离场策略
- [ ] 离场策略卡片显示"离场策略"标识
- [ ] 离场策略的回测按钮被禁用
- [ ] 离场策略可以查看代码
- [ ] 离场策略可以编辑参数
- [ ] 离场策略可以克隆
- [ ] 自定义离场策略可以删除
- [ ] API 返回数据包含 `strategy_type` 字段

### 测试脚本

```bash
# 1. 测试初始化脚本
cd /Volumes/MacDriver/stock-analysis/core
./venv/bin/python scripts/init_exit_strategies.py

# 2. 测试数据库
psql -d stock_analysis -c "SELECT name, strategy_type FROM strategies WHERE strategy_type='exit';"

# 3. 测试API
curl http://localhost:8000/api/strategies?strategy_type=exit

# 4. 前端测试
# 访问 http://localhost:3000/strategies
# 筛选条件: strategy_type = 'exit'
```

---

## 📌 后续优化建议

### 1. 筛选器增强

在前端策略列表页面添加"策略类型"筛选器：

```typescript
<Select value={strategyTypeFilter} onValueChange={setStrategyTypeFilter}>
  <SelectItem value="all">全部类型</SelectItem>
  <SelectItem value="entry">入场策略</SelectItem>
  <SelectItem value="exit">离场策略</SelectItem>
</Select>
```

### 2. 离场策略编辑器

创建专门的离场策略编辑器，提供：
- 参数可视化配置
- 实时参数验证
- 离场信号模拟

### 3. 组合回测

在回测页面添加"选择离场策略"功能：

```typescript
interface BacktestForm {
  entry_strategy_id: number    // 入场策略
  exit_strategy_ids: number[]  // 多个离场策略（组合）
  // ...
}
```

### 4. 性能对比

支持对比不同离场策略组合的回测结果：
- 不使用离场策略
- 只用止损
- 止损 + 止盈
- 完整离场策略组合

---

## 🐛 常见问题

### Q1: 为什么离场策略不能单独回测？

**A**: 离场策略需要**已有持仓**才能工作。没有入场策略就无法建立持仓，因此离场策略无法单独运行。

### Q2: 如何创建自定义离场策略？

**A**:
1. 在策略创建页面选择"自定义"
2. 继承 `BaseExitStrategy` 类
3. 实现 `should_exit()` 方法
4. 设置 `strategy_type='exit'`

### Q3: 一个回测可以使用多个离场策略吗？

**A**: 可以！使用 `CompositeExitManager` 组合多个离场策略：

```python
from src.ml.exit_strategy import (
    CompositeExitManager,
    StopLossExitStrategy,
    TakeProfitExitStrategy
)

exit_manager = CompositeExitManager([
    StopLossExitStrategy(stop_loss_pct=0.10),
    TakeProfitExitStrategy(take_profit_pct=0.20)
])
```

### Q4: 离场策略的优先级如何工作？

**A**: 优先级规则：
1. **反向入场** (11) - 最高优先级
2. **止损** (10) - 风控级别
3. **移动止损** (9) - 风控级别
4. **止盈** (8)
5. **持仓时长** (3)

当多个策略同时触发时，选择优先级最高的。

---

## 📚 相关文档

- [离场策略核心代码](../core/src/ml/exit_strategy.py)
- [ML策略回测引擎](../core/src/backtest/backtest_engine.py)
- [使用示例](../core/examples/ml_strategy_with_exit.py)
- [初始化脚本](../core/scripts/init_exit_strategies.py)

---

## ✅ 总结

本方案实现了：

1. ✅ 离场策略在前端的完整展示
2. ✅ 禁止离场策略单独回测
3. ✅ 保留离场策略的其他管理功能
4. ✅ 4个内置离场策略
5. ✅ 完整的数据模型和类型定义
6. ✅ 数据库迁移方案
7. ✅ 初始化脚本

现在你可以在前端策略管理页面查看、编辑、克隆离场策略，但它们的回测按钮会被禁用，并显示"需要配合入场策略使用"的提示。
