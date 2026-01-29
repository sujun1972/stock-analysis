# 因子分析和参数优化完整指南

## 📋 概述

本指南介绍core量化系统新增的两个关键模块：

### 第一部分：因子有效性分析工具
- IC分析（信息系数）
- 分层回测（按因子值分组测试）
- 因子相关性分析和热力图
- 因子组合优化

### 第二部分：参数优化模块
- 网格搜索优化器
- 贝叶斯优化器（使用scikit-optimize）
- Walk-Forward验证框架

---

## 🚀 快速开始

### 安装依赖

```bash
cd core
source ../stock_env/bin/activate  # 激活虚拟环境
pip install scipy  # 因子分析需要
pip install seaborn networkx  # 相关性可视化需要
pip install scikit-optimize  # 贝叶斯优化需要（可选）
```

### 运行示例

```bash
python examples/complete_factor_analysis_example.py
```

---

## 📊 第一部分：因子有效性分析

### 1. IC分析（Information Coefficient）

**用途**：评估因子的预测能力

**示例**：

```python
from analysis import ICCalculator

# 创建IC计算器
ic_calc = ICCalculator(
    forward_periods=5,  # 前瞻期5天
    method='spearman'   # 使用秩相关（更稳健）
)

# 计算IC统计
ic_result = ic_calc.calculate_ic_stats(factor_df, prices_df)

print(f"IC均值: {ic_result.mean_ic:.4f}")
print(f"ICIR: {ic_result.ic_ir:.4f}")
print(f"IC正值率: {ic_result.positive_rate:.2%}")

# 绘制IC时间序列
ic_calc.plot_ic_series(ic_result, title="因子IC分析")
```

**判断标准**：
- |IC| > 0.03：有效因子
- ICIR > 0.5：稳定的有效因子
- IC正值率 > 55%：有方向性

**高级功能**：

```python
# 批量计算多个因子的IC
ic_summary = ic_calc.calculate_multi_factor_ic(factor_dict, prices_df)

# IC衰减分析（不同持有期）
decay_df = ic_calc.analyze_ic_decay(factor_df, prices_df, max_period=20)

# 滚动IC（评估因子稳定性）
rolling_ic = ic_calc.calculate_rolling_ic(factor_df, prices_df, window=60)
```

---

### 2. 分层回测

**用途**：测试因子的单调性（是否分层越高收益越高）

**示例**：

```python
from analysis import LayeringTest

# 创建分层测试工具
layering_test = LayeringTest(
    n_layers=5,         # 分为5层
    holding_period=5,    # 持有期5天
    long_short=True      # 计算多空组合收益
)

# 执行分层测试
result_df = layering_test.perform_layering_test(factor_df, prices_df)

print(result_df)

# 分析单调性
monotonicity = layering_test.analyze_monotonicity(result_df)
print(f"是否单调: {monotonicity['是否单调']}")
print(f"收益差距: {monotonicity['收益差距']:.4f}")

# 绘制分层结果
layering_test.plot_layering_result(result_df)
```

**高级功能**：

```python
# 完整净值回测
equity_curves = layering_test.backtest_layers(
    factor_df,
    prices_df,
    initial_capital=1_000_000
)

# 查看各层净值曲线
for layer_name, curve in equity_curves.items():
    print(f"{layer_name}: {curve.iloc[-1]:,.2f}")
```

---

### 3. 因子相关性分析

**用途**：识别高度相关的因子，避免重复

**示例**：

```python
from analysis import FactorCorrelation

# 创建相关性分析工具
corr_analyzer = FactorCorrelation(method='spearman')

# 计算相关性矩阵
corr_matrix = corr_analyzer.calculate_factor_correlation(
    factor_dict,
    aggregate_method='concat'  # 或'mean'
)

# 找出高相关性因子对
high_corr_pairs = corr_analyzer.find_high_correlation_pairs(
    corr_matrix,
    threshold=0.7
)

# 选择低相关性因子
selected_factors = corr_analyzer.select_low_correlation_factors(
    corr_matrix,
    max_corr=0.7,
    ic_scores=ic_scores  # 基于IC优先选择
)

# 绘制热力图
corr_analyzer.plot_correlation_heatmap(corr_matrix)

# 绘制网络图
corr_analyzer.plot_correlation_network(corr_matrix, threshold=0.5)
```

**高级功能**：

```python
# 因子聚类
clusters = corr_analyzer.cluster_factors(corr_matrix, n_clusters=5)

for cluster_id, factors in clusters.items():
    print(f"簇{cluster_id}: {factors}")
```

---

### 4. 因子组合优化

**用途**：优化多因子的权重组合

**示例**：

