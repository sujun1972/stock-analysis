# 回测中使用离场策略指南

> 版本: v1.0.0
> 创建时间: 2026-02-13

## 📋 概述

现在回测页面支持选择一个或多个离场策略，用于在回测过程中自动管理持仓的离场时机。

---

## 🎯 功能特性

### 1. **离场策略选择器**

在回测页面新增了"离场策略"选择器，具有以下特点：

- ✅ 支持多选（可同时选择多个离场策略）
- ✅ 默认折叠，不影响原有页面布局
- ✅ 显示每个离场策略的详细信息（描述、风险等级、标签）
- ✅ 全选/清空快捷按钮
- ✅ 实时显示已选择的策略数量

### 2. **离场策略执行优先级**

当选择多个离场策略时，按以下优先级执行：

```
11. 反向入场信号（最高优先级）
10. 止损策略
9.  移动止损策略
8.  止盈策略
...
3.  持仓时长策略
```

当多个策略同时触发时，选择优先级最高的策略执行离场。

---

## 🚀 使用方法

### Step 1: 选择入场策略

1. 从策略列表页面点击某个入场策略的"回测"按钮
2. 或从 ML 模型页面点击某个模型的"回测"按钮

### Step 2: 配置基本参数

在回测页面配置：
- 股票池
- 回测日期范围
- 初始资金
- 调仓频率

### Step 3: 选择离场策略（可选）

1. 点击"离场策略"卡片右上角的展开按钮
2. 浏览可用的离场策略列表
3. 勾选需要使用的离场策略（可多选）
4. 或点击"全选"使用所有离场策略

**内置离场策略**:
- **止损离场策略**: 当亏损超过10%时触发离场
- **止盈离场策略**: 当盈利达到20%时触发离场
- **移动止损离场策略**: 跟踪最高价，回撤超过5%时触发离场
- **持仓时长离场策略**: 持仓超过30天时触发离场

### Step 4: 运行回测

点击"开始回测"按钮，系统会：

1. 使用入场策略生成买入信号
2. 在每个交易日检查离场条件：
   - 检查是否有反向入场信号（例如持有多头时出现做空信号）
   - 检查所有已选择的离场策略
   - 按优先级执行第一个触发的离场策略
3. 生成完整的回测报告

---

## 📊 回测结果解读

### 离场信息记录

回测结果中会记录每次离场的详细信息：

```json
{
  "trade_type": "exit",
  "stock_code": "600000.SH",
  "exit_date": "2024-05-15",
  "exit_reason": "risk_control",
  "exit_trigger": "stop_loss",
  "entry_price": 10.0,
  "exit_price": 8.9,
  "pnl_pct": -0.11,
  "metadata": {
    "stop_loss_pct": 0.10,
    "actual_loss_pct": -0.11
  }
}
```

### 离场原因 (exit_reason)

- `risk_control`: 风险控制（止损、移动止损）
- `strategy`: 策略信号（止盈、持仓时长）
- `reverse_entry`: 反向入场信号

### 离场触发器 (exit_trigger)

- `stop_loss`: 止损
- `take_profit`: 止盈
- `trailing_stop`: 移动止损
- `max_holding_period`: 持仓时长
- `reverse_entry`: 反向入场

---

## 🔧 API 使用

### 前端 TypeScript 示例

```typescript
// 选择离场策略
const [exitStrategyIds, setExitStrategyIds] = useState<number[]>([])

// 运行回测
const response = await apiClient.runUnifiedBacktest({
  strategy_id: 123,  // 入场策略ID
  stock_pool: ['600000.SH', '000001.SZ'],
  start_date: '2023-01-01',
  end_date: '2023-12-31',
  initial_capital: 1000000,
  rebalance_freq: 'W',
  exit_strategy_ids: [10, 11, 12]  // 离场策略IDs
})
```

### 后端 Python 示例

