# Core 项目：策略架构重构规划

**文档版本**: v3.0.0
**创建日期**: 2026-02-07
**更新日期**: 2026-02-07
**规划阶段**: Phase 4.0 - 架构优化

---

## 📋 改造目的

### 问题分析

当前三层架构（选股器 → 入场策略 → 退出策略）存在以下根本性问题：

#### 1. **职责混淆**
```
问题：选股器和入场策略职责重叠
- 选股器（MomentumSelector）：计算动量，选出Top 50
- 入场策略（ImmediateEntry）：立即买入这50只股票

本质上：选股器已经完成了"选股"，入场策略变成摆设
```

#### 2. **不支持卖空**
```
❌ 现有架构：只支持做多
   选股器 → 选出股票 → 买入 → 卖出

✅ 实际需求：需要支持多空策略
   入场策略 → 买入/卖空信号
   退出策略 → 平仓/反向开仓信号
```

#### 3. **ML模型被降级为"选股器"**
```
问题：ML模型预测收益率，但只用于选股

ML模型输出：
- 预测收益率：+8%（应该做多）
- 预测波动率：2.5%
- 置信度：85%

现有架构：只保留股票代码，丢弃预测信息
新架构：直接生成入场信号（买入权重、止损位）
```

#### 4. **止损管理分散**
```
问题：止损逻辑分散在各个退出策略中
- FixedStopLossExit：固定止损-5%
- ATRStopLossExit：动态止损
- 没有全局风控保护

新架构：统一由风控层管理止损
```

#### 5. **股票池管理不清晰**
```
问题：股票池应该由业务层（Backend）管理，而不是Core

现有：Core内部有选股器生成股票池
新架构：Backend提供股票池，Core专注策略执行
```

---

### 改造目标

**核心目标**：重构策略架构，支持多空交易，清晰的职责分工

**具体目标**：
1. ✅ 分离股票池管理（Backend）和策略执行（Core）
2. ✅ 支持多空交易（买入/卖空）
3. ✅ 入场策略直接生成交易信号（不再是"过滤器"）
4. ✅ 退出策略支持平仓和反向开仓
5. ✅ 统一的风控层管理止损
6. ✅ ML模型重新定位:
   - **MLSelector**: 独立选股工具（Backend调用）
   - **MLEntry/MLExit**: 入场/退出策略（回测引擎调用）
7. ✅ MLSelector 作为独立工具供 Backend 使用
8. ✅ 自由组合入场和退出策略

---

## 🎯 新架构设计

### 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    Backend 层                            │
│                  (股票池管理)                            │
├─────────────────────────────────────────────────────────┤
│  职责：                                                  │
│  · 用户选择股票                                          │
│  · 行业/市值/概念筛选                                    │
│  · 研报推荐                                              │
│  · 技术指标预筛选                                        │
│  · 基本面筛选                                            │
│  · 调用 MLSelector 进行智能选股                         │
│                                                          │
│  Backend 可选择性使用 MLSelector:                        │
│  1. 基础筛选(3000只) → MLSelector → Top 50              │
│  2. 或直接使用人工筛选的股票池                           │
│                                                          │
│  输出: stock_pool = ['600000.SH', '000001.SZ', ...]    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌═════════════════════════════════════════════════════════┐
║                    Core 层                               ║
║          (ML选股工具 + 策略引擎 + 回测引擎)              ║
└═════════════════════════════════════════════════════════┘

    ┌───────────────────────────────────────────┐
    │    0. ML选股工具 (独立工具)               │
    │       MLSelector (类似StarRanker)         │
    ├───────────────────────────────────────────┤
    │  定位: 独立的机器学习选股工具             │
    │  调用方: Backend (主动调用)               │
    │                                           │
    │  输入: 股票候选池 (全A股或行业池)         │
    │  输出: {                                  │
    │    '600000.SH': {                        │
    │      'score': 0.85,      # ML评分        │
    │      'rank': 1,          # 排名          │
    │      'expected_return': 0.08  # 预测收益 │
    │    },                                     │
    │    ...                                    │
    │  }                                       │
    │                                           │
    │  Backend可以:                             │
    │  1. 读取评分结果                          │
    │  2. 选择Top N作为stock_pool               │
    │  3. 或结合其他规则综合筛选                │
    └───────────────────────────────────────────┘
                           ↓
    ┌───────────────────────────────────────────┐
    │    1. 入场策略层 (核心)                   │
    │       EntryStrategy                       │
    ├───────────────────────────────────────────┤
    │  职责: 生成买入/卖空信号                  │
    │  输入: stock_pool (Backend提供)           │
    │  输出: {                                  │
    │    '600000.SH': {                        │
    │      'action': 'long',    # 买入         │
    │      'weight': 0.15       # 权重         │
    │    },                                     │
    │    '000001.SZ': {                        │
    │      'action': 'short',   # 卖空         │
    │      'weight': 0.10                      │
    │    }                                     │
    │  }                                       │
    │                                           │
    │  策略类型:                                │
    │  · 技术指标策略                           │
    │    - MomentumEntry (动量)                │
    │    - RSIOversoldEntry (RSI超卖)          │
    │    - MABreakoutEntry (均线突破)          │
    │  · ML入场策略                             │
    │    - MLEntry (预测收益率→多空信号)       │
    └───────────────────────────────────────────┘
                    ↓
    ┌───────────────────────────────────────────┐
    │    2. 入场策略层 (核心)                   │
    │       EntryStrategy                       │
    ├───────────────────────────────────────────┤
    │  职责: 生成买入/卖空信号                  │
    │  输入: stock_pool + market_data           │
    │  输出: {                                  │
    │    '600000.SH': {                        │
    │      'action': 'long',    # 买入         │
    │      'weight': 0.15       # 权重         │
    │    },                                     │
    │    '000001.SZ': {                        │
    │      'action': 'short',   # 卖空         │
    │      'weight': 0.10                      │
    │    }                                     │
    │  }                                       │
    │                                           │
    │  策略类型:                                │
    │  · 技术指标策略                           │
    │    - MomentumEntry (动量)                │
    │    - RSIOversoldEntry (RSI超卖)          │
    │    - MABreakoutEntry (均线突破)          │
    │  · ML入场策略                             │
    │    - MLEntry (预测收益率→多空信号)       │
    └───────────────────────────────────────────┘
                    ↓
    ┌───────────────────────────────────────────┐
    │    3. 退出策略层                          │
    │       ExitStrategy                        │
    ├───────────────────────────────────────────┤
    │  职责: 决定何时平仓或反向开仓              │
    │  输入: current_positions + market_data    │
    │  输出: {                                  │
    │    'close': ['600000.SH', ...],  # 平仓  │
    │    'reverse': {              # 反向开仓   │
    │      '000001.SZ': {                      │
    │        'action': 'short',               │
    │        'weight': 0.10                   │
    │      }                                   │
    │    }                                     │
    │  }                                       │
    │                                           │
    │  策略类型:                                │
    │  · 技术指标退出                           │
    │    - SignalReversalExit (信号反转)       │
    │    - TargetReachedExit (目标达成)        │
    │  · ML退出策略                             │
    │    - MLExit (预测反转→平仓/反向)         │
    │  · 时间退出                               │
    │    - TimeBasedExit (固定持仓期)          │
    └───────────────────────────────────────────┘
                    ↓
    ┌───────────────────────────────────────────┐
    │    4. 风控层                              │
    │       RiskManager                         │
    ├───────────────────────────────────────────┤
    │  职责: 止损管理 + 风险控制                │
    │                                           │
    │  止损检查:                                │
    │  · 单仓位止损 (亏损>10%强制平仓)         │
    │  · 组合止损 (总亏损>20%全部平仓)         │
    │  · 时间止损 (持仓>30天强制平仓)          │
    │                                           │
    │  风险控制:                                │
    │  · 杠杆限制 (最大1倍)                    │
    │  · 单仓位限制 (最大20%)                  │
    │  · 行业集中度限制 (单行业最大40%)        │
    │                                           │
    │  注: 风控层优先级最高，可强制平仓         │
    └───────────────────────────────────────────┘
                    ↓
    ┌───────────────────────────────────────────┐
    │    5. 回测引擎                            │
    │       BacktestEngine                      │
    ├───────────────────────────────────────────┤
    │  职责: 协调所有层的执行                   │
    │  · 按日期循环执行                         │
    │  · 先执行风控检查                         │
    │  · 再执行退出策略                         │
    │  · 最后执行入场策略                       │
    │  · 生成回测报告                           │
    └───────────────────────────────────────────┘