```python
from analysis import FactorOptimizer

optimizer = FactorOptimizer()

# 方法1：等权重
equal_w = optimizer.equal_weight(factor_names)

# 方法2：IC加权
ic_w = optimizer.ic_weight(ic_stats)

# 方法3：ICIR加权（推荐）
icir_w = optimizer.ic_ir_weight(ic_stats)

# 方法4：优化最大化ICIR
opt_result = optimizer.optimize_max_icir(
    ic_series_dict,
    method='SLSQP',
    max_weight=0.5  # 单因子最大权重限制
)

print(f"最优权重:\n{opt_result.weights}")
print(f"组合ICIR: {opt_result.ic_ir:.4f}")

# 组合因子
combined_factor = optimizer.combine_factors(
    factor_dict,
    opt_result.weights,
    normalize=True
)
```

**高级功能**：

```python
# 最小相关性优化
opt_result = optimizer.optimize_min_correlation(
    ic_series_dict,
    corr_matrix,
    max_avg_corr=0.3  # 最大平均相关性
)
```

---

## ⚙️ 第二部分：参数优化

### 1. 网格搜索

**用途**：遍历所有参数组合（适合参数空间小的情况）

**示例**：

```python
from optimization import GridSearchOptimizer

# 创建优化器
grid_optimizer = GridSearchOptimizer(
    metric='sharpe_ratio',
    n_jobs=4,  # 并行任务数
    verbose=True
)

# 定义参数网格
param_grid = {
    'lookback': [10, 20, 30, 40],
    'top_n': [30, 50, 70, 100]
}

# 定义目标函数
def backtest_strategy(params):
    strategy = MomentumStrategy('MOM', params)
    result = strategy.backtest(engine, prices_df)
    return result['sharpe_ratio']

# 执行搜索
result = grid_optimizer.search(backtest_strategy, param_grid)

print(f"最优参数: {result.best_params}")
print(f"最优得分: {result.best_score:.4f}")

# 参数重要性分析
importance = grid_optimizer.analyze_param_importance(result)
print(importance)

# 绘制参数敏感性
grid_optimizer.plot_param_sensitivity(result, 'lookback')
```

---

### 2. 贝叶斯优化

**用途**：智能搜索参数空间（适合计算昂贵的目标函数）

**示例**：

```python
from optimization import BayesianOptimizer

# 创建优化器
bayesian_optimizer = BayesianOptimizer(
    n_calls=50,           # 总迭代次数
    n_initial_points=10,   # 随机初始化点数
    acq_func='EI'          # 采集函数（期望改进）
)

# 定义参数空间
param_space = {
    'lookback': (5, 50),      # 整数范围
    'threshold': (0.0, 1.0),  # 浮点数范围
    'method': ['pearson', 'spearman']  # 类别选择
}

# 执行优化
result = bayesian_optimizer.optimize(
    backtest_strategy,
    param_space,
    maximize=True
)

print(f"最优参数: {result.best_params}")
print(f"迭代次数: {result.n_iterations}")

# 绘制收敛曲线
bayesian_optimizer.plot_convergence(result)
```

**优势**：
- 比网格搜索快5-10倍
- 自动聚焦到最优区域
- 适合昂贵的回测函数

---

### 3. Walk-Forward验证

**用途**：防止参数过拟合的滚动验证

**示例**：

```python
from optimization import WalkForwardValidator

# 创建验证器
validator = WalkForwardValidator(
    train_period=252,  # 训练期1年
    test_period=63,    # 测试期1季度
    step_size=63       # 滚动步长
)

# 准备数据
data = {
    'prices': prices_df,
    'features': features_df
}

# 执行验证
results_df = validator.validate(
    objective_func=backtest_strategy,
    optimizer=grid_optimizer,  # 或 bayesian_optimizer
    data=data,
    dates=prices_df.index.tolist()
)

# 查看结果
print(results_df[['窗口', '训练得分', '测试得分', '过拟合度']])

# 绘制验证结果
validator.plot_validation_results(results_df)
```

**验证指标**：
- 平均过拟合度 < 0.1：参数稳定
- 测试得分标准差：参数鲁棒性
- 过拟合窗口数：参数可靠性

---

## 🎯 完整工作流示例

### 多因子策略开发流程

