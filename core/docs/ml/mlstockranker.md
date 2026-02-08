# MLStockRanker 完整指南

**文档版本**: v5.1.0
**最后更新**: 2026-02-08

---

## 📋 目录

- [什么是 MLStockRanker](#什么是-mlstockranker)
- [核心概念](#核心概念)
- [实现细节](#实现细节)
- [使用指南](#使用指南)
- [训练 MLStockRanker 模型](#训练-mlstockranker-模型)
- [性能优化](#性能优化)
- [常见问题](#常见问题)

---

## 什么是 MLStockRanker

### 定位

**MLStockRanker** 是一个**股票评分和排名工具**，类似于 BigQuant 的 StockRanker。

```
┌────────────────────────────────────────────┐
│         MLStockRanker 的作用                │
└────────────────────────────────────────────┘

输入: 大量候选股票 (例如 3000 只 A 股)
  ↓
MLStockRanker 评分
  ↓
输出: 评分 + 排名 (例如 Top 100 高潜力股票)
```

### 核心概念澄清

```
❌ 错误理解: MLStockRanker 是"选股器"
✅ 正确理解: MLStockRanker 是"预测器"

MLStockRanker 的作用:
- 预测: 预测哪些股票未来可能表现好
- 评分: 输出评分和排名供参考
- 辅助: 提供决策参考，不直接执行交易

与量化策略的区别:
- MLStockRanker: 预测 → "这些股票可能表现好" (信息)
- EntryStrategy: 决策 → "何时买、买多少、何时卖" (指令)
```

### 与 MLEntry 的对比

| 对比项 | MLStockRanker | MLEntry |
|--------|--------------|---------|
| **类型** | 辅助工具 | 策略组件 |
| **定位** | 股票筛选器/预测器 | 交易信号生成器 |
| **输入** | 大股票池 (3000+) | 小股票池 (50-100) |
| **输出** | 评分 + 排名 | 多空信号 + 权重 |
| **模型目标** | 预测表现好的股票 | 预测收益率 + 生成信号 |
| **使用时机** | 回测前（一次性） | 回测中（每日） |
| **调用方** | 外部系统/策略可选 | 回测引擎必需 |
| **频率** | 低（回测前 1 次） | 高（每日） |
| **可选性** | 完全可选 | 策略必需 |

---

## 核心概念

### 工作原理

```
Step 1: 特征计算
  输入: 3000 只 A 股 + 市场数据
    ↓
  FeatureEngine.calculate_features()
    ├─ Alpha 因子 (125+)
    ├─ 技术指标 (60+)
    └─ 成交量特征
    ↓
  特征矩阵 (3000 stocks × 125+ features)

Step 2: ML 模型预测
  输入: 特征矩阵
    ↓
  MLStockRanker.model.predict()
    ├─ predicted_return: 预测收益率
    ├─ volatility: 预测波动率
    └─ confidence: 预测置信度
    ↓
  预测结果 (3000 只股票的预测)

Step 3: 评分计算
  公式: score = sharpe_ratio × confidence
       = (predicted_return / volatility) × confidence
    ↓
  评分结果 (3000 只股票的评分)

Step 4: 排名
  按 score 降序排列
    ↓
  输出 Top N (例如 Top 100)
```

### 评分公式详解

**核心公式**:
```python
score = sharpe_ratio × confidence
      = (predicted_return / volatility) × confidence
```

**为什么这样设计？**

1. **Sharpe Ratio**: 风险调整后的收益
   - `predicted_return / volatility`
   - 收益高、风险低的股票得分高

2. **Confidence**: 预测置信度
   - 基于特征质量计算
   - 数据完整、特征有效的股票置信度高

3. **组合效果**:
   - 既要收益高，又要风险低，还要预测可靠
   - 全方位评估股票质量

**示例**:
```python
# 股票 A: 高收益、高风险、高置信度
predicted_return = 0.10    # 10%
volatility = 0.08          # 8%
confidence = 0.90          # 90%
score_A = (0.10 / 0.08) × 0.90 = 1.125

# 股票 B: 中等收益、低风险、高置信度
predicted_return = 0.06    # 6%
volatility = 0.03          # 3%
confidence = 0.85          # 85%
score_B = (0.06 / 0.03) × 0.85 = 1.700

# 结果: 股票 B 得分更高（风险调整后收益更好）
```

---

## 实现细节

### API 接口

```python
from typing import Dict, List
import pandas as pd

class MLStockRanker:
    """
    ML 股票评分工具 (类似 BigQuant StockRanker)

    定位:
    - 辅助工具，非策略组件
    - 预测股票未来表现，输出评分排名
    - 可独立使用，也可集成到策略流程

    与策略的区别:
    - MLStockRanker: 评分 → "这些股票可能表现好"
    - EntryStrategy: 决策 → "何时买、买多少、何时卖"
    """

    def __init__(self, model_path: str, feature_config: Dict = None):
        """
        初始化 MLStockRanker

        Args:
            model_path: 模型文件路径
            feature_config: 特征计算配置
        """
        self.model = self._load_model(model_path)
        self.feature_config = feature_config or self._default_feature_config()

    def rank(
        self,
        stock_pool: List[str],      # 候选股票池
        market_data: pd.DataFrame,  # 市场数据
        date: str,                  # 评分日期
        return_top_n: int = None    # 可选：只返回 Top N
    ) -> Dict[str, Dict]:
        """
        对股票进行 ML 评分和排名

        Args:
            stock_pool: 候选股票列表 (例如全 A 股 3000+)
            market_data: 市场数据 DataFrame
            date: 评分日期 (YYYY-MM-DD)
            return_top_n: 可选，只返回 Top N

        Returns:
            {
                '600000.SH': {
                    'score': 0.85,              # ML 综合评分 (0-1)
                    'rank': 1,                  # 排名
                    'predicted_return': 0.08,   # 预测未来收益率
                    'confidence': 0.85          # 置信度
                },
                '000001.SZ': {
                    'score': 0.78,
                    'rank': 2,
                    'predicted_return': 0.06,
                    'confidence': 0.80
                },
                ...
            }

        注意:
        - 这是预测结果，不是交易指令
        - 外部系统可自由使用评分结果
        - 可用于股票池筛选或策略参考
        """
        # 1. 计算特征 (125+ Alpha因子)
        features = self._calculate_features(stock_pool, market_data, date)

        # 2. ML 模型预测
        predictions = self.model.predict(features)
        # predictions 包含: predicted_return, volatility, confidence

        # 3. 计算综合评分
        scores = self._calculate_score(predictions)
        # score = sharpe_ratio × confidence

        # 4. 排名
        rankings = self._rank(scores, return_top_n)

        return rankings

    def _calculate_features(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> pd.DataFrame:
        """
        计算特征矩阵

        使用 FeatureEngine 计算 125+ 特征
        """
        from core.features.feature_engine import FeatureEngine

        engine = FeatureEngine(
            feature_groups=self.feature_config.get('feature_groups', ['all']),
            lookback_window=self.feature_config.get('lookback_window', 60)
        )

        features = engine.calculate_features(stock_pool, market_data, date)
        return features

    def _calculate_score(self, predictions: pd.DataFrame) -> pd.Series:
        """
        计算综合评分

        公式: score = sharpe_ratio × confidence
             = (predicted_return / volatility) × confidence
        """
        # 计算 Sharpe Ratio
        sharpe = predictions['predicted_return'] / predictions['volatility']

        # 综合评分
        scores = sharpe * predictions['confidence']

        # 归一化到 [0, 1]
        scores = scores.clip(lower=0)

        return scores

    def _rank(
        self,
        scores: pd.Series,
        return_top_n: int = None
    ) -> Dict[str, Dict]:
        """
        根据评分进行排名

        Returns:
            {stock: {score, rank, ...}}
        """
        # 按评分降序排列
        sorted_scores = scores.sort_values(ascending=False)

        # 如果指定了 return_top_n，只返回 Top N
        if return_top_n:
            sorted_scores = sorted_scores.head(return_top_n)

        # 构建结果
        rankings = {}
        for rank, (stock, score) in enumerate(sorted_scores.items(), 1):
            rankings[stock] = {
                'score': score,
                'rank': rank,
                'predicted_return': self.model.predictions.loc[stock, 'predicted_return'],
                'confidence': self.model.predictions.loc[stock, 'confidence']
            }

        return rankings

    def _load_model(self, model_path: str):
        """加载训练好的模型"""
        import joblib
        return joblib.load(model_path)

    def _default_feature_config(self) -> Dict:
        """默认特征配置"""
        return {
            'feature_groups': ['all'],
            'lookback_window': 60
        }
```

---

## 使用指南

### 场景 1: 外部系统使用 MLStockRanker 筛选股票池

```python
from core.features.ml_ranker import MLStockRanker

# 初始化 MLStockRanker
ranker = MLStockRanker(model_path='models/ranker.pkl')

# 对全 A 股进行评分
all_a_stocks = get_all_a_stocks()  # 3000+ 只股票
rankings = ranker.rank(
    stock_pool=all_a_stocks,
    market_data=market_data,
    date='2024-01-01',
    return_top_n=50  # 只返回 Top 50
)

# 查看评分结果
for stock, info in rankings.items():
    print(f"{stock}: "
          f"score={info['score']:.2f}, "
          f"rank={info['rank']}, "
          f"predicted_return={info['predicted_return']:.2%}")

# 输出示例:
# 600000.SH: score=0.85, rank=1, predicted_return=8.00%
# 000001.SZ: score=0.78, rank=2, predicted_return=6.00%
# ...

# 提取 Top 50 股票池
selected_pool = list(rankings.keys())
print(f"✓ 筛选出 {len(selected_pool)} 只高潜力股票")

# 传给回测引擎
result = backtest_engine.run(stock_pool=selected_pool, ...)
```

### 场景 2: 策略内部可选择性参考评分

```python
from core.strategies.entries import EntryStrategy

class SmartEntry(EntryStrategy):
    """结合 ML 评分的策略"""

    def __init__(self, ranker: MLStockRanker = None):
        self.ranker = ranker  # 可选

    def generate_signals(self, stock_pool, market_data, date):
        signals = {}

        # 计算技术指标
        momentum = self._calculate_momentum(stock_pool, market_data, date)

        # 可选：参考 ML 评分
        if self.ranker:
            rankings = self.ranker.rank(stock_pool, market_data, date)

        for stock in stock_pool:
            mom_score = momentum[stock]

            # 如果有 ML 评分，综合考虑
            if self.ranker and stock in rankings:
                if rankings[stock]['score'] > 0.7:
                    ml_boost = rankings[stock]['score']
                    weight = mom_score * ml_boost
                else:
                    continue  # ML 评分太低，跳过
            else:
                weight = mom_score

            if weight > 0.10:
                signals[stock] = {
                    'action': 'long',
                    'weight': weight
                }

        return self._normalize_weights(signals)
```

### 场景 3: 前端展示供人工参考

```python
# Frontend API 调用
ranker = MLStockRanker(model_path='models/ranker.pkl')
rankings = ranker.rank(
    stock_pool=user_watchlist,  # 用户自选股
    market_data=market_data,
    date='2024-01-01'
)

# 前端展示评分表格
# | 股票代码 | 评分 | 排名 | 预测收益 | 置信度 |
# |---------|------|------|---------|--------|
# | 600000  | 0.85 | 1    | 8%      | 85%    |
# | 000001  | 0.78 | 2    | 6%      | 80%    |

# 用户根据评分手动决策是否买入
```

---

## 训练 MLStockRanker 模型

### 训练流程

```python
from core.ml.model_trainer import ModelTrainer, TrainingConfig

# Step 1: 配置训练参数
config = TrainingConfig(
    model_type='lightgbm',
    train_start_date='2020-01-01',
    train_end_date='2023-12-31',
    validation_split=0.2,
    forward_window=20,  # 预测未来 20 天表现
    feature_groups=['all'],
    hyperparameters={
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.8
    }
)

# Step 2: 准备数据
all_a_stocks = get_all_a_stocks()  # 全 A 股
market_data = load_market_data(
    stock_codes=all_a_stocks,
    start_date='2019-01-01',
    end_date='2023-12-31'
)

# Step 3: 训练模型
trainer = ModelTrainer(config)
trained_model = trainer.train(all_a_stocks, market_data)

# Step 4: 保存模型
trained_model.save('models/ranker.pkl')

print(f"✅ MLStockRanker 模型训练完成!")
print(f"验证集 IC: {trained_model.metrics['ic']:.4f}")
print(f"验证集 Rank IC: {trained_model.metrics['rank_ic']:.4f}")
```

### 训练建议

**与 MLEntry 训练的区别**:

| 配置项 | MLStockRanker | MLEntry |
|--------|---------------|---------|
| **forward_window** | 20-30 天 | 5-10 天 |
| **stock_pool** | 全 A 股 (3000+) | 精选池 (300-500) |
| **目标** | 预测长期表现 | 预测短期收益 |
| **使用频率** | 低（回测前 1 次） | 高（每日） |

**推荐配置**:
```python
# MLStockRanker 配置
config_ranker = TrainingConfig(
    forward_window=20,        # 预测未来 20 天
    feature_groups=['all'],   # 使用所有特征
    train_start_date='2018-01-01',
    train_end_date='2023-12-31'
)

# MLEntry 配置
config_entry = TrainingConfig(
    forward_window=5,         # 预测未来 5 天
    feature_groups=['alpha', 'technical'],
    train_start_date='2020-01-01',
    train_end_date='2023-12-31'
)
```

---

## 性能优化

### 1. 缓存特征

```python
class CachedMLStockRanker(MLStockRanker):
    """带缓存的 MLStockRanker"""

    def __init__(self, model_path: str, cache_dir: str = './cache'):
        super().__init__(model_path)
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def rank(self, stock_pool, market_data, date, return_top_n=None):
        # 检查缓存
        cache_key = f"{date}_{len(stock_pool)}_{return_top_n}"
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.pkl")

        if os.path.exists(cache_path):
            import joblib
            return joblib.load(cache_path)

        # 计算评分
        rankings = super().rank(stock_pool, market_data, date, return_top_n)

        # 保存缓存
        import joblib
        joblib.dump(rankings, cache_path)

        return rankings
```

### 2. 批量处理

```python
def rank_batch(
    self,
    stock_pool: List[str],
    market_data: pd.DataFrame,
    dates: List[str]  # 多个日期
) -> Dict[str, Dict]:
    """
    批量评分（多个日期）
    """
    all_rankings = {}

    for date in dates:
        rankings = self.rank(stock_pool, market_data, date)
        all_rankings[date] = rankings

    return all_rankings
```

---

## 常见问题

### Q1: MLStockRanker 和 MLEntry 可以共用模型吗？

**答：不建议。**

虽然它们共享特征工程，但训练目标不同：
- MLStockRanker: 预测长期表现（20-30 天）
- MLEntry: 预测短期收益（5-10 天）

建议分别训练，各自优化。

### Q2: MLStockRanker 评分多久更新一次？

**推荐频率**:
- 回测: 回测开始前评分 1 次
- 实盘: 每月或每季度更新 1 次

**原因**:
- MLStockRanker 预测的是长期表现
- 评分变化不会太快
- 频繁更新反而增加噪声

### Q3: 如何判断 MLStockRanker 的质量？

**评估指标**:
```python
# 训练时的指标
IC > 0.05        # 有预测能力
Rank IC > 0.10   # 排序能力强

# 回测验证
# 将股票池分为 Top 20%, Middle 60%, Bottom 20%
# 比较三组的平均收益:
# - Top 20% 应该表现最好
# - Bottom 20% 应该表现最差
```

### Q4: MLStockRanker 能否直接用于交易？

**答：不建议。**

MLStockRanker 只提供评分和排名，不提供：
- 具体的多空方向
- 仓位权重
- 入场时机
- 退出时机

**正确用法**:
```python
# ✅ 用于筛选股票池
rankings = ranker.rank(all_stocks, ...)
selected_pool = list(rankings.keys())[:50]

# 再用策略进行交易
entry_strategy = MomentumEntry()
result = engine.run(stock_pool=selected_pool, ...)
```

---

## 相关文档

- [MLEntry 详解](./README.md)
- [评估指标详解](./evaluation-metrics.md)
- [架构详解](../architecture/overview.md)
- [API 参考](../api/reference.md)

---

**文档版本**: v5.1.0
**最后更新**: 2026-02-08
