# 机器学习系统完整指南

**文档版本**: v5.1.0
**最后更新**: 2026-02-07

---

## 📋 目录

- [系统概述](#系统概述)
- [核心组件](#核心组件)
- [完整工作流程](#完整工作流程)
- [使用指南](#使用指南)
- [性能优化](#性能优化)
- [模型维护](#模型维护)

**📖 专题文档**:
- [MLStockRanker 完整指南](./mlstockranker.md) - 股票评分和排名工具的详细说明
- [评估指标详解](./evaluation-metrics.md) - RMSE, IC, 夏普比率等指标的完整说明

---

## 系统概述

### 机器学习在系统中的角色

```
┌─────────────────────────────────────────────────────────┐
│             ML 入场信号系统完整流程                       │
└─────────────────────────────────────────────────────────┘

阶段 1: 数据准备与特征工程
  ├─ [股票池] + [历史行情数据]
  ├─ FeatureEngine.calculate_features()
  │   ├─ Alpha 因子 (125+)
  │   ├─ 技术指标 (60+)
  │   ├─ 成交量特征
  │   └─ 市场情绪特征
  ├─ 特征预处理(缺失值、异常值、标准化)
  └─ → [特征矩阵] (N stocks × 125+ features)
        ↓
阶段 2: 模型训练
  ├─ LabelGenerator.generate_labels()
  ├─ ModelTrainer.train()
  │   ├─ 模型选择: LightGBM / XGBoost / Neural Net
  │   ├─ 超参数优化: Optuna / Grid Search
  │   └─ 交叉验证: TimeSeriesSplit
  ├─ ModelEvaluator.evaluate()
  │   ├─ IC (Information Coefficient)
  │   ├─ Rank IC
  │   └─ 分组回测
  └─ → [训练好的模型] (model.pkl)
        ↓
阶段 3: 信号生成(回测/实盘)
  ├─ MLEntry.generate_signals(stock_pool, date)
  │   ├─ 1. 计算当日特征
  │   ├─ 2. 模型预测(expected_return + confidence)
  │   ├─ 3. 信号筛选(置信度过滤 + Top N)
  │   ├─ 4. 权重计算(sharpe × confidence)
  │   └─ 5. 归一化权重
  └─ → [交易信号] {'stock': {'action': 'long/short', 'weight': 0.xx}}
```

### ML 组件对比

| 组件 | MLStockRanker | MLEntry |
|------|--------------|---------|
| **类型** | 辅助工具 | 策略组件 |
| **定位** | 股票筛选器/预测器 | 交易信号生成器 |
| **输入** | 大股票池 (3000+) | 小股票池 (50-100) |
| **输出** | 评分 + 排名 | 多空信号 + 权重 |
| **使用时机** | 回测前(一次性) | 回测中(每日) |
| **频率** | 低 | 高 |
| **可选性** | 完全可选 | 策略必需 |

---

## 核心组件

### 1. 特征工程引擎 (FeatureEngine)

**职责**: 计算 125+ 特征(Alpha 因子 + 技术指标 + 成交量特征)

```python
class FeatureEngine:
    """
    特征工程引擎
    """

    def __init__(
        self,
        feature_groups: List[str] = None,
        lookback_window: int = 60,
        cache_enabled: bool = True
    ):
        self.feature_groups = feature_groups or ['all']
        self.lookback_window = lookback_window
        self.cache = {} if cache_enabled else None

    def calculate_features(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> pd.DataFrame:
        """
        计算特征矩阵

        Returns:
            pd.DataFrame:
                index = stock_codes
                columns = feature_names (125+)
        """
        features = pd.DataFrame(index=stock_codes)

        # Alpha 因子 (125+)
        if 'alpha' in self.feature_groups or 'all' in self.feature_groups:
            alpha_features = self._calculate_alpha_features(
                stock_codes, market_data, date
            )
            features = pd.concat([features, alpha_features], axis=1)

        # 技术指标 (60+)
        if 'technical' in self.feature_groups or 'all' in self.feature_groups:
            tech_features = self._calculate_technical_features(
                stock_codes, market_data, date
            )
            features = pd.concat([features, tech_features], axis=1)

        # 成交量特征
        if 'volume' in self.feature_groups or 'all' in self.feature_groups:
            volume_features = self._calculate_volume_features(
                stock_codes, market_data, date
            )
            features = pd.concat([features, volume_features], axis=1)

        return features
```

**特征类别**:

| 类别 | 数量 | 示例 |
|------|------|------|
| Alpha 因子 | 125+ | 动量、反转、波动率、成交量 |
| 技术指标 | 60+ | RSI, MACD, KDJ, 布林带 |
| 成交量特征 | 10+ | 成交量比率、换手率 |
| 市场情绪 | 5+ | 市场宽度、涨跌家数 |

### 2. 标签生成器 (LabelGenerator)

**职责**: 生成训练标签(未来收益率)

```python
class LabelGenerator:
    """
    标签生成器
    """

    def __init__(
        self,
        forward_window: int = 5,
        label_type: str = 'return'
    ):
        self.forward_window = forward_window
        self.label_type = label_type

    def generate_labels(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> pd.Series:
        """
        生成标签

        Returns:
            pd.Series:
                index = stock_codes
                values = 未来收益率(或方向)
        """
        labels = {}

        for stock in stock_codes:
            stock_data = market_data[market_data['stock_code'] == stock]

            # 找到当前日期的位置
            current_idx = stock_data[stock_data['date'] == date].index
            if len(current_idx) == 0:
                continue

            # 计算未来收益率
            current_price = stock_data.loc[current_idx[0], 'close']
            future_idx = current_idx[0] + self.forward_window

            if future_idx < len(stock_data):
                future_price = stock_data.iloc[future_idx]['close']

                if self.label_type == 'return':
                    labels[stock] = (future_price - current_price) / current_price
                elif self.label_type == 'direction':
                    labels[stock] = 1 if future_price > current_price else 0

        return pd.Series(labels)
```

### 3. 模型训练器 (ModelTrainer)

**职责**: 训练机器学习模型

```python
@dataclass
class TrainingConfig:
    """训练配置"""
    model_type: str = 'lightgbm'
    train_start_date: str = '2020-01-01'
    train_end_date: str = '2023-12-31'
    validation_split: float = 0.2
    forward_window: int = 5
    feature_groups: List[str] = None
    hyperparameters: Dict = None


class ModelTrainer:
    """
    模型训练器
    """

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.feature_engine = FeatureEngine(
            feature_groups=config.feature_groups,
            lookback_window=60
        )
        self.label_generator = LabelGenerator(
            forward_window=config.forward_window,
            label_type='return'
        )

    def train(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame
    ) -> 'TrainedModel':
        """
        训练模型

        Returns:
            TrainedModel: 训练好的模型
        """
        # 1. 准备训练数据
        X_train, y_train, X_val, y_val = self._prepare_training_data(
            stock_pool, market_data
        )

        # 2. 训练模型
        model = self._train_model(X_train, y_train, X_val, y_val)

        # 3. 评估模型
        metrics = self._evaluate_model(model, X_val, y_val)

        return TrainedModel(
            model=model,
            feature_engine=self.feature_engine,
            config=self.config,
            metrics=metrics
        )
```

### 4. 训练好的模型 (TrainedModel)

**职责**: 封装模型 + 特征引擎，提供预测接口

```python
class TrainedModel:
    """
    训练好的模型(可保存和加载)
    """

    def __init__(
        self,
        model,
        feature_engine: FeatureEngine,
        config: TrainingConfig,
        metrics: Dict
    ):
        self.model = model
        self.feature_engine = feature_engine
        self.config = config
        self.metrics = metrics

    def predict(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> pd.DataFrame:
        """
        预测

        Returns:
            pd.DataFrame:
                columns = ['expected_return', 'volatility', 'confidence']
                index = stock_codes
        """
        # 1. 计算特征
        features = self.feature_engine.calculate_features(
            stock_codes, market_data, date
        )

        # 2. 数据清洗
        features = features.fillna(0).replace([np.inf, -np.inf], 0)

        # 3. 模型预测
        predictions = self.model.predict(features)

        # 4. 构建预测结果
        result = pd.DataFrame(index=features.index)
        result['expected_return'] = predictions
        result['volatility'] = self._estimate_volatility(
            stock_codes, market_data, date
        )
        result['confidence'] = self._estimate_confidence(features)

        return result

    def save(self, path: str):
        """保存模型"""
        import joblib
        joblib.dump(self, path)

    @staticmethod
    def load(path: str) -> 'TrainedModel':
        """加载模型"""
        import joblib
        return joblib.load(path)
```

### 5. ML 入场策略 (MLEntry)

**职责**: 使用训练好的模型生成交易信号

```python
class MLEntry(EntryStrategy):
    """
    机器学习入场策略
    """

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.7,
        top_long: int = 20,
        top_short: int = 10
    ):
        self.model: TrainedModel = TrainedModel.load(model_path)
        self.confidence_threshold = confidence_threshold
        self.top_long = top_long
        self.top_short = top_short

    def generate_signals(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> Dict[str, Dict]:
        """
        生成入场信号
        """
        # 1. 模型预测
        predictions = self.model.predict(stock_pool, market_data, date)

        # 2. 筛选做多候选
        long_candidates = predictions[
            (predictions['expected_return'] > 0) &
            (predictions['confidence'] > self.confidence_threshold)
        ].copy()

        # 计算做多权重
        long_candidates['weight'] = (
            (long_candidates['expected_return'] / long_candidates['volatility']) *
            long_candidates['confidence']
        )
        long_candidates = long_candidates.nlargest(self.top_long, 'weight')

        # 3. 筛选做空候选
        short_candidates = predictions[
            (predictions['expected_return'] < 0) &
            (predictions['confidence'] > self.confidence_threshold)
        ].copy()

        # 计算做空权重
        short_candidates['weight'] = (
            (abs(short_candidates['expected_return']) / short_candidates['volatility']) *
            short_candidates['confidence']
        )
        short_candidates = short_candidates.nlargest(self.top_short, 'weight')

        # 4. 合并信号
        signals = {}
        for stock, row in long_candidates.iterrows():
            signals[stock] = {'action': 'long', 'weight': row['weight']}
        for stock, row in short_candidates.iterrows():
            signals[stock] = {'action': 'short', 'weight': row['weight']}

        # 5. 归一化权重
        total_weight = sum(s['weight'] for s in signals.values())
        if total_weight > 0:
            for stock in signals:
                signals[stock]['weight'] /= total_weight

        return signals
```

---

## 完整工作流程

### 场景 1: 训练 ML 模型

```python
from core.ml.model_trainer import ModelTrainer, TrainingConfig
from core.data import load_market_data

# Step 1: 配置训练参数
config = TrainingConfig(
    model_type='lightgbm',
    train_start_date='2020-01-01',
    train_end_date='2023-12-31',
    validation_split=0.2,
    forward_window=5,
    feature_groups=['alpha', 'technical', 'volume'],
    hyperparameters={
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.8
    }
)

# Step 2: 准备数据
stock_pool = ['600000.SH', '000001.SZ', ..., 300]
market_data = load_market_data(
    stock_codes=stock_pool,
    start_date='2019-01-01',
    end_date='2023-12-31'
)

# Step 3: 训练模型
trainer = ModelTrainer(config)
trained_model = trainer.train(stock_pool, market_data)

# Step 4: 保存模型
trained_model.save('models/ml_entry_model.pkl')

print(f"✅ 模型训练完成!")
print(f"验证集 IC: {trained_model.metrics['ic']:.4f}")
print(f"验证集 Rank IC: {trained_model.metrics['rank_ic']:.4f}")
```

### 场景 2: 使用 ML 策略回测

```python
from core.strategies.entries import MLEntry
from core.strategies.exits import TimeBasedExit
from core.risk import RiskManager
from core.backtest import BacktestEngine

# Step 1: 加载训练好的模型
entry_strategy = MLEntry(
    model_path='models/ml_entry_model.pkl',
    confidence_threshold=0.7,
    top_long=20,
    top_short=10
)

# Step 2: 配置退出策略和风控
exit_strategy = TimeBasedExit(max_holding_days=10)
risk_manager = RiskManager(
    max_position_loss_pct=0.10,
    max_leverage=1.0
)

# Step 3: 运行回测
engine = BacktestEngine(
    entry_strategy=entry_strategy,
    exit_strategy=exit_strategy,
    risk_manager=risk_manager
)

result = engine.run(
    stock_pool=stock_pool,
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# Step 4: 分析结果
print(f"总收益率: {result.total_return:.2%}")
print(f"年化收益率: {result.annual_return:.2%}")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
print(f"最大回撤: {result.max_drawdown:.2%}")
```

### 场景 3: MLStockRanker + ML 策略组合

```python
from core.features.ml_ranker import MLStockRanker

# Step 1: 使用 MLStockRanker 筛选高潜力股票池
ranker = MLStockRanker(model_path='models/ranker.pkl')
rankings = ranker.rank(
    stock_pool=all_a_stocks,  # 全 A 股(3000+)
    market_data=market_data,
    date='2024-01-01',
    return_top_n=100
)

# 提取 Top 100 作为股票池
selected_stock_pool = list(rankings.keys())

# Step 2: 在筛选后的股票池上运行 ML 策略
entry_strategy = MLEntry(
    model_path='models/ml_entry_model.pkl',
    confidence_threshold=0.7
)

result = engine.run(
    stock_pool=selected_stock_pool,
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

---

## 使用指南

### 模型训练最佳实践

#### 1. 数据准备

```python
# 确保数据完整性
market_data = load_market_data(
    stock_codes=stock_pool,
    start_date='2019-01-01',  # 留出 lookback window
    end_date='2023-12-31'
)

# 检查数据质量
assert market_data.isnull().sum().sum() == 0
assert len(market_data) > 0
```

#### 2. 特征选择

```python
# 全特征训练
config = TrainingConfig(
    feature_groups=['all'],  # 使用所有特征
    ...
)

# 或选择特定特征组
config = TrainingConfig(
    feature_groups=['alpha', 'technical'],  # 只使用 Alpha 和技术指标
    ...
)
```

#### 3. 超参数调优

```python
# LightGBM 推荐参数
hyperparameters = {
    'objective': 'regression',
    'metric': 'l2',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5
}

config = TrainingConfig(
    model_type='lightgbm',
    hyperparameters=hyperparameters,
    ...
)
```

#### 4. 模型评估

```python
# 评估指标
metrics = trained_model.metrics

print(f"IC: {metrics['ic']:.4f}")           # 信息系数
print(f"Rank IC: {metrics['rank_ic']:.4f}") # 秩相关系数

# IC > 0.05 表示模型有效
# Rank IC > 0.1 表示模型优秀
```

---

## 性能优化

### 1. 特征缓存

```python
class CachedFeatureEngine(FeatureEngine):
    """带缓存的特征引擎"""

    def __init__(self, cache_dir: str = './cache/features', **kwargs):
        super().__init__(**kwargs)
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def calculate_features(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> pd.DataFrame:
        # 检查缓存
        cache_key = f"{date}_{hash(tuple(sorted(stock_codes)))}"
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.parquet")

        if os.path.exists(cache_path):
            return pd.read_parquet(cache_path)

        # 计算特征
        features = super().calculate_features(stock_codes, market_data, date)

        # 保存缓存
        features.to_parquet(cache_path)
        return features
```

### 2. 并行计算

```python
from joblib import Parallel, delayed

class ParallelFeatureEngine(FeatureEngine):
    """并行特征引擎"""

    def __init__(self, n_jobs: int = 4, **kwargs):
        super().__init__(**kwargs)
        self.n_jobs = n_jobs

    def calculate_features(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> pd.DataFrame:
        # 将股票池分批
        batch_size = len(stock_codes) // self.n_jobs
        batches = [
            stock_codes[i:i+batch_size]
            for i in range(0, len(stock_codes), batch_size)
        ]

        # 并行计算
        results = Parallel(n_jobs=self.n_jobs)(
            delayed(super().calculate_features)(batch, market_data, date)
            for batch in batches
        )

        # 合并结果
        return pd.concat(results, axis=0)
```

### 3. 模型推理优化

```python
# 批量预测
predictions = model.predict(features, num_iteration=model.best_iteration)

# 使用 GPU 加速 (XGBoost)
params = {
    'tree_method': 'gpu_hist',
    'gpu_id': 0
}
```

---

## 模型维护

### 模型重训练策略

```python
class ModelUpdateScheduler:
    """模型更新调度器"""

    def __init__(
        self,
        retrain_frequency: str = 'quarterly',
        performance_threshold: float = 0.10
    ):
        self.retrain_frequency = retrain_frequency
        self.performance_threshold = performance_threshold

    def should_retrain(
        self,
        current_model: TrainedModel,
        recent_performance: Dict
    ) -> bool:
        """判断是否需要重训练"""
        # 策略 1: 按时间周期
        if self._is_time_to_retrain():
            return True

        # 策略 2: 性能下降
        baseline_ic = current_model.metrics['ic']
        recent_ic = recent_performance['ic']

        if (baseline_ic - recent_ic) / baseline_ic > self.performance_threshold:
            return True

        return False
```

### 在线性能监控

```python
class ModelMonitor:
    """模型性能监控"""

    def __init__(self, model: TrainedModel):
        self.model = model
        self.performance_history = []

    def evaluate_recent_performance(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        start_date: str,
        end_date: str
    ) -> Dict:
        """评估近期模型性能"""
        dates = pd.date_range(start_date, end_date, freq='B')

        all_predictions = []
        all_actuals = []

        for date in dates:
            # 预测
            predictions = self.model.predict(stock_pool, market_data, date)

            # 实际收益
            actuals = self._get_actual_returns(
                stock_pool, market_data, date, forward_window=5
            )

            all_predictions.extend(predictions['expected_return'].values)
            all_actuals.extend(actuals.values)

        # 计算 IC
        ic = np.corrcoef(all_actuals, all_predictions)[0, 1]

        return {'ic': ic, 'period': f'{start_date} to {end_date}'}
```

---

## 相关文档

- [MLStockRanker 完整指南](./mlstockranker.md) - ⭐ 推荐阅读
- [评估指标详解](./evaluation-metrics.md) - ⭐ 推荐阅读
- [架构详解](../architecture/overview.md)
- [策略系统](../strategies/README.md)
- [特征工程](../features/README.md)
- [API 参考](../api/reference.md)

---

**文档版本**: v5.1.0
**最后更新**: 2026-02-08
