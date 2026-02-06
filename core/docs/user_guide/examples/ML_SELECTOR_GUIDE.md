# MLSelector 机器学习选股器使用指南

**MLSelector Machine Learning Stock Selection Guide**

**版本**: v3.0.0
**最后更新**: 2026-02-06

---

## 📚 概述

MLSelector 是 v3.0 三层架构的核心组件，提供两种智能选股模式：

1. **多因子加权模式** (multi_factor_weighted): 基于启发式规则的快速选股
2. **LightGBM 排序模式** (lightgbm_ranker): 基于机器学习的智能排序选股

本指南配套3个示例文件，帮助你全面掌握 MLSelector 的使用。

---

## 📂 示例文件清单

### 1. [ml_selector_usage_example.py](ml_selector_usage_example.py)
**基础用法示例 - 快速上手**

**包含示例**:
- 示例1: 基础多因子加权选股
- 示例2: 自定义特征集
- 示例3: 价格过滤
- 示例4: 使用默认特征集
- 示例5: 不同时期选股对比
- 示例6: 单一特征探索
- 示例7: LightGBM 模式（无模型回退）
- 示例8: 三层架构策略集成

**适合人群**: 初学者
**学习时间**: 30分钟

---

### 2. [ml_selector_multi_factor_weighted_example.py](ml_selector_multi_factor_weighted_example.py)
**多因子加权模式深度指南**

**包含示例**:
- 示例1: 基础等权模型
- 示例2: 自定义因子权重
- 示例3: 因子分组加权
- 示例4: 4种归一化方法对比（z_score, min_max, rank, none）
- 示例5: 价格过滤 + 多因子加权
- 示例6: 完整回测流程
- 示例7: 多策略组合（动量/技术/均衡）
- 示例8: 参数敏感性分析

**适合人群**: 进阶用户
**学习时间**: 1小时

---

### 3. [ml3_lightgbm_ranker_example.py](ml3_lightgbm_ranker_example.py)
**LightGBM 排序模型完整流程**

**包含示例**:
- 示例1: 训练 LightGBM 排序模型（完整流程）
- 示例2: 使用训练好的模型进行选股
- 示例3: 多因子加权 vs LightGBM 对比
- 示例4: LightGBM 选股器回测
- 示例5: 超参数调优

**适合人群**: 高级用户
**学习时间**: 2小时

---

### 4. [ml4_feature_integration_example.py](ml4_feature_integration_example.py)
**特征库集成示例（125+ 因子）**

**包含示例**:
- 示例1: 基础用法（完整特征库）
- 示例2: 使用通配符 `alpha:*`（所有Alpha因子）
- 示例3: 使用通配符 `tech:*`（所有技术指标）
- 示例4: 类别选择（指定因子类别）
- 示例5: 混合格式（通配符 + 具体特征）
- 示例6: 性能对比（快速模式 vs 完整特征库）
- 示例7: 自定义因子权重
- 示例8: 查看可用特征分类

**适合人群**: 高级用户
**学习时间**: 1.5小时

---

## 🚀 快速开始

### 步骤 1: 基础选股（5分钟）

```bash
# 运行基础示例
cd /Volumes/MacDriver/stock-analysis/core/docs/user_guide/examples
python ml_selector_usage_example.py
```

**你将学到**:
- 如何创建 MLSelector 实例
- 如何执行选股
- 如何配置基础参数

---

### 步骤 2: 多因子加权进阶（20分钟）

```bash
# 运行多因子加权示例
python ml_selector_multi_factor_weighted_example.py
```

**你将学到**:
- 自定义因子权重
- 因子分组策略
- 归一化方法选择
- 参数敏感性分析

---

### 步骤 3: LightGBM 排序模型（60分钟）

```bash
# 运行 LightGBM 示例
python ml3_lightgbm_ranker_example.py
```

**你将学到**:
- 如何准备训练数据
- 如何训练排序模型
- 如何使用模型进行选股
- 如何进行超参数调优

---

### 步骤 4: 特征库集成（30分钟）

```bash
# 运行特征库示例
python ml4_feature_integration_example.py
```

**你将学到**:
- 如何使用 125+ Alpha 因子
- 通配符语法（alpha:*, tech:*）
- 类别选择策略
- 性能优化技巧

---

## 📖 详细示例说明

### 1. 多因子加权模式

#### 1.1 基础用法

