# ML 模型评估指标详解

**文档版本**: v5.1.0
**最后更新**: 2026-02-08

---

## 📋 目录

- [评估指标的两个阶段](#评估指标的两个阶段)
- [阶段 1: 模型训练评估](#阶段-1-模型训练评估)
- [阶段 2: 策略回测评估](#阶段-2-策略回测评估)
- [完整评估流程](#完整评估流程)
- [MLEntry 是否需要退出策略](#mlentry-是否需要退出策略)

---

## 评估指标的两个阶段

### 重要概念区分

机器学习量化策略的评估分为**两个独立的阶段**：

```
阶段 1: 模型训练评估 (离线评估)
  └─ 评估模型的预测能力
  └─ 指标: RMSE, R², IC, Rank IC

阶段 2: 策略回测评估 (在线评估)
  └─ 评估完整策略的交易表现
  └─ 指标: 夏普比率, 最大回撤, 年化收益率
```

### 为什么需要两个阶段？

**模型好 ≠ 策略好！**

- **模型评估**: 预测准确度
- **策略评估**: 实际赚钱能力

**示例**：
```
模型 A: IC = 0.15 (预测很准)
策略 A: 夏普比率 = 0.5 (实际表现差)

原因：交易成本太高、信号频繁切换导致

模型 B: IC = 0.08 (预测一般)
策略 B: 夏普比率 = 1.2 (实际表现好)

原因：信号稳定、持仓时间长、成本低
```

---

## 阶段 1: 模型训练评估

### 1.1 评估指标

#### RMSE (Root Mean Squared Error)

**定义**: 预测收益率与实际收益率的均方根误差

```python
from sklearn.metrics import mean_squared_error

# 计算 RMSE
predictions = model.predict(X_val)
rmse = np.sqrt(mean_squared_error(y_val, predictions))

print(f"RMSE: {rmse:.4f}")  # 例如: 0.0245 (2.45%)
```

**解读**:
- RMSE 越小越好
- 0.02 (2%) 以下表示预测较准确
- 0.05 (5%) 以上表示预测较差

#### R² (决定系数)

**定义**: 模型对收益率变化的解释能力

```python
from sklearn.metrics import r2_score

r2 = r2_score(y_val, predictions)
print(f"R²: {r2:.4f}")  # 例如: 0.12 (12%)
```

**解读**:
- R² ∈ [0, 1]，越大越好
- 量化领域 R² > 0.05 就算不错（股市噪声大）
- R² < 0 表示模型比随机预测还差

#### IC (Information Coefficient)

**定义**: 预测收益率与实际收益率的皮尔逊相关系数

```python
ic = np.corrcoef(y_val, predictions)[0, 1]
print(f"IC: {ic:.4f}")  # 例如: 0.08
```

**解读**:
- IC ∈ [-1, 1]
- IC > 0.05: 模型有预测能力
- IC > 0.10: 模型预测能力很强
- IC < 0: 模型预测方向错误

#### Rank IC (秩相关系数)

**定义**: 预测排名与实际排名的斯皮尔曼相关系数

```python
from scipy.stats import spearmanr

rank_ic = spearmanr(y_val, predictions)[0]
print(f"Rank IC: {rank_ic:.4f}")  # 例如: 0.12
```

**解读**:
- Rank IC 比 IC 更鲁棒（对异常值不敏感）
- Rank IC > 0.10: 模型排序能力强
- 通常 Rank IC > IC

### 1.2 完整的训练评估代码

```python
class ModelTrainer:
    def train(self, stock_pool, market_data):
        # 准备数据
        X_train, y_train, X_val, y_val = self._prepare_data(...)

        # 训练模型
        model = self._train_model(X_train, y_train)

        # 评估模型
        metrics = self._evaluate_model(model, X_val, y_val)

        return TrainedModel(model, ..., metrics=metrics)

    def _evaluate_model(self, model, X_val, y_val):
        """模型评估（阶段 1）"""
        # 预测
        predictions = model.predict(X_val)

        # 计算指标
        rmse = np.sqrt(mean_squared_error(y_val, predictions))
        r2 = r2_score(y_val, predictions)
        ic = np.corrcoef(y_val, predictions)[0, 1]
        rank_ic = spearmanr(y_val, predictions)[0]

        metrics = {
            'rmse': rmse,
            'r2': r2,
            'ic': ic,
            'rank_ic': rank_ic
        }

        print("\n📊 模型评估结果:")
        print(f"  RMSE:     {rmse:.4f}")
        print(f"  R²:       {r2:.4f}")
        print(f"  IC:       {ic:.4f}")
        print(f"  Rank IC:  {rank_ic:.4f}")

        return metrics
```

**输出示例**:
```
📊 模型评估结果:
  RMSE:     0.0238
  R²:       0.1245
  IC:       0.0856
  Rank IC:  0.1124

✅ 模型训练完成! IC > 0.05，模型有预测能力
```

---

## 阶段 2: 策略回测评估

### 2.1 评估指标

#### 夏普比率 (Sharpe Ratio)

**定义**: 风险调整后的收益率

```python
sharpe_ratio = (annual_return - risk_free_rate) / volatility
```

**解读**:
- 夏普比率 > 1.0: 策略表现优秀
- 夏普比率 > 2.0: 策略表现非常优秀
- 夏普比率 < 0: 策略亏损

#### 最大回撤 (Max Drawdown)

**定义**: 从最高点到最低点的最大跌幅

```python
drawdown = (equity_curve - equity_curve.cummax()) / equity_curve.cummax()
max_drawdown = drawdown.min()
```

**解读**:
- 最大回撤越小越好
- -10% 以内: 风险较低
- -30% 以上: 风险较高

#### 年化收益率 (Annual Return)

**定义**: 年化后的收益率

```python
total_days = (end_date - start_date).days
annual_return = (final_value / initial_value) ** (365 / total_days) - 1
```

### 2.2 完整的回测评估代码

```python
# 使用 MLEntry 策略进行回测
entry_strategy = MLEntry(model_path='ml_entry_model.pkl')
exit_strategy = TimeBasedExit(max_holding_days=10)
risk_manager = RiskManager()

engine = BacktestEngine(
    entry_strategy=entry_strategy,
    exit_strategy=exit_strategy,
    risk_manager=risk_manager
)

# 运行回测（阶段 2）
result = engine.run(
    stock_pool=stock_pool,
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 策略评估指标
print("\n📈 策略回测结果:")
print(f"  总收益率:     {result.total_return:.2%}")
print(f"  年化收益率:   {result.annual_return:.2%}")
print(f"  夏普比率:     {result.sharpe_ratio:.2f}")
print(f"  最大回撤:     {result.max_drawdown:.2%}")
print(f"  胜率:         {result.win_rate:.2%}")
```

**输出示例**:
```
📈 策略回测结果:
  总收益率:     28.50%
  年化收益率:   32.10%
  夏普比率:     1.45
  最大回撤:     -12.30%
  胜率:         58.20%

✅ 策略表现优秀! 夏普比率 > 1.0
```

---

## 完整评估流程

### 流程图

```
┌─────────────────────────────────────────────────┐
│           完整的 ML 策略评估流程                 │
└─────────────────────────────────────────────────┘

Step 1: 训练模型
  ├─ 准备数据 (2020-2023)
  ├─ 训练 MLEntry 模型
  └─ 模型评估 (阶段 1)
      ├─ RMSE: 0.0238
      ├─ R²: 0.1245
      ├─ IC: 0.0856      ← 模型预测能力
      └─ Rank IC: 0.1124
        ↓
  ✅ IC > 0.05, 模型可用
        ↓

Step 2: 回测策略
  ├─ 创建 MLEntry 策略
  ├─ 配置退出策略 (TimeBasedExit)
  ├─ 配置风控 (RiskManager)
  └─ 运行回测 (2024)
        ↓

Step 3: 策略评估 (阶段 2)
  ├─ 总收益率: 28.50%
  ├─ 年化收益率: 32.10%
  ├─ 夏普比率: 1.45      ← 策略实际表现
  ├─ 最大回撤: -12.30%
  └─ 胜率: 58.20%
        ↓
  ✅ 夏普比率 > 1.0, 策略可用

Step 4: 实盘部署
  └─ 使用训练好的模型 + 策略配置
```

### 代码示例

```python
# ========================================
# Step 1: 训练模型 + 模型评估 (阶段 1)
# ========================================
from core.ml.model_trainer import ModelTrainer, TrainingConfig

config = TrainingConfig(
    model_type='lightgbm',
    train_start_date='2020-01-01',
    train_end_date='2023-12-31',
    forward_window=5
)

trainer = ModelTrainer(config)
trained_model = trainer.train(stock_pool, market_data)

# 模型评估指标
print(f"IC: {trained_model.metrics['ic']:.4f}")
print(f"Rank IC: {trained_model.metrics['rank_ic']:.4f}")

# 保存模型
trained_model.save('models/ml_entry_model.pkl')

# ========================================
# Step 2 & 3: 回测策略 + 策略评估 (阶段 2)
# ========================================
from core.strategies.entries import MLEntry
from core.strategies.exits import TimeBasedExit
from core.backtest import BacktestEngine

# 创建策略
entry_strategy = MLEntry(model_path='models/ml_entry_model.pkl')
exit_strategy = TimeBasedExit(max_holding_days=10)

# 回测
engine = BacktestEngine(entry_strategy, exit_strategy, risk_manager)
result = engine.run(
    stock_pool=stock_pool,
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 策略评估指标
print(f"夏普比率: {result.sharpe_ratio:.2f}")
print(f"最大回撤: {result.max_drawdown:.2%}")
```

---

## MLEntry 是否需要退出策略？

### 答案：**需要！**

#### 原因 1: MLEntry 只负责入场

```python
class MLEntry(EntryStrategy):
    """ML 入场策略 - 只负责"买什么、买多少"

    输出:
    - 做多哪些股票
    - 做空哪些股票
    - 各自的权重

    不负责:
    - 何时卖出 ← 这是退出策略的职责
    - 止损管理 ← 这是风控的职责
    """
    def generate_signals(self, stock_pool, market_data, date):
        # ... 生成入场信号 ...
        return signals
```

#### 原因 2: 完整的策略 = 入场 + 退出 + 风控

```python
# ✅ 完整的策略配置
engine = BacktestEngine(
    entry_strategy=MLEntry(...),        # 入场: 买什么
    exit_strategy=TimeBasedExit(...),   # 退出: 何时卖
    risk_manager=RiskManager(...)       # 风控: 止损
)
```

#### 退出策略的选择

**选项 1: 时间退出 (简单有效)**
```python
exit_strategy = TimeBasedExit(max_holding_days=10)
# 持仓 10 天后强制退出
```

**选项 2: 信号反转退出**
```python
exit_strategy = SignalReversalExit(
    indicator='momentum',
    enable_reverse=False  # 不反向开仓
)
# 当动量反转时退出
```

**选项 3: 目标达成退出**
```python
exit_strategy = TargetReachedExit(take_profit_pct=0.15)
# 盈利 15% 后退出
```

**选项 4: ML 退出策略 (高级)**
```python
# 训练专门的退出模型
exit_strategy = MLExit(model_path='ml_exit_model.pkl')
```

### 推荐配置

**初学者推荐**:
```python
# 简单、稳定、易于理解
entry_strategy = MLEntry(model_path='ml_entry_model.pkl')
exit_strategy = TimeBasedExit(max_holding_days=10)
```

**进阶配置**:
```python
# 结合多种退出条件
from core.strategies.exits import CompositeExit

exit_strategy = CompositeExit(
    strategies=[
        TimeBasedExit(max_holding_days=20),      # 最多持仓 20 天
        TargetReachedExit(take_profit_pct=0.15), # 盈利 15% 退出
    ],
    mode='any'  # 任意一个条件满足就退出
)
```

---

## 总结

### 关键要点

1. **两阶段评估**:
   - 阶段 1 (模型评估): RMSE, R², IC, Rank IC
   - 阶段 2 (策略评估): 夏普比率, 最大回撤, 年化收益率

2. **MLEntry 需要退出策略**:
   - MLEntry 只负责入场信号
   - 必须配合退出策略使用
   - 推荐: TimeBasedExit (简单有效)

3. **评估指标的意义**:
   - IC > 0.05: 模型可用
   - 夏普比率 > 1.0: 策略可用
   - 两者都满足，才是好策略！

---

## 相关文档

- [机器学习系统](./README.md)
- [架构详解](../architecture/overview.md)
- [最佳实践](../guides/best-practices.md)

---

**文档版本**: v5.1.0
**最后更新**: 2026-02-08
