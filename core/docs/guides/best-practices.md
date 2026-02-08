# 最佳实践指南

**文档版本**: v5.1.0
**最后更新**: 2026-02-07

---

## 📋 目录

- [策略开发](#策略开发)
- [权重管理](#权重管理)
- [机器学习使用](#机器学习使用)
- [A 股特有处理](#a-股特有处理)
- [交易成本建模](#交易成本建模)
- [性能优化](#性能优化)
- [常见陷阱](#常见陷阱)

---

## 策略开发

### 1. 策略职责分离

**✅ 正确做法**: 每个策略只负责一件事

```python
# 入场策略: 只负责生成入场信号
class MyEntry(EntryStrategy):
    def generate_signals(self, stock_pool, market_data, date):
        # 只做信号生成
        signals = {}
        for stock in stock_pool:
            momentum = self._calculate_momentum(stock, market_data, date)
            if momentum > self.threshold:
                signals[stock] = {'action': 'long', 'weight': momentum}
        return self._normalize_weights(signals)

# 退出策略: 只负责生成退出信号
class MyExit(ExitStrategy):
    def generate_exit_signals(self, positions, market_data, date):
        # 只做退出判断
        close_list = []
        for stock, position in positions.items():
            if self._should_exit(position, market_data, date):
                close_list.append(stock)
        return {'close': close_list, 'reverse': {}}
```

**❌ 错误做法**: 策略包含过多职责

```python
# 不要在策略中做风控
class BadEntry(EntryStrategy):
    def generate_signals(self, stock_pool, market_data, date):
        signals = {}
        # ...
        # ❌ 不要在这里做风控检查
        for stock in signals:
            if self._check_risk(stock):  # 风控应该在 RiskManager 中
                del signals[stock]
        return signals
```

### 2. 策略可配置性

**✅ 正确做法**: 参数可配置

```python
class MomentumEntry(EntryStrategy):
    def __init__(
        self,
        lookback: int = 20,           # 可配置参数
        threshold: float = 0.10,      # 可配置参数
        weight_method: str = 'equal'  # 可配置参数
    ):
        self.lookback = lookback
        self.threshold = threshold
        self.weight_method = weight_method

# 使用时可以灵活调整
strategy1 = MomentumEntry(lookback=10, threshold=0.05)
strategy2 = MomentumEntry(lookback=30, threshold=0.15)
```

### 3. 策略测试

**✅ 正确做法**: 为每个策略编写单元测试

```python
import unittest

class TestMomentumEntry(unittest.TestCase):
    def setUp(self):
        self.strategy = MomentumEntry(lookback=20, threshold=0.10)
        self.market_data = self._prepare_test_data()

    def test_generate_signals_long(self):
        """测试做多信号生成"""
        signals = self.strategy.generate_signals(
            stock_pool=['600000.SH'],
            market_data=self.market_data,
            date='2024-01-01'
        )

        self.assertIn('600000.SH', signals)
        self.assertEqual(signals['600000.SH']['action'], 'long')
        self.assertGreater(signals['600000.SH']['weight'], 0)

    def test_weights_normalized(self):
        """测试权重归一化"""
        signals = self.strategy.generate_signals(
            stock_pool=['600000.SH', '000001.SZ'],
            market_data=self.market_data,
            date='2024-01-01'
        )

        total_weight = sum(s['weight'] for s in signals.values())
        self.assertAlmostEqual(total_weight, 1.0, places=5)
```

---

## 权重管理

### 1. 权重归一化

**✅ 正确做法**: 多空分别归一化

```python
def normalize_weights(self, signals: Dict[str, Dict]) -> Dict[str, Dict]:
    """正确的权重归一化方法"""
    # 分离多空信号
    long_signals = {k: v for k, v in signals.items() if v['action'] == 'long'}
    short_signals = {k: v for k, v in signals.items() if v['action'] == 'short'}

    # 分别归一化
    long_total = sum(s['weight'] for s in long_signals.values())
    short_total = sum(s['weight'] for s in short_signals.values())

    if long_total > 0:
        for stock in long_signals:
            long_signals[stock]['weight'] /= long_total

    if short_total > 0:
        for stock in short_signals:
            short_signals[stock]['weight'] /= short_total

    # 合并
    return {**long_signals, **short_signals}
```

**❌ 错误做法**: 多空一起归一化

```python
def bad_normalize_weights(self, signals: Dict[str, Dict]) -> Dict[str, Dict]:
    # ❌ 这样会导致多空权重不平衡
    total = sum(s['weight'] for s in signals.values())
    for stock in signals:
        signals[stock]['weight'] /= total
    return signals
```

### 2. 权重检查

**✅ 正确做法**: 在生成信号后检查权重

```python
def generate_signals(self, stock_pool, market_data, date):
    signals = {}
    # ... 生成信号 ...

    # 检查权重
    self._validate_weights(signals)

    return signals

def _validate_weights(self, signals: Dict[str, Dict]):
    """验证权重的有效性"""
    for stock, signal in signals.items():
        assert 0 <= signal['weight'] <= 1, f"权重必须在 [0, 1] 之间: {stock}"
        assert signal['action'] in ['long', 'short'], f"动作必须是 long 或 short: {stock}"

    total = sum(s['weight'] for s in signals.values())
    assert 0.99 <= total <= 1.01, f"总权重必须接近 1.0: {total}"
```

---

## 机器学习使用

### 1. MLStockRanker 使用建议

**✅ 推荐**: 回测前筛选 1 次

```python
# 在回测开始前使用 MLStockRanker 筛选股票池
ranker = MLStockRanker(model_path='ranker.pkl')
rankings = ranker.rank(
    stock_pool=candidate_pool,  # 3000 只候选
    market_data=market_data,
    date='2024-01-01'  # 回测开始日期
)
stock_pool = list(rankings.keys())[:50]  # 选择 Top 50

# 回测中只处理筛选后的 50 只
for date in backtest_dates:
    entry_signals = entry_strategy.generate_signals(
        stock_pool=stock_pool,  # 固定的 50 只
        market_data=market_data,
        date=date
    )
```

**❌ 不推荐**: 回测中每日调用

```python
# ❌ 性能差: 每天重复计算
for date in backtest_dates:
    rankings = ranker.rank(
        stock_pool=candidate_pool,  # 每天都对 3000 只评分
        market_data=market_data,
        date=date
    )
    stock_pool = list(rankings.keys())[:50]
    entry_signals = entry_strategy.generate_signals(...)
```

### 2. ML 模型训练

**✅ 正确做法**: 使用时间序列切分

```python
from sklearn.model_selection import TimeSeriesSplit

# ✅ 使用 TimeSeriesSplit 避免未来信息泄露
tscv = TimeSeriesSplit(n_splits=5)

for train_idx, val_idx in tscv.split(X):
    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

    model.fit(X_train, y_train)
    score = model.score(X_val, y_val)
```

**❌ 错误做法**: 使用普通交叉验证

```python
from sklearn.model_selection import KFold

# ❌ 会导致未来信息泄露
kfold = KFold(n_splits=5, shuffle=True)  # shuffle=True 是致命错误
for train_idx, val_idx in kfold.split(X):
    # ... 训练 ...
```

### 3. 特征工程

**✅ 正确做法**: 使用 lookback window

```python
def calculate_features(self, stock_codes, market_data, date):
    """正确的特征计算方法"""
    features = {}

    for stock in stock_codes:
        # 只使用 date 之前的数据
        stock_data = market_data[
            (market_data['stock_code'] == stock) &
            (market_data['date'] <= date)
        ].tail(self.lookback_window)

        if len(stock_data) < 20:
            continue

        # 计算特征
        features[stock] = {
            'momentum_20': stock_data['close'].pct_change(20).iloc[-1],
            'volatility_20': stock_data['close'].pct_change().std(),
            # ...
        }

    return pd.DataFrame(features).T
```

**❌ 错误做法**: 使用未来信息

```python
def bad_calculate_features(self, stock_codes, market_data, date):
    # ❌ 包含了未来信息
    stock_data = market_data[market_data['stock_code'] == stock]

    # ❌ 这里计算的是全时间段的统计量,包含了未来信息
    features = {
        'momentum': stock_data['close'].pct_change(20).mean(),
        'volatility': stock_data['close'].pct_change().std()
    }
```

---

## A 股特有处理

### 1. 融券限制

**✅ 正确做法**: 过滤不可融券股票

```python
# 定义可融券股票池
shortable_stocks = ['600000.SH', '000001.SZ', ...]  # 从券商获取

# 在风控层过滤
class RiskManager:
    def __init__(self, shortable_stocks: List[str] = None):
        self.shortable_stocks = set(shortable_stocks or [])

    def check_entry_limits(self, signals, ...):
        # 过滤不可融券的做空信号
        filtered_signals = {}
        for stock, signal in signals.items():
            if signal['action'] == 'short':
                if stock in self.shortable_stocks:
                    filtered_signals[stock] = signal
            else:
                filtered_signals[stock] = signal

        return filtered_signals
```

### 2. 涨跌停处理

**✅ 正确做法**: 在交易执行时检查涨跌停

```python
def execute_trade(self, stock, action, price, shares, market_data, date):
    """执行交易时检查涨跌停"""
    # 获取昨日收盘价
    yesterday_close = self._get_yesterday_close(stock, market_data, date)

    # 计算涨跌停价格
    limit_up = yesterday_close * 1.10
    limit_down = yesterday_close * 0.90

    # 检查是否涨跌停
    if action == 'long' and price >= limit_up * 0.99:
        # 涨停，无法买入
        return False, "涨停无法买入"

    if action == 'short' and price <= limit_down * 1.01:
        # 跌停，无法卖空
        return False, "跌停无法卖空"

    # 执行交易
    return True, "交易成功"
```

### 3. T+1 交易制度

**✅ 正确做法**: 记录买入日期

```python
@dataclass
class Position:
    stock_code: str
    entry_date: str  # 记录买入日期
    # ...

def can_sell(self, position: Position, current_date: str) -> bool:
    """检查是否可以卖出 (T+1)"""
    entry_date = pd.Timestamp(position.entry_date)
    current_date = pd.Timestamp(current_date)

    # 至少持有 1 个交易日
    return (current_date - entry_date).days >= 1
```

---

## 交易成本建模

### 1. 完整的成本模型

**✅ 正确做法**: 包含所有成本

```python
class TransactionCost:
    """交易成本模型"""

    def __init__(self):
        self.commission_rate = 0.0003   # 万三佣金
        self.commission_min = 5.0       # 最低 5 元
        self.stamp_tax = 0.001          # 千一印花税 (卖出单边)
        self.transfer_fee = 0.00002     # 过户费 (双边)
        self.slippage_pct = 0.001       # 0.1% 滑点

    def calculate_buy_cost(self, price: float, shares: int) -> float:
        """计算买入成本"""
        trade_value = price * shares

        # 佣金
        commission = max(trade_value * self.commission_rate, self.commission_min)

        # 过户费
        transfer_fee = trade_value * self.transfer_fee

        # 滑点
        slippage = price * shares * self.slippage_pct

        return commission + transfer_fee + slippage

    def calculate_sell_cost(self, price: float, shares: int) -> float:
        """计算卖出成本"""
        trade_value = price * shares

        # 佣金
        commission = max(trade_value * self.commission_rate, self.commission_min)

        # 印花税 (卖出单边)
        stamp_tax = trade_value * self.stamp_tax

        # 过户费
        transfer_fee = trade_value * self.transfer_fee

        # 滑点
        slippage = price * shares * self.slippage_pct

        return commission + stamp_tax + transfer_fee + slippage
```

### 2. 滑点模型

**✅ 正确做法**: 根据成交量调整滑点

```python
def calculate_slippage(
    self,
    price: float,
    shares: int,
    daily_volume: int,
    action: str
) -> float:
    """
    计算滑点

    滑点与交易量占比相关
    """
    # 计算交易量占比
    volume_ratio = shares / daily_volume

    # 基础滑点
    base_slippage = 0.001  # 0.1%

    # 根据交易量占比调整
    if volume_ratio < 0.01:
        slippage_pct = base_slippage
    elif volume_ratio < 0.05:
        slippage_pct = base_slippage * 2
    else:
        slippage_pct = base_slippage * 5

    # 买入向上滑点，卖出向下滑点
    if action == 'long':
        return price * slippage_pct
    else:
        return -price * slippage_pct
```

---

## 性能优化

### 1. 数据缓存

**✅ 正确做法**: 缓存计算结果

```python
from functools import lru_cache

class FeatureEngine:
    def __init__(self):
        self.cache = {}

    def calculate_features(self, stock_codes, market_data, date):
        # 生成缓存键
        cache_key = f"{date}_{hash(tuple(sorted(stock_codes)))}"

        # 检查缓存
        if cache_key in self.cache:
            return self.cache[cache_key]

        # 计算特征
        features = self._do_calculate_features(stock_codes, market_data, date)

        # 保存缓存
        self.cache[cache_key] = features

        return features
```

### 2. 向量化计算

**✅ 正确做法**: 使用 NumPy/Pandas 向量化

```python
# ✅ 向量化计算
def calculate_momentum_vectorized(df: pd.DataFrame, window: int = 20):
    """向量化计算动量"""
    return df['close'].pct_change(window)

# ❌ 循环计算
def calculate_momentum_loop(df: pd.DataFrame, window: int = 20):
    """循环计算动量 (慢)"""
    momentum = []
    for i in range(len(df)):
        if i < window:
            momentum.append(np.nan)
        else:
            ret = (df['close'].iloc[i] - df['close'].iloc[i-window]) / df['close'].iloc[i-window]
            momentum.append(ret)
    return pd.Series(momentum, index=df.index)
```

### 3. 并行处理

**✅ 正确做法**: 使用多进程处理独立任务

```python
from joblib import Parallel, delayed

def calculate_features_parallel(stock_codes, market_data, date, n_jobs=4):
    """并行计算特征"""
    # 分批
    batch_size = len(stock_codes) // n_jobs
    batches = [
        stock_codes[i:i+batch_size]
        for i in range(0, len(stock_codes), batch_size)
    ]

    # 并行计算
    results = Parallel(n_jobs=n_jobs)(
        delayed(calculate_features_batch)(batch, market_data, date)
        for batch in batches
    )

    # 合并结果
    return pd.concat(results, axis=0)
```

---

## 常见陷阱

### 1. 未来信息泄露

**❌ 常见错误**:

```python
# 错误: 使用全部数据计算统计量
def bad_zscore(df):
    return (df - df.mean()) / df.std()  # 包含了未来信息

# 正确: 使用滚动窗口
def good_zscore(df, window=20):
    return (df - df.rolling(window).mean()) / df.rolling(window).std()
```

### 2. 幸存者偏差

**❌ 常见错误**:

```python
# 错误: 只使用当前仍在交易的股票
stock_pool = get_current_trading_stocks()  # 只包含未退市股票

# 正确: 使用历史时点的股票池
stock_pool = get_stocks_at_date('2020-01-01')  # 包含后来退市的股票
```

### 3. 过拟合

**❌ 常见错误**:

```python
# 错误: 使用过多特征和过长的训练时间
features = calculate_features(stock_pool, market_data)  # 500+ 特征
model.fit(features, labels, epochs=1000)  # 过度训练

# 正确: 特征选择和早停
features = select_top_features(features, k=50)  # 只使用 Top 50 特征
model.fit(features, labels, early_stopping_rounds=50)  # 早停
```

### 4. 数据对齐问题

**❌ 常见错误**:

```python
# 错误: 直接拼接 DataFrame
features = pd.concat([alpha_features, tech_features], axis=1)  # 可能不对齐

# 正确: 使用 join 确保对齐
features = alpha_features.join(tech_features, how='inner')
```

---

## 检查清单

### 回测前检查

- [ ] 数据完整性: 是否有缺失值？
- [ ] 时间对齐: 特征和标签是否对齐？
- [ ] 幸存者偏差: 是否使用了历史时点的股票池？
- [ ] 未来信息: 是否使用了未来信息？
- [ ] 交易成本: 是否包含了所有交易成本？
- [ ] A 股约束: 是否考虑了涨跌停、T+1？

### 策略上线前检查

- [ ] 单元测试: 所有策略是否有单元测试？
- [ ] 参数验证: 是否验证了参数的合理性？
- [ ] 异常处理: 是否处理了异常情况？
- [ ] 日志记录: 是否记录了关键操作？
- [ ] 性能测试: 是否通过了性能测试？

---

## 相关文档

- [架构详解](../architecture/overview.md)
- [机器学习系统](../ml/README.md)
- [API 参考](../api/reference.md)

---

**文档版本**: v5.1.0
**最后更新**: 2026-02-07