```python
from src.strategies.three_layer.selectors.ml_selector import MLSelector

# 创建选股器
selector = MLSelector(params={
    'mode': 'multi_factor_weighted',
    'features': 'momentum_20d,rsi_14d,volatility_20d',
    'normalization_method': 'z_score',
    'top_n': 10
})

# 选股
selected_stocks = selector.select(test_date, prices)
print(f"选中股票: {selected_stocks}")
```

**参数说明**:
- `mode`: 选股模式（'multi_factor_weighted' 或 'lightgbm_ranker'）
- `features`: 因子列表（逗号分隔）
- `normalization_method`: 归一化方法（z_score/min_max/rank/none）
- `top_n`: 选出股票数量

---

#### 1.2 自定义因子权重

```python
import json

# 配置因子权重
factor_weights = json.dumps({
    "momentum_20d": 0.6,  # 60% 权重
    "rsi_14d": 0.4        # 40% 权重
})

selector = MLSelector(params={
    'mode': 'multi_factor_weighted',
    'features': 'momentum_20d,rsi_14d',
    'factor_weights': factor_weights,
    'normalization_method': 'z_score',
    'top_n': 10
})
```

**适用场景**: 强调特定因子（如强动量策略）

---

#### 1.3 因子分组加权

```python
# 配置因子分组
factor_groups = json.dumps({
    "momentum": ["momentum_5d", "momentum_20d", "momentum_60d"],
    "technical": ["rsi_14d", "rsi_28d", "ma_cross_20d"],
    "volatility": ["volatility_20d", "atr_14d"]
})

# 配置分组权重
group_weights = json.dumps({
    "momentum": 0.5,    # 50% 权重
    "technical": 0.3,   # 30% 权重
    "volatility": 0.2   # 20% 权重
})

selector = MLSelector(params={
    'mode': 'multi_factor_weighted',
    'features': 'momentum_5d,momentum_20d,momentum_60d,rsi_14d,rsi_28d,ma_cross_20d,volatility_20d,atr_14d',
    'factor_groups': factor_groups,
    'group_weights': group_weights,
    'normalization_method': 'z_score',
    'top_n': 10
})
```

**优势**:
- 组内等权，组间加权
- 控制因子类别的影响力
- 提高模型稳定性

---

#### 1.4 归一化方法对比

| 方法 | 公式 | 适用场景 | 优缺点 |
|------|------|---------|--------|
| **z_score** | `(x - mean) / std` | 因子值呈正态分布 | ✅ 标准化<br>❌ 受异常值影响 |
| **min_max** | `(x - min) / (max - min)` | 因子值范围固定 | ✅ 保留分布<br>❌ 受极值影响 |
| **rank** | 排名 / 总数 | 非线性关系 | ✅ 抗异常值<br>❌ 损失信息 |
| **none** | 原始值 | 因子已归一化 | ✅ 保留原始信息<br>❌ 量纲影响大 |

**示例**:
```python
# 对比不同归一化方法
methods = ['z_score', 'min_max', 'rank', 'none']
results = {}

for method in methods:
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'features': 'momentum_20d,rsi_14d,volatility_20d',
        'normalization_method': method,
        'top_n': 10
    })
    selected_stocks = selector.select(test_date, prices)
    results[method] = selected_stocks
```

---

### 2. LightGBM 排序模式

#### 2.1 训练流程

**步骤 1: 准备数据**
```python
from tools.train_stock_ranker_lgbm import StockRankerTrainer

trainer = StockRankerTrainer(
    label_forward_days=5,      # 预测未来5日收益
    label_threshold=0.02        # 收益率阈值 2%
)

# 准备训练数据
X_train, y_train, groups_train = trainer.prepare_training_data(
    prices=prices,
    start_date='2020-02-01',
    end_date='2021-12-31',
    sample_freq='W'  # 周频采样
)
```

**步骤 2: 训练模型**
```python
model = trainer.train_model(
    X_train=X_train,
    y_train=y_train,
    groups_train=groups_train,
    model_params={
        'n_estimators': 100,
        'learning_rate': 0.05,
        'max_depth': 6,
        'num_leaves': 31
    }
)
```

**步骤 3: 评估模型**
```python
metrics = trainer.evaluate_model(
    model=model,
    X_test=X_test,
    y_test=y_test,
    groups_test=groups_test
)
print(f"NDCG@10: {metrics['ndcg@10']:.4f}")
```

**步骤 4: 保存模型**
```python
model_path = './models/stock_ranker_lgbm.pkl'
trainer.save_model(model, model_path)
```

---

#### 2.2 使用模型选股