```

---

## 📐 核心类设计

### 0. ML选股工具 (MLSelector - 独立工具)

**定位**: 独立的机器学习选股工具（类似 StarRanker）

**调用方**: Backend 主动调用

**核心功能**:
- 对候选股票进行 ML 评分和排名
- 预测股票未来收益率
- 提供完整的评分结果供 Backend 使用

**使用场景**:
```
场景1: Backend 使用 MLSelector 智能选股
  全A股 (5000只)
  → Backend 基础筛选 (流动性、市值) → 3000只
  → 调用 MLSelector.rank() → 获取评分
  → Backend 选择 Top 50 作为 stock_pool
  → 传给 Core 回测引擎

场景2: Backend 不使用 MLSelector
  → Backend 直接人工筛选股票池
  → 传给 Core 回测引擎
```

#### 接口设计

```python
from typing import Dict, List
import pandas as pd

class MLSelector:
    """
    机器学习选股工具（独立工具，类似 StarRanker）

    定位:
    - 独立的选股工具，不是策略组件
    - Backend 主动调用，获取评分结果
    - Core 提供工具，Backend 决定如何使用

    与 MLEntry 的区别:
    - MLSelector: 选股工具（对股票评分排名）
    - MLEntry: 入场策略（生成多空交易信号）
    """

    def __init__(self, model_path: str, feature_config: Dict = None):
        """
        Args:
            model_path: 模型文件路径
            feature_config: 特征计算配置（可选）
        """
        self.model = self._load_model(model_path)
        self.feature_config = feature_config or self._default_feature_config()

    def rank(
        self,
        stock_pool: List[str],      # 候选股票池
        market_data: pd.DataFrame,  # 市场数据
        date: str,                  # 评分日期
        return_top_n: int = None    # 可选：只返回Top N
    ) -> Dict[str, Dict]:
        """
        对股票池进行 ML 评分和排名

        Args:
            stock_pool: 候选股票列表（如全A股、行业股票池）
            market_data: 市场数据（价格、成交量等）
            date: 评分日期
            return_top_n: 可选，只返回Top N（None表示返回全部）

        Returns:
            {
                '600000.SH': {
                    'score': 0.85,              # ML评分 (0-1)
                    'rank': 1,                  # 排名
                    'expected_return': 0.08,    # 预测收益率
                    'volatility': 0.025,        # 预测波动率
                    'confidence': 0.85,         # 预测置信度
                    'features': {...}           # 可选：特征值
                },
                '000001.SZ': {
                    'score': 0.78,
                    'rank': 2,
                    'expected_return': 0.06,
                    'volatility': 0.020,
                    'confidence': 0.80,
                    'features': {...}
                },
                ...
            }

        注意:
        - 返回完整的评分信息，供 Backend 灵活使用
        - Backend 可以根据 score、rank、expected_return 等进行筛选
        - Backend 可以结合其他规则（如行业平衡）综合决策
        """
        # 1. 计算特征（125+ Alpha因子库）
        features = self._calculate_features(stock_pool, market_data, date)

        # 2. ML模型预测
        predictions = self.model.predict(features)
        # predictions = DataFrame with columns:
        # ['expected_return', 'volatility', 'confidence']

        # 3. 计算综合评分
        scores = self._calculate_score(predictions)
        # score = sharpe_ratio * confidence
        # score = (expected_return / volatility) * confidence

        # 4. 排名
        ranked_results = {}
        sorted_stocks = scores.sort_values(ascending=False)

        for rank, (stock, score) in enumerate(sorted_stocks.items(), start=1):
            ranked_results[stock] = {
                'score': float(score),
                'rank': rank,
                'expected_return': float(predictions.loc[stock, 'expected_return']),
                'volatility': float(predictions.loc[stock, 'volatility']),
                'confidence': float(predictions.loc[stock, 'confidence']),
                'features': features.loc[stock].to_dict()  # 可选
            }

        # 5. 可选：只返回Top N
        if return_top_n:
            ranked_results = {
                stock: info
                for stock, info in ranked_results.items()
                if info['rank'] <= return_top_n
            }

        return ranked_results

    def _calculate_score(self, predictions: pd.DataFrame) -> pd.Series:
        """
        计算综合评分

        公式: score = sharpe_ratio * confidence
             = (expected_return / volatility) * confidence
        """
        sharpe = predictions['expected_return'] / predictions['volatility']
        scores = sharpe * predictions['confidence']
        return scores.clip(lower=0)  # 确保非负
```

#### Backend 使用示例

```python
# Backend 代码示例

from core.strategies.selectors import MLSelector

# 1. 初始化 MLSelector
ml_selector = MLSelector(model_path='models/lgbm_v1.pkl')

# 2. Backend 基础筛选
candidate_pool = backend_filter(
    universe='A股',
    min_market_cap=50_0000_0000,  # 50亿
    min_volume=100_0000,           # 日均成交量100万
    exclude_st=True
)
# candidate_pool = ['600000.SH', '000001.SZ', ..., 3000只]

