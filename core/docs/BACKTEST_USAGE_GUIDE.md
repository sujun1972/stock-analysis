# 回测层使用指南

## 📋 目录

- [简介](#简介)
- [快速开始](#快速开始)
- [核心模块](#核心模块)
  - [回测引擎 (BacktestEngine)](#回测引擎-backtestengine)
  - [绩效分析器 (PerformanceAnalyzer)](#绩效分析器-performanceanalyzer)
  - [持仓管理器 (PositionManager)](#持仓管理器-positionmanager)
  - [成本分析器 (TradingCostAnalyzer)](#成本分析器-tradingcostanalyzer)
- [完整示例](#完整示例)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

---

## 简介

回测层提供了完整的量化策略回测框架，支持：

- ✅ **向量化回测**：高性能的批量计算
- ✅ **T+1 交易规则**：严格遵守A股交易规则
- ✅ **完整成本分析**：佣金、印花税、滑点全覆盖
- ✅ **丰富绩效指标**：15+ 专业绩效指标
- ✅ **灵活配置**：支持多种调仓频率和持仓策略

**适用场景**：
- 量化策略开发与验证
- 因子有效性测试
- 成本敏感性分析
- 参数优化与调优

---

## 快速开始

### 5分钟快速回测

```python
from src.backtest import BacktestEngine, PerformanceAnalyzer
import pandas as pd
import numpy as np

# 1. 准备数据
dates = pd.date_range('2023-01-01', periods=252, freq='D')
stocks = ['600000', '600001', '600002']

# 价格数据 (DataFrame: index=日期, columns=股票代码)
prices = pd.DataFrame(
    np.random.uniform(9, 11, (252, 3)),
    index=dates,
    columns=stocks
)

# 信号数据 (DataFrame: 值越大越看好)
signals = pd.DataFrame(
    np.random.uniform(-1, 1, (252, 3)),
    index=dates,
    columns=stocks
)

# 2. 创建回测引擎
engine = BacktestEngine(
    initial_capital=1000000,  # 初始资金100万
    commission_rate=0.0003,   # 佣金万三
    stamp_tax_rate=0.001,     # 印花税千一
    slippage=0.001            # 滑点千一
)

# 3. 运行回测
results = engine.backtest_long_only(
    signals=signals,
    prices=prices,
    top_n=2,                  # 每期持有2只股票
    holding_period=5,         # 最短持有5天
    rebalance_freq='W'        # 每周调仓
)

# 4. 分析绩效
analyzer = PerformanceAnalyzer(
    returns=results['daily_returns'],
    risk_free_rate=0.03
)
metrics = analyzer.calculate_all_metrics(verbose=True)

# 5. 查看成本分析
cost_metrics = results['cost_analysis']
print(f"\n总交易成本: {cost_metrics['total_cost']:,.2f} 元")
print(f"年化换手率: {cost_metrics['annual_turnover_rate']:.2f}")
print(f"成本拖累: {cost_metrics['cost_drag']*100:.2f}%")
```

**输出示例**：
```
开始回测...
初始资金: 1,000,000
选股数量: 2
调仓频率: W
持仓期: 5天

回测完成
最终资产: 1,125,430
总收益率: 12.54%

============================================================
策略绩效分析
============================================================

收益指标:
  总收益率:              12.54%
  年化收益率:            12.84%

风险指标:
  年化波动率:            18.32%
  最大回撤:              -8.45%

风险调整收益:
  夏普比率:              0.5372
  索提诺比率:            0.7821

总交易成本: 8,243.50 元
年化换手率: 3.24
成本拖累: 0.82%
```

---

## 核心模块

### 回测引擎 (BacktestEngine)

回测引擎是回测系统的核心，负责模拟交易执行和资金管理。

#### 初始化参数

```python
BacktestEngine(
    initial_capital: float = 1000000.0,     # 初始资金
    commission_rate: float = None,          # 佣金率（None=默认万三）
    stamp_tax_rate: float = None,           # 印花税率（None=默认千一）
    min_commission: float = None,           # 最小佣金（None=默认5元）
    slippage: float = 0.0,                  # 滑点比例
    verbose: bool = True                    # 是否打印日志
)
```

**参数说明**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `initial_capital` | 1,000,000 | 初始资金（元） |
| `commission_rate` | 0.0003 | 佣金费率（万三） |
| `stamp_tax_rate` | 0.001 | 印花税率（千一，仅卖出） |
| `min_commission` | 5.0 | 最小佣金（元） |
| `slippage` | 0.0 | 滑点比例（0.001=千一） |
| `verbose` | True | 是否打印详细信息 |

#### 核心方法

##### 1. 纯多头回测 (backtest_long_only)

```python
results = engine.backtest_long_only(
    signals: pd.DataFrame,        # 信号矩阵
    prices: pd.DataFrame,         # 价格矩阵
    top_n: int = 50,              # 每期选股数量
    holding_period: int = 5,      # 最短持仓期（天）
    rebalance_freq: str = 'W'     # 调仓频率
)
```

**调仓频率选项**：
- `'D'`: 每日调仓
- `'W'`: 每周调仓（周一）
- `'M'`: 每月调仓（月初）

**返回结果**：
```python
{
    'portfolio_value': pd.DataFrame,    # 组合净值序列
    'positions': List[Dict],            # 持仓历史
    'daily_returns': pd.Series,         # 每日收益率
    'cost_analysis': Dict,              # 成本分析结果
    'cost_analyzer': TradingCostAnalyzer  # 成本分析器对象
}
```

##### 2. 市场中性回测 (backtest_market_neutral)

```python
# 注意：当前版本暂不支持
results = engine.backtest_market_neutral(
    signals=signals,
    prices=prices,
    top_n=20,      # 做多前20只
    bottom_n=20    # 做空后20只
)
# 抛出 NotImplementedError（A股融券成本高）
```

---

### 绩效分析器 (PerformanceAnalyzer)

计算策略的各项绩效指标。

#### 初始化

```python
from src.backtest import PerformanceAnalyzer

analyzer = PerformanceAnalyzer(
    returns: pd.Series,                    # 收益率序列
    benchmark_returns: pd.Series = None,   # 基准收益率（可选）
    risk_free_rate: float = 0.03,          # 无风险利率（年化）
    periods_per_year: int = 252            # 年化因子
)
```

#### 核心指标方法

##### 收益指标

```python
# 总收益率
total_return = analyzer.total_return()  # 例：0.1254 (12.54%)

# 年化收益率
ann_return = analyzer.annualized_return()  # 例：0.1284 (12.84%)

# 累计收益曲线
cum_returns = analyzer.cumulative_returns()  # pd.Series
```

##### 风险指标

```python
# 年化波动率
volatility = analyzer.volatility(annualize=True)  # 例：0.1832 (18.32%)

# 最大回撤
max_dd = analyzer.max_drawdown()  # 例：-0.0845 (-8.45%)

# 最大回撤持续期（天数）
max_dd_duration = analyzer.max_drawdown_duration()  # 例：45

# 下行偏差
downside_dev = analyzer.downside_deviation()  # 例：0.1245
```

##### 风险调整收益

```python
# 夏普比率
sharpe = analyzer.sharpe_ratio()  # 例：0.5372

# 索提诺比率
sortino = analyzer.sortino_ratio()  # 例：0.7821

# 卡玛比率
calmar = analyzer.calmar_ratio()  # 例：1.52
```

##### 相对基准指标

```python
# 需要提供 benchmark_returns
analyzer = PerformanceAnalyzer(
    returns=strategy_returns,
    benchmark_returns=hs300_returns
)

# Alpha（年化超额收益）
alpha = analyzer.information_ratio()  # 例：0.0234 (2.34%)

# Beta（系统性风险）
metrics = analyzer.calculate_all_metrics()
beta = metrics['beta']  # 例：0.85

# 信息比率
ir = metrics['information_ratio']  # 例：0.45
```

##### 交易统计

```python
# 胜率
win_rate = analyzer.win_rate()  # 例：0.5634 (56.34%)

# 盈亏比
profit_factor = analyzer.profit_factor()  # 例：1.52

# 平均盈利
avg_win = analyzer.average_win()  # 例：0.0123 (1.23%)

# 平均亏损
avg_loss = analyzer.average_loss()  # 例：-0.0089 (-0.89%)

# 盈亏比率
win_loss_ratio = analyzer.win_loss_ratio()  # 例：1.38
```

#### 综合分析

```python
# 计算所有指标（一次性）
metrics = analyzer.calculate_all_metrics(verbose=True)

# 返回字典包含所有指标
print(metrics.keys())
# dict_keys(['total_return', 'annualized_return', 'volatility',
#            'max_drawdown', 'sharpe_ratio', 'sortino_ratio', ...])
```

---

### 持仓管理器 (PositionManager)

管理股票持仓、计算权重、执行风险控制。

#### 初始化

```python
from src.backtest import PositionManager

manager = PositionManager(
    initial_capital=1000000,      # 初始资金
    max_position_pct=0.2,         # 单只股票最大仓位20%
    max_single_loss_pct=0.05,     # 单只股票最大亏损5%（止损）
    min_position_value=10000      # 最小持仓市值
)
```

#### 核心方法

##### 1. 添加持仓

```python
from datetime import datetime

# 买入股票
manager.add_position(
    stock_code='600000',
    shares=1000,                  # 股数
    entry_price=10.0,             # 买入价
    entry_date=datetime(2023, 1, 1),
    entry_cost=30.5               # 买入成本（佣金等）
)
```

##### 2. 卖出持仓

```python
# 部分卖出
pnl = manager.remove_position(
    stock_code='600000',
    shares=500,                   # 卖出500股
    exit_price=11.0,              # 卖出价
    exit_cost=25.0                # 卖出成本
)
print(f"实现盈亏: {pnl:.2f} 元")
```

##### 3. 计算总资产

```python
current_prices = {
    '600000': 11.5,
    '600001': 15.2
}

total_value = manager.calculate_total_value(current_prices)
print(f"总资产: {total_value:,.0f} 元")
```

##### 4. 计算持仓权重

```python
weights = manager.calculate_position_weights(current_prices)

for stock, weight in weights.items():
    print(f"{stock}: {weight*100:.2f}%")
# 600000: 35.20%
# 600001: 28.50%
```

##### 5. 获取持仓摘要

```python
summary = manager.get_summary(current_prices)

print(summary)
# {
#     'total_value': 1125430.50,
#     'cash': 324500.00,
#     'holdings_value': 800930.50,
#     'position_count': 2,
#     'total_return': 0.1254,
#     'cash_ratio': 0.288
# }
```

---

### 成本分析器 (TradingCostAnalyzer)

深度分析交易成本，识别成本优化机会。

#### 自动集成

回测引擎会自动记录所有交易到成本分析器：

```python
results = engine.backtest_long_only(...)

# 成本分析结果已自动计算
cost_metrics = results['cost_analysis']
cost_analyzer = results['cost_analyzer']
```

#### 成本指标

##### 1. 总成本统计

```python
cost_metrics = results['cost_analysis']

print(f"总成本: {cost_metrics['total_cost']:,.2f} 元")
print(f"  佣金: {cost_metrics['total_commission']:,.2f} 元")
print(f"  印花税: {cost_metrics['total_stamp_tax']:,.2f} 元")
print(f"  滑点: {cost_metrics['total_slippage']:,.2f} 元")

# 成本构成比例
print(f"\n成本构成:")
print(f"  佣金占比: {cost_metrics['commission_pct']*100:.1f}%")
print(f"  印花税占比: {cost_metrics['stamp_tax_pct']*100:.1f}%")
print(f"  滑点占比: {cost_metrics['slippage_pct']*100:.1f}%")
```

##### 2. 换手率

```python
# 年化换手率
annual_turnover = cost_metrics['annual_turnover_rate']
print(f"年化换手率: {annual_turnover:.2f}")
# 3.24 表示每年全仓换手3.24次

# 总换手率
total_turnover = cost_metrics['total_turnover_rate']
print(f"总换手率: {total_turnover:.2f}")
```

##### 3. 成本影响

```python
# 成本占初始资金比例
cost_to_capital = cost_metrics['cost_to_capital_ratio']
print(f"成本/初始资金: {cost_to_capital*100:.2f}%")

# 成本占总收益比例
cost_to_profit = cost_metrics['cost_to_profit_ratio']
print(f"成本/总收益: {cost_to_profit*100:.2f}%")

# 成本拖累（收益率下降）
cost_drag = cost_metrics['cost_drag']
print(f"成本拖累: {cost_drag*100:.2f}%")

# 对比有无成本的收益率
print(f"有成本收益率: {cost_metrics['return_with_cost']*100:.2f}%")
print(f"无成本收益率: {cost_metrics['return_without_cost']*100:.2f}%")
```

##### 4. 交易统计

```python
print(f"总交易次数: {cost_metrics['n_trades']}")
print(f"  买入次数: {cost_metrics['n_buy_trades']}")
print(f"  卖出次数: {cost_metrics['n_sell_trades']}")
print(f"平均每笔成本: {cost_metrics['avg_cost_per_trade']:.2f} 元")
```

#### 深度分析

##### 1. 按股票统计成本

```python
cost_analyzer = results['cost_analyzer']

cost_by_stock = cost_analyzer.calculate_cost_by_stock()
print(cost_by_stock)

#           trade_count  total_value  total_cost  commission  stamp_tax  slippage  cost_ratio
# 600000             24    2450300.0      3245.2      1523.4     1345.6     376.2    0.001325
# 600001             18    1895600.0      2567.8      1201.5     1056.3     310.0    0.001354
```

##### 2. 成本时间序列

```python
cost_over_time = cost_analyzer.calculate_cost_over_time()
print(cost_over_time.tail())

#              commission  stamp_tax  slippage  total_cost  cumulative_total_cost
# 2023-11-20       156.3      124.5      45.2       326.0                  7854.2
# 2023-11-27       142.8      115.6      41.3       299.7                  8153.9
```

##### 3. 成本场景模拟

```python
# 模拟不同成本下的收益
scenarios = cost_analyzer.simulate_cost_scenarios(
    portfolio_values=results['portfolio_value']['total'],
    cost_multipliers=[0.5, 0.8, 1.0, 1.5, 2.0]  # 成本减半/翻倍等
)

print(scenarios)

#    cost_multiplier  total_cost  final_value  total_return  annualized_return
# 0              0.5      4121.7    1129551.8      0.129552           0.132450
# 1              0.8      6594.7    1127079.1      0.127079           0.129920
# 2              1.0      8243.4    1125430.4      0.125430           0.128240
# 3              1.5     12365.1    1121308.9      0.121309           0.124060
# 4              2.0     16486.8    1117187.2      0.117187           0.119880
```

##### 4. 完整成本报告

```python
# 打印完整成本分析报告
cost_analyzer.analyze_all(
    portfolio_returns=results['daily_returns'],
    portfolio_values=results['portfolio_value']['total'],
    verbose=True  # 打印详细报告
)
```

**输出示例**：
```
============================================================
交易成本分析报告
============================================================

📊 总成本:
  总成本:                     8,243.50 元
    - 佣金:                   3,856.20 元 ( 46.8%)
    - 印花税:                 3,421.80 元 ( 41.5%)
    - 滑点:                     965.50 元 ( 11.7%)

📈 换手率:
  年化换手率:                         3.24
  总换手率:                           3.24

🔄 交易统计:
  总交易次数:                           84 次
    - 买入次数:                         42 次
    - 卖出次数:                         42 次
  平均每笔成本:                      98.14 元

💰 成本影响:
  成本占初始资金:                    0.82%
  成本占总收益:                      6.57%
  成本拖累:                          0.82%
  有成本收益率:                     12.54%
  无成本收益率:                     13.36%
============================================================
```

---

## 完整示例

### 示例1：基础动量策略回测

```python
import pandas as pd
import numpy as np
from src.backtest import BacktestEngine, PerformanceAnalyzer

# 1. 加载真实数据（示例）
def load_market_data():
    # 假设已有数据加载函数
    prices = pd.read_csv('stock_prices.csv', index_col=0, parse_dates=True)
    return prices

prices = load_market_data()

# 2. 生成动量信号
def calculate_momentum_signals(prices, lookback=20):
    """计算过去N日收益率作为信号"""
    signals = prices.pct_change(lookback)
    return signals

signals = calculate_momentum_signals(prices, lookback=20)

# 3. 回测配置
backtest_config = {
    'initial_capital': 1000000,
    'top_n': 30,
    'holding_period': 10,
    'rebalance_freq': 'W'
}

# 4. 运行回测
engine = BacktestEngine(
    initial_capital=backtest_config['initial_capital'],
    commission_rate=0.0003,
    stamp_tax_rate=0.001,
    slippage=0.001
)

results = engine.backtest_long_only(
    signals=signals,
    prices=prices,
    top_n=backtest_config['top_n'],
    holding_period=backtest_config['holding_period'],
    rebalance_freq=backtest_config['rebalance_freq']
)

# 5. 绩效分析
analyzer = PerformanceAnalyzer(
    returns=results['daily_returns'],
    risk_free_rate=0.03
)

print("\n" + "="*60)
print("动量策略回测结果")
print("="*60)

metrics = analyzer.calculate_all_metrics(verbose=True)

# 6. 成本分析
print("\n成本分析:")
cost_metrics = results['cost_analysis']
print(f"总成本: {cost_metrics['total_cost']:,.2f} 元")
print(f"成本拖累: {cost_metrics['cost_drag']*100:.2f}%")
print(f"年化换手率: {cost_metrics['annual_turnover_rate']:.2f}")

# 7. 保存结果
results['portfolio_value'].to_csv('backtest_portfolio_value.csv')
pd.Series(metrics).to_csv('backtest_metrics.csv')
```

### 示例2：多策略对比

```python
from src.backtest import BacktestEngine, PerformanceAnalyzer

def backtest_strategy(signals, prices, name):
    """回测单个策略"""
    engine = BacktestEngine(initial_capital=1000000)

    results = engine.backtest_long_only(
        signals=signals,
        prices=prices,
        top_n=30,
        holding_period=5,
        rebalance_freq='W'
    )

    analyzer = PerformanceAnalyzer(results['daily_returns'])
    metrics = analyzer.calculate_all_metrics(verbose=False)

    return {
        'name': name,
        'return': metrics['annualized_return'],
        'sharpe': metrics['sharpe_ratio'],
        'max_dd': metrics['max_drawdown'],
        'turnover': results['cost_analysis']['annual_turnover_rate']
    }

# 定义多个策略
strategies = {
    'MOM20': calculate_momentum_signals(prices, 20),
    'MOM60': calculate_momentum_signals(prices, 60),
    'REV5': -prices.pct_change(5),  # 反转策略
}

# 回测所有策略
comparison = []
for name, signals in strategies.items():
    result = backtest_strategy(signals, prices, name)
    comparison.append(result)

# 对比结果
comparison_df = pd.DataFrame(comparison)
print("\n策略对比:")
print(comparison_df.to_string(index=False))

# 输出：
#    name    return  sharpe   max_dd  turnover
#   MOM20    0.1284  0.5372  -0.0845      3.24
#   MOM60    0.0956  0.4231  -0.1023      2.15
#    REV5    0.0723  0.3145  -0.1345      5.67
```

### 示例3：成本优化分析

```python
from src.backtest import BacktestEngine

def test_rebalance_frequency(signals, prices):
    """测试不同调仓频率对成本的影响"""
    frequencies = ['D', 'W', 'M']
    results_list = []

    for freq in frequencies:
        engine = BacktestEngine(initial_capital=1000000)

        results = engine.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=30,
            holding_period=1 if freq == 'D' else 5,
            rebalance_freq=freq
        )

        analyzer = PerformanceAnalyzer(results['daily_returns'])
        metrics = analyzer.calculate_all_metrics(verbose=False)
        cost = results['cost_analysis']

        results_list.append({
            'freq': freq,
            'return': metrics['annualized_return'],
            'cost': cost['total_cost'],
            'turnover': cost['annual_turnover_rate'],
            'cost_drag': cost['cost_drag'],
            'n_trades': cost['n_trades']
        })

    comparison = pd.DataFrame(results_list)
    print("\n调仓频率对比:")
    print(comparison.to_string(index=False))

    return comparison

# 运行分析
freq_comparison = test_rebalance_frequency(signals, prices)

# 输出：
#  freq    return      cost  turnover  cost_drag  n_trades
#     D    0.1456  28543.20     12.45     0.0285       504
#     W    0.1284   8243.50      3.24     0.0082        84
#     M    0.1123   2156.30      1.08     0.0022        24
```

---

## 最佳实践

### 1. 数据准备

✅ **推荐做法**：
```python
# 确保数据对齐和清洗
signals = signals.dropna()  # 移除缺失值
prices = prices.dropna()

# 确保索引和列名一致
common_dates = signals.index.intersection(prices.index)
common_stocks = signals.columns.intersection(prices.columns)

signals = signals.loc[common_dates, common_stocks]
prices = prices.loc[common_dates, common_stocks]
```

❌ **避免**：
```python
# 不要使用未对齐的数据
results = engine.backtest_long_only(signals, prices)  # 可能产生错误结果
```

### 2. 信号设计

✅ **推荐做法**：
```python
# 信号应该是截面排序（横截面）
# 值越大 = 越看好

def good_signal_design(prices):
    # 计算动量
    momentum = prices.pct_change(20)

    # 横截面标准化（每天独立排名）
    signals = momentum.rank(axis=1, pct=True)

    return signals
```

❌ **避免**：
```python
# 不要使用绝对值作为信号
bad_signals = prices.pct_change(20)  # 不同股票不可比
```

### 3. 参数设置

✅ **合理的参数组合**：

| 调仓频率 | 持仓期 | 选股数 | 适用场景 |
|---------|--------|--------|----------|
| 日 (D) | 1-3天 | 10-30 | 高频策略 |
| 周 (W) | 5-10天 | 30-50 | 中频策略 |
| 月 (M) | 20-30天 | 50-100 | 低频策略 |

```python
# 中频策略示例（推荐）
engine.backtest_long_only(
    signals=signals,
    prices=prices,
    top_n=30,              # 分散风险
    holding_period=5,      # 1周
    rebalance_freq='W'     # 每周调仓
)
```

### 4. 成本设置

✅ **真实成本**：
```python
# A股散户典型成本（2024年）
engine = BacktestEngine(
    commission_rate=0.0003,   # 万三佣金
    stamp_tax_rate=0.001,     # 千一印花税
    min_commission=5.0,       # 最低5元
    slippage=0.001            # 千一滑点
)

# A股机构典型成本
engine = BacktestEngine(
    commission_rate=0.0001,   # 万一佣金
    stamp_tax_rate=0.001,     # 千一印花税
    min_commission=5.0,
    slippage=0.0005           # 万五滑点
)
```

### 5. 基准对比

✅ **加入基准收益**：
```python
# 加载沪深300指数收益
hs300_returns = load_benchmark_returns('000300')

# 创建分析器时传入基准
analyzer = PerformanceAnalyzer(
    returns=strategy_returns,
    benchmark_returns=hs300_returns,
    risk_free_rate=0.03
)

# 计算Alpha、Beta、信息比率
metrics = analyzer.calculate_all_metrics()
print(f"Alpha: {metrics['alpha']*100:.2f}%")
print(f"Beta: {metrics['beta']:.2f}")
print(f"信息比率: {metrics['information_ratio']:.2f}")
```

### 6. 过拟合预防

✅ **样本内/外分离**：
```python
# 训练期：2020-2022
train_dates = (prices.index >= '2020-01-01') & (prices.index < '2023-01-01')
train_results = engine.backtest_long_only(
    signals=signals.loc[train_dates],
    prices=prices.loc[train_dates],
    top_n=30,
    holding_period=5,
    rebalance_freq='W'
)

# 测试期：2023-2024
test_dates = prices.index >= '2023-01-01'
test_results = engine.backtest_long_only(
    signals=signals.loc[test_dates],
    prices=prices.loc[test_dates],
    top_n=30,
    holding_period=5,
    rebalance_freq='W'
)

# 对比样本内外表现
print(f"训练期夏普: {train_sharpe:.2f}")
print(f"测试期夏普: {test_sharpe:.2f}")
print(f"衰减率: {(train_sharpe - test_sharpe) / train_sharpe * 100:.1f}%")
```

---

## 常见问题

### Q1: 为什么回测收益远高于实盘？

**可能原因**：

1. **未来信息泄露**：信号使用了未来数据
   ```python
   # ❌ 错误：使用未来价格
   bad_signal = prices.shift(-5)  # 偷看未来

   # ✅ 正确：只使用历史数据
   good_signal = prices.pct_change(20)  # 过去20日收益
   ```

2. **交易成本设置过低**
   ```python
   # ✅ 使用真实成本
   engine = BacktestEngine(
       commission_rate=0.0003,
       slippage=0.001  # 不要设为0
   )
   ```

3. **未考虑流动性**
   - 回测假设无限流动性
   - 实盘可能无法成交

4. **幸存者偏差**
   - 回测数据只包含当前存活的股票
   - 已退市股票未纳入

### Q2: 如何选择合适的调仓频率？

**决策框架**：

| 因素 | 建议频率 |
|------|---------|
| 策略类型：高频 | 日度 (D) |
| 策略类型：趋势 | 周度 (W) 或 月度 (M) |
| 信号稳定性：低 | 降低频率 |
| 交易成本：高 | 降低频率 |
| 资金容量：大 | 降低频率 |

**测试方法**：
```python
# 回测不同频率并对比
for freq in ['D', 'W', 'M']:
    results = engine.backtest_long_only(..., rebalance_freq=freq)
    # 计算夏普比率 / 成本拖累
```

### Q3: 夏普比率多少算好？

**参考标准**（A股年化）：

| 夏普比率 | 评价 |
|---------|------|
| < 0.5 | 较差 |
| 0.5 - 1.0 | 一般 |
| 1.0 - 1.5 | 良好 |
| 1.5 - 2.0 | 优秀 |
| > 2.0 | 卓越（需警惕过拟合） |

**注意**：
- 夏普比率受无风险利率影响
- 不同市场标准不同
- 应与基准对比

### Q4: 最大回撤控制在多少合适？

**风险偏好参考**：

| 策略类型 | 建议最大回撤 |
|---------|------------|
| 保守型 | < 10% |
| 稳健型 | 10% - 15% |
| 积极型 | 15% - 25% |
| 激进型 | > 25% |

**回撤控制方法**：
```python
from src.risk_management import DrawdownController

# 在策略中加入回撤控制
controller = DrawdownController(max_drawdown=0.15)

# 每日检查
status = controller.check_drawdown_limit(current_value)
if status['should_stop']:
    # 停止交易或减仓
    pass
```

### Q5: 如何解读成本分析？

**关键指标解读**：

1. **年化换手率**
   - < 2: 低频策略
   - 2-5: 中频策略
   - > 5: 高频策略
   - > 10: 需优化（成本过高）

2. **成本拖累**
   - < 1%: 可接受
   - 1%-3%: 需关注
   - > 3%: 需优化策略

3. **成本占收益比**
   - < 10%: 健康
   - 10%-30%: 偏高
   - > 30%: 策略可能不可行

**优化建议**：
```python
# 如果成本过高
# 1. 降低调仓频率
rebalance_freq='M'  # 从周改为月

# 2. 减少选股数量（减少换仓）
top_n=20  # 从50减到20

# 3. 增加持仓期
holding_period=20  # 从5天增到20天
```

### Q6: 回测结果如何保存和分享？

```python
# 保存组合净值
results['portfolio_value'].to_csv('portfolio_value.csv')

# 保存绩效指标
metrics_df = pd.Series(metrics).to_frame('value')
metrics_df.to_csv('metrics.csv')

# 保存成本分析
cost_df = pd.Series(results['cost_analysis']).to_frame('value')
cost_df.to_csv('cost_analysis.csv')

# 保存交易记录
trades_df = results['cost_analyzer'].get_trades_dataframe()
trades_df.to_csv('trades.csv')
```

---

## 相关文档

- [策略层使用指南](./STRATEGY_USAGE_GUIDE.md)（待创建）
- [风控层使用指南](./RISK_MANAGEMENT_GUIDE.md)（待创建）
- [因子分析指南](./FACTOR_ANALYSIS_GUIDE.md)
- [模型使用指南](./MODEL_USAGE_GUIDE.md)

---

## 技术支持

如有问题，请：
1. 查看示例代码：`core/examples/backtest_*.py`
2. 运行集成测试：`pytest tests/integration/test_phase4_backtest.py`
3. 提交Issue到GitHub

---

**文档版本**: v1.0
**最后更新**: 2026-01-30
**维护者**: Stock Analysis Core Team