```python
# 创建选股器（LightGBM 模式）
selector = MLSelector(params={
    'mode': 'lightgbm_ranker',
    'model_path': './models/stock_ranker_lgbm.pkl',
    'top_n': 30,
    'filter_min_price': 10,
    'filter_max_price': 500
})

# 执行选股
selected_stocks = selector.select(test_date, prices)
print(f"LightGBM 选中: {selected_stocks}")
```

---

#### 2.3 性能对比

| 模式 | 训练时间 | 推理时间 | 准确率 | 适用场景 |
|------|---------|---------|--------|---------|
| **多因子加权** | 无需训练 | <15ms | 中等 | 快速原型、实时选股 |
| **LightGBM Ranker** | <5秒 | <100ms | 高 | 生产环境、高精度需求 |

**推荐策略**:
- 开发阶段：使用多因子加权快速迭代
- 生产环境：使用 LightGBM 提升效果

---

### 3. 特征库集成（125+ 因子）

#### 3.1 通配符语法

**所有 Alpha 因子**:
```python
selector = MLSelector(params={
    'mode': 'multi_factor_weighted',
    'use_feature_engine': True,
    'features': 'alpha:*'  # 自动展开为 125+ Alpha 因子
})
```

**所有技术指标**:
```python
selector = MLSelector(params={
    'mode': 'multi_factor_weighted',
    'use_feature_engine': True,
    'features': 'tech:*'  # 自动展开为 60+ 技术指标
})
```

**类别选择**:
```python
selector = MLSelector(params={
    'mode': 'multi_factor_weighted',
    'use_feature_engine': True,
    'features': 'alpha:momentum,alpha:reversal,tech:rsi,tech:macd'
})
```

**混合格式**:
```python
selector = MLSelector(params={
    'mode': 'multi_factor_weighted',
    'use_feature_engine': True,
    'features': 'momentum_20d,alpha:reversal,tech:ma'
})
```

---

#### 3.2 特征分类清单

**Alpha 因子类别**:
- `momentum`: 动量因子（20+）
- `reversal`: 反转因子（15+）
- `volatility`: 波动率因子（12+）
- `volume`: 成交量因子（18+）
- `trend`: 趋势因子（10+）

**技术指标类别**:
- `ma`: 移动平均线（8+）
- `ema`: 指数移动平均（6+）
- `rsi`: 相对强弱指标（4+）
- `macd`: MACD 指标（3+）
- `bb`: 布林带（4+）
- `atr`: ATR 指标（3+）
- `cci`: CCI 指标（2+）

---

#### 3.3 性能优化建议

**快速模式 vs 完整特征库**:

```python
# 快速模式（开发/调试）
selector_fast = MLSelector(params={
    'mode': 'multi_factor_weighted',
    'use_feature_engine': False,  # 快速模式
    'features': 'momentum_20d,rsi_14d,volatility_20d'
})
# 耗时: ~12ms

# 完整特征库（生产环境）
selector_full = MLSelector(params={
    'mode': 'multi_factor_weighted',
    'use_feature_engine': True,  # 完整特征库
    'features': 'alpha:*'  # 125+ 因子
})
# 耗时: ~650ms
```

**优化建议**:
1. ✅ 开发阶段使用 `use_feature_engine=False`
2. ✅ 生产环境使用 `use_feature_engine=True`
3. ✅ 使用类别选择代替 `alpha:*`（减少冗余）
4. ✅ 启用特征缓存（自动优化）

---

## 🎯 实战场景

### 场景 1: 动量选股策略

```python
# 动量导向策略
selector = MLSelector(params={
    'mode': 'multi_factor_weighted',
    'features': 'momentum_5d,momentum_20d,momentum_60d',
    'normalization_method': 'z_score',
    'top_n': 20
})
```

**适用市场**: 趋势市场、牛市
**预期效果**: 捕捉强势股

---

### 场景 2: 均衡多因子策略

```python
# 均衡配置
factor_groups = json.dumps({
    "momentum": ["momentum_20d"],
    "technical": ["rsi_14d"],
    "volatility": ["volatility_20d"]
})
group_weights = json.dumps({
    "momentum": 0.33,
    "technical": 0.33,
    "volatility": 0.34
})

selector = MLSelector(params={
    'mode': 'multi_factor_weighted',
    'features': 'momentum_20d,rsi_14d,volatility_20d',
    'factor_groups': factor_groups,
    'group_weights': group_weights,
    'normalization_method': 'rank',
    'top_n': 30
})
```

