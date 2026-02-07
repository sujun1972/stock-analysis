# Stock-Analysis Core 系统完整指南

**文档版本**: v5.0.0
**创建日期**: 2026-02-07
**最后更新**: 2026-02-07
**项目状态**: 🎯 架构设计完成 + ML 系统完整文档

---

## 📋 目录

- [项目概述](#-项目概述)
- [核心架构](#-核心架构)
- [核心组件详解](#-核心组件详解)
- [数据模型](#-数据模型)
- [工作流程](#-工作流程)
- [API 参考](#-api-参考)
- [性能指标](#-性能指标)
- [最佳实践](#-最佳实践)

---

## 🎯 项目概述

### 项目简介

**Stock-Analysis Core** 是一个专业的 A 股量化交易系统核心引擎，提供从数据处理、因子计算、策略执行到回测分析的完整解决方案。

### 核心定位

Core 项目是一个**纯粹的量化引擎**，专注于:
- ✅ 因子计算 (125+ Alpha 因子 + 60+ 技术指标)
- ✅ ML 股票评分工具 (MLStockRanker - 类似 BigQuant StockRanker)
- ✅ 策略执行 (入场/退出策略)
- ✅ 回测引擎 (支持多空交易)
- ✅ 风险控制 (统一风控层)
- ✅ 性能分析 (完整的绩效指标)

### 设计原则

1. **职责清晰**: 每个组件职责单一，边界明确
2. **高度解耦**: 组件之间低耦合，可独立测试和替换
3. **灵活组合**: 支持策略自由组合
4. **性能优先**: JIT 编译、向量化计算、并行处理
5. **类型安全**: 完整的类型提示，静态类型检查

---

## 🏗️ 核心架构

### 架构总览

```
┌═══════════════════════════════════════════════════════════┐
║              Stock-Analysis Core 核心引擎                  ║
║                    (独立运行)                              ║
└═══════════════════════════════════════════════════════════┘

    ┌───────────────────────────────────────────────────┐
    │         1. 策略层 (Strategy Layer)                 │
    ├───────────────────────────────────────────────────┤
    │  1.1 入场策略 (Entry Strategy)                     │
    │      - 职责: 生成买入/卖空信号                     │
    │      - 输入: stock_pool + market_data              │
    │      - 输出: {stock: {action, weight}}             │
    │      - 策略类型:                                   │
    │        · 技术指标策略 (动量/RSI/均线突破)          │
    │        · ML 入场策略 (预测收益率→多空信号)         │
    │                                                   │
    │  1.2 退出策略 (Exit Strategy)                      │
    │      - 职责: 决定何时平仓或反向开仓                │
    │      - 输入: current_positions + market_data       │
    │      - 输出: {close: [...], reverse: {...}}        │
    │      - 策略类型:                                   │
    │        · 信号反转退出                              │
    │        · 目标达成退出                              │
    │        · 时间退出                                  │
    │        · ML 退出策略                               │
    └───────────────────────────────────────────────────┘
                           ↓
    ┌───────────────────────────────────────────────────┐
    │         2. 风控层 (Risk Management Layer)          │
    ├───────────────────────────────────────────────────┤
    │  职责: 止损管理 + 风险控制                         │
    │  优先级: 最高(可强制平仓)                          │
    │                                                   │
    │  止损检查:                                         │
    │  ├─ 单仓位止损 (亏损 > 10% 强制平仓)               │
    │  ├─ 组合止损 (总亏损 > 20% 全部平仓)               │
    │  └─ 时间止损 (持仓 > 30天 强制平仓)                │
    │                                                   │
    │  风险控制:                                         │
    │  ├─ 杠杆限制 (最大 1 倍)                           │
    │  ├─ 单仓位限制 (最大 20%)                          │
    │  ├─ 行业集中度限制 (单行业最大 40%)                │
    │  └─ A 股特有约束 (融券限制、涨跌停)                │
    └───────────────────────────────────────────────────┘
                           ↓
    ┌───────────────────────────────────────────────────┐
    │         3. 回测引擎层 (Backtest Engine Layer)       │
    ├───────────────────────────────────────────────────┤
    │  职责: 协调所有层的执行                            │
    │                                                   │
    │  执行顺序 (每日):                                  │
    │  1. 更新持仓市值                                   │
    │  2. 风控检查 (止损) - 优先级最高                   │
    │  3. 退出策略 (平仓/反向)                           │
    │  4. 入场策略 (新信号)                              │
    │  5. 风控检查 (入场限制)                            │
    │  6. 执行交易 (考虑滑点、成本)                      │
    │  7. 更新持仓状态                                   │
    │                                                   │
    │  特性:                                             │
    │  ├─ 支持多空交易                                   │
    │  ├─ 完整的交易成本建模                             │
    │  ├─ 滑点模拟                                       │
    │  └─ 涨跌停限制                                     │
    └───────────────────────────────────────────────────┘
                           ↓
    ┌───────────────────────────────────────────────────┐
    │         4. 组合管理层 (Portfolio Layer)             │
    ├───────────────────────────────────────────────────┤
    │  职责: 持仓管理 + 盈亏计算                         │
    │                                                   │
    │  功能:                                             │
    │  ├─ 持仓管理 (多头/空头分离)                       │
    │  ├─ 资金管理 (现金流、保证金)                     │
    │  ├─ 盈亏计算 (已实现/未实现)                       │
    │  ├─ 权重归一化                                     │
    │  └─ 组合价值更新                                   │
    └───────────────────────────────────────────────────┘
                           ↓
    ┌───────────────────────────────────────────────────┐
    │         5. 绩效分析层 (Performance Layer)           │
    ├───────────────────────────────────────────────────┤
    │  职责: 回测结果分析和可视化                        │
    │                                                   │
    │  绩效指标:                                         │
    │  ├─ 收益指标 (总收益、年化收益、超额收益)         │
    │  ├─ 风险指标 (波动率、最大回撤、下行风险)         │
    │  ├─ 风险调整收益 (夏普、索提诺、卡玛)             │
    │  ├─ 交易指标 (胜率、盈亏比、换手率)               │
    │  └─ 归因分析 (因子贡献、行业贡献)                 │
    │                                                   │
    │  可视化:                                           │
    │  ├─ 累计收益曲线                                   │
    │  ├─ 回撤曲线                                       │
    │  ├─ 持仓分布                                       │
    │  └─ 交易明细                                       │
    └───────────────────────────────────────────────────┘
                           ↓
    ┌───────────────────────────────────────────────────┐
    │         6. 特征与模型层 (Feature & Model Layer)     │
    ├───────────────────────────────────────────────────┤
    │  6.1 因子库:                                       │
    │      - 125+ Alpha 因子                             │
    │      - 60+ 技术指标                                │
    │      - 因子缓存 + JIT 加速                         │
    │                                                   │
    │  6.2 ML 工具 (辅助工具,非策略组件):                │
    │      MLStockRanker (类似 BigQuant StockRanker)    │
    │      ├─ 定位: 股票表现预测器                       │
    │      ├─ 功能: 预测未来表现,输出评分排名            │
    │      ├─ 用途: 辅助决策,非交易执行                  │
    │      └─ 调用: Backend 或策略可选择性使用           │
    │                                                   │
    │  6.3 数据访问:                                     │
    │      - TimescaleDB 连接                            │
    │      - 数据缓存                                    │
    │      - 数据质量检查                                │
    └───────────────────────────────────────────────────┘
```

### 架构特点

#### 1. **职责清晰**

| 层级 | 职责 | 不做什么 |
|------|------|---------|
| MLStockRanker | 预测股票表现 | 不生成交易信号 |
| EntryStrategy | 生成入场信号 | 不筛选股票池 |
| ExitStrategy | 生成退出信号 | 不管理止损 |
| RiskManager | 风险控制 | 不生成策略信号 |
| BacktestEngine | 协调执行 | 不包含策略逻辑 |
| Portfolio | 持仓管理 | 不包含风控逻辑 |

#### 2. **数据流向**

```
外部输入
  └─> stock_pool (股票池)
  └─> market_data (市场数据)
        ↓
  (可选) MLStockRanker → 辅助参考
        ↓
  EntryStrategy → 信号
        ↓
  RiskManager → 调整权重
        ↓
  Portfolio → 执行交易
        ↓
  ExitStrategy → 退出信号
        ↓
  RiskManager → 止损检查
        ↓
  Portfolio → 更新持仓
        ↓
  BacktestResult → 输出结果
```

#### 3. **多空支持**

```python
# 所有信号统一格式
Signal = {
    'stock_code': str,
    'action': Literal['long', 'short'],  # 做多 / 做空
    'weight': float                       # 仓位权重 0-1
}

# 持仓分离管理
Portfolio = {
    'long_positions': {...},   # 多头持仓
    'short_positions': {...}   # 空头持仓
}
```

---

## 📐 核心组件详解

### 0. 特征与模型层

#### 0.1 Alpha 因子库 (125+)

- 动量因子
- 反转因子
- 波动率因子
- 成交量因子
- 趋势因子
- 流动性因子

#### 0.2 技术指标库 (60+)

- MA, EMA, SMA
- RSI, MACD, KDJ
- 布林带, ATR, CCI
- ...

#### 0.3 ML 股票评分工具 (辅助工具)

**MLStockRanker** (类似 BigQuant StockRanker)

**定位**: 辅助预测工具，**非策略组件**

**核心概念澄清**:

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

##### API 接口

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
            stock_pool: 候选股票列表
            market_data: 市场数据
            date: 评分日期
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
        # score = sharpe_ratio * confidence

        # 4. 排名
        rankings = self._rank(scores)

        return rankings

    def _calculate_score(self, predictions: pd.DataFrame) -> pd.Series:
        """
        计算综合评分

        公式: score = sharpe_ratio * confidence
             = (predicted_return / volatility) * confidence
        """
        sharpe = predictions['predicted_return'] / predictions['volatility']
        scores = sharpe * predictions['confidence']
        return scores.clip(lower=0)
```

##### 使用场景

**场景 1: 外部系统使用 MLStockRanker 筛选股票池**

```python
# 外部系统(如 Backend)调用
ranker = MLStockRanker(model_path='ranker.pkl')

# 对候选池评分
rankings = ranker.rank(
    stock_pool=all_a_stocks,  # 3000 只
    market_data=market_data,
    date='2024-01-01',
    return_top_n=50
)

# 读取评分结果
for stock, info in rankings.items():
    print(f"{stock}: score={info['score']:.2f}, "
          f"rank={info['rank']}, "
          f"predicted_return={info['predicted_return']:.2%}")

# 外部系统自主决策如何使用
# 选项1: 直接取 Top 50
stock_pool = [s for s, _ in rankings.items()]

# 选项2: 结合其他规则
stock_pool = custom_selection(rankings)

# 传给回测引擎
result = backtest_engine.run(stock_pool=stock_pool, ...)
```

**场景 2: 策略内部可选择性参考评分**

```python
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
            if self.ranker and rankings[stock]['score'] > 0.7:
                ml_boost = rankings[stock]['score']
                weight = mom_score * ml_boost
            else:
                weight = mom_score

            if weight > 0.10:
                signals[stock] = {
                    'action': 'long',
                    'weight': weight
                }

        return self._normalize_weights(signals)
```

**场景 3: 前端展示供人工参考**

```python
# Frontend 调用
ranker = MLStockRanker(model_path='ranker.pkl')
rankings = ranker.rank(
    stock_pool=user_watchlist,  # 用户自选股
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

### 1. 策略层 (Strategy Layer)

策略层包含两个核心组件:**入场策略**和**退出策略**

#### 1.1 入场策略 (EntryStrategy)

**职责**: 生成买入/卖空信号(包含权重、方向)

**基类接口**:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Literal
import pandas as pd

class EntryStrategy(ABC):
    """入场策略基类"""

    @abstractmethod
    def generate_signals(
        self,
        stock_pool: List[str],           # 股票池
        market_data: pd.DataFrame,       # 市场数据
        date: str                        # 当前日期
    ) -> Dict[str, Dict]:
        """
        生成入场信号

        Returns:
            {
                '600000.SH': {
                    'action': 'long',      # 'long' 或 'short'
                    'weight': 0.15         # 仓位权重 0-1
                },
                '000001.SZ': {
                    'action': 'short',
                    'weight': 0.10
                },
                ...
            }

        注意:
        - 所有权重之和应为 1.0 (代表 100% 仓位)
        - action 只能是 'long' 或 'short'
        - 策略内部需要归一化权重
        """
        pass
```

**内置策略**:

##### 1.1.1 动量入场策略

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
```

##### 1.1.2 RSI 超卖/超买策略

```python
class RSIOversoldEntry(EntryStrategy):
    """RSI 超卖/超买入场策略"""

    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 30,
        overbought: float = 70
    ):
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
```

##### 1.1.3 ML 入场策略（完整指南）

**定位**: 策略组件，使用机器学习模型生成交易信号

**与 MLStockRanker 的区别**:
- MLStockRanker: 预测工具，输出评分排名（辅助筛选股票池）
- MLEntry: 策略组件，输出交易指令（多空方向 + 仓位权重）

---

###### 1.1.3.1 ML 入场信号完整架构

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
  ├─ 特征预处理（缺失值、异常值、标准化）
  └─ → [特征矩阵] (N stocks × 125+ features)
        ↓
阶段 2: 模型训练
  ├─ LabelGenerator.generate_labels() - 生成训练标签
  ├─ ModelTrainer.train() - 模型训练
  │   ├─ 模型选择: LightGBM / XGBoost / Neural Net
  │   ├─ 超参数优化: Optuna / Grid Search
  │   └─ 交叉验证: TimeSeriesSplit
  ├─ ModelEvaluator.evaluate() - 模型评估
  │   ├─ IC (Information Coefficient)
  │   ├─ Rank IC
  │   └─ 分组回测
  └─ → [训练好的模型] (model.pkl)
        ↓
阶段 3: 信号生成（回测/实盘）
  ├─ MLEntry.generate_signals(stock_pool, date)
  │   ├─ 1. 计算当日特征
  │   ├─ 2. 模型预测（expected_return + confidence）
  │   ├─ 3. 信号筛选（置信度过滤 + Top N）
  │   ├─ 4. 权重计算（sharpe × confidence）
  │   └─ 5. 归一化权重
  └─ → [交易信号] {'stock': {'action': 'long/short', 'weight': 0.xx}}
```

---

###### 1.1.3.2 核心组件实现

**A. 特征工程引擎**

```python
class FeatureEngine:
    """
    特征工程引擎

    职责: 计算 125+ 特征（Alpha 因子 + 技术指标 + 成交量特征）
    """

    def __init__(
        self,
        feature_groups: List[str] = None,  # ['alpha', 'technical', 'volume']
        lookback_window: int = 60,          # 回看窗口
        cache_enabled: bool = True          # 是否启用缓存
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
            from core.features.alpha_factors import AlphaFactorCalculator
            calculator = AlphaFactorCalculator()
            alpha_features = calculator.calculate_all(
                stock_codes=stock_codes,
                market_data=market_data,
                end_date=date,
                lookback=self.lookback_window
            )
            features = pd.concat([features, alpha_features], axis=1)

        # 技术指标 (60+)
        if 'technical' in self.feature_groups or 'all' in self.feature_groups:
            from core.features.technical_indicators import TechnicalIndicatorCalculator
            calculator = TechnicalIndicatorCalculator()
            tech_features = calculator.calculate_all(
                stock_codes=stock_codes,
                market_data=market_data,
                end_date=date,
                lookback=self.lookback_window
            )
            features = pd.concat([features, tech_features], axis=1)

        # 成交量特征
        if 'volume' in self.feature_groups or 'all' in self.feature_groups:
            volume_features = self._calculate_volume_features(
                stock_codes, market_data, date
            )
            features = pd.concat([features, volume_features], axis=1)

        return features

    def _calculate_volume_features(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> pd.DataFrame:
        """计算成交量特征"""
        features = {}
        for stock in stock_codes:
            stock_data = market_data[market_data['stock_code'] == stock]
            stock_data = stock_data[stock_data['date'] <= date].tail(self.lookback_window)

            if len(stock_data) < 20:
                continue

            volume = stock_data['volume'].values
            features[stock] = {
                'volume_ma_5': np.mean(volume[-5:]),
                'volume_ma_20': np.mean(volume[-20:]),
                'volume_std_20': np.std(volume[-20:]),
                'volume_ratio': volume[-1] / np.mean(volume[-20:]) if np.mean(volume[-20:]) > 0 else 1.0,
            }

        return pd.DataFrame(features).T
```

**B. 标签生成器**

```python
class LabelGenerator:
    """
    标签生成器

    职责: 生成训练标签（未来收益率）
    """

    def __init__(
        self,
        forward_window: int = 5,           # 前向窗口（预测未来 5 天）
        label_type: str = 'return'         # 'return' 或 'direction'
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
                values = 未来收益率（或方向）
        """
        labels = {}

        for stock in stock_codes:
            stock_data = market_data[market_data['stock_code'] == stock]

            # 找到当前日期的位置
            current_idx = stock_data[stock_data['date'] == date].index
            if len(current_idx) == 0:
                continue
            current_idx = current_idx[0]

            # 获取当前价格和未来价格
            current_price = stock_data.loc[current_idx, 'close']

            # 获取未来价格（forward_window 天后）
            future_idx = current_idx + self.forward_window
            if future_idx >= len(stock_data):
                continue

            future_price = stock_data.iloc[future_idx]['close']

            # 计算标签
            if self.label_type == 'return':
                labels[stock] = (future_price - current_price) / current_price
            elif self.label_type == 'direction':
                labels[stock] = 1 if future_price > current_price else 0

        return pd.Series(labels)
```

**C. 模型训练器**

```python
@dataclass
class TrainingConfig:
    """训练配置"""
    model_type: str = 'lightgbm'           # 'lightgbm', 'xgboost', 'neural_net'
    train_start_date: str = '2020-01-01'
    train_end_date: str = '2023-12-31'
    validation_split: float = 0.2
    forward_window: int = 5                # 预测未来 5 天
    feature_groups: List[str] = None
    hyperparameters: Dict = None


class ModelTrainer:
    """
    模型训练器

    职责: 训练机器学习模型
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
        print("📊 Step 1: 准备训练数据...")
        X_train, y_train, X_val, y_val = self._prepare_training_data(
            stock_pool, market_data
        )

        print(f"  ✓ 训练集样本数: {len(X_train)}")
        print(f"  ✓ 验证集样本数: {len(X_val)}")
        print(f"  ✓ 特征数量: {X_train.shape[1]}")

        print("\n🤖 Step 2: 训练模型...")
        model = self._train_model(X_train, y_train, X_val, y_val)

        print("\n📈 Step 3: 评估模型...")
        metrics = self._evaluate_model(model, X_val, y_val)

        print("\n✅ 训练完成!")
        print(f"  - 验证集 IC: {metrics['ic']:.4f}")
        print(f"  - 验证集 Rank IC: {metrics['rank_ic']:.4f}")

        return TrainedModel(
            model=model,
            feature_engine=self.feature_engine,
            config=self.config,
            metrics=metrics
        )

    def _prepare_training_data(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """准备训练数据"""
        train_dates = pd.date_range(
            self.config.train_start_date,
            self.config.train_end_date,
            freq='B'  # 工作日
        )

        all_features = []
        all_labels = []
        all_dates = []

        for date in train_dates:
            date_str = date.strftime('%Y-%m-%d')

            # 计算特征
            features = self.feature_engine.calculate_features(
                stock_pool, market_data, date_str
            )

            # 生成标签
            labels = self.label_generator.generate_labels(
                stock_pool, market_data, date_str
            )

            # 合并
            common_stocks = features.index.intersection(labels.index)
            if len(common_stocks) == 0:
                continue

            all_features.append(features.loc[common_stocks])
            all_labels.append(labels.loc[common_stocks])
            all_dates.extend([date_str] * len(common_stocks))

        # 合并所有数据
        X = pd.concat(all_features, axis=0)
        y = pd.concat(all_labels, axis=0)
        dates = pd.Series(all_dates, index=X.index)

        # 按时间切分训练集和验证集
        split_date = dates.quantile(1 - self.config.validation_split)
        train_mask = dates < split_date
        val_mask = dates >= split_date

        X_train = X[train_mask].fillna(0).replace([np.inf, -np.inf], 0)
        y_train = y[train_mask]
        X_val = X[val_mask].fillna(0).replace([np.inf, -np.inf], 0)
        y_val = y[val_mask]

        return X_train, y_train, X_val, y_val

    def _train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series
    ):
        """训练模型"""
        if self.config.model_type == 'lightgbm':
            import lightgbm as lgb

            params = self.config.hyperparameters or {
                'objective': 'regression',
                'metric': 'l2',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.8,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'verbose': -1
            }

            train_data = lgb.Dataset(X_train, label=y_train)
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

            model = lgb.train(
                params,
                train_data,
                num_boost_round=500,
                valid_sets=[train_data, val_data],
                callbacks=[lgb.early_stopping(stopping_rounds=50)]
            )

            return model

        elif self.config.model_type == 'xgboost':
            import xgboost as xgb

            params = self.config.hyperparameters or {
                'objective': 'reg:squarederror',
                'max_depth': 6,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8
            }

            dtrain = xgb.DMatrix(X_train, label=y_train)
            dval = xgb.DMatrix(X_val, label=y_val)

            model = xgb.train(
                params,
                dtrain,
                num_boost_round=500,
                evals=[(dtrain, 'train'), (dval, 'val')],
                early_stopping_rounds=50,
                verbose_eval=False
            )

            return model

    def _evaluate_model(
        self,
        model,
        X_val: pd.DataFrame,
        y_val: pd.Series
    ) -> Dict:
        """评估模型"""
        # 预测
        if self.config.model_type == 'lightgbm':
            y_pred = model.predict(X_val, num_iteration=model.best_iteration)
        elif self.config.model_type == 'xgboost':
            import xgboost as xgb
            dval = xgb.DMatrix(X_val)
            y_pred = model.predict(dval)

        # 计算指标
        ic = np.corrcoef(y_val, y_pred)[0, 1]
        rank_ic = pd.Series(y_val).corr(pd.Series(y_pred), method='spearman')

        return {
            'ic': ic,
            'rank_ic': rank_ic
        }
```

**D. 训练好的模型**

```python
class TrainedModel:
    """
    训练好的模型（可保存和加载）

    职责: 封装模型 + 特征引擎，提供预测接口
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
        if self.config.model_type == 'lightgbm':
            predictions = self.model.predict(
                features,
                num_iteration=self.model.best_iteration
            )
        elif self.config.model_type == 'xgboost':
            import xgboost as xgb
            dmat = xgb.DMatrix(features)
            predictions = self.model.predict(dmat)

        # 4. 构建预测结果
        result = pd.DataFrame(index=features.index)
        result['expected_return'] = predictions

        # 估算波动率（使用历史波动率）
        volatility = self._estimate_volatility(stock_codes, market_data, date)
        result['volatility'] = volatility

        # 置信度（基于特征质量）
        confidence = self._estimate_confidence(features)
        result['confidence'] = confidence

        return result

    def _estimate_volatility(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str,
        lookback: int = 20
    ) -> pd.Series:
        """估算波动率"""
        volatility = {}
        for stock in stock_codes:
            stock_data = market_data[market_data['stock_code'] == stock]
            stock_data = stock_data[stock_data['date'] <= date].tail(lookback)

            if len(stock_data) < lookback:
                volatility[stock] = 0.02  # 默认 2%
                continue

            returns = stock_data['close'].pct_change().dropna()
            volatility[stock] = returns.std()

        return pd.Series(volatility)

    def _estimate_confidence(self, features: pd.DataFrame) -> pd.Series:
        """估算置信度"""
        # 基于特征完整性
        confidence = 1.0 - (features.isna().sum(axis=1) / len(features.columns))
        return confidence.clip(lower=0.5)  # 最低 50%

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

**E. ML 入场策略**

```python
class MLEntry(EntryStrategy):
    """
    机器学习入场策略

    定位: 策略组件，使用训练好的模型生成交易信号

    与 MLStockRanker 的区别:
    - MLStockRanker: 预测工具，输出评分排名
    - MLEntry: 策略组件，输出交易指令（多空+权重）
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

        Returns:
            {
                '600000.SH': {'action': 'long', 'weight': 0.15},
                '000001.SZ': {'action': 'short', 'weight': 0.08},
                ...
            }
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

        # 选出 Top N
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

        # 选出 Top N
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

###### 1.1.3.3 完整使用案例

**案例 1: 训练 ML 模型**

```python
from core.ml.model_trainer import ModelTrainer, TrainingConfig
from core.data import load_market_data

# Step 1: 配置训练参数
config = TrainingConfig(
    model_type='lightgbm',
    train_start_date='2020-01-01',
    train_end_date='2023-12-31',
    validation_split=0.2,
    forward_window=5,  # 预测未来 5 天
    feature_groups=['alpha', 'technical', 'volume'],
    hyperparameters={
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.8
    }
)

# Step 2: 准备数据
stock_pool = ['600000.SH', '000001.SZ', ..., 300]  # 300 只股票
market_data = load_market_data(
    stock_codes=stock_pool,
    start_date='2019-01-01',  # 留出 lookback window
    end_date='2023-12-31'
)

# Step 3: 训练模型
trainer = ModelTrainer(config)
trained_model = trainer.train(stock_pool, market_data)

# Step 4: 保存模型
trained_model.save('models/ml_entry_model.pkl')

print("\n✅ 模型训练完成!")
print(f"验证集 IC: {trained_model.metrics['ic']:.4f}")
```

**案例 2: 使用 ML 策略进行回测**

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

**案例 3: MLStockRanker + ML 策略组合**

```python
from core.features.ml_ranker import MLStockRanker
from core.strategies.entries import MLEntry

# Step 1: 使用 MLStockRanker 筛选高潜力股票池
ranker = MLStockRanker(model_path='models/ranker.pkl')
rankings = ranker.rank(
    stock_pool=all_a_stocks,  # 全 A 股（3000+）
    market_data=market_data,
    date='2024-01-01',
    return_top_n=100
)

# 提取 Top 100 作为股票池
selected_stock_pool = list(rankings.keys())
print(f"✓ 筛选出 {len(selected_stock_pool)} 只高潜力股票")

# Step 2: 在筛选后的股票池上运行 ML 策略
entry_strategy = MLEntry(
    model_path='models/ml_entry_model.pkl',
    confidence_threshold=0.7
)

result = engine.run(
    stock_pool=selected_stock_pool,  # 使用筛选后的池
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31'
)

print(f"\n✅ 回测完成!")
print(f"总收益率: {result.total_return:.2%}")
```

---

###### 1.1.3.4 模型维护与更新

**模型重训练策略**

```python
class ModelUpdateScheduler:
    """模型更新调度器"""

    def __init__(
        self,
        retrain_frequency: str = 'quarterly',  # 'monthly', 'quarterly', 'yearly'
        performance_threshold: float = 0.10     # IC 下降 10% 触发重训练
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

**在线性能监控**

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
            date_str = date.strftime('%Y-%m-%d')

            # 预测
            predictions = self.model.predict(stock_pool, market_data, date_str)

            # 实际收益（5 天后）
            actuals = self._get_actual_returns(
                stock_pool, market_data, date_str, forward_window=5
            )

            # 合并
            common = predictions.index.intersection(actuals.index)
            all_predictions.extend(predictions.loc[common, 'expected_return'].values)
            all_actuals.extend(actuals.loc[common].values)

        # 计算 IC
        ic = np.corrcoef(all_actuals, all_predictions)[0, 1]
        rank_ic = pd.Series(all_actuals).corr(
            pd.Series(all_predictions),
            method='spearman'
        )

        metrics = {
            'ic': ic,
            'rank_ic': rank_ic,
            'period': f'{start_date} to {end_date}'
        }

        self.performance_history.append(metrics)

        return metrics
```

---

###### 1.1.3.5 性能优化

**特征缓存**

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
        """计算特征（带缓存）"""
        cache_key = f"{date}_{hash(tuple(sorted(stock_codes)))}"
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.parquet")

        # 检查缓存
        if os.path.exists(cache_path):
            return pd.read_parquet(cache_path)

        # 计算特征
        features = super().calculate_features(stock_codes, market_data, date)

        # 保存缓存
        features.to_parquet(cache_path)

        return features
```

**并行计算**

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
        """并行计算特征"""
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

#### 1.2 退出策略 (ExitStrategy)

**职责**: 决定何时平仓或反向开仓

**数据模型**:

```python
from dataclasses import dataclass
from typing import Literal

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
```

**基类接口**:

```python
class ExitStrategy(ABC):
    """退出策略基类"""

    @abstractmethod
    def generate_exit_signals(
        self,
        positions: Dict[str, Position],  # 当前持仓
        market_data: pd.DataFrame,
        date: str
    ) -> Dict[str, Any]:
        """
        生成退出信号

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
        - 'close': 平仓(关闭当前持仓)
        - 'reverse': 反向开仓(平掉当前仓位 + 开反向新仓位)
        """
        pass
```

**内置策略**:

##### 1.2.1 信号反转退出

```python
class SignalReversalExit(ExitStrategy):
    """
    信号反转退出策略

    当技术指标给出反向信号时:
    - 平掉当前仓位
    - 可选:开反向仓位
    """

    def __init__(
        self,
        indicator: str = 'momentum',
        lookback: int = 20,
        enable_reverse: bool = False  # 默认不启用反向开仓
    ):
        self.indicator = indicator
        self.lookback = lookback
        self.enable_reverse = enable_reverse

    def generate_exit_signals(self, positions, market_data, date):
        close_list = []
        reverse_dict = {}

        for stock, position in positions.items():
            current_signal = self._calculate_signal(
                market_data[stock], date, self.lookback
            )

            if position.action == 'long' and current_signal == 'short':
                close_list.append(stock)
                if self.enable_reverse:
                    reverse_dict[stock] = {
                        'action': 'short',
                        'weight': position.weight
                    }

            elif position.action == 'short' and current_signal == 'long':
                close_list.append(stock)
                if self.enable_reverse:
                    reverse_dict[stock] = {
                        'action': 'long',
                        'weight': position.weight
                    }

            elif current_signal == 'neutral':
                close_list.append(stock)

        return {
            'close': close_list,
            'reverse': reverse_dict
        }
```

##### 1.2.2 目标达成退出

```python
class TargetReachedExit(ExitStrategy):
    """目标达成退出策略"""

    def __init__(self, take_profit_pct: float = 0.15):
        self.take_profit_pct = take_profit_pct

    def generate_exit_signals(self, positions, market_data, date):
        close_list = []

        for stock, position in positions.items():
            if position.unrealized_pnl_pct >= self.take_profit_pct:
                close_list.append(stock)

        return {
            'close': close_list,
            'reverse': {}
        }
```

##### 1.2.3 时间退出

```python
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

---

### 2. 风控层 (RiskManager)

**职责**: 止损管理 + 风险控制(优先级最高)

**特点**:
- ✅ 优先级最高,可强制平仓
- ✅ 先于退出策略执行
- ✅ 统一管理所有止损逻辑

#### API 接口

```python
class RiskManager:
    """风控层"""

    def __init__(
        self,
        # 止损参数
        max_position_loss_pct: float = 0.10,    # 单仓位最大亏损 10%
        max_portfolio_loss_pct: float = 0.20,   # 组合最大亏损 20%
        max_holding_days: int = 30,             # 最长持仓 30 天

        # 风险控制参数
        max_leverage: float = 1.0,              # 最大杠杆 1 倍
        max_position_size: float = 0.20,        # 单仓位最大 20%
        max_sector_concentration: float = 0.40, # 单行业最大 40%

        # A 股特有约束
        enable_short_constraints: bool = True,  # 启用融券限制
        shortable_stocks: List[str] = None      # 可融券股票池
    ):
        pass

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

        # 3. 组合止损(最严格)
        if positions:
            total_pnl_pct = sum(
                p.unrealized_pnl_pct * p.weight
                for p in positions.values()
            )
            if total_pnl_pct < -self.max_portfolio_loss_pct:
                force_close = list(positions.keys())

        return force_close

    def check_entry_limits(
        self,
        new_signals: Dict[str, Dict],
        current_positions: Dict[str, Position],
        portfolio_value: float,
        sector_map: Dict[str, str] = None
    ) -> Dict[str, Dict]:
        """
        检查入场限制,调整新信号的权重

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
            scale_factor = (self.max_leverage - current_exposure) / new_exposure
            for stock in adjusted_signals:
                adjusted_signals[stock]['weight'] *= scale_factor

        # 3. A 股融券限制
        if self.enable_short_constraints:
            adjusted_signals = self._filter_short_signals(adjusted_signals)

        return adjusted_signals
```

---

### 3. 回测引擎 (BacktestEngine)

**职责**: 协调所有层的执行

**执行流程**:

```python
class BacktestEngine:
    """回测引擎"""

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
        stock_pool: List[str],        # 股票池
        market_data: pd.DataFrame,    # 市场数据
        start_date: str,
        end_date: str,
        initial_capital: float = 1000000.0,
        # 交易成本参数
        commission_rate: float = 0.0003,  # 万三佣金
        stamp_tax: float = 0.001,         # 单边印花税
        slippage_pct: float = 0.001       # 0.1% 滑点
    ) -> BacktestResult:
        """
        运行回测

        Returns:
            BacktestResult: 回测结果
        """
        # 初始化组合
        portfolio = Portfolio(
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            stamp_tax=stamp_tax,
            slippage_pct=slippage_pct
        )

        dates = pd.date_range(start_date, end_date, freq='B')

        for date in dates:
            date_str = date.strftime('%Y-%m-%d')

            # 1. 更新持仓市值
            portfolio.update_positions_value(market_data, date_str)

            # 2. 风控检查: 止损(优先级最高)
            force_close = self.risk_manager.check_stop_loss(
                portfolio.positions, date_str
            )
            if force_close:
                portfolio.close_positions(force_close, market_data, date_str)

            # 3. 退出策略: 平仓或反向开仓
            exit_signals = self.exit_strategy.generate_exit_signals(
                portfolio.positions, market_data, date_str
            )

            # 3.1 平仓
            if exit_signals['close']:
                portfolio.close_positions(
                    exit_signals['close'], market_data, date_str
                )

            # 3.2 反向开仓
            if exit_signals['reverse']:
                reverse_signals = self.risk_manager.check_entry_limits(
                    exit_signals['reverse'],
                    portfolio.positions,
                    portfolio.total_value
                )
                portfolio.open_positions(reverse_signals, market_data, date_str)

            # 4. 入场策略: 新信号
            entry_signals = self.entry_strategy.generate_signals(
                stock_pool, market_data, date_str
            )

            # 4.1 风控检查入场限制
            entry_signals = self.risk_manager.check_entry_limits(
                entry_signals,
                portfolio.positions,
                portfolio.total_value
            )

            # 4.2 开仓
            portfolio.open_positions(entry_signals, market_data, date_str)

            # 5. 更新组合价值
            portfolio.update_total_value(market_data, date_str)

        # 生成回测报告
        return self._generate_report(portfolio)
```

---

### 4. 组合管理 (Portfolio)

**职责**: 持仓管理 + 盈亏计算

```python
class Portfolio:
    """组合管理"""

    def __init__(
        self,
        initial_capital: float,
        commission_rate: float = 0.0003,
        stamp_tax: float = 0.001,
        slippage_pct: float = 0.001
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}

        # 交易成本参数
        self.commission_rate = commission_rate
        self.stamp_tax = stamp_tax
        self.slippage_pct = slippage_pct

        # 历史记录
        self.trade_history = []
        self.value_history = []

    def open_positions(
        self,
        signals: Dict[str, Dict],
        market_data: pd.DataFrame,
        date: str
    ):
        """开仓"""
        for stock, signal in signals.items():
            action = signal['action']
            weight = signal['weight']

            # 计算目标金额
            target_value = self.total_value * weight

            # 获取价格(考虑滑点)
            price = market_data.loc[date, stock]
            if action == 'long':
                execution_price = price * (1 + self.slippage_pct)
            else:  # short
                execution_price = price * (1 - self.slippage_pct)

            # 计算股数
            shares = int(target_value / execution_price / 100) * 100

            # 计算成本
            trade_value = shares * execution_price
            commission = trade_value * self.commission_rate
            cost = commission

            # 更新现金
            if action == 'long':
                self.cash -= (trade_value + cost)
            else:  # short - 卖空收到现金
                self.cash += (trade_value - cost)

            # 创建持仓
            position = Position(
                stock_code=stock,
                action=action,
                entry_date=date,
                entry_price=execution_price,
                shares=shares,
                weight=weight,
                unrealized_pnl=0.0,
                unrealized_pnl_pct=0.0
            )

            self.positions[stock] = position

    def close_positions(
        self,
        stocks: List[str],
        market_data: pd.DataFrame,
        date: str
    ):
        """平仓"""
        for stock in stocks:
            if stock not in self.positions:
                continue

            position = self.positions[stock]

            # 获取价格(考虑滑点)
            price = market_data.loc[date, stock]
            if position.action == 'long':
                execution_price = price * (1 - self.slippage_pct)
            else:  # short
                execution_price = price * (1 + self.slippage_pct)

            # 计算成本
            trade_value = position.shares * execution_price
            commission = trade_value * self.commission_rate
            stamp = trade_value * self.stamp_tax if position.action == 'long' else 0
            cost = commission + stamp

            # 计算盈亏
            if position.action == 'long':
                pnl = (execution_price - position.entry_price) * position.shares - cost
                self.cash += (trade_value - cost)
            else:  # short
                pnl = (position.entry_price - execution_price) * position.shares - cost
                self.cash -= (trade_value + cost)

            # 删除持仓
            del self.positions[stock]

    @property
    def total_value(self) -> float:
        """组合总价值"""
        positions_value = sum(
            pos.shares * pos.entry_price + pos.unrealized_pnl
            for pos in self.positions.values()
        )
        return self.cash + positions_value
```

---

## 📊 数据模型

### 核心数据类

```python
from dataclasses import dataclass
from typing import Literal, Dict, Any, List

@dataclass
class Position:
    """持仓信息"""
    stock_code: str
    action: Literal['long', 'short']
    entry_date: str
    entry_price: float
    shares: int
    weight: float
    unrealized_pnl: float
    unrealized_pnl_pct: float

@dataclass
class Signal:
    """交易信号"""
    stock_code: str
    action: Literal['long', 'short']
    weight: float
    metadata: Dict[str, Any] = None

@dataclass
class BacktestResult:
    """回测结果"""
    # 基础信息
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float

    # 收益指标
    total_return: float
    annual_return: float
    excess_return: float

    # 风险指标
    volatility: float
    max_drawdown: float
    downside_risk: float

    # 风险调整收益
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # 交易指标
    win_rate: float
    profit_loss_ratio: float
    turnover_rate: float
    total_trades: int

    # 详细数据
    equity_curve: pd.Series
    drawdown_curve: pd.Series
    positions_history: List[Dict]
    trades_history: List[Dict]
```

---

## 🔄 工作流程

### 完整回测流程

```python
from core.features.ml_ranker import MLStockRanker
from core.strategies.entries import MomentumEntry, MLEntry
from core.strategies.exits import TimeBasedExit, SignalReversalExit
from core.risk import RiskManager
from core.backtest import BacktestEngine

# ============================================
# 场景1: 纯技术指标策略(不用 ML)
# ============================================

# Step 1: 准备数据
stock_pool = ['600000.SH', '000001.SZ', ..., 50]
market_data = load_market_data()

# Step 2: 创建策略
entry = MomentumEntry(lookback=20, threshold=0.10)
exit_strategy = TimeBasedExit(max_holding_days=20)
risk_manager = RiskManager()

# Step 3: 运行回测
engine = BacktestEngine(
    entry_strategy=entry,
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
print(f"夏普比率: {result.sharpe_ratio:.2f}")

# ============================================
# 场景2: 使用 MLStockRanker 辅助筛选
# ============================================

# Step 1: 使用 MLStockRanker 筛选股票池
ranker = MLStockRanker(model_path='models/ranker.pkl')
rankings = ranker.rank(
    stock_pool=candidate_pool,  # 3000 只候选
    market_data=market_data,
    date='2024-01-01',
    return_top_n=50
)

# 提取 Top 50
stock_pool = [stock for stock, info in rankings.items()]

# Step 2-4: 同场景1 (运行技术指标策略)

# ============================================
# 场景3: ML 策略(策略内部使用 ML)
# ============================================

# Step 1: 准备股票池
stock_pool = ['600000.SH', ..., 50]

# Step 2: 创建 ML 策略
entry = MLEntry(
    model_path='models/entry.pkl',
    confidence_threshold=0.7
)

exit_strategy = SignalReversalExit(
    indicator='momentum',
    enable_reverse=False
)

# Step 3-4: 运行回测和分析
```

---

## 📖 API 参考

### MLStockRanker

```python
MLStockRanker(
    model_path: str,               # 模型文件路径
    feature_config: Dict = None    # 特征配置
)

.rank(
    stock_pool: List[str],         # 候选股票
    market_data: pd.DataFrame,     # 市场数据
    date: str,                     # 评分日期
    return_top_n: int = None       # 返回 Top N
) -> Dict[str, Dict]
```

### EntryStrategy

```python
EntryStrategy.generate_signals(
    stock_pool: List[str],         # 股票池
    market_data: pd.DataFrame,     # 市场数据
    date: str                      # 当前日期
) -> Dict[str, Dict]               # {stock: {action, weight}}
```

### ExitStrategy

```python
ExitStrategy.generate_exit_signals(
    positions: Dict[str, Position],  # 当前持仓
    market_data: pd.DataFrame,       # 市场数据
    date: str                        # 当前日期
) -> Dict[str, Any]                  # {close: [...], reverse: {...}}
```

### RiskManager

```python
RiskManager(
    max_position_loss_pct: float = 0.10,
    max_portfolio_loss_pct: float = 0.20,
    max_holding_days: int = 30,
    max_leverage: float = 1.0,
    max_position_size: float = 0.20,
    max_sector_concentration: float = 0.40
)

.check_stop_loss(
    positions: Dict[str, Position],
    date: str
) -> List[str]

.check_entry_limits(
    new_signals: Dict[str, Dict],
    current_positions: Dict[str, Position],
    portfolio_value: float
) -> Dict[str, Dict]
```

### BacktestEngine

```python
BacktestEngine(
    entry_strategy: EntryStrategy,
    exit_strategy: ExitStrategy,
    risk_manager: RiskManager
)

.run(
    stock_pool: List[str],
    market_data: pd.DataFrame,
    start_date: str,
    end_date: str,
    initial_capital: float = 1000000.0,
    commission_rate: float = 0.0003,
    stamp_tax: float = 0.001,
    slippage_pct: float = 0.001
) -> BacktestResult
```

---

## ⚡ 性能指标

### 回测性能

| 场景 | 股票数 | 日期数 | 耗时 | 性能 |
|------|--------|--------|------|------|
| 纯技术指标 | 50 | 250 | <5s | ✅ 优秀 |
| 使用 MLStockRanker | 50 | 250 | <8s | ✅ 良好 |
| ML 策略 | 50 | 250 | <15s | ✅ 可接受 |

### MLStockRanker 性能

| 操作 | 股票数 | 特征数 | 耗时 | 性能 |
|------|--------|--------|------|------|
| 评分 | 3000 | 125 | <2s | ✅ 优秀 |
| 评分 | 100 | 125 | <100ms | ✅ 优秀 |
| 评分 | 50 | 10 | <50ms | ✅ 优秀 |

---

## 💡 最佳实践

### 1. 权重归一化

```python
# ✅ 正确:分别归一化
long_total = sum(w for s, w in signals.items() if s['action'] == 'long')
short_total = sum(w for s, w in signals.items() if s['action'] == 'short')

for stock, signal in signals.items():
    if signal['action'] == 'long':
        signal['weight'] /= long_total
    else:
        signal['weight'] /= short_total
```

### 2. MLStockRanker 使用建议

```python
# ✅ 推荐: 回测前筛选1次
ranker = MLStockRanker(model_path='ranker.pkl')
rankings = ranker.rank(
    stock_pool=candidate_pool,
    date='2024-01-01'  # 回测开始日期
)
stock_pool = select_top_n(rankings, n=50)

# 回测中只处理筛选后的50只
for date in backtest_dates:
    entry_signals = entry_strategy.generate_signals(
        stock_pool=stock_pool,  # 固定的50只
        market_data=market_data,
        date=date
    )

# ❌ 不推荐: 回测中每日调用
for date in backtest_dates:
    rankings = ranker.rank(...)  # 每天重复计算,性能差
    stock_pool = select_top_n(rankings, n=50)
    entry_signals = entry_strategy.generate_signals(...)
```

### 3. A 股特有处理

```python
# 融券限制
shortable_stocks = ['600000.SH', '000001.SZ', ...]

def filter_short_signals(signals, shortable_stocks):
    return {
        stock: sig
        for stock, sig in signals.items()
        if sig['action'] == 'long' or stock in shortable_stocks
    }
```

### 4. 交易成本建模

```python
class TransactionCost:
    def __init__(self):
        self.commission_rate = 0.0003  # 万三佣金
        self.stamp_tax = 0.001         # 千一印花税(卖出单边)
        self.slippage_pct = 0.001      # 0.1% 滑点

    def calculate_buy_cost(self, price, shares):
        trade_value = price * shares
        commission = trade_value * self.commission_rate
        slippage = price * shares * self.slippage_pct
        return commission + slippage

    def calculate_sell_cost(self, price, shares):
        trade_value = price * shares
        commission = trade_value * self.commission_rate
        stamp = trade_value * self.stamp_tax
        slippage = price * shares * self.slippage_pct
        return commission + stamp + slippage
```

---

## 📚 附录

### A. MLStockRanker vs MLEntry 详细对比

| 对比项 | MLStockRanker | MLEntry |
|--------|--------------|---------|
| **类型** | 辅助工具 | 策略组件 |
| **定位** | 股票筛选器/预测器 | 交易信号生成器/决策器 |
| **输入** | 大股票池 (3000+) | 小股票池 (50-100) |
| **输出** | 评分 + 排名 | 多空信号 + 权重 |
| **模型目标** | 预测表现好的股票 | 预测收益率 + 生成信号 |
| **使用时机** | 回测前（一次性） | 回测中（每日） |
| **调用方** | 外部系统/策略可选 | 回测引擎必需 |
| **频率** | 低（回测前 1 次） | 高（每日） |
| **职责** | 预测表现 | 执行交易 |
| **可选性** | 完全可选 | 策略必需 |
| **依赖** | 独立运行 | 依赖训练好的模型 |
| **性能要求** | 可处理大规模数据 | 需要快速预测 |

**使用场景示例**:

```python
# MLStockRanker: 筛选股票池（一次性）
ranker = MLStockRanker(model_path='ranker.pkl')
rankings = ranker.rank(stock_pool=all_3000_stocks, date='2024-01-01')
selected_pool = list(rankings.keys())[:100]  # 选出 Top 100

# MLEntry: 在筛选后的池上每日生成信号
ml_entry = MLEntry(model_path='ml_entry.pkl')
for date in backtest_dates:
    signals = ml_entry.generate_signals(
        stock_pool=selected_pool,  # 固定的 100 只
        market_data=market_data,
        date=date
    )
    # 执行交易...
```

### B. 文件结构

```
core/
├── src/
│   ├── strategies/
│   │   ├── entries/                # 入场策略
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── momentum_entry.py
│   │   │   ├── rsi_entry.py
│   │   │   └── ml_entry.py        # ML 入场策略
│   │   │
│   │   └── exits/                  # 退出策略
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── signal_reversal_exit.py
│   │       ├── target_reached_exit.py
│   │       └── time_based_exit.py
│   │
│   ├── risk/                       # 风控层
│   │   ├── __init__.py
│   │   └── risk_manager.py
│   │
│   ├── backtest/                   # 回测引擎
│   │   ├── __init__.py
│   │   ├── backtest_engine.py
│   │   ├── portfolio.py
│   │   └── backtest_result.py
│   │
│   ├── features/                   # 特征与模型层
│   │   ├── __init__.py
│   │   ├── alpha_factors.py       # 125+ Alpha 因子
│   │   ├── technical_indicators.py # 60+ 技术指标
│   │   └── ml_ranker.py           # MLStockRanker (辅助工具)
│   │
│   ├── ml/                         # 🆕 机器学习模块
│   │   ├── __init__.py
│   │   ├── feature_engine.py      # 特征工程引擎
│   │   ├── label_generator.py     # 标签生成器
│   │   ├── model_trainer.py       # 模型训练器
│   │   ├── trained_model.py       # 训练好的模型
│   │   ├── model_monitor.py       # 模型性能监控
│   │   └── model_updater.py       # 模型更新调度器
│   │
│   ├── models/                     # 数据模型
│   │   ├── __init__.py
│   │   ├── position.py
│   │   └── signal.py
│   │
│   └── data/                       # 数据层
│       ├── __init__.py
│       ├── database.py
│       └── cache.py
│
├── models/                         # 🆕 训练好的模型文件
│   ├── ml_entry_model.pkl         # ML 入场策略模型
│   ├── ranker.pkl                 # MLStockRanker 模型
│   └── version_history/           # 模型版本历史
│       ├── ml_entry_v1.pkl
│       ├── ml_entry_v2.pkl
│       └── ...
│
├── cache/                          # 🆕 缓存目录
│   └── features/                  # 特征缓存
│       ├── 2024-01-01_xxx.parquet
│       └── ...
│
└── tests/
    ├── unit/
    │   ├── test_entries.py
    │   ├── test_exits.py
    │   ├── test_risk_manager.py
    │   ├── test_backtest_engine.py
    │   ├── test_ml_ranker.py
    │   ├── test_feature_engine.py     # 🆕 特征引擎测试
    │   ├── test_label_generator.py    # 🆕 标签生成器测试
    │   └── test_model_trainer.py      # 🆕 模型训练器测试
    │
    └── integration/
        ├── test_end_to_end.py
        └── test_ml_workflow.py         # 🆕 ML 完整流程测试
```

---

## 🔗 相关链接

- **项目主页**: [Stock-Analysis Core](https://github.com/your-org/stock-analysis)
- **问题反馈**: [Issues](https://github.com/your-org/stock-analysis/issues)
- **API 文档**: [Sphinx Docs](../sphinx/build/html/index.html)

---

**文档版本**: v5.0.0
**最后更新**: 2026-02-07
**更新内容**: 新增完整的机器学习入场信号系统文档
**维护团队**: Quant Team
**项目状态**: 🎯 架构设计完成 + ML 系统完整文档
