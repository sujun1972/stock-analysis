# 策略层文档 (Strategy Layer)

**文档版本**: v1.0.0
**最后更新**: 2026-02-08
**适用版本**: Core v5.2.0+

---

## 目录

- [概述](#概述)
- [架构设计](#架构设计)
- [策略类型](#策略类型)
- [快速开始](#快速开始)
- [核心组件](#核心组件)
- [自定义策略](#自定义策略)
- [策略组合](#策略组合)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

---

## 概述

策略层是 Stock-Analysis Core 系统的核心模块之一，负责生成交易信号和股票评分。策略层提供了灵活、可扩展的框架，支持多种交易策略的实现和组合。

### 核心职责

1. **信号生成**: 根据市场数据和指标生成买入/卖出/持有信号
2. **股票评分**: 对股票池中的股票进行打分排序
3. **股票过滤**: 过滤不符合条件的股票(如ST股、流动性不足等)
4. **仓位管理**: 计算持仓权重分配
5. **策略组合**: 支持多策略组合和信号融合

### 设计理念

- **职责清晰**: 策略只负责信号生成，不涉及交易执行
- **高度解耦**: 与回测引擎、风控层完全解耦
- **易于扩展**: 通过继承 `BaseStrategy` 快速实现自定义策略
- **类型安全**: 完整的类型提示和接口约束
- **可组合性**: 支持多策略加权组合

---

## 架构设计

### 类层次结构

```
BaseStrategy (抽象基类)
├── MomentumStrategy (动量策略)
├── MeanReversionStrategy (均值回归策略)
├── MultiFactorStrategy (多因子策略)
└── [自定义策略]

StrategyCombiner (策略组合器)
SignalGenerator (信号生成工具)
```

### 数据流

```
输入数据
  ├── prices: 价格DataFrame
  ├── features: 特征DataFrame (可选)
  └── volumes: 成交量DataFrame (可选)
         ↓
    策略处理
  ├── 1. 计算指标/因子
  ├── 2. 计算股票评分
  ├── 3. 生成交易信号
  ├── 4. 过滤股票
  └── 5. 验证信号
         ↓
输出信号
  └── signals: 信号DataFrame
      (1=买入, 0=持有, -1=卖出)
```

### 核心接口

所有策略必须实现两个核心方法:

```python
class BaseStrategy(ABC):
    @abstractmethod
    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """生成交易信号"""
        pass

    @abstractmethod
    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """计算股票评分"""
        pass
```

---

## 策略类型

### 1. 动量策略 (MomentumStrategy)

**原理**: 买入近期强势股票，持有一段时间后卖出

**适用场景**:
- 趋势性行情
- 市场整体上涨
- 中短期交易

**核心参数**:
- `lookback_period`: 动量计算回看期(默认20天)
- `top_n`: 每期选择前N只股票(默认50只)
- `holding_period`: 持仓期(默认5天)
- `use_log_return`: 是否使用对数收益率(默认False)
- `filter_negative`: 是否过滤负动量股票(默认True)

**使用示例**:
```python
from core.strategies import MomentumStrategy

config = {
    'lookback_period': 20,
    'top_n': 30,
    'holding_period': 5,
    'filter_negative': True
}

strategy = MomentumStrategy('MOM20', config)
signals = strategy.generate_signals(prices, volumes=volumes)
```

**风险提示**:
- 震荡市场可能频繁止损
- 追高风险
- 转势时可能出现较大回撤

---

### 2. 均值回归策略 (MeanReversionStrategy)

**原理**: 买入短期超跌股票，等待价格回归均线后卖出

**适用场景**:
- 震荡市场
- 个股短期超买超卖
- 均值回归明显的股票

**核心参数**:
- `lookback_period`: 均线计算周期(默认20天)
- `z_score_threshold`: Z-score阈值(默认-2.0)
- `top_n`: 每期选择前N只股票
- `holding_period`: 持仓期
- `use_bollinger`: 是否使用布林带(默认False)

**使用示例**:
```python
from core.strategies import MeanReversionStrategy

config = {
    'lookback_period': 20,
    'z_score_threshold': -2.0,
    'top_n': 30,
    'holding_period': 5
}

strategy = MeanReversionStrategy('MR20', config)
signals = strategy.generate_signals(prices, volumes=volumes)
```

**指标说明**:
- **Z-score**: (当前价 - 移动平均) / 标准差
  - Z-score < -2.0: 严重超跌
  - Z-score > 2.0: 严重超买
- **布林带位置**: (当前价 - 下轨) / (上轨 - 下轨)
  - 接近0: 触及下轨(超卖)
  - 接近1: 触及上轨(超买)

**风险提示**:
- 趋势市场可能持续下跌
- 价值陷阱(基本面恶化导致的下跌)
- 需要设置严格止损

---

### 3. 多因子策略 (MultiFactorStrategy)

**原理**: 结合多个Alpha因子进行选股

**适用场景**:
- 所有市场环境
- 分散单因子风险
- 提高稳定性

**核心参数**:
- `factors`: 因子列表 ['MOM20', 'REV5', 'VOLATILITY20']
- `weights`: 因子权重 [0.4, 0.3, 0.3]
- `normalize_method`: 标准化方法 ('rank'/'zscore'/'minmax')
- `neutralize`: 是否行业中性化(默认False)
- `min_factor_coverage`: 最少需要的因子覆盖率(默认0.8)

**使用示例**:
```python
from core.strategies import MultiFactorStrategy

config = {
    'factors': ['MOM20', 'REV5', 'VOLATILITY20'],
    'weights': [0.4, 0.3, 0.3],
    'normalize_method': 'rank',
    'top_n': 50,
    'holding_period': 5
}

strategy = MultiFactorStrategy('MultiF', config)
signals = strategy.generate_signals(prices, features=features_df)
```

**标准化方法**:
- `rank`: 排名百分位(0-1) - 推荐
- `zscore`: Z-score标准化
- `minmax`: Min-Max归一化(0-1)

**优势**:
- 因子分散，风险降低
- 可以capture多种市场特征
- 可调整因子权重适应不同市场

---

## 快速开始

### 基础使用流程

```python
from core.strategies import MomentumStrategy
from core.backtest import BacktestEngine
from core.data import load_market_data

# Step 1: 准备数据
stock_pool = ['600000.SH', '000001.SZ', '600036.SH']
market_data = load_market_data(
    stock_codes=stock_pool,
    start_date='2023-01-01',
    end_date='2024-12-31'
)

prices = market_data['prices']
volumes = market_data['volumes']

# Step 2: 创建策略
config = {
    'lookback_period': 20,
    'top_n': 30,
    'holding_period': 5
}
strategy = MomentumStrategy('MOM20', config)

# Step 3: 生成信号
signals = strategy.generate_signals(prices, volumes=volumes)

# Step 4: 回测
engine = BacktestEngine(
    initial_capital=1000000,
    commission_rate=0.0003
)

results = strategy.backtest(engine, prices)

# Step 5: 分析结果
print(f"总收益率: {results['total_return']:.2%}")
print(f"夏普比率: {results['sharpe_ratio']:.2f}")
print(f"最大回撤: {results['max_drawdown']:.2%}")
```

---

## 核心组件

### 1. BaseStrategy (策略基类)

**职责**: 定义所有策略必须遵循的接口和通用功能

**核心方法**:

| 方法 | 类型 | 说明 |
|------|------|------|
| `generate_signals()` | 抽象方法 | 生成交易信号 |
| `calculate_scores()` | 抽象方法 | 计算股票评分 |
| `filter_stocks()` | 可选方法 | 过滤不符合条件的股票 |
| `validate_signals()` | 可选方法 | 验证信号有效性 |
| `get_position_weights()` | 可选方法 | 计算持仓权重 |
| `backtest()` | 便捷方法 | 执行回测 |

**配置参数**:

```python
@dataclass
class StrategyConfig:
    # 基础参数
    name: str = "BaseStrategy"
    description: str = ""

    # 选股参数
    top_n: int = 50
    min_stocks: int = 10
    max_stocks: int = 100

    # 持仓参数
    holding_period: int = 5
    rebalance_freq: str = 'W'

    # 过滤参数
    min_price: float = 1.0
    max_price: float = 1000.0
    min_volume: float = 1000000

    # 风控参数
    max_position_pct: float = 0.2
    stop_loss_pct: float = -0.1
    take_profit_pct: float = 0.3

    # 自定义参数
    custom_params: Dict[str, Any] = field(default_factory=dict)
```

---

### 2. SignalGenerator (信号生成器)

**职责**: 提供通用的信号生成工具函数

**信号类型**:
```python
class SignalType(Enum):
    BUY = 1      # 买入信号
    HOLD = 0     # 持有信号
    SELL = -1    # 卖出信号
```

**核心方法**:

#### 2.1 阈值信号
```python
SignalGenerator.generate_threshold_signals(
    scores: pd.DataFrame,
    buy_threshold: float,
    sell_threshold: Optional[float] = None
) -> Response
```

**用途**: 基于评分阈值生成信号
**规则**:
- 评分 > buy_threshold → 买入
- 评分 < sell_threshold → 卖出

#### 2.2 排名信号
```python
SignalGenerator.generate_rank_signals(
    scores: pd.DataFrame,
    top_n: int,
    bottom_n: Optional[int] = None
) -> Response
```

**用途**: 基于评分排名生成信号
**规则**:
- 排名前top_n → 买入
- 排名后bottom_n → 卖出(如果指定)

#### 2.3 交叉信号
```python
SignalGenerator.generate_crossover_signals(
    fast_line: pd.DataFrame,
    slow_line: pd.DataFrame
) -> Response
```

**用途**: 基于均线交叉生成信号
**规则**:
- 快线上穿慢线 → 买入
- 快线下穿慢线 → 卖出

---

### 3. StrategyCombiner (策略组合器)

**职责**: 组合多个策略的信号

**组合方法**:

#### 3.1 加权组合 (weighted)
```python
combiner = StrategyCombiner(
    strategies=[strategy1, strategy2],
    weights=[0.6, 0.4]
)

combined_signals = combiner.combine(
    prices=prices,
    method='weighted'
)
```

**规则**:
- 综合信号 = Σ(权重i × 策略信号i)
- 超过阈值(默认0.5)则买入

#### 3.2 投票组合 (voting)
```python
combined_signals = combiner.combine(
    prices=prices,
    method='voting',
    threshold=0.5  # 至少50%策略同意
)
```

**规则**:
- 统计各策略的买入/卖出信号
- 超过threshold比例的策略同意才生成信号

#### 3.3 交集组合 (intersection)
```python
combined_signals = combiner.combine(
    prices=prices,
    method='intersection'
)
```

**规则**:
- 只有所有策略都同意才生成买入信号
- 适合保守型组合

---

## 自定义策略

### 实现步骤

#### Step 1: 继承 BaseStrategy
```python
from core.strategies.base_strategy import BaseStrategy
from typing import Optional, Dict, Any
import pandas as pd

class MyCustomStrategy(BaseStrategy):
    def __init__(self, name: str, config: Dict[str, Any]):
        # 设置默认参数
        default_config = {
            'param1': 10,
            'param2': 20,
            'top_n': 50,
            'holding_period': 5
        }
        default_config.update(config)

        super().__init__(name, default_config)

        # 提取策略特有参数
        self.param1 = self.config.custom_params.get('param1', 10)
        self.param2 = self.config.custom_params.get('param2', 20)
```

#### Step 2: 实现 calculate_scores()
```python
    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """计算股票评分"""
        # 1. 计算指标
        indicator = self._calculate_indicator(prices)

        # 2. 获取指定日期的评分
        if date is None:
            date = indicator.index[-1]

        scores = indicator.loc[date]

        # 3. 过滤不符合条件的股票
        scores[scores < 0] = np.nan

        return scores
```

#### Step 3: 实现 generate_signals()
```python
    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """生成交易信号"""
        from core.strategies.signal_generator import SignalGenerator

        # 1. 计算评分
        scores = self._calculate_scores_for_all_dates(prices, features)

        # 2. 生成排名信号
        signals_response = SignalGenerator.generate_rank_signals(
            scores=scores,
            top_n=self.config.top_n
        )

        if not signals_response.is_success():
            raise ValueError(f"信号生成失败: {signals_response.error}")

        signals = signals_response.data

        # 3. 过滤股票
        if volumes is not None:
            for date in signals.index:
                try:
                    valid_stocks = self.filter_stocks(prices, volumes, date)
                    invalid_stocks = [s for s in signals.columns if s not in valid_stocks]
                    signals.loc[date, invalid_stocks] = 0
                except:
                    pass

        # 4. 验证信号
        signals = self.validate_signals(signals)

        return signals
```

#### Step 4: 实现辅助方法(可选)
```python
    def _calculate_indicator(self, prices: pd.DataFrame) -> pd.DataFrame:
        """计算自定义指标"""
        # 实现你的指标计算逻辑
        indicator = prices.pct_change(self.param1) * 100
        return indicator

    def _calculate_scores_for_all_dates(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """计算所有日期的评分"""
        scores_dict = {}
        for date in prices.index:
            scores = self.calculate_scores(prices, features, date)
            scores_dict[date] = scores

        return pd.DataFrame(scores_dict).T
```

### 完整示例

```python
"""
自定义波动率突破策略
"""
from core.strategies.base_strategy import BaseStrategy
from core.strategies.signal_generator import SignalGenerator
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

class VolatilityBreakoutStrategy(BaseStrategy):
    """
    波动率突破策略

    原理: 买入突破近期波动率上限的股票
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        default_config = {
            'lookback_period': 20,
            'std_multiplier': 2.0,
            'top_n': 30,
            'holding_period': 5
        }
        default_config.update(config)
        super().__init__(name, default_config)

        self.lookback_period = self.config.custom_params.get('lookback_period', 20)
        self.std_multiplier = self.config.custom_params.get('std_multiplier', 2.0)

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """计算突破强度"""
        # 计算移动平均和标准差
        ma = prices.rolling(window=self.lookback_period).mean()
        std = prices.rolling(window=self.lookback_period).std()

        # 计算上轨
        upper_band = ma + self.std_multiplier * std

        # 计算突破强度 = (当前价 - 上轨) / 上轨
        breakout_strength = (prices - upper_band) / upper_band * 100

        if date is None:
            date = breakout_strength.index[-1]

        scores = breakout_strength.loc[date]

        # 只保留正突破
        scores[scores < 0] = np.nan

        return scores

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """生成交易信号"""
        # 计算所有日期的评分
        ma = prices.rolling(window=self.lookback_period).mean()
        std = prices.rolling(window=self.lookback_period).std()
        upper_band = ma + self.std_multiplier * std
        scores = (prices - upper_band) / upper_band * 100

        # 过滤负值
        scores[scores < 0] = np.nan

        # 生成排名信号
        signals_response = SignalGenerator.generate_rank_signals(
            scores=scores,
            top_n=self.config.top_n
        )

        if not signals_response.is_success():
            raise ValueError(f"信号生成失败: {signals_response.error}")

        signals = signals_response.data

        # 过滤和验证
        if volumes is not None:
            for date in signals.index:
                try:
                    valid_stocks = self.filter_stocks(prices, volumes, date)
                    invalid_stocks = [s for s in signals.columns if s not in valid_stocks]
                    signals.loc[date, invalid_stocks] = 0
                except:
                    pass

        signals = self.validate_signals(signals)

        return signals

# 使用示例
if __name__ == "__main__":
    config = {
        'lookback_period': 20,
        'std_multiplier': 2.0,
        'top_n': 30,
        'holding_period': 5
    }

    strategy = VolatilityBreakoutStrategy('VolBreak20', config)
    signals = strategy.generate_signals(prices, volumes=volumes)
```

---

## 策略组合

### 为什么要组合策略?

1. **分散风险**: 单一策略可能在某些市场环境下失效
2. **提高稳定性**: 多策略组合可以平滑收益曲线
3. **capture多种机会**: 不同策略适合不同市场特征
4. **降低回撤**: 策略之间的对冲效应

### 组合方法对比

| 方法 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **加权组合** | 灵活，可调整权重 | 需要优化权重 | 通用场景 |
| **投票组合** | 简单，易理解 | 权重不灵活 | 保守型组合 |
| **交集组合** | 信号质量高 | 信号数量少 | 高质量选股 |
| **并集组合** | 信号数量多 | 可能包含噪音 | 积极型组合 |

### 组合示例

```python
from core.strategies import (
    MomentumStrategy,
    MeanReversionStrategy,
    MultiFactorStrategy,
    StrategyCombiner
)

# 1. 创建多个策略
strategies = []

# 动量策略
strategies.append(MomentumStrategy('MOM20', {
    'lookback_period': 20,
    'top_n': 50,
    'holding_period': 5
}))

# 均值回归策略
strategies.append(MeanReversionStrategy('MR15', {
    'lookback_period': 15,
    'z_score_threshold': -1.5,
    'top_n': 50,
    'holding_period': 5
}))

# 多因子策略
strategies.append(MultiFactorStrategy('MultiF', {
    'factors': ['MOM20', 'REV5', 'VOLATILITY20'],
    'weights': [0.4, 0.3, 0.3],
    'top_n': 50,
    'holding_period': 5
}))

# 2. 创建组合器
combiner = StrategyCombiner(
    strategies=strategies,
    weights=[0.4, 0.3, 0.3]  # 策略权重
)

# 3. 生成组合信号
combined_signals = combiner.combine(
    prices=prices,
    features=features,
    volumes=volumes,
    method='weighted'
)

# 4. 回测组合策略
engine = BacktestEngine(initial_capital=1000000)
results = engine.backtest_long_only(
    signals=combined_signals,
    prices=prices,
    top_n=50,
    holding_period=5
)

# 5. 分析策略一致性
signals_list = combiner.generate_individual_signals(
    prices,
    features=features,
    volumes=volumes
)
analysis = combiner.analyze_agreement(signals_list)

print(f"各策略买入信号数: {analysis['buy_counts']}")
print(f"平均相关性: {analysis['avg_correlation']:.3f}")
print(f"一致性分数: {analysis['consensus_score']:.3f}")
```

---

## 最佳实践

### 1. 策略设计

#### 单一职责
```python
# ✅ Good: 策略只负责信号生成
class GoodStrategy(BaseStrategy):
    def generate_signals(self, prices, **kwargs):
        scores = self._calculate_scores(prices)
        return SignalGenerator.generate_rank_signals(scores, self.config.top_n)

# ❌ Bad: 策略包含回测逻辑
class BadStrategy(BaseStrategy):
    def generate_signals_and_backtest(self, prices, **kwargs):
        signals = self._generate_signals(prices)
        # ❌ 不要在策略中执行回测
        results = self._run_backtest(signals, prices)
        return signals, results
```

#### 参数配置化
```python
# ✅ Good: 所有参数通过config传入
config = {
    'lookback_period': 20,
    'threshold': 0.05,
    'top_n': 50
}
strategy = MomentumStrategy('MOM20', config)

# ❌ Bad: 硬编码参数
class BadStrategy(BaseStrategy):
    def __init__(self, name, config):
        super().__init__(name, config)
        self.lookback_period = 20  # ❌ 硬编码
        self.threshold = 0.05      # ❌ 硬编码
```

### 2. 信号生成

#### 使用SignalGenerator
```python
# ✅ Good: 使用统一的信号生成器
from core.strategies.signal_generator import SignalGenerator

signals_response = SignalGenerator.generate_rank_signals(
    scores=scores,
    top_n=self.config.top_n
)

if signals_response.is_success():
    signals = signals_response.data
else:
    raise ValueError(f"信号生成失败: {signals_response.error}")

# ❌ Bad: 手动实现信号生成
top_stocks = scores.nlargest(self.config.top_n)
signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)
# ... 复杂的信号生成逻辑
```

#### 信号验证
```python
# ✅ Good: 总是验证信号
signals = strategy.generate_signals(prices)
signals = strategy.validate_signals(signals)  # 验证

# ✅ Good: 过滤无效股票
if volumes is not None:
    for date in signals.index:
        valid_stocks = strategy.filter_stocks(prices, volumes, date)
        invalid_stocks = [s for s in signals.columns if s not in valid_stocks]
        signals.loc[date, invalid_stocks] = 0
```

### 3. 性能优化

#### 向量化计算
```python
# ✅ Good: 向量化
momentum = prices.pct_change(20) * 100

# ❌ Bad: 循环计算
momentum = pd.DataFrame()
for stock in prices.columns:
    momentum[stock] = prices[stock].pct_change(20) * 100
```

#### 缓存结果
```python
class OptimizedStrategy(BaseStrategy):
    def __init__(self, name, config):
        super().__init__(name, config)
        self._indicator_cache = {}  # 缓存指标计算结果

    def _get_indicator(self, prices):
        cache_key = prices.index[-1]
        if cache_key not in self._indicator_cache:
            self._indicator_cache[cache_key] = self._calculate_indicator(prices)
        return self._indicator_cache[cache_key]
```

### 4. 错误处理

```python
# ✅ Good: 完善的错误处理
def generate_signals(self, prices, **kwargs):
    try:
        if prices.empty:
            logger.warning("价格数据为空")
            return pd.DataFrame()

        # 检查数据长度
        if len(prices) < self.lookback_period:
            logger.warning(f"数据长度不足: {len(prices)} < {self.lookback_period}")
            return pd.DataFrame(0, index=prices.index, columns=prices.columns)

        # 生成信号
        signals = self._generate_signals_internal(prices)

        return signals

    except Exception as e:
        logger.error(f"信号生成失败: {e}")
        raise
```

### 5. 日志记录

```python
# ✅ Good: 适度的日志记录
from loguru import logger

def generate_signals(self, prices, **kwargs):
    logger.info(f"生成{self.name}策略信号...")

    signals = self._generate_signals_internal(prices)

    n_buy = (signals == 1).sum().sum()
    logger.info(f"信号生成完成，买入信号数: {n_buy}")

    return signals

# ❌ Bad: 过多或过少的日志
def generate_signals(self, prices, **kwargs):
    # ❌ 没有任何日志
    signals = self._generate_signals_internal(prices)
    return signals

def generate_signals(self, prices, **kwargs):
    # ❌ 日志过多
    logger.info("开始生成信号")
    logger.debug(f"价格数据形状: {prices.shape}")
    logger.debug(f"配置: {self.config}")
    for date in prices.index:
        logger.debug(f"处理日期: {date}")
        # ...
```

---

## 常见问题

### Q1: 如何选择合适的策略?

**A**: 根据市场环境和投资目标选择:

| 市场环境 | 推荐策略 | 理由 |
|---------|---------|------|
| 趋势上涨 | 动量策略 | 追踪强势股 |
| 震荡市场 | 均值回归策略 | 捕捉超跌反弹 |
| 不确定 | 多因子策略 | 分散风险 |
| 所有环境 | 策略组合 | 平滑收益 |

### Q2: 策略信号和回测引擎如何配合?

**A**: 策略只负责生成信号，回测引擎负责执行:

```python
# 策略: 生成信号
signals = strategy.generate_signals(prices)

# 回测引擎: 执行交易
engine = BacktestEngine(initial_capital=1000000)
results = engine.backtest_long_only(
    signals=signals,
    prices=prices,
    top_n=50,
    holding_period=5
)
```

### Q3: 如何处理数据缺失?

**A**: 在 `calculate_scores()` 中过滤:

```python
def calculate_scores(self, prices, features=None, date=None):
    # 计算指标
    indicator = self._calculate_indicator(prices)

    if date is None:
        date = indicator.index[-1]

    scores = indicator.loc[date]

    # 过滤缺失值
    scores = scores.dropna()

    # 或者设置为NaN
    scores[scores.isna()] = np.nan

    return scores
```

### Q4: 如何进行参数优化?

**A**: 使用网格搜索:

```python
from core.optimization import GridSearchCV

# 定义参数网格
param_grid = {
    'lookback_period': [10, 20, 30],
    'top_n': [30, 50, 70],
    'holding_period': [3, 5, 10]
}

# 网格搜索
optimizer = GridSearchCV(
    strategy_class=MomentumStrategy,
    param_grid=param_grid,
    scoring='sharpe_ratio'
)

best_params = optimizer.fit(prices, volumes)
print(f"最优参数: {best_params}")
```

### Q5: 多因子策略需要什么格式的特征?

**A**: 特征DataFrame的格式:

```python
# 方式1: 简单列索引 (推荐)
# columns = stock_codes
# 每列是一个股票的某个因子值
features = pd.DataFrame({
    '600000.SH': [...],  # 该股票的因子值
    '000001.SZ': [...],
    ...
}, index=dates)

# 方式2: MultiIndex列
# columns = MultiIndex[(factor, stock)]
features = pd.DataFrame(
    columns=pd.MultiIndex.from_product([
        ['MOM20', 'REV5', 'VOLATILITY20'],  # 因子
        stock_codes  # 股票
    ]),
    index=dates
)
```

### Q6: 如何实现行业中性化?

**A**: 在 `MultiFactorStrategy` 中实现:

```python
def neutralize_by_industry(
    self,
    scores: pd.Series,
    industry_mapping: Dict[str, str]
) -> pd.Series:
    """
    行业中性化

    Args:
        scores: 原始评分
        industry_mapping: {stock_code: industry}

    Returns:
        中性化后的评分
    """
    neutralized = pd.Series(index=scores.index, dtype=float)

    # 按行业分组
    for industry in set(industry_mapping.values()):
        industry_stocks = [
            s for s, ind in industry_mapping.items()
            if ind == industry and s in scores.index
        ]

        if len(industry_stocks) > 0:
            industry_scores = scores[industry_stocks]
            # Z-score标准化（行业内）
            mean = industry_scores.mean()
            std = industry_scores.std()
            neutralized[industry_stocks] = (industry_scores - mean) / (std + 1e-8)

    return neutralized
```

### Q7: 策略组合的权重如何确定?

**A**: 几种常见方法:

```python
# 方法1: 等权重
weights = [1/3, 1/3, 1/3]

# 方法2: 根据历史夏普比率
sharpe_ratios = [1.5, 1.2, 1.8]
weights = np.array(sharpe_ratios) / sum(sharpe_ratios)

# 方法3: 最大夏普组合(马科维茨优化)
from core.optimization import optimize_portfolio_weights
weights = optimize_portfolio_weights(
    strategies=strategies,
    prices=prices,
    method='max_sharpe'
)
```

### Q8: 如何处理ST股票?

**A**: 在 `filter_stocks()` 中过滤:

```python
def filter_stocks(self, prices, volumes=None, date=None):
    """过滤ST股票"""
    valid_stocks = super().filter_stocks(prices, volumes, date)

    # 假设ST股票价格都很低
    if date is None:
        date = prices.index[-1]

    current_prices = prices.loc[date]

    # 过滤价格低于1元的股票（可能是ST）
    valid_stocks = [
        s for s in valid_stocks
        if current_prices[s] >= 1.0
    ]

    return valid_stocks
```

---

## 相关链接

- **回测引擎文档**: [docs/backtest/README.md](../backtest/README.md)
- **特征工程文档**: [docs/features/README.md](../features/README.md)
- **机器学习文档**: [docs/ml/README.md](../ml/README.md)
- **API参考**: [docs/api/reference.md](../api/reference.md)

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0.0 | 2026-02-08 | 初始版本，完整策略层文档 |

---

**维护团队**: Quant Team
**反馈渠道**: [GitHub Issues](https://github.com/your-org/stock-analysis/issues)