# 3. 调用 MLSelector 评分
ml_results = ml_selector.rank(
    stock_pool=candidate_pool,
    market_data=market_data,
    date='2024-01-01',
    return_top_n=100  # 只返回Top 100
)

# 4. Backend 读取结果
for stock, info in ml_results.items():
    print(f"{stock}: score={info['score']:.2f}, "
          f"rank={info['rank']}, "
          f"expected_return={info['expected_return']:.2%}")

# 5. Backend 灵活筛选
# 选项1: 直接使用 Top 50
final_pool = [
    stock for stock, info in ml_results.items()
    if info['rank'] <= 50
]

# 选项2: 结合行业平衡
final_pool = backend_sector_balance(
    ml_results=ml_results,
    max_per_sector=10,
    total_count=50
)

# 选项3: 结合预期收益和置信度
final_pool = [
    stock for stock, info in ml_results.items()
    if info['expected_return'] > 0.05 and info['confidence'] > 0.7
]

# 6. 传给 Core 回测引擎
backtest_result = core_backtest_engine.run(
    stock_pool=final_pool,  # Backend 筛选好的股票池
    entry_strategy=MomentumEntry(),
    exit_strategy=TimeBasedExit(),
    ...
)
```

---

---

### 1. 入场策略 (EntryStrategy)

**职责**: 生成买入/卖空信号（包含权重、方向）

**与 MLSelector 的区别**:
- **MLSelector**: 选股工具，对股票评分排名（Backend 调用）
- **EntryStrategy**: 策略组件，生成交易信号（回测引擎调用）

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Literal
import pandas as pd

class EntryStrategy(ABC):
    """
    入场策略基类

    职责: 生成买入/卖空信号（包含权重、方向）
    """

    @abstractmethod
    def generate_signals(
        self,
        stock_pool: List[str],           # 股票池（可能经过MLSelector筛选）
        market_data: pd.DataFrame,       # 市场数据
        date: str                        # 当前日期
    ) -> Dict[str, Dict]:
        """
        生成入场信号

        Args:
            stock_pool: 候选股票列表
            market_data: 市场价格数据
            date: 当前日期

        Returns:
            {
                '600000.SH': {
                    'action': 'long',      # 'long' 或 'short'
                    'weight': 0.15         # 仓位权重 (0-1之间)
                },
                '000001.SZ': {
                    'action': 'short',
                    'weight': 0.10
                },
                ...
            }

        注意:
        - 所有权重之和应为1.0（代表100%仓位）
        - action只能是'long'或'short'
        - 策略内部需要归一化权重
        """
        pass
```

#### 1.1 技术指标入场策略

```python
class MomentumEntry(EntryStrategy):
    """
    动量入场策略

    逻辑:
    - 动量 > threshold → 做多
    - 动量 < -threshold → 做空
    - 权重与动量大小成正比
    """

    def __init__(self, lookback: int = 20, threshold: float = 0.10):
        self.lookback = lookback
        self.threshold = threshold

    def generate_signals(self, stock_pool, market_data, date):
        signals = {}

        for stock in stock_pool:
            momentum = market_data[stock].pct_change(self.lookback).loc[date]

            if momentum > self.threshold:
                signals[stock] = {
                    'action': 'long',
                    'weight': momentum
                }
            elif momentum < -self.threshold:
                signals[stock] = {
                    'action': 'short',
                    'weight': abs(momentum)
                }

        # 归一化权重
        total = sum(s['weight'] for s in signals.values())
        if total > 0:
            for stock in signals:
                signals[stock]['weight'] /= total

        return signals


class RSIOversoldEntry(EntryStrategy):
    """RSI超卖/超买入场策略"""

    def __init__(self, rsi_period: int = 14, oversold: float = 30, overbought: float = 70):
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, stock_pool, market_data, date):
        signals = {}

        for stock in stock_pool:
            rsi = self._calculate_rsi(market_data[stock], self.rsi_period).loc[date]

            if rsi < self.oversold:  # 超卖 → 做多
                signals[stock] = {
                    'action': 'long',
                    'weight': (self.oversold - rsi) / self.oversold
                }
            elif rsi > self.overbought:  # 超买 → 做空
                signals[stock] = {
                    'action': 'short',
                    'weight': (rsi - self.overbought) / (100 - self.overbought)
                }

        # 归一化权重
        total = sum(s['weight'] for s in signals.values())
        if total > 0:
            for stock in signals:
                signals[stock]['weight'] /= total

        return signals


class MABreakoutEntry(EntryStrategy):
    """均线突破入场策略"""

    def __init__(self, short_window: int = 5, long_window: int = 20):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, stock_pool, market_data, date):
        signals = {}

        for stock in stock_pool:
            prices = market_data[stock]
            short_ma = prices.rolling(self.short_window).mean()
            long_ma = prices.rolling(self.long_window).mean()

            current_idx = prices.index.get_loc(date)
            if current_idx < 1:
                continue
            prev_date = prices.index[current_idx - 1]

            # 金叉 → 做多
            if short_ma.loc[prev_date] <= long_ma.loc[prev_date] and \
               short_ma.loc[date] > long_ma.loc[date]:
                signals[stock] = {'action': 'long', 'weight': 1.0}

            # 死叉 → 做空
            elif short_ma.loc[prev_date] >= long_ma.loc[prev_date] and \
                 short_ma.loc[date] < long_ma.loc[date]:
                signals[stock] = {'action': 'short', 'weight': 1.0}

        # 归一化权重
        total = sum(s['weight'] for s in signals.values())
        if total > 0:
            for stock in signals:
                signals[stock]['weight'] /= total

        return signals
```

#### 1.2 ML入场策略

**与 MLSelector 的对比**:

| 对比项 | MLSelector | MLEntry |
|--------|-----------|---------|
| **定位** | 选股工具 | 入场策略 |
| **调用方** | Backend | 回测引擎 |
| **输入** | 大量候选股票(3000只) | 精选股票池(50只) |
| **输出** | 评分+排名 | 交易信号(多空+权重) |
| **用途** | 筛选股票 | 生成交易 |

