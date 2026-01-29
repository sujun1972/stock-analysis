# 模型使用指南

## 📋 目录

- [简介](#简介)
- [快速开始](#快速开始)
- [基础模型](#基础模型)
- [模型集成](#模型集成)
- [模型管理](#模型管理)
- [高级功能](#高级功能)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

---

## 简介

Core 模块提供了完整的量化交易模型框架，包括：

- **3种基础模型**：Ridge、LightGBM、GRU
- **3种集成方法**：加权平均、投票法、Stacking
- **模型注册表**：版本管理、元数据追踪
- **自动调优**：超参数优化

### 模型性能对比

| 模型 | 训练速度 | 预测性能 | 可解释性 | 适用场景 |
|------|----------|----------|----------|----------|
| Ridge | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 基准模型、特征选择 |
| LightGBM | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 生产环境、复杂特征 |
| GRU | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | 时序数据、深度学习 |
| 集成模型 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 追求最优性能 |

---

## 快速开始

### 安装依赖

```bash
# 必需依赖
pip install pandas numpy scikit-learn lightgbm loguru

# 可选依赖（GRU模型）
pip install torch

# 可选依赖（贝叶斯优化）
pip install scikit-optimize
```

### 30秒快速上手

```python
from models import LightGBMStockModel
import pandas as pd
import numpy as np

# 1. 准备数据
X_train = pd.DataFrame(np.random.randn(1000, 30))
y_train = pd.Series(np.random.randn(1000))

# 2. 训练模型
model = LightGBMStockModel()
model.train(X_train, y_train)

# 3. 预测
X_test = pd.DataFrame(np.random.randn(100, 30))
predictions = model.predict(X_test)

print(f"预测结果: {predictions[:5]}")
```

---

## 基础模型

### 1. Ridge 回归模型

**特点**：简单快速、稳定可靠、适合做基准

```python
from models import RidgeStockModel

# 创建模型
model = RidgeStockModel(alpha=1.0)

# 训练
model.train(X_train, y_train)

# 预测
predictions = model.predict(X_test)

# 保存/加载
model.save('ridge_model.pkl')
loaded_model = RidgeStockModel.load('ridge_model.pkl')
```

**参数说明**：

- `alpha`: L2正则化系数（默认1.0）
  - 较大值：防止过拟合，模型更保守
  - 较小值：拟合更好，可能过拟合

**使用建议**：

- ✅ 适合：特征数量 > 样本数量
- ✅ 适合：需要快速训练和预测
- ✅ 适合：作为基准模型对比
- ❌ 不适合：特征间存在复杂非线性关系

---

### 2. LightGBM 模型

**特点**：性能优秀、训练快速、生产首选

```python
from models import LightGBMStockModel

# 创建模型
model = LightGBMStockModel(
    n_estimators=100,
    learning_rate=0.05,
    max_depth=5,
    num_leaves=31,
    min_child_samples=20,
    subsample=0.8,
    colsample_bytree=0.8
)

# 训练（带验证集和早停）
model.train(
    X_train, y_train,
    X_valid, y_valid,
    early_stopping_rounds=20,
    verbose_eval=10
)

# 预测
predictions = model.predict(X_test)

# 特征重要性
importance = model.get_feature_importance('gain', top_n=10)
print(importance)
```

**关键参数**：

| 参数 | 说明 | 推荐范围 |
|------|------|----------|
| `n_estimators` | 树的数量 | 100-500 |
| `learning_rate` | 学习率 | 0.01-0.1 |
| `num_leaves` | 叶子节点数 | 15-127 |
| `max_depth` | 最大深度 | 3-9 |
| `min_child_samples` | 叶子最小样本数 | 20-50 |
| `subsample` | 行采样比例 | 0.6-1.0 |
| `colsample_bytree` | 列采样比例 | 0.6-1.0 |

**调优建议**：

```python
# 防止过拟合
model = LightGBMStockModel(
    max_depth=3,              # 限制深度
    num_leaves=15,            # 减少叶子数
    min_child_samples=50,     # 增加最小样本数
    reg_alpha=0.1,            # L1正则化
    reg_lambda=0.1            # L2正则化
)

# 追求性能
model = LightGBMStockModel(
    n_estimators=500,
    learning_rate=0.01,       # 降低学习率
    num_leaves=127,           # 增加复杂度
    max_depth=-1              # 不限制深度
)
```

---

### 3. GRU 深度学习模型

**特点**：处理时序、捕获长期依赖

```python
from models import GRUStockModel

# 准备时序数据 (n_samples, sequence_length, n_features)
# 注意：需要重塑数据格式

# 创建模型
model = GRUStockModel(
    input_size=20,           # 特征数
    hidden_size=64,          # 隐藏层大小
    num_layers=2,            # GRU层数
    dropout=0.2,             # Dropout比例
    sequence_length=10       # 序列长度
)

# 训练
model.train(
    X_train, y_train,
    X_valid, y_valid,
    epochs=50,
    batch_size=32,
    learning_rate=0.001
)

# 预测
predictions = model.predict(X_test)
```

**使用场景**：

- ✅ 股票价格时序预测
- ✅ 长期趋势建模
- ✅ 数据量充足（>10,000样本）
- ❌ 简单截面数据（推荐用LightGBM）

---

## 模型集成

### 为什么使用集成？

- **提升性能**：通常提升 5-15% IC
- **降低方差**：减少单模型波动
- **模型互补**：融合不同模型优势

### 1. 加权平均集成

**最常用、最简单**

```python
from models import WeightedAverageEnsemble

# 训练基础模型
ridge = RidgeStockModel(alpha=1.0)
ridge.train(X_train, y_train)

lgb = LightGBMStockModel()
lgb.train(X_train, y_train, X_valid, y_valid)

# 方法1: 等权重
ensemble = WeightedAverageEnsemble([ridge, lgb])

# 方法2: 自定义权重
ensemble = WeightedAverageEnsemble(
    [ridge, lgb],
    weights=[0.3, 0.7]  # LightGBM权重更高
)

# 方法3: 自动优化权重（推荐！）
ensemble = WeightedAverageEnsemble([ridge, lgb])
ensemble.optimize_weights(X_valid, y_valid, metric='ic')

# 预测
predictions = ensemble.predict(X_test)
```

---

### 2. 投票法集成

**适合选股策略**

```python
from models import VotingEnsemble

# 创建投票集成
ensemble = VotingEnsemble(
    models=[ridge, lgb1, lgb2],
    voting_weights=[1.0, 1.5, 1.0]  # lgb1权重更高
)

# 方法1: 选择Top N股票
top_50_indices = ensemble.select_top_n(X_test, top_n=50)

# 方法2: 获取投票分数
scores = ensemble.predict(X_test)

# 方法3: 同时获取索引和分数
indices, scores = ensemble.select_top_n(
    X_test, top_n=50, return_scores=True
)
```

**应用：量化选股**

```python
# 每周选股示例
def weekly_stock_selection(X, ensemble, n_stocks=30):
    """使用投票法选股"""
    top_indices = ensemble.select_top_n(X, top_n=n_stocks)
    return top_indices

# 使用
selected_stocks = weekly_stock_selection(X_latest, ensemble)
print(f"本周选股: {selected_stocks}")
```

---

### 3. Stacking 集成

**性能最优，需要独立验证集**

```python
from models import StackingEnsemble, RidgeStockModel

# 数据分割（重要！）
# 60% 训练 | 20% 验证（训练元学习器） | 20% 测试
X_train, y_train = X[:600], y[:600]
X_valid, y_valid = X[600:800], y[600:800]
X_test, y_test = X[800:], y[800:]

# 训练基础模型（在训练集上）
base_models = [ridge, lgb1, lgb2]
for model in base_models:
    model.train(X_train, y_train)

# 创建Stacking
ensemble = StackingEnsemble(
    base_models=base_models,
    meta_learner=RidgeStockModel(alpha=0.5),
    use_original_features=True  # 结合原始特征
)

# 训练元学习器（在验证集上）
ensemble.train_meta_learner(X_train, y_train, X_valid, y_valid)

# 预测
predictions = ensemble.predict(X_test)
```

**关键要点**：

- ⚠️ 必须使用独立验证集训练元学习器
- ⚠️ 防止数据泄露
- ✅ 性能通常比加权平均高 1-3%

---

## 模型管理

### 模型注册表

**统一管理所有模型版本**

```python
from models import ModelRegistry

# 创建注册表
registry = ModelRegistry(base_dir='model_registry')

# 保存模型
registry.save_model(
    model=my_model,
    name='lightgbm_v1',
    metadata={
        'train_ic': 0.95,
        'test_ic': 0.92,
        'train_date': '2024-01-01'
    },
    model_type='lightgbm',
    description='生产环境模型'
)

# 加载最新版本
model, metadata = registry.load_model('lightgbm_v1')

# 加载指定版本
model, metadata = registry.load_model('lightgbm_v1', version=2)

# 查看模型历史
history = registry.get_model_history('lightgbm_v1')
print(history)

# 列出所有模型
models = registry.list_models()
print(models)

# 对比版本
comparison = registry.compare_versions('lightgbm_v1', 1, 2)
print(comparison)

# 导出模型
registry.export_model('lightgbm_v1', version=None, output_path='exports/')
```

**元数据追踪**：

```python
# 保存时自动记录
metadata = {
    'model_name': 'lightgbm_v1',
    'version': 1,
    'timestamp': '2024-01-15T10:30:00',
    'model_type': 'lightgbm',
    'feature_names': ['feature_0', 'feature_1', ...],
    'performance_metrics': {
        'train_ic': 0.95,
        'test_ic': 0.92
    },
    'training_config': {...}
}
```

---

## 高级功能

### 1. 自动超参数调优

```python
# LightGBM 自动调优
model = LightGBMStockModel()

best_model, results = model.auto_tune(
    X_train, y_train,
    X_valid, y_valid,
    metric='ic',
    method='grid',  # 'grid' 或 'random'
    n_trials=20
)

print(f"最佳参数: {results['best_params']}")
print(f"最佳IC: {results['best_score']:.6f}")

# 使用最佳模型预测
predictions = best_model.predict(X_test)
```

**自定义搜索空间**：

```python
param_grid = {
    'learning_rate': [0.01, 0.03, 0.05, 0.1],
    'num_leaves': [15, 31, 63],
    'max_depth': [3, 5, 7],
    'n_estimators': [100, 200, 300]
}

best_model, results = model.auto_tune(
    X_train, y_train, X_valid, y_valid,
    param_grid=param_grid,
    metric='ic'
)
```

---

### 2. 完整训练流水线

```python
from models import ModelRegistry, LightGBMStockModel, WeightedAverageEnsemble

class ProductionPipeline:
    """生产环境训练流水线"""

    def __init__(self):
        self.registry = ModelRegistry()

    def train_and_deploy(self, X_train, y_train, X_valid, y_valid):
        """训练并部署模型"""

        # 1. 训练多个模型
        models = {}

        # Ridge基准
        ridge = RidgeStockModel(alpha=1.0)
        ridge.train(X_train, y_train)
        models['ridge'] = ridge

        # LightGBM（自动调优）
        lgb = LightGBMStockModel()
        lgb_tuned, _ = lgb.auto_tune(
            X_train, y_train, X_valid, y_valid,
            metric='ic', n_trials=20
        )
        models['lightgbm'] = lgb_tuned

        # 2. 创建集成
        ensemble = WeightedAverageEnsemble(list(models.values()))
        ensemble.optimize_weights(X_valid, y_valid, metric='ic')

        # 3. 评估
        y_pred = ensemble.predict(X_valid)
        ic = np.corrcoef(y_pred, y_valid)[0, 1]

        # 4. 保存到注册表
        self.registry.save_model(
            model=ensemble,
            name='ensemble_prod',
            metadata={'valid_ic': ic},
            model_type='ensemble',
            description='生产集成模型'
        )

        return ensemble, ic

# 使用
pipeline = ProductionPipeline()
model, ic = pipeline.train_and_deploy(X_train, y_train, X_valid, y_valid)
```

---

## 最佳实践

### 1. 数据分割

```python
# 推荐分割比例
# 训练集: 60%
# 验证集: 20% (调参、早停)
# 测试集: 20% (最终评估)

n = len(X)
train_end = int(n * 0.6)
valid_end = int(n * 0.8)

X_train, y_train = X[:train_end], y[:train_end]
X_valid, y_valid = X[train_end:valid_end], y[train_end:valid_end]
X_test, y_test = X[valid_end:], y[valid_end:]
```

### 2. 模型选择流程

```
1. 从Ridge基准开始
   ↓
2. 尝试LightGBM（通常提升明显）
   ↓
3. 调优LightGBM参数
   ↓
4. 尝试集成（加权平均）
   ↓
5. 如果数据充足，尝试Stacking
```

### 3. 防止过拟合

```python
# 策略1: 使用正则化
model = LightGBMStockModel(
    reg_alpha=0.1,
    reg_lambda=0.1
)

# 策略2: 限制复杂度
model = LightGBMStockModel(
    max_depth=5,
    num_leaves=31,
    min_child_samples=20
)

# 策略3: 早停
model.train(
    X_train, y_train,
    X_valid, y_valid,
    early_stopping_rounds=20
)

# 策略4: 监控训练/验证集差异
if train_ic - valid_ic > 0.1:
    print("警告：可能过拟合！")
```

### 4. 性能评估

```python
# 多个指标综合评估
def evaluate_model(model, X_test, y_test):
    y_pred = model.predict(X_test)

    # IC (Information Coefficient)
    ic = np.corrcoef(y_pred, y_test)[0, 1]

    # Rank IC
    rank_ic = pd.Series(y_test.values).corr(
        pd.Series(y_pred), method='spearman'
    )

    # MSE
    mse = np.mean((y_test - y_pred) ** 2)

    # Top 20% 收益
    top_20_mask = y_pred >= np.quantile(y_pred, 0.8)
    top_20_return = y_test[top_20_mask].mean()

    return {
        'ic': ic,
        'rank_ic': rank_ic,
        'mse': mse,
        'top_20_return': top_20_return
    }
```

---

## 常见问题

### Q1: 如何选择模型？

**答**：按此顺序尝试：

1. **Ridge**：快速基准，了解数据
2. **LightGBM**：生产首选，性能优秀
3. **集成**：追求极致性能
4. **GRU**：仅用于时序数据

### Q2: 集成模型效果不好？

**可能原因**：

- 基础模型高度相关（预测相关性>0.95）
- 基础模型质量差
- 权重设置不合理

**解决方案**：

```python
# 检查模型相关性
pred1 = model1.predict(X_test)
pred2 = model2.predict(X_test)
corr = np.corrcoef(pred1, pred2)[0, 1]

if corr > 0.95:
    print("模型过于相似，集成收益有限")
else:
    print(f"模型相关性={corr:.2f}，适合集成")

# 使用自动权重优化
ensemble.optimize_weights(X_valid, y_valid, metric='ic')
```

### Q3: 训练时间太长？

**优化方法**：

```python
# 1. 减少特征数量
from sklearn.feature_selection import SelectKBest
selector = SelectKBest(k=50)
X_selected = selector.fit_transform(X, y)

# 2. 减少样本数量
X_sample = X.sample(frac=0.5)

# 3. 使用更快的参数
model = LightGBMStockModel(
    n_estimators=50,  # 减少树数量
    max_depth=3       # 限制深度
)

# 4. 并行训练（如果有多个模型）
from joblib import Parallel, delayed

models = Parallel(n_jobs=-1)(
    delayed(train_single_model)(params)
    for params in param_list
)
```

### Q4: 如何在生产环境使用？

**完整流程**：

```python
# 1. 训练阶段
registry = ModelRegistry()

# 训练并保存
model = LightGBMStockModel()
model.train(X_train, y_train, X_valid, y_valid)

ic = np.corrcoef(model.predict(X_test), y_test)[0, 1]

registry.save_model(
    model=model,
    name='prod_model',
    metadata={'test_ic': ic, 'date': '2024-01-15'},
    model_type='lightgbm'
)

# 2. 预测阶段（另一个脚本）
registry = ModelRegistry()
model, metadata = registry.load_model('prod_model')

# 验证元数据
print(f"模型版本: {metadata.version}")
print(f"训练日期: {metadata.timestamp}")
print(f"测试IC: {metadata.performance_metrics['test_ic']}")

# 预测
predictions = model.predict(X_new)
```

---

## 示例代码

完整示例位于 `core/examples/` 目录：

1. **[model_basic_usage.py](../examples/model_basic_usage.py)** - 基础模型使用
2. **[ensemble_example.py](../examples/ensemble_example.py)** - 集成模型示例
3. **[model_training_pipeline.py](../examples/model_training_pipeline.py)** - 完整训练流程
4. **[model_comparison_demo.py](../examples/model_comparison_demo.py)** - 模型对比

运行示例：

```bash
cd core/examples
python model_basic_usage.py
python ensemble_example.py
python model_training_pipeline.py
python model_comparison_demo.py
```

---

## 参考资料

- **集成学习指南**: [ENSEMBLE_GUIDE.md](ENSEMBLE_GUIDE.md)
- **因子分析指南**: [FACTOR_ANALYSIS_GUIDE.md](FACTOR_ANALYSIS_GUIDE.md)
- **开发路线图**: [DEVELOPMENT_ROADMAP.md](../DEVELOPMENT_ROADMAP.md)

---

**版本**: v1.0
**更新日期**: 2026-01-29
**贡献者**: Claude Code