```python
from src.ml.exit_strategy import (
    StopLossExitStrategy,
    TakeProfitExitStrategy,
    CompositeExitManager
)

# 创建离场策略
exit_manager = CompositeExitManager([
    StopLossExitStrategy(stop_loss_pct=0.10, priority=10),
    TakeProfitExitStrategy(take_profit_pct=0.20, priority=8)
])

# 运行回测
result = engine.backtest_long_only(
    signals=signals,
    prices=prices,
    top_n=50,
    holding_period=5,
    rebalance_freq='W',
    exit_manager=exit_manager  # 传入离场管理器
)
```

---

## 💡 最佳实践

### 1. 离场策略组合建议

**保守型组合** (适合风险厌恶者):
```
✅ 止损离场策略 (10%)
✅ 移动止损离场策略 (5%)
✅ 持仓时长离场策略 (30天)
```

**平衡型组合** (风险收益平衡):
```
✅ 止损离场策略 (10%)
✅ 止盈离场策略 (20%)
✅ 移动止损离场策略 (5%)
```

**激进型组合** (追求高收益):
```
✅ 止盈离场策略 (30%)
✅ 持仓时长离场策略 (60天)
```

### 2. 参数调优建议

对比不同离场策略组合的回测结果：

1. **无离场策略**: 纯重新平衡策略（基准）
2. **只用止损**: 风险控制效果
3. **止损+止盈**: 完整风控
4. **全部离场策略**: 最大化策略组合

通过对比夏普率、最大回撤、年化收益等指标，找到最优组合。

### 3. 注意事项

⚠️ **离场策略是可选的**
- 如果不选择任何离场策略，将使用默认的重新平衡策略
- 重新平衡策略：在每个调仓日，自动卖出不在新信号中的股票

⚠️ **离场策略只能配合入场策略使用**
- 离场策略不能单独回测
- 必须先选择一个入场策略，然后才能添加离场策略

⚠️ **多个离场策略可能产生冲突**
- 优先级系统会自动解决冲突
- 只有优先级最高的离场信号会被执行

---

## 🐛 常见问题

### Q1: 为什么我看不到离场策略选择器？

**A**: 请确保：
1. 已经选择了入场策略（通过 URL 参数）
2. 数据库中有可用的离场策略（检查 `strategies` 表中 `strategy_type='exit'` 的记录）
3. 前端已更新到最新版本

### Q2: 离场策略会影响回测性能吗？

**A**:
- 影响很小。离场检查是在每日进行，计算复杂度为 O(N)，N 为持仓数量
- 通常持仓数量 < 50，每日检查耗时 < 1ms
- 对整体回测性能影响可忽略不计

### Q3: 可以自定义离场策略吗？

**A**: 可以！
1. 在策略管理页面创建新策略
2. 继承 `BaseExitStrategy` 类
3. 实现 `should_exit()` 方法
4. 设置 `strategy_type='exit'`

示例代码见 [adaptive_exit_strategy.py](../core/src/ml/adaptive_exit_strategy.py)

### Q4: 离场策略的默认参数可以修改吗？

**A**:
- 当前版本使用策略定义中的 `default_params`
- 未来版本会支持在回测页面动态调整离场策略参数

---

## 📚 相关文档

- [离场策略核心代码](../core/src/ml/exit_strategy.py)
- [自适应离场策略](../core/src/ml/adaptive_exit_strategy.py)
- [离场策略前后端集成](./exit_strategy_integration.md)
- [回测引擎文档](../core/src/backtest/backtest_engine.py)

---

## ✅ 总结

现在你可以在回测页面：

1. ✅ 查看所有可用的离场策略
2. ✅ 选择一个或多个离场策略
3. ✅ 运行包含离场策略的回测
4. ✅ 分析离场策略对回测结果的影响
5. ✅ 对比不同离场策略组合的效果

离场策略让你的回测更接近真实交易场景，通过自动化的风险管理提升策略的稳健性！