```python
class MLEntry(EntryStrategy):
    """
    机器学习入场策略

    重新定位:
    - 不再是"选股器"
    - 直接生成入场信号（买入/卖空 + 权重）

    模型预测:
    - 预测收益率 > 0 → 做多
    - 预测收益率 < 0 → 做空
    - 权重 = 夏普比率 × 置信度
    """

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.7,
        top_long: int = 20,
        top_short: int = 10
    ):
        """
        Args:
            model_path: 模型文件路径
            confidence_threshold: 置信度阈值
            top_long: 最多做多多少只
            top_short: 最多做空多少只
        """
        self.model = self._load_model(model_path)
        self.confidence_threshold = confidence_threshold
        self.top_long = top_long
        self.top_short = top_short

    def generate_signals(self, stock_pool, market_data, date):
        # 1. 计算特征
        features = self._calculate_features(stock_pool, market_data, date)

        # 2. 模型预测
        predictions = self.model.predict(features)
        # predictions = {
        #     '600000.SH': {
        #         'expected_return': 0.08,    # 预测收益率
        #         'volatility': 0.025,        # 预测波动率
        #         'confidence': 0.85          # 置信度
        #     },
        #     ...
        # }

        # 3. 筛选做多候选
        long_candidates = {}
        for stock, pred in predictions.items():
            if pred['expected_return'] > 0 and pred['confidence'] > self.confidence_threshold:
                # 权重 = 夏普比率 × 置信度
                weight = (pred['expected_return'] / pred['volatility']) * pred['confidence']
                long_candidates[stock] = weight

        # 选出Top N
        long_candidates = dict(
            sorted(long_candidates.items(), key=lambda x: x[1], reverse=True)[:self.top_long]
        )

        # 4. 筛选做空候选
        short_candidates = {}
        for stock, pred in predictions.items():
            if pred['expected_return'] < 0 and pred['confidence'] > self.confidence_threshold:
                weight = (abs(pred['expected_return']) / pred['volatility']) * pred['confidence']
                short_candidates[stock] = weight

        # 选出Top N
        short_candidates = dict(
            sorted(short_candidates.items(), key=lambda x: x[1], reverse=True)[:self.top_short]
        )

        # 5. 合并信号
        signals = {}
        for stock, weight in long_candidates.items():
            signals[stock] = {'action': 'long', 'weight': weight}
        for stock, weight in short_candidates.items():
            signals[stock] = {'action': 'short', 'weight': weight}

        # 6. 归一化权重
        total = sum(s['weight'] for s in signals.values())
        if total > 0:
            for stock in signals:
                signals[stock]['weight'] /= total

        return signals
```

---

---

### 2. 退出策略 (ExitStrategy)

**职责**: 决定何时平仓或反向开仓

```python
from dataclasses import dataclass
from typing import List, Dict, Literal

@dataclass
class Position:
    """持仓信息"""
    stock_code: str                       # 股票代码
    action: Literal['long', 'short']      # 'long' 或 'short'
    entry_date: str                       # 入场日期
    entry_price: float                    # 入场价格
    shares: int                           # 持仓数量
    weight: float                         # 仓位权重
    unrealized_pnl: float                 # 浮动盈亏
    unrealized_pnl_pct: float             # 浮动盈亏百分比


class ExitStrategy(ABC):
    """
    退出策略基类

    职责: 决定何时平仓或反向开仓
    """

    @abstractmethod
    def generate_exit_signals(
        self,
        positions: Dict[str, Position],  # 当前持仓
        market_data: pd.DataFrame,
        date: str
    ) -> Dict[str, Any]:
        """
        生成退出信号

        Args:
            positions: 当前持仓字典 {股票代码: Position}
            market_data: 市场数据
            date: 当前日期

        Returns:
            {
                'close': ['600000.SH', '000001.SZ'],  # 需要平仓的股票
                'reverse': {                          # 需要反向开仓的股票
                    '600036.SH': {
                        'action': 'short',            # 反向操作
                        'weight': 0.10                # 新仓位权重
                    }
                }
            }

        注意:
        - 'close': 平仓（关闭当前持仓）
        - 'reverse': 反向开仓（平掉当前仓位 + 开反向新仓位）
        """
        pass
```

#### 2.1 技术指标退出策略

```python
class SignalReversalExit(ExitStrategy):
    """
    信号反转退出策略

    当技术指标给出反向信号时:
    - 平掉当前仓位
    - 开反向仓位
    """

    def __init__(self, indicator: str = 'momentum', lookback: int = 20):
        self.indicator = indicator
        self.lookback = lookback

    def generate_exit_signals(self, positions, market_data, date):
        close_list = []
        reverse_dict = {}

        for stock, position in positions.items():
            # 计算当前信号
            if self.indicator == 'momentum':
                current_signal = self._calculate_momentum_signal(
                    market_data[stock], date, self.lookback
                )

            # 检查是否反转
            if position.action == 'long' and current_signal == 'short':
                # 原来做多，现在信号变空 → 平仓 + 反向做空
                close_list.append(stock)
                reverse_dict[stock] = {
                    'action': 'short',
                    'weight': position.weight
                }

            elif position.action == 'short' and current_signal == 'long':
                # 原来做空，现在信号变多 → 平仓 + 反向做多
                close_list.append(stock)
                reverse_dict[stock] = {
                    'action': 'long',
                    'weight': position.weight
                }

            elif current_signal == 'neutral':
                # 信号消失 → 只平仓，不反向
                close_list.append(stock)

        return {
            'close': close_list,
            'reverse': reverse_dict
        }


class TargetReachedExit(ExitStrategy):
    """
    目标达成退出策略

    当达到预期收益目标时平仓
    """

    def __init__(self, take_profit_pct: float = 0.15):
        self.take_profit_pct = take_profit_pct

    def generate_exit_signals(self, positions, market_data, date):
        close_list = []

        for stock, position in positions.items():
            if position.unrealized_pnl_pct >= self.take_profit_pct:
                close_list.append(stock)

        return {
            'close': close_list,
            'reverse': {}  # 达到目标只平仓，不反向
        }


class TimeBasedExit(ExitStrategy):
    """时间退出策略"""

    def __init__(self, max_holding_days: int = 20):
        self.max_holding_days = max_holding_days

    def generate_exit_signals(self, positions, market_data, date):
        close_list = []

        for stock, position in positions.items():
            holding_days = (pd.Timestamp(date) - pd.Timestamp(position.entry_date)).days
            if holding_days >= self.max_holding_days:
                close_list.append(stock)

        return {
            'close': close_list,
            'reverse': {}
        }
```

#### 2.2 ML退出策略

