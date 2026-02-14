# 离场策略必选验证功能

## 功能概述

为了防止用户在不选择离场策略的情况下运行回测（导致永远不卖出、无限亏损），系统现在强制要求用户在运行回测前至少选择一个离场策略。

---

## 问题背景

### 发现的问题

用户在测试时使用以下参数进行回测：

```json
{
  "stock_pool": ["600031"],
  "start_date": "2021-02-13",
  "end_date": "2026-02-13",
  "initial_capital": 1000000,
  "rebalance_freq": "W",
  "strategy_id": 6
  // ❌ 缺少 exit_strategy_ids
}
```

**测试结果：**
- 只有1笔交易（买入 ¥44.40）
- 股价从 ¥44.40 跌到 ¥23.01（-48%）
- 整个回测期间从未卖出
- 最终亏损 -48%

**原因分析：**

在 `backtest_engine.py` 第 144-157 行：

```python
# 构建离场策略管理器
exit_manager = None
if exit_strategy_ids:
    exit_strategies_data = self.strategy_service.get_exit_strategies_by_ids(exit_strategy_ids)
    exit_manager = ExitStrategyManager(
        strategies=exit_strategies_data,
        recorder=recorder
    )

# ... 主回测循环 ...

# 检查离场信号（每日检查）
if exit_manager and i < len(dates) - 1:  # ← 如果 exit_manager 为 None，整个退出逻辑被跳过
    next_date = dates[i + 1]
    current_positions = self._prepare_positions_for_exit_check(portfolio, prices, date)
    exits = exit_manager.check_exit_signals(
        positions=current_positions,
        current_date=date,
        rebalance_freq=rebalance_freq,
        all_dates=all_dates
    )
    # ... 执行卖出 ...
```

**问题核心：**
- 如果请求中没有 `exit_strategy_ids`，则 `exit_manager = None`
- 第 155 行的条件 `if exit_manager and ...` 永远为 `False`
- 整个离场检查逻辑被完全跳过
- 系统永远不会卖出股票，即使触发止损条件

---

## 解决方案

### 1. 前端表单验证

#### 文件：`frontend/src/app/backtest/page.tsx`

**修改位置：第 232-242 行**

```typescript
const handleRunBacktest = async () => {
  // ... 现有验证逻辑 ...

  // ⚠️ 验证离场策略（必选）
  if (!exitStrategyIds || exitStrategyIds.length === 0) {
    toast({
      title: '请选择离场策略',
      description: '离场策略是必选项，用于控制何时卖出股票（止损/止盈/持仓时长等）。如果不选择离场策略，系统将永远不会卖出持仓，可能导致巨大亏损。',
      variant: 'destructive'
    })
    return  // ✓ 阻止回测提交
  }

  setIsLoading(true)
  setError(null)
  // ... 提交回测请求 ...
}
```

**验证效果：**
- 用户点击"运行回测"按钮时，系统检查 `exitStrategyIds` 是否为空
- 如果为空，显示错误提示并阻止表单提交
- Toast 消息清楚说明后果："系统将永远不会卖出持仓，可能导致巨大亏损"

---

### 2. 视觉提示增强

#### 文件：`frontend/src/components/backtest/ExitStrategySelector.tsx`

**修改 1：添加"必选"标签（第 122-126 行）**

```typescript
<CardTitle className="flex items-center gap-2">
  离场策略
  <Badge variant="destructive" className="text-xs">必选</Badge>
  {selectedIds.length > 0 && (
    <Badge variant="secondary">{selectedIds.length} 个已选</Badge>
  )}
</CardTitle>
```

**修改 2：添加警告描述（第 128-134 行）**

```typescript
<CardDescription>
  <span className="font-medium text-yellow-600 dark:text-yellow-500">
    ⚠️ 必须选择至少一个离场策略
  </span>
  <span className="block mt-1">
    离场策略控制何时卖出持仓（止损/止盈/持仓时长等），是风险控制的关键。
    不选择离场策略会导致系统永远不卖出，可能造成巨大亏损。
  </span>
</CardDescription>
```

**修改 3：默认展开状态（第 41 行）**

```typescript
const [isOpen, setIsOpen] = useState(true)  // 默认展开，因为是必选项
```

**修改 4：推荐配置功能（第 83-89 行）**

```typescript
const handleSelectRecommended = () => {
  // 推荐策略：止损 + 止盈
  const stopLoss = strategies.find(s => s.category === 'stop_loss')
  const takeProfit = strategies.find(s => s.category === 'take_profit')
  const recommendedIds = [stopLoss?.id, takeProfit?.id].filter((id): id is number => id !== undefined)
  onChange(recommendedIds)
}
```

**修改 5：推荐配置 UI（第 166-183 行）**

```typescript
{selectedIds.length === 0 && (
  <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-3">
    <p className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
      💡 推荐选择
    </p>
    <p className="text-sm text-blue-700 dark:text-blue-300 mb-3">
      建议同时选择<strong>止损</strong>和<strong>止盈</strong>策略，实现风险控制和利润保护。
    </p>
    <Button
      variant="default"
      size="sm"
      onClick={handleSelectRecommended}
      className="w-full"
    >
      使用推荐配置（止损 + 止盈）
    </Button>
  </div>
)}
```

---

## UI 效果对比

### 修改前

```
┌─────────────────────────────┐
│ 离场策略             [▼]   │  ← 默认折叠
└─────────────────────────────┘
```

**问题：**
- 用户可能忽略这个选项
- 没有提示这是必选项
- 可以直接运行回测（导致永远不卖出）

---

### 修改后