```python
from analysis import *
from optimization import *

# 步骤1：计算因子
from features.alpha_factors import AlphaFactors

af = AlphaFactors(price_df)
af.add_all_alpha_factors()
factor_df = af.get_dataframe()

# 步骤2：IC分析筛选因子
ic_calc = ICCalculator(forward_periods=5, method='spearman')
ic_summary = ic_calc.calculate_multi_factor_ic(factor_dict, prices_df)

# 选出ICIR > 0.3的因子
good_factors = ic_summary[ic_summary['ICIR'] > 0.3].index.tolist()

# 步骤3：相关性分析去重
corr_analyzer = FactorCorrelation()
corr_matrix = corr_analyzer.calculate_factor_correlation(good_factor_dict)

selected_factors = corr_analyzer.select_low_correlation_factors(
    corr_matrix,
    max_corr=0.7,
    ic_scores=ic_summary['IC均值'].abs()
)

# 步骤4：优化因子权重
optimizer = FactorOptimizer()
opt_result = optimizer.optimize_max_icir(selected_ic_series_dict)

combined_factor = optimizer.combine_factors(
    selected_factor_dict,
    opt_result.weights
)

# 步骤5：策略参数优化
from strategies import MultiFactorStrategy

def backtest_multi_factor(params):
    strategy = MultiFactorStrategy('MF', params)
    result = strategy.backtest(engine, prices_df, features=combined_factor)
    return result['sharpe_ratio']

# 网格搜索
grid_optimizer = GridSearchOptimizer()
param_grid = {'top_n': [30, 50, 70], 'holding_period': [5, 10, 20]}

grid_result = grid_optimizer.search(backtest_multi_factor, param_grid)

# 步骤6：Walk-Forward验证
validator = WalkForwardValidator(train_period=252, test_period=63)

wf_results = validator.validate(
    objective_func=backtest_multi_factor,
    optimizer=grid_optimizer,
    data={'prices': prices_df, 'features': combined_factor},
    dates=dates
)

# 步骤7：查看最终结果
print("\n最终多因子策略：")
print(f"因子组合: {selected_factors}")
print(f"因子权重: {opt_result.weights}")
print(f"策略参数: {grid_result.best_params}")
print(f"平均测试得分: {wf_results['测试得分'].mean():.4f}")
print(f"参数稳定性: {wf_results['过拟合度'].std():.4f}")
```

---

## 📈 性能优化建议

### 因子分析加速

1. **并行计算多因子IC**
```python
# 使用Task工具并行计算
from joblib import Parallel, delayed

ic_results = Parallel(n_jobs=-1)(
    delayed(ic_calc.calculate_ic_stats)(factor_df, prices_df)
    for factor_df in factor_dict.values()
)
```

2. **缓存IC序列**
```python
# 避免重复计算IC
ic_cache = {}
for name, factor_df in factor_dict.items():
    if name not in ic_cache:
        ic_cache[name] = ic_calc.calculate_ic_series(factor_df, prices_df)
```

### 参数优化加速

1. **使用贝叶斯优化代替网格搜索**
```python
# 50次贝叶斯优化 vs 1000次网格搜索
bayesian_optimizer = BayesianOptimizer(n_calls=50)
```

2. **并行网格搜索**
```python
grid_optimizer = GridSearchOptimizer(n_jobs=-1)  # 使用所有CPU
```

3. **减少Walk-Forward窗口数**
```python
validator = WalkForwardValidator(
    train_period=120,
    test_period=30,
    step_size=60  # 增大步长，减少窗口数
)
```

---

## 🐛 常见问题

### 1. IC值很小怎么办？

**可能原因**：
- 因子确实无效
- 前瞻期设置不当
- 数据质量问题

**解决方案**：
```python
# 尝试不同前瞻期
for period in [1, 3, 5, 10, 20]:
    ic_calc = ICCalculator(forward_periods=period)
    ic_result = ic_calc.calculate_ic_stats(factor_df, prices_df)
    print(f"前瞻期{period}天: IC={ic_result.mean_ic:.4f}")
```

### 2. 分层测试不单调？

**可能原因**：
- 因子噪声大
- 分层数太多
- 持有期不合适

**解决方案**：
```python
# 减少分层数，增加每层股票数
layering_test = LayeringTest(n_layers=3, holding_period=10)
```

### 3. Walk-Forward验证失败？

**可能原因**：
- 训练集太小
- 参数过拟合
- 数据不足

**解决方案**：
```python
validator = WalkForwardValidator(
    min_train_size=60,  # 降低最小训练集要求
    train_period=180    # 增大训练窗口
)
```

---

## 📚 参考文献

1. **IC分析**
   - Grinold & Kahn, "Active Portfolio Management"

2. **因子组合**
   - Meucci, "Risk and Asset Allocation"

3. **参数优化**
   - Bergstra et al., "Algorithms for Hyper-Parameter Optimization"

4. **Walk-Forward验证**
   - Pardo, "The Evaluation and Optimization of Trading Strategies"

---

## 💡 最佳实践

1. **因子开发**：
   - 先用IC快速筛选
   - 再用分层测试验证
   - 最后组合优化

2. **参数优化**：
   - 粗搜索用网格
   - 精搜索用贝叶斯
   - 验证用Walk-Forward

3. **避免过拟合**：
   - 限制参数数量 < 5个
   - Walk-Forward窗口 >= 10个
   - 过拟合度 < 10%

---

**完成日期**：2026-01-29
**作者**：Claude (Anthropic)
**版本**：v1.0