```python
class MLExit(ExitStrategy):
    """
    机器学习退出策略

    根据ML模型重新预测，决定是否平仓或反向
    """

    def __init__(
        self,
        model_path: str,
        reversal_threshold: float = 0.05,
        confidence_threshold: float = 0.7
    ):
        self.model = self._load_model(model_path)
        self.reversal_threshold = reversal_threshold
        self.confidence_threshold = confidence_threshold

    def generate_exit_signals(self, positions, market_data, date):
        close_list = []
        reverse_dict = {}

        for stock, position in positions.items():
            # 重新预测该股票
            features = self._calculate_features(stock, market_data, date)
            prediction = self.model.predict(features)

            expected_return = prediction['expected_return']
            confidence = prediction['confidence']

            # 情况1: 持有多头，预测变为大幅下跌 → 平仓+做空
            if position.action == 'long' and \
               expected_return < -self.reversal_threshold and \
               confidence > self.confidence_threshold:
                close_list.append(stock)
                reverse_dict[stock] = {
                    'action': 'short',
                    'weight': position.weight
                }

            # 情况2: 持有空头，预测变为大幅上涨 → 平仓+做多
            elif position.action == 'short' and \
                 expected_return > self.reversal_threshold and \
                 confidence > self.confidence_threshold:
                close_list.append(stock)
                reverse_dict[stock] = {
                    'action': 'long',
                    'weight': position.weight
                }

            # 情况3: 预测收益接近0 → 只平仓
            elif abs(expected_return) < 0.01:
                close_list.append(stock)

        return {
            'close': close_list,
            'reverse': reverse_dict
        }
```

---

---

### 3. 风控层 (RiskManager)

**职责**: 止损管理 + 风险控制（优先级最高）

```python
class RiskManager:
    """
    风控层

    职责:
    - 止损管理（统一管理所有止损逻辑）
    - 风险控制（杠杆、仓位、集中度限制）

    注意:
    - 风控层优先级最高，可以强制平仓
    - 先于退出策略执行
    """

    def __init__(
        self,
        # 止损参数
        max_position_loss_pct: float = 0.10,    # 单仓位最大亏损10%
        max_portfolio_loss_pct: float = 0.20,   # 组合最大亏损20%
        max_holding_days: int = 30,             # 最长持仓30天

        # 风险控制参数
        max_leverage: float = 1.0,              # 最大杠杆1倍
        max_position_size: float = 0.20,        # 单仓位最大20%
        max_sector_concentration: float = 0.40   # 单行业最大40%
    ):
        self.max_position_loss_pct = max_position_loss_pct
        self.max_portfolio_loss_pct = max_portfolio_loss_pct
        self.max_holding_days = max_holding_days
        self.max_leverage = max_leverage
        self.max_position_size = max_position_size
        self.max_sector_concentration = max_sector_concentration

    def check_stop_loss(
        self,
        positions: Dict[str, Position],
        date: str
    ) -> List[str]:
        """
        检查止损条件

        Returns:
            需要强制平仓的股票列表
        """
        force_close = []

        # 1. 单仓位止损
        for stock, position in positions.items():
            if position.unrealized_pnl_pct < -self.max_position_loss_pct:
                force_close.append(stock)

        # 2. 时间止损
        for stock, position in positions.items():
            if stock in force_close:
                continue
            holding_days = (pd.Timestamp(date) - pd.Timestamp(position.entry_date)).days
            if holding_days > self.max_holding_days:
                force_close.append(stock)

        # 3. 组合止损（最严格）
        if positions:
            total_pnl_pct = sum(
                p.unrealized_pnl_pct * p.weight
                for p in positions.values()
            )
            if total_pnl_pct < -self.max_portfolio_loss_pct:
                # 全部平仓
                force_close = list(positions.keys())

        return force_close

    def check_entry_limits(
        self,
        new_signals: Dict[str, Dict],
        current_positions: Dict[str, Position],
        portfolio_value: float
    ) -> Dict[str, Dict]:
        """
        检查入场限制，调整新信号的权重

        Returns:
            调整后的信号
        """
        adjusted_signals = new_signals.copy()

        # 1. 单仓位限制
        for stock in adjusted_signals:
            if adjusted_signals[stock]['weight'] > self.max_position_size:
                adjusted_signals[stock]['weight'] = self.max_position_size

        # 2. 杠杆限制
        current_exposure = sum(p.weight for p in current_positions.values())
        new_exposure = sum(s['weight'] for s in adjusted_signals.values())
        total_exposure = current_exposure + new_exposure

        if total_exposure > self.max_leverage:
            # 按比例缩减新信号的权重
            scale_factor = (self.max_leverage - current_exposure) / new_exposure
            for stock in adjusted_signals:
                adjusted_signals[stock]['weight'] *= scale_factor

        return adjusted_signals
```

---

---

### 4. 回测引擎 (BacktestEngine)

**职责**: 协调所有层的执行

**重要说明**:
- MLSelector **不在**回测引擎中调用
- MLSelector 由 Backend 在回测前调用
- 回测引擎只接收 Backend 提供的最终 stock_pool

```python
class BacktestEngine:
    """
    回测引擎

    职责: 协调所有层的执行顺序
    执行顺序:
    1. 风控检查（止损）
    2. 退出策略（平仓/反向）
    3. 入场策略（新信号）
    4. 更新持仓

    注意:
    - MLSelector 由 Backend 调用，不在这里
    - stock_pool 是 Backend 筛选好的最终股票池
    """

    def __init__(
        self,
        entry_strategy: EntryStrategy,
        exit_strategy: ExitStrategy,
        risk_manager: RiskManager
    ):
        self.entry_strategy = entry_strategy
        self.exit_strategy = exit_strategy
        self.risk_manager = risk_manager

    def run(
        self,
        stock_pool: List[str],        # Backend提供的最终股票池（已经过MLSelector筛选）
        market_data: pd.DataFrame,
        start_date: str,
        end_date: str,
        initial_capital: float = 1000000.0
    ) -> BacktestResult:
        """
        运行回测

        Args:
            stock_pool: Backend提供的最终股票池
                       （可能经过MLSelector筛选，也可能是人工筛选）
            market_data: 市场数据
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金

        Returns:
            BacktestResult: 回测结果
        """
        # 初始化组合
        portfolio = Portfolio(initial_capital)
        dates = pd.date_range(start_date, end_date, freq='B')

        for date in dates:
            date_str = date.strftime('%Y-%m-%d')

            # 1. 风控检查: 止损（优先级最高）
            force_close = self.risk_manager.check_stop_loss(
                portfolio.positions, date_str
            )
            if force_close:
                portfolio.close_positions(force_close, market_data, date_str)

            # 2. 退出策略: 平仓或反向开仓
            exit_signals = self.exit_strategy.generate_exit_signals(
                portfolio.positions, market_data, date_str
            )

            # 2.1 平仓
            if exit_signals['close']:
                portfolio.close_positions(
                    exit_signals['close'], market_data, date_str
                )

            # 2.2 反向开仓
            if exit_signals['reverse']:
                reverse_signals = self.risk_manager.check_entry_limits(
                    exit_signals['reverse'],
                    portfolio.positions,
                    portfolio.total_value
                )
                portfolio.open_positions(reverse_signals, market_data, date_str)

            # 3. 入场策略: 新信号（使用Backend提供的stock_pool）
            entry_signals = self.entry_strategy.generate_signals(
                stock_pool, market_data, date_str
            )

            # 3.1 风控检查入场限制
            entry_signals = self.risk_manager.check_entry_limits(
                entry_signals,
                portfolio.positions,
                portfolio.total_value
            )

            # 3.2 开仓
            portfolio.open_positions(entry_signals, market_data, date_str)

            # 4. 更新组合价值
            portfolio.update_value(market_data, date_str)

        # 生成回测报告
        return self._generate_report(portfolio)
```