```
┌────────────────────────────────────────┐
│ 离场策略 [必选] [0 个已选]      [▲]  │  ← 默认展开
│                                        │
│ ⚠️ 必须选择至少一个离场策略            │
│ 离场策略控制何时卖出持仓（止损/止     │
│ 盈/持仓时长等），是风险控制的关键。   │
│ 不选择离场策略会导致系统永远不卖出，   │
│ 可能造成巨大亏损。                     │
├────────────────────────────────────────┤
│                                        │
│  💡 推荐选择                          │
│  建议同时选择止损和止盈策略，实现风   │
│  险控制和利润保护。                   │
│                                        │
│  [使用推荐配置（止损 + 止盈）]       │
│                                        │
│  [全选] [清空] [推荐配置]             │
│                                        │
│  ┌──────────────────────────┐        │
│  │ □ 止损策略 (10%)         │        │
│  │ □ 止盈策略 (20%)         │        │
│  │ □ 移动止损 (15%)         │        │
│  │ □ 持仓时长 (30天)        │        │
│  └──────────────────────────┘        │
└────────────────────────────────────────┘
```

**改进：**
- ✓ 显眼的"必选"红色标签
- ✓ 黄色警告文字说明后果
- ✓ 默认展开，用户无法忽略
- ✓ 推荐配置按钮，一键选择最佳组合
- ✓ 如果不选择，无法提交回测（表单验证阻止）

---

## 用户流程

### 场景 1：用户忘记选择离场策略

1. 用户填写股票池、日期、资金等参数
2. 用户忽略离场策略选择器（虽然默认展开）
3. 用户点击"运行回测"按钮
4. **系统拦截** → 显示 Toast 错误消息：
   ```
   ❌ 请选择离场策略

   离场策略是必选项，用于控制何时卖出股票
   （止损/止盈/持仓时长等）。如果不选择离场
   策略，系统将永远不会卖出持仓，可能导致
   巨大亏损。
   ```
5. 用户返回选择离场策略
6. 回测成功提交

---

### 场景 2：新用户不知道如何选择

1. 用户看到离场策略选择器（默认展开）
2. 用户看到"0 个已选"和警告消息
3. 用户看到推荐配置提示：
   ```
   💡 推荐选择
   建议同时选择止损和止盈策略，实现风险
   控制和利润保护。

   [使用推荐配置（止损 + 止盈）]
   ```
4. 用户点击"使用推荐配置"按钮
5. 系统自动选择：
   - ✓ 止损策略 (category='stop_loss')
   - ✓ 止盈策略 (category='take_profit')
6. 显示"2 个已选"
7. 回测成功提交

---

## 技术细节

### 验证触发时机

验证发生在前端表单提交阶段，而非后端 API 层：

```typescript
// frontend/src/app/backtest/page.tsx

const handleRunBacktest = async () => {
  // 验证顺序：
  // 1. 股票池不为空
  // 2. 日期有效
  // 3. 资金 > 0
  // 4. ✓ 离场策略至少选择一个 ← 新增验证

  if (!exitStrategyIds || exitStrategyIds.length === 0) {
    toast({ ... })
    return  // 阻止 API 请求
  }

  // 通过验证，发送请求
  await apiClient.runBacktest({ exit_strategy_ids: exitStrategyIds, ... })
}
```

**设计理由：**
- 前端验证：快速反馈，无需等待网络请求
- 用户体验更好（即时 Toast 提示）
- 减少无效 API 调用

---

### 推荐策略选择逻辑

```typescript
const handleSelectRecommended = () => {
  const stopLoss = strategies.find(s => s.category === 'stop_loss')
  const takeProfit = strategies.find(s => s.category === 'take_profit')
  const recommendedIds = [stopLoss?.id, takeProfit?.id]
    .filter((id): id is number => id !== undefined)
  onChange(recommendedIds)
}
```

**智能匹配：**
- 根据 `category` 字段查找策略
- `stop_loss`：风险控制（防止大幅亏损）
- `take_profit`：利润保护（防止盈利回吐）
- 使用 TypeScript 类型守卫过滤 `undefined`

---

## 测试验证

### 测试步骤

1. **测试场景：不选择离场策略**
   - 访问 `/backtest?type=unified&id=6`
   - 填写股票池、日期、资金
   - **不选择任何离场策略**
   - 点击"运行回测"
   - **预期**：显示错误 Toast，阻止提交

2. **测试场景：使用推荐配置**
   - 访问回测页面
   - 点击"使用推荐配置（止损 + 止盈）"
   - **预期**：自动选择 2 个策略，显示"2 个已选"
   - 点击"运行回测"
   - **预期**：成功提交，回测正常运行

3. **测试场景：手动选择单个策略**
   - 手动勾选"止损策略"
   - **预期**：显示"1 个已选"
   - 点击"运行回测"
   - **预期**：成功提交（满足至少 1 个的要求）

---

## 相关文档

- [调仓逻辑优化说明](./REBALANCE_OPTIMIZATION.md) - 解释为什么离场策略如此重要
- [交易明细过滤功能](./TRADES_TABLE_FILTER.md) - 如何分析回测结果中的交易记录

---

## 总结

### 核心价值

1. **防止灾难性损失**：强制用户选择离场策略，避免永远不卖出的情况
2. **用户教育**：通过警告消息和推荐配置，帮助用户理解离场策略的重要性
3. **降低使用门槛**：推荐配置功能让新手也能快速选择合适的策略组合
4. **更好的 UX**：默认展开 + 视觉提示 + 即时验证

### 实施效果

- ✓ 用户无法绕过离场策略选择
- ✓ 清晰的错误提示说明后果
- ✓ 推荐配置降低决策难度
- ✓ 默认展开确保可见性

### 向后兼容性

- ✓ API 层不受影响（后端仍然允许不传 `exit_strategy_ids`）
- ✓ 仅在前端增加验证逻辑
- ✓ 现有回测逻辑保持不变