**适用市场**: 震荡市场
**预期效果**: 稳定收益

---

### 场景 3: 机器学习高精度选股

```python
# 1. 训练模型
trainer = StockRankerTrainer()
X_train, y_train, groups = trainer.prepare_training_data(prices, ...)
model = trainer.train_model(X_train, y_train, groups)
trainer.save_model(model, './models/ranker.pkl')

# 2. 使用模型选股
selector = MLSelector(params={
    'mode': 'lightgbm_ranker',
    'model_path': './models/ranker.pkl',
    'top_n': 50
})
```

**适用市场**: 所有市场
**预期效果**: 高精度预测

---

## 📊 性能指标

### 选股性能

| 模式 | 股票数 | 因子数 | 耗时 | 内存 |
|------|--------|--------|------|------|
| 快速模式 | 20 | 3 | <15ms | ~10MB |
| 完整模式 | 20 | 125+ | <700ms | ~50MB |
| LightGBM | 100 | 50+ | <100ms | ~20MB |

### 回测性能

| 策略类型 | 数据规模 | 耗时 | 提升 |
|---------|---------|------|------|
| 单层策略 | 100股×252天 | 120s | 基准 |
| 三层架构（快速） | 100股×252天 | 17.6s | 6.8× |
| 三层架构（LightGBM） | 100股×252天 | 18.8s | 6.4× |

---

## ❓ 常见问题

### Q1: 多因子加权和 LightGBM 如何选择？

**A**:
- **快速原型**: 多因子加权（无需训练，<15ms）
- **生产环境**: LightGBM（高精度，<100ms）
- **实时选股**: 多因子加权（延迟更低）
- **离线分析**: LightGBM（准确率更高）

---

### Q2: 如何选择归一化方法？

**A**:
- **z_score**: 因子呈正态分布时首选
- **min_max**: 需要保留分布形状时使用
- **rank**: 存在异常值或非线性关系时使用
- **none**: 因子已预处理或量纲一致时使用

建议：先尝试 `z_score`，有问题再换 `rank`

---

### Q3: LightGBM 模型训练失败怎么办？

**A**:
1. 检查数据质量（缺失值、异常值）
2. 增加训练样本数（建议 >1000）
3. 调整超参数（降低 `max_depth`、`num_leaves`）
4. 检查标签分布（5档评分是否均衡）

---

### Q4: 特征过多会影响性能吗？

**A**:
是的。建议策略：
- 开发阶段：使用3-5个核心因子
- 测试阶段：使用类别选择（如 `alpha:momentum,tech:rsi`）
- 生产环境：使用完整特征库 + 缓存优化

---

### Q5: 如何评估选股效果？

**A**:
```python
# 方法1: 回测评估
from src.backtest import BacktestEngine
result = engine.backtest_three_layer(selector, entry, exit, prices)
print(f"年化收益: {result['annual_return']:.2%}")

# 方法2: IC 分析
from src.features.factor_analyzer import FactorAnalyzer
analyzer = FactorAnalyzer()
ic = analyzer.calculate_ic(factors, returns)
print(f"平均IC: {ic.mean():.4f}")
```

---

## 📚 相关文档

- 📖 [三层架构概览](../../architecture/overview.md)
- 🔧 [技术栈详解](../../architecture/tech_stack.md)
- ⚡ [性能优化分析](../../architecture/performance.md)
- 🎨 [设计模式详解](../../architecture/design_patterns.md)

---

## 🎓 学习路径建议

### 第1天: 基础入门（2小时）
1. 运行 `ml_selector_usage_example.py`
2. 理解多因子加权原理
3. 尝试修改参数（top_n, features）

### 第2天: 进阶学习（3小时）
4. 运行 `ml_selector_multi_factor_weighted_example.py`
5. 学习因子分组策略
6. 对比不同归一化方法

### 第3天: 高级应用（4小时）
7. 运行 `ml3_lightgbm_ranker_example.py`
8. 训练自己的排序模型
9. 进行超参数调优

### 第4天: 特征工程（3小时）
10. 运行 `ml4_feature_integration_example.py`
11. 探索 125+ 因子库
12. 设计自己的特征组合

### 第5天: 实战项目（4小时）
13. 整合到完整回测流程
14. 对比不同策略效果
15. 优化性能和参数

---

**文档版本**: v3.0.0
**维护团队**: Quant Team
**最后更新**: 2026-02-06
**核心功能**: MLSelector 多因子加权 + LightGBM 排序 + 125+ 因子库