#### Backend-Core 完整调用流程

```python
# ============ Backend 代码 ============

from core.strategies.selectors import MLSelector
from core.backtest import BacktestEngine
from core.strategies.entries import MomentumEntry
from core.strategies.exits import TimeBasedExit
from core.risk import RiskManager

# Step 1: Backend 基础筛选
candidate_pool = backend.filter_stocks(
    min_market_cap=50_0000_0000,
    min_volume=100_0000,
    exclude_st=True
)
# candidate_pool = 3000只

# Step 2: Backend 调用 MLSelector（可选）
ml_selector = MLSelector(model_path='models/lgbm_v1.pkl')
ml_results = ml_selector.rank(
    stock_pool=candidate_pool,
    market_data=market_data,
    date='2024-01-01',
    return_top_n=50
)

# Step 3: Backend 获取最终股票池
final_stock_pool = [
    stock for stock, info in ml_results.items()
    if info['rank'] <= 50
]
# final_stock_pool = ['600000.SH', ..., 50只]

# Step 4: Backend 调用 Core 回测引擎
backtest_engine = BacktestEngine(
    entry_strategy=MomentumEntry(lookback=20),
    exit_strategy=TimeBasedExit(max_holding_days=20),
    risk_manager=RiskManager()
)

backtest_result = backtest_engine.run(
    stock_pool=final_stock_pool,  # Backend筛选好的股票池
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# Step 5: Backend 展示结果
backend.display_result(backtest_result)
```

---

## 🔍 MLSelector vs MLEntry vs 技术指标策略

### 核心区别对比

| 对比项 | MLSelector | MLEntry | MomentumEntry |
|--------|-----------|---------|---------------|
| **类型** | 选股工具 | 入场策略 | 入场策略 |
| **调用方** | Backend | 回测引擎 | 回测引擎 |
| **调用时机** | 回测前（准备股票池） | 回测中（每日生成信号） | 回测中（每日生成信号） |
| **输入规模** | 大量候选(3000只) | 精选池(50只) | 精选池(50只) |
| **输出内容** | 评分+排名 | 交易信号(多空+权重) | 交易信号(多空+权重) |
| **核心功能** | 筛选股票 | 生成交易 | 生成交易 |
| **决策依据** | ML模型预测 | ML模型预测 | 技术指标计算 |
| **是否多空** | N/A（只评分） | 支持 | 支持 |

### 使用场景对比

#### 场景1: 纯技术指标策略（不用ML）

```python
# Backend: 人工筛选股票池
stock_pool = ['600000.SH', '000001.SZ', ..., 50只]

# Core: 运行技术指标策略
backtest_engine = BacktestEngine(
    entry_strategy=MomentumEntry(lookback=20),  # 技术指标入场
    exit_strategy=TimeBasedExit(max_holding_days=20),
    risk_manager=RiskManager()
)

result = backtest_engine.run(
    stock_pool=stock_pool,  # 人工筛选的50只
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

#### 场景2: MLSelector选股 + 技术指标策略

```python
# Backend: 调用MLSelector智能选股
ml_selector = MLSelector(model_path='models/selector_v1.pkl')
ml_results = ml_selector.rank(
    stock_pool=candidate_pool,  # 3000只候选
    market_data=market_data,
    date='2024-01-01',
    return_top_n=50
)

stock_pool = [stock for stock, info in ml_results.items() if info['rank'] <= 50]

# Core: 运行技术指标策略
backtest_engine = BacktestEngine(
    entry_strategy=MomentumEntry(lookback=20),  # 技术指标入场
    exit_strategy=TimeBasedExit(max_holding_days=20),
    risk_manager=RiskManager()
)

