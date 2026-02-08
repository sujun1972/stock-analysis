# ML系统使用指南

**文档版本**: v1.0.0
**最后更新**: 2026-02-08
**适用对象**: 新用户、量化策略开发者

---

## 📋 目录

- [快速开始](#快速开始)
- [场景1: 训练第一个ML模型](#场景1-训练第一个ml模型)
- [场景2: 运行ML策略回测](#场景2-运行ml策略回测)
- [场景3: 使用MLStockRanker筛选股票](#场景3-使用mlstockranker筛选股票)
- [常见问题](#常见问题)
- [最佳实践](#最佳实践)
- [进阶主题](#进阶主题)

---

## 快速开始

### 系统要求

```bash
# Python 版本
Python >= 3.8

# 核心依赖
pip install pandas numpy scikit-learn lightgbm joblib
```

### 目录结构

```
core/
├── src/ml/                     # ML核心模块
│   ├── feature_engine.py       # 特征工程引擎
│   ├── label_generator.py      # 标签生成器
│   ├── trained_model.py        # 训练好的模型
│   ├── ml_entry.py            # ML入场策略
│   └── ml_stock_ranker.py     # 股票评分工具
├── examples/                   # 示例代码
│   ├── feature_engine_demo.py
│   ├── ml_entry_demo.py
│   ├── ml_stock_ranker_demo.py
│   └── backtest_ml_strategy.py
└── docs/ml/                    # 文档
    ├── README.md              # 系统总览
    ├── mlstockranker.md       # MLStockRanker详解
    ├── evaluation-metrics.md  # 评估指标详解
    └── user-guide.md          # 本文档
```

### 10分钟快速体验

```bash
# 1. 进入core目录
cd /Volumes/MacDriver/stock-analysis/core

# 2. 运行ML策略回测示例
python examples/backtest_ml_strategy.py

# 3. 查看输出结果
# - 模型训练过程
# - 回测绩效指标
# - 净值曲线图
```

---

## 场景1: 训练第一个ML模型

### 步骤 1: 准备数据

```python
from core.src.data import DataManager

# 初始化数据管理器
data_manager = DataManager()

# 定义股票池 (建议50-300只股票)
stock_pool = [
    '600000.SH', '600036.SH', '600519.SH',  # 上证
    '000001.SZ', '000002.SZ', '000858.SZ',  # 深证
    # ... 更多股票
]

# 加载历史数据 (建议至少3年数据)
market_data = data_manager.load_data(
    stock_codes=stock_pool,
    start_date='2019-01-01',  # 留出lookback window
    end_date='2023-12-31',
    fields=['open', 'high', 'low', 'close', 'volume']
)

print(f"✅ 数据加载完成: {len(market_data)} 条记录")
print(f"   股票数量: {len(stock_pool)}")
print(f"   日期范围: 2019-01-01 ~ 2023-12-31")
```

### 步骤 2: 配置训练参数

```python
from core.src.ml import TrainingConfig
from core.src.models import ModelTrainerConfig

# 模型配置
model_config = TrainingConfig(
    model_type='lightgbm',           # 模型类型
    train_start_date='2020-01-01',   # 训练开始日期
    train_end_date='2023-12-31',     # 训练结束日期
    validation_split=0.2,            # 验证集比例
    forward_window=5,                # 预测未来5天收益率
    feature_groups=['alpha', 'technical'],  # 使用Alpha因子+技术指标
    hyperparameters={
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'max_depth': 6,
        'min_data_in_leaf': 20
    }
)

# 训练器配置
trainer_config = ModelTrainerConfig(
    output_dir='models/',
    early_stopping=True,
    verbose=1
)
```

### 步骤 3: 训练模型

```python
from core.src.models import ModelTrainer

# 创建训练器
trainer = ModelTrainer(model_config, trainer_config)

# 训练模型
print("\n🚀 开始训练模型...")
trained_model = trainer.train(stock_pool, market_data)

# 查看评估结果
print("\n📊 模型评估结果:")
print(f"  RMSE:     {trained_model.metrics['rmse']:.4f}")
print(f"  R²:       {trained_model.metrics['r2']:.4f}")
print(f"  IC:       {trained_model.metrics['ic']:.4f}")
print(f"  Rank IC:  {trained_model.metrics['rank_ic']:.4f}")

# 判断模型质量
if trained_model.metrics['ic'] > 0.05:
    print("\n✅ 模型有预测能力 (IC > 0.05)")
else:
    print("\n⚠️  模型预测能力较弱 (IC < 0.05)")
```

### 步骤 4: 保存模型

```python
import os

# 创建模型目录
os.makedirs('models', exist_ok=True)

# 保存模型
model_path = 'models/ml_entry_model.pkl'
trained_model.save(model_path)

print(f"\n✅ 模型已保存: {model_path}")
print(f"   模型类型: {trained_model.config.model_type}")
print(f"   IC: {trained_model.metrics['ic']:.4f}")
print(f"   Rank IC: {trained_model.metrics['rank_ic']:.4f}")
```

### 步骤 5: 加载和验证模型

```python
from core.src.ml import TrainedModel

# 加载模型
loaded_model = TrainedModel.load(model_path)

# 验证模型
test_date = '2024-01-15'
test_stocks = stock_pool[:10]

predictions = loaded_model.predict(
    stock_codes=test_stocks,
    market_data=market_data,
    date=test_date
)

print(f"\n🔮 预测结果 ({test_date}):")
print(predictions.head())

# 输出:
#             expected_return  volatility  confidence
# 600000.SH          0.0250       0.018       0.85
# 600036.SH          0.0180       0.022       0.78
# 600519.SH          0.0320       0.025       0.92
```

---

## 场景2: 运行ML策略回测

### 步骤 1: 创建ML策略

```python
from core.src.ml import MLEntry

# 加载训练好的模型
ml_strategy = MLEntry(
    model_path='models/ml_entry_model.pkl',
    confidence_threshold=0.7,  # 置信度阈值
    top_long=20,               # 做多数量
    top_short=0,               # 做空数量
    enable_short=False         # 是否启用做空
)

print("✅ ML策略已创建")
print(f"   模型路径: models/ml_entry_model.pkl")
print(f"   置信度阈值: 0.7")
print(f"   做多数量: 20")
```

### 步骤 2: 准备回测数据

```python
from core.src.data import DataManager

# 加载回测期数据
data_manager = DataManager()
backtest_data = data_manager.load_data(
    stock_codes=stock_pool,
    start_date='2023-06-01',  # 预留lookback
    end_date='2024-01-31'
)

print(f"✅ 回测数据加载完成")
print(f"   回测期: 2023-07-01 ~ 2024-01-31")
```

### 步骤 3: 运行回测

```python
from core.src.backtest import BacktestEngine

# 创建回测引擎
backtest_engine = BacktestEngine(
    initial_capital=1000000,      # 初始资金100万
    commission_rate=0.0003,       # 佣金率0.03%
    slippage_rate=0.0001          # 滑点率0.01%
)

# 运行回测
print("\n🚀 开始回测...")
result = backtest_engine.backtest_ml_strategy(
    ml_strategy=ml_strategy,
    stock_pool=stock_pool,
    market_data=backtest_data,
    start_date='2023-07-01',
    end_date='2024-01-31',
    rebalance_frequency='W'  # 每周调仓
)

print("✅ 回测完成")
```

### 步骤 4: 分析结果

```python
# 打印绩效指标
print("\n📈 回测绩效:")
print(f"  总收益率:     {result['total_return']:.2%}")
print(f"  年化收益率:   {result['annual_return']:.2%}")
print(f"  夏普比率:     {result['sharpe_ratio']:.2f}")
print(f"  最大回撤:     {result['max_drawdown']:.2%}")
print(f"  波动率:       {result['volatility']:.2%}")

# 判断策略质量
if result['sharpe_ratio'] > 1.0:
    print("\n✅ 策略表现优秀 (夏普比率 > 1.0)")
else:
    print("\n⚠️  策略需要优化 (夏普比率 < 1.0)")

if result['max_drawdown'] > -0.15:
    print("✅ 风险可控 (最大回撤 > -15%)")
else:
    print("⚠️  回撤较大 (最大回撤 < -15%)")

# 可视化净值曲线
if 'equity_curve' in result:
    import matplotlib.pyplot as plt

    equity_curve = result['equity_curve']

    plt.figure(figsize=(12, 6))
    plt.plot(equity_curve.index, equity_curve.values, linewidth=2)
    plt.title('ML策略净值曲线', fontsize=14)
    plt.xlabel('日期')
    plt.ylabel('净值')
    plt.grid(True, alpha=0.3)
    plt.savefig('ml_strategy_equity_curve.png', dpi=150)
    print("\n✅ 净值曲线已保存: ml_strategy_equity_curve.png")
```

---

## 场景3: 使用MLStockRanker筛选股票

### 步骤 1: 创建MLStockRanker

```python
from core.src.ml import MLStockRanker

# 创建评分工具
ranker = MLStockRanker(
    model_path='models/ranker_model.pkl',
    scoring_method='sharpe',     # 评分方法: simple/sharpe/risk_adjusted
    min_confidence=0.6,          # 最小置信度
    min_expected_return=0.01     # 最小预期收益1%
)

print("✅ MLStockRanker 已创建")
print(f"   评分方法: sharpe")
print(f"   最小置信度: 0.6")
```

### 步骤 2: 评分排名

```python
# 准备全市场股票池
all_stocks = [
    # A股所有股票代码...
    '600000.SH', '600036.SH', '600519.SH',
    '000001.SZ', '000002.SZ', '000858.SZ',
    # ... 3000+ 只股票
]

# 评分排名
rankings = ranker.rank(
    stock_pool=all_stocks,
    market_data=market_data,
    date='2024-01-01',
    return_top_n=100,   # 返回Top 100
    ascending=False     # 降序排列
)

print(f"\n✅ 评分完成: {len(rankings)} 只股票")
print("\n📊 Top 10 高潜力股票:")
for i, (stock, score) in enumerate(list(rankings.items())[:10], 1):
    print(f"  {i:2d}. {stock}: {score:.4f}")
```

### 步骤 3: 查看详细信息

```python
# 获取详细评分信息 (DataFrame格式)
result_df = ranker.rank_dataframe(
    stock_pool=all_stocks,
    market_data=market_data,
    date='2024-01-01',
    return_top_n=100
)

print("\n📋 详细评分信息:")
print(result_df.head(20))

# 分析评分分布
print(f"\n📊 评分统计:")
print(f"  平均评分:     {result_df['score'].mean():.4f}")
print(f"  最高评分:     {result_df['score'].max():.4f}")
print(f"  最低评分:     {result_df['score'].min():.4f}")
print(f"  标准差:       {result_df['score'].std():.4f}")
```

### 步骤 4: 应用到回测

```python
# 提取Top 100股票池
selected_pool = list(rankings.keys())

# 在筛选后的股票池上运行ML策略
ml_strategy = MLEntry(model_path='models/ml_entry_model.pkl')

result = backtest_engine.backtest_ml_strategy(
    ml_strategy=ml_strategy,
    stock_pool=selected_pool,  # 使用筛选后的股票池
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31',
    rebalance_frequency='W'
)

print(f"\n📈 筛选后回测结果:")
print(f"  总收益率: {result['total_return']:.2%}")
print(f"  夏普比率: {result['sharpe_ratio']:.2f}")
```

---

## 常见问题

### Q1: 训练模型需要多少数据?

**建议**:
- **最少**: 2年历史数据 (500个交易日)
- **推荐**: 3-5年历史数据
- **股票数量**: 50-300只股票

**原因**:
- 需要足够的样本来学习市场规律
- 太少: 过拟合
- 太多: 训练时间长,可能包含过时的规律

### Q2: 如何选择 forward_window?

| forward_window | 适用场景 | 说明 |
|----------------|---------|------|
| 1-3天 | 日内/短线交易 | 预测短期波动 |
| 5-10天 | 中短线交易 | **推荐** |
| 20-30天 | 中长线交易 | 用于MLStockRanker |

**推荐**: 5天 (一周)

### Q3: IC多少算好?

| IC值 | 评价 | 说明 |
|------|------|------|
| < 0.02 | 差 | 基本无预测能力 |
| 0.02-0.05 | 一般 | 有一定预测能力 |
| 0.05-0.10 | 良好 | 有较强预测能力 |
| > 0.10 | 优秀 | 预测能力很强 |

**注意**: 量化领域 IC > 0.05 就算不错了！

### Q4: 夏普比率多少算好?

| 夏普比率 | 评价 | 说明 |
|---------|------|------|
| < 0.5 | 差 | 风险调整后收益差 |
| 0.5-1.0 | 一般 | 可以接受 |
| 1.0-2.0 | 良好 | **优秀策略** |
| > 2.0 | 优秀 | 极其优秀 |

**目标**: 夏普比率 > 1.0

### Q5: 模型多久需要重训练?

**推荐频率**:
- **MLEntry**: 每季度 (3个月)
- **MLStockRanker**: 每半年

**触发条件**:
- IC下降超过20%
- 策略夏普比率下降明显
- 市场环境发生重大变化

### Q6: 特征太多会过拟合吗?

**是的！** 特征选择建议:

```python
# 方案1: 分组选择
config = TrainingConfig(
    feature_groups=['alpha', 'technical'],  # 不使用全部特征
    ...
)

# 方案2: 使用LightGBM的特征选择
hyperparameters = {
    'feature_fraction': 0.8,  # 每次训练只使用80%的特征
    'lambda_l1': 0.1,         # L1正则化
    'lambda_l2': 0.1          # L2正则化
}
```

---

## 最佳实践

### 1. 数据质量检查

```python
# 检查缺失值
missing_count = market_data.isnull().sum().sum()
print(f"缺失值: {missing_count}")

# 检查数据范围
print("\n数据范围:")
print(f"  日期: {market_data['date'].min()} ~ {market_data['date'].max()}")
print(f"  股票数量: {market_data['stock_code'].nunique()}")
print(f"  总记录数: {len(market_data)}")

# 检查异常值
print("\n价格统计:")
print(market_data[['open', 'high', 'low', 'close']].describe())
```

### 2. 模型训练流程

```
1. 准备数据 (3-5年)
    ↓
2. 配置参数 (forward_window=5)
    ↓
3. 训练模型
    ↓
4. 评估模型 (IC > 0.05?)
    ├─ Yes → 保存模型 → 回测验证
    └─ No  → 调整参数 → 重新训练
```

### 3. 回测验证流程

```
1. 加载模型
    ↓
2. 准备回测数据 (Out-of-Sample)
    ↓
3. 运行回测
    ↓
4. 评估策略 (夏普比率 > 1.0?)
    ├─ Yes → 可以实盘
    └─ No  → 优化策略参数
```

### 4. 参数调优顺序

```python
# 1. 先调整模型参数
hyperparameters = {
    'num_leaves': [15, 31, 63],     # 树的复杂度
    'learning_rate': [0.01, 0.05, 0.1],  # 学习率
    'max_depth': [4, 6, 8]          # 最大深度
}

# 2. 再调整特征组合
feature_groups_list = [
    ['alpha', 'technical'],
    ['technical', 'volume'],
    ['all']
]

# 3. 最后调整策略参数
confidence_thresholds = [0.6, 0.7, 0.8]
top_long_values = [10, 20, 30]
```

---

## 进阶主题

### 1. 多模型集成

```python
from core.src.models import EnsembleModel

# 训练多个模型
models = []
for model_type in ['lightgbm', 'xgboost', 'ridge']:
    config = TrainingConfig(model_type=model_type, ...)
    trainer = ModelTrainer(config)
    model = trainer.train(stock_pool, market_data)
    models.append(model)

# 创建集成模型
ensemble = EnsembleModel(models=models, method='average')
ensemble.save('models/ensemble_model.pkl')
```

### 2. 特征重要性分析

```python
# LightGBM特征重要性
import lightgbm as lgb

# 获取特征重要性
importance_df = pd.DataFrame({
    'feature': feature_names,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\n📊 Top 20 重要特征:")
print(importance_df.head(20))

# 可视化
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 8))
plt.barh(importance_df['feature'][:20], importance_df['importance'][:20])
plt.xlabel('Importance')
plt.title('Feature Importance Top 20')
plt.tight_layout()
plt.savefig('feature_importance.png')
```

### 3. 自定义评分方法

```python
from core.src.ml import MLStockRanker

class CustomMLStockRanker(MLStockRanker):
    """自定义评分方法"""

    def _calculate_scores(self, predictions: pd.DataFrame) -> pd.Series:
        """
        自定义评分公式

        示例: 考虑动量因子
        score = (expected_return / volatility) × confidence × momentum
        """
        base_score = super()._calculate_scores(predictions)

        # 添加动量加权
        momentum = self._calculate_momentum(predictions)
        final_score = base_score * (1 + momentum * 0.5)

        return final_score

    def _calculate_momentum(self, predictions: pd.DataFrame) -> pd.Series:
        # 自定义动量计算逻辑
        pass
```

### 4. 滚动回测

```python
from datetime import datetime, timedelta

def rolling_backtest(
    ml_strategy,
    stock_pool,
    market_data,
    start_date,
    end_date,
    window_days=90  # 90天滚动窗口
):
    """滚动回测"""
    results = []

    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    while current_date < end:
        # 回测窗口
        window_start = current_date.strftime('%Y-%m-%d')
        window_end = (current_date + timedelta(days=window_days)).strftime('%Y-%m-%d')

        # 运行回测
        result = backtest_engine.backtest_ml_strategy(
            ml_strategy=ml_strategy,
            stock_pool=stock_pool,
            market_data=market_data,
            start_date=window_start,
            end_date=window_end
        )

        results.append({
            'period': f"{window_start}~{window_end}",
            'return': result['total_return'],
            'sharpe': result['sharpe_ratio'],
            'max_drawdown': result['max_drawdown']
        })

        # 移动到下一个窗口
        current_date += timedelta(days=30)  # 每月滚动

    return pd.DataFrame(results)

# 运行滚动回测
rolling_results = rolling_backtest(
    ml_strategy=ml_strategy,
    stock_pool=stock_pool,
    market_data=market_data,
    start_date='2023-01-01',
    end_date='2024-12-31'
)

print("\n📊 滚动回测结果:")
print(rolling_results)
print(f"\n平均收益率: {rolling_results['return'].mean():.2%}")
print(f"平均夏普比率: {rolling_results['sharpe'].mean():.2f}")
```

---

## 相关文档

**📖 核心文档**:
- [ML系统完整指南](./README.md) - ⭐ 系统架构和组件详解
- [MLStockRanker 完整指南](./mlstockranker.md) - 股票评分工具
- [评估指标详解](./evaluation-metrics.md) - IC/夏普比率等指标

**💻 示例代码**:
- [examples/](../../examples/) - 所有示例代码
- [tests/integration/](../../tests/integration/) - 集成测试

**🔧 技术文档**:
- [架构详解](../architecture/overview.md)
- [ML系统重构方案](../planning/ml_system_refactoring_plan.md)

---

## 获取帮助

**问题反馈**:
1. 查看 [常见问题](#常见问题)
2. 阅读 [最佳实践](#最佳实践)
3. 参考 [示例代码](../../examples/)
4. 提交 Issue

**快速链接**:
- 示例代码: [examples/](../../examples/)
- 测试代码: [tests/](../../tests/)
- API文档: [src/ml/](../../src/ml/)

---

**文档版本**: v1.0.0
**最后更新**: 2026-02-08
**维护者**: Core ML Team