result = backtest_engine.run(
    stock_pool=stock_pool,  # ML筛选的50只
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

#### 场景3: MLSelector选股 + MLEntry策略（双ML）

```python
# Backend: 调用MLSelector智能选股
ml_selector = MLSelector(model_path='models/selector_v1.pkl')
ml_results = ml_selector.rank(
    stock_pool=candidate_pool,  # 3000只候选
    market_data=market_data,
    date='2024-01-01',
    return_top_n=50
)

stock_pool = [stock for stock, info in ml_results.items() if info['rank'] <= 50]

# Core: 运行ML入场策略
backtest_engine = BacktestEngine(
    entry_strategy=MLEntry(model_path='models/entry_v1.pkl'),  # ML入场
    exit_strategy=MLExit(model_path='models/exit_v1.pkl'),     # ML退出
    risk_manager=RiskManager()
)

result = backtest_engine.run(
    stock_pool=stock_pool,  # ML筛选的50只
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

#### 场景4: 人工选股 + MLEntry策略

```python
# Backend: 人工筛选股票池（基本面分析）
stock_pool = ['600000.SH', '000001.SZ', ..., 30只]  # 精选蓝筹股

# Core: 运行ML入场策略
backtest_engine = BacktestEngine(
    entry_strategy=MLEntry(model_path='models/entry_v1.pkl'),  # ML入场
    exit_strategy=MLExit(model_path='models/exit_v1.pkl'),
    risk_manager=RiskManager()
)

result = backtest_engine.run(
    stock_pool=stock_pool,  # 人工筛选的30只
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

### 为什么需要 MLSelector？

**问题**: 为什么不直接用 MLEntry 既选股又生成信号？

**回答**: 职责分离 + 性能优化

| 方面 | MLSelector | MLEntry |
|------|-----------|---------|
| **处理规模** | 3000只 → 50只 | 50只 → 20只交易信号 |
| **调用频率** | 回测前1次 | 回测中每日调用 |
| **计算成本** | 高（3000只×125特征） | 低（50只×125特征） |
| **职责** | 粗筛（排除明显不好的） | 精选（生成具体交易） |
| **灵活性** | Backend可结合其他规则 | 专注策略逻辑 |

**举例说明**:

```python
# 如果没有 MLSelector，直接用 MLEntry
# ❌ 问题：每天都要对3000只股票计算特征+预测
for date in backtest_dates:  # 250天
    entry_signals = MLEntry.generate_signals(
        stock_pool=candidate_pool,  # 3000只
        market_data=market_data,
        date=date
    )
    # 计算量：250天 × 3000只 × 125特征 = 巨大

# ✅ 有 MLSelector：先筛选再策略
# Step 1: Backend 用 MLSelector 筛选1次
ml_results = MLSelector.rank(
    stock_pool=candidate_pool,  # 3000只
    date='2024-01-01'  # 只计算1次
)
stock_pool = top_50_from(ml_results)

# Step 2: 回测引擎每天只处理50只
for date in backtest_dates:  # 250天
    entry_signals = MLEntry.generate_signals(
        stock_pool=stock_pool,  # 50只
        market_data=market_data,
        date=date
    )
    # 计算量：250天 × 50只 × 125特征 = 合理
```

---

## 📂 文件结构

### 新文件结构

```
core/
├── src/
│   ├── strategies/
│   │   ├── selectors/                  # ML选股器（保留）
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # MLSelector基类
│   │   │   └── ml_selector.py         # ML选股器实现
│   │   │
│   │   ├── entries/                    # 入场策略（重构）
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # EntryStrategy基类
│   │   │   ├── momentum_entry.py      # 动量入场
│   │   │   ├── rsi_entry.py           # RSI入场
│   │   │   ├── ma_breakout_entry.py   # 均线突破入场
│   │   │   └── ml_entry.py            # ML入场策略
│   │   │
│   │   └── exits/                      # 退出策略（重构）
│   │       ├── __init__.py
│   │       ├── base.py                # ExitStrategy基类
│   │       ├── signal_reversal_exit.py # 信号反转退出
│   │       ├── target_reached_exit.py  # 目标达成退出
│   │       ├── time_based_exit.py      # 时间退出
│   │       └── ml_exit.py             # ML退出策略
│   │
│   ├── risk/                           # 风控层（新增）
│   │   ├── __init__.py
│   │   └── risk_manager.py            # 风控管理器
│   │
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── backtest_engine.py         # 回测引擎（重构）
│   │   ├── portfolio.py               # 组合管理
│   │   └── backtest_result.py         # 回测结果
│   │
│   └── models/
│       ├── __init__.py
│       ├── position.py                # Position数据类
│       └── signal.py                  # Signal数据类
│
└── tests/
    ├── unit/
    │   ├── test_selectors.py
    │   ├── test_entries.py
    │   ├── test_exits.py
    │   └── test_risk_manager.py
    └── integration/
        └── test_backtest_engine.py
```

### 删除的文件/目录

```
删除:
├── strategies/three_layer/           # 删除整个三层架构目录
│   ├── base/
│   │   └── strategy_composer.py      # 删除策略组合器
│   ├── selectors/
│   │   ├── momentum_selector.py      # 移动到entries/momentum_entry.py
│   │   └── value_selector.py         # 移动到entries/
│   ├── entries/
│   │   └── immediate_entry.py        # 删除（不再需要）
│   └── exits/
│       ├── fixed_stop_loss_exit.py   # 移动到risk/risk_manager.py
│       └── atr_stop_loss_exit.py     # 移动到risk/risk_manager.py
```

---

## 🔄 实施计划

### Phase 1: 数据结构设计（2天）

**目标**: 设计核心数据类

- [ ] 设计 `Position` 数据类
  ```python
  @dataclass
  class Position:
      stock_code: str
      action: Literal['long', 'short']
      entry_date: str
      entry_price: float
      shares: int
      weight: float
      unrealized_pnl: float
      unrealized_pnl_pct: float
  ```

- [ ] 设计 `Signal` 数据类
  ```python
  @dataclass
  class Signal:
      stock_code: str
      action: Literal['long', 'short']
      weight: float
      metadata: Dict[str, Any]
  ```

- [ ] 设计 `BacktestResult` 数据类

---

### Phase 2: 入场策略重构（5天）

**目标**: 重构入场策略，支持多空信号

- [ ] 重构 `EntryStrategy` 基类
  - 定义新的 `generate_signals()` 接口
  - 支持多空信号输出

- [ ] 迁移技术指标策略
  - [ ] `MomentumEntry` (从 MomentumSelector 改造)
  - [ ] `RSIOversoldEntry` (从 RSIOversoldEntry 改造)
  - [ ] `MABreakoutEntry` (从 MABreakoutEntry 改造)

- [ ] 实现 ML入场策略
  - [ ] `MLEntry` 类
  - [ ] 集成现有 LightGBM 模型
  - [ ] 支持预测收益率 → 多空信号转换

- [ ] 单元测试（50+ 用例）

---

### Phase 3: 退出策略重构（5天）

**目标**: 重构退出策略，支持平仓和反向开仓

- [ ] 重构 `ExitStrategy` 基类
  - 定义新的 `generate_exit_signals()` 接口
  - 支持平仓和反向开仓输出

- [ ] 实现技术指标退出策略
  - [ ] `SignalReversalExit` (信号反转退出)
  - [ ] `TargetReachedExit` (目标达成退出)
  - [ ] `TimeBasedExit` (时间退出)

- [ ] 实现 ML退出策略
  - [ ] `MLExit` 类
  - [ ] 基于预测反转的退出逻辑

- [ ] 单元测试（50+ 用例）

---

### Phase 4: 风控层实现（3天）

**目标**: 实现统一的风控层

- [ ] 实现 `RiskManager` 类
  - [ ] 单仓位止损
  - [ ] 组合止损
  - [ ] 时间止损
  - [ ] 杠杆限制
  - [ ] 仓位限制
  - [ ] 行业集中度限制

- [ ] 单元测试（30+ 用例）

---

### Phase 5: ML选股工具实现（3天）

**目标**: 实现独立的 ML选股工具

- [ ] 实现 `MLSelector` 类
  - [ ] 实现 `rank()` 方法（评分+排名）
  - [ ] 返回完整的评分结果（score, rank, expected_return, volatility, confidence）
  - [ ] 支持 `return_top_n` 参数

- [ ] 实现 Backend-MLSelector 接口
  - [ ] Backend 调用 MLSelector 的接口设计
  - [ ] 结果读取和解析

- [ ] 单元测试（30+ 用例）
  - [ ] 测试评分计算
  - [ ] 测试排名逻辑
  - [ ] 测试 Top N 筛选

- [ ] 更新文档说明使用场景
  - [ ] Backend 如何调用 MLSelector
  - [ ] MLSelector vs MLEntry 区别说明

---

### Phase 6: 回测引擎重构（7天）

**目标**: 重构回测引擎，协调所有层

- [ ] 重构 `BacktestEngine` 类
  - [ ] 实现新的执行顺序（风控→退出→入场）
  - [ ] 支持多空交易
  - [ ] 集成风控层

- [ ] 实现 `Portfolio` 类
  - [ ] 持仓管理（多空分离）
  - [ ] 盈亏计算
  - [ ] 组合价值更新

- [ ] 实现 `BacktestResult` 类
  - [ ] 绩效指标计算
  - [ ] 回测报告生成
  - [ ] 可视化图表

- [ ] 集成测试（100+ 用例）

---

### Phase 7: 测试更新（5天）

**目标**: 更新所有测试用例

- [ ] 删除三层架构测试
- [ ] 新增入场策略测试
- [ ] 新增退出策略测试
- [ ] 新增风控层测试
- [ ] 端到端回测测试
- [ ] 测试覆盖率检查（目标 90%+）

---

### Phase 8: 文档更新（3天）

**目标**: 完整的文档体系

- [ ] 更新架构文档
  - 删除三层架构说明
  - 添加新架构说明
  - 添加多空交易说明

- [ ] 编写策略开发指南
  - 入场策略开发教程
  - 退出策略开发教程
  - ML策略开发教程

- [ ] 编写 Backend-Core 接口文档
  - 股票池提供接口
  - 回测调用接口

- [ ] 更新 API 文档

---

### Phase 9: 示例和模板（2天）

**目标**: 丰富的示例代码

- [ ] 编写完整示例（10+ 个）
  - 技术指标策略示例
  - ML策略示例
  - 混合策略示例
  - 多空策略示例

- [ ] 创建 Jupyter Notebook 教程
  - 新手入门教程
  - 高级用法教程
  - 实战案例教程

---

## 📈 预期收益

### 架构优势

| 指标 | 旧架构 | 新架构 | 改进 |
|------|--------|--------|------|
| 职责清晰度 | 选股/入场混淆 | 清晰分离 | ↑ 显著 |
| 卖空支持 | ❌ 不支持 | ✅ 完整支持 | ↑ 新增 |
| ML模型利用 | 只用于选股 | 直接生成策略 | ↑ 显著 |
| 止损管理 | 分散在各策略 | 统一风控层 | ↑ 显著 |
| 股票池管理 | Core内部 | Backend提供 | ↑ 清晰 |
| 策略组合灵活性 | 三层固定 | 自由组合 | ↑ 显著 |
| 代码复杂度 | 高耦合 | 低耦合 | ↓ 30% |

### 功能提升

1. ✅ **完整的多空策略支持**
   - 买入/卖空信号
   - 平仓/反向开仓
   - 多空分离的持仓管理

2. ✅ **ML模型充分利用**
   - 预测收益率 → 直接生成入场信号
   - 预测波动率 → 计算仓位权重
   - 预测置信度 → 过滤信号

3. ✅ **统一的风控体系**
   - 全局止损规则
   - 优先级最高
   - 保护性强制平仓

4. ✅ **清晰的职责分工**
   - Backend: 股票池管理
   - Core: 策略执行和回测
   - 各司其职

### 代码质量提升

1. ✅ **更低的耦合度**
   - 入场策略独立
   - 退出策略独立
   - 风控层独立
   - ML选股器可选

2. ✅ **更高的可测试性**
   - 每层独立测试
   - Mock依赖简单
   - 测试覆盖率高

3. ✅ **更强的扩展性**
   - 新增入场策略容易
   - 新增退出策略容易
   - 自由组合策略

---

## ⚠️ 风险与缓解措施

### 风险点

1. **迁移成本**
   - **风险**: 需要重写所有策略代码
   - **缓解**: 分阶段迁移，优先迁移核心策略
   - **缓解**: 提供迁移工具和脚本

2. **测试工作量大**
   - **风险**: 需要重写所有测试用例
   - **缓解**: 自动化测试生成工具
   - **缓解**: 先测试核心功能，后测试边缘情况

3. **Backend 集成复杂**
   - **风险**: 需要 Backend 适配新接口
   - **缓解**: 提供清晰的接口文档
   - **缓解**: 提供 Mock Backend 用于测试

4. **用户学习曲线**
   - **风险**: 用户需要理解新架构
   - **缓解**: 丰富的文档和示例
   - **缓解**: 新架构更简单直观

---

## 📚 相关文档

- [新架构详细设计](../architecture/new_architecture.md)
- [入场策略开发指南](../user_guide/entry_strategy_guide.md)
- [退出策略开发指南](../user_guide/exit_strategy_guide.md)
- [风控层使用指南](../user_guide/risk_manager_guide.md)
- [Backend-Core 接口文档](../api/backend_core_interface.md)
- [ML策略开发指南](../user_guide/ml_strategy_guide.md)

---

## ✅ 验收标准

### 1. 功能完整性

- ✅ 入场策略正常工作
  - 技术指标入场策略
  - ML入场策略
  - 支持多空信号

- ✅ 退出策略正常工作
  - 平仓信号
  - 反向开仓信号
  - ML退出策略

- ✅ 风控层正常工作
  - 单仓位止损
  - 组合止损
  - 时间止损
  - 入场限制

- ✅ ML选股器保留
  - 作为可选组件
  - 与新架构兼容

- ✅ 回测引擎正常工作
  - 协调所有层执行
  - 支持多空交易
  - 生成完整报告

### 2. 性能达标

- ✅ 回测速度稳定
  - 单策略回测 < 30s
  - 多策略对比 < 2min

- ✅ 内存占用稳定
  - 单策略回测 < 2GB
  - 多策略对比 < 4GB

### 3. 测试覆盖

- ✅ 代码测试覆盖率 90%+
  - 入场策略 95%+
  - 退出策略 95%+
  - 风控层 95%+
  - 回测引擎 90%+

- ✅ 所有测试通过
  - 单元测试 500+ 用例
  - 集成测试 100+ 用例

### 4. 文档完整

- ✅ API 文档完整
  - 所有公共 API 有文档
  - 参数说明清晰
  - 返回值说明完整

- ✅ 使用指南清晰
  - 入场策略开发指南
  - 退出策略开发指南
  - 风控层使用指南
  - Backend-Core 接口文档
  - 示例代码充足（10+ 个）

### 5. 代码质量

- ✅ 代码规范
  - 通过 Pylint 检查
  - 通过 Black 格式化
  - 通过 MyPy 类型检查

- ✅ 架构清晰
  - 模块职责明确
  - 依赖关系简单
  - 扩展性好

---

## 🎯 成功指标

### 短期指标（1 个月内）

- ✅ 所有测试通过
- ✅ 文档完整
- ✅ Backend 成功集成
- ✅ 代码审查通过

### 中期指标（3 个月内）

- ✅ 至少 10 个实际使用案例
- ✅ 多空策略稳定运行
- ✅ Bug 数量 < 5 个
- ✅ 用户反馈满意度 >= 90%

### 长期指标（6 个月内）

- ✅ 成为主流架构
- ✅ 社区贡献 5+ 个新策略
- ✅ 性能持续稳定
- ✅ 文档持续更新

---

**文档维护**: Quant Team
**最后更新**: 2026-02-07
**状态**: 📋 待审批
