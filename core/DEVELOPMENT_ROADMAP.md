# Core 模块后续开发路线图

## 📋 文档说明

**文档目的**：指导 Core 量化交易系统从当前 85% 完成度提升到生产级 100%

**适用人员**：量化策略开发者、后端工程师、系统架构师

**最后更新**：2026-01-29

---

## 🎯 开发目标

### 当前状态
- ✅ 数据层：完成 95%（多数据源、TimescaleDB）
- ✅ 特征层：完成 98%（125+ Alpha因子）
- ✅ 模型层：完成 85%（LightGBM/GRU/Ridge）
- ✅ 回测层：完成 80%（向量化引擎）
- ✅ **策略层：完成 90%** ⭐ NEW（5种策略，统一框架）
- ❌ **风控层：缺失**
- ⚠️  优化层：不完整

### 最终目标
- 🎯 完成度达到 **100%**
- 🎯 支持 **完整的量化交易工作流**
- 🎯 提供 **10+ 可用的交易策略**
- 🎯 实现 **实时风险监控**
- 🎯 支持 **自动参数优化**
- 🎯 具备 **生产环境部署能力**

---

## 📅 三阶段开发计划

### 阶段1：核心补充（1-2周）🔴 高优先级

**目标**：~~补充策略层和~~风险管理模块，使系统可用

**工作量估算**：~~60-80~~ 32-40 工时（策略层已完成 ✅）

#### 1.1 ~~实现交易策略层 (strategies/)~~ ✅ 已完成

**状态**：✅ 已完成（2026-01-29）

**时间**：~~5天 / 40工时~~

**目录结构**：
```
core/src/strategies/
├── __init__.py
├── base_strategy.py              # 策略基类 (8h)
├── signal_generator.py           # 信号生成器 (6h)
├── momentum_strategy.py          # 动量策略 (4h)
├── mean_reversion_strategy.py    # 均值回归策略 (4h)
├── ml_strategy.py                # 机器学习策略 (6h)
├── multi_factor_strategy.py      # 多因子策略 (6h)
├── strategy_combiner.py          # 策略组合器 (4h)
└── examples/                     # 使用示例 (2h)
    ├── example_momentum.py
    ├── example_ml.py
    └── example_multi_factor.py
```

**已实现功能** ✅：

1. **策略基类** ([base_strategy.py](core/src/strategies/base_strategy.py:1))
```python
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Optional

class BaseStrategy(ABC):
    """
    交易策略基类

    所有策略必须实现的方法：
    - generate_signals(): 生成买卖信号
    - get_positions(): 获取持仓建议
    - get_strategy_name(): 返回策略名称
    """

    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config

    @abstractmethod
    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: pd.DataFrame
    ) -> pd.DataFrame:
        """
        生成交易信号

        Args:
            prices: 价格数据 (index=date, columns=stock_codes)
            features: 特征数据

        Returns:
            signals: 信号DataFrame (值: 1=买入, 0=持有, -1=卖出)
        """
        pass

    @abstractmethod
    def calculate_scores(
        self,
        features: pd.DataFrame
    ) -> pd.DataFrame:
        """
        计算股票评分（用于排序选股）

        Returns:
            scores: 评分DataFrame (值越大越好)
        """
        pass

    def backtest(self, engine, prices, features):
        """回测接口"""
        signals = self.generate_signals(prices, features)
        return engine.backtest_long_only(signals, prices)
```

2. **动量策略** ([momentum_strategy.py](core/src/strategies/momentum_strategy.py:1))
```python
class MomentumStrategy(BaseStrategy):
    """
    动量策略：买入近期强势股，持有一段时间后卖出

    参数：
        - lookback_period: 回看期（默认20天）
        - holding_period: 持仓期（默认5天）
        - top_n: 选股数量（默认50）
    """

    def generate_signals(self, prices, features):
        # 计算动量得分：过去N日收益率
        momentum = prices.pct_change(self.config['lookback_period'])

        # 每期选择动量最高的top_n只股票
        signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)

        for date in signals.index:
            scores = momentum.loc[date].dropna()
            top_stocks = scores.nlargest(self.config['top_n']).index
            signals.loc[date, top_stocks] = 1

        return signals

    def calculate_scores(self, features):
        # 使用 MOM20 因子作为评分
        return features['MOM20']
```

3. **多因子策略** ([multi_factor_strategy.py](core/src/strategies/multi_factor_strategy.py:1))
```python
class MultiFactorStrategy(BaseStrategy):
    """
    多因子策略：结合多个Alpha因子进行选股

    参数：
        - factors: 因子列表 ['MOM20', 'REV5', 'VOLATILITY20']
        - weights: 因子权重 [0.4, 0.3, 0.3]
        - top_n: 选股数量
    """

    def calculate_scores(self, features):
        # 因子标准化
        normalized = features[self.config['factors']].rank(pct=True)

        # 加权求和
        weights = self.config['weights']
        scores = sum(normalized[f] * w for f, w in zip(self.config['factors'], weights))

        return scores

    def generate_signals(self, prices, features):
        scores = self.calculate_scores(features)

        signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)
        for date in signals.index:
            if date in scores.index:
                top_stocks = scores.loc[date].nlargest(self.config['top_n']).index
                signals.loc[date, top_stocks] = 1

        return signals
```

4. **机器学习策略** ([ml_strategy.py](core/src/strategies/ml_strategy.py:1))
```python
class MLStrategy(BaseStrategy):
    """
    机器学习策略：使用训练好的模型预测收益率

    参数：
        - model: 已训练的模型（LightGBM/GRU）
        - threshold: 预测阈值（默认0.01，即预测收益>1%才买入）
        - top_n: 选股数量
    """

    def __init__(self, name, config, model):
        super().__init__(name, config)
        self.model = model

    def calculate_scores(self, features):
        # 使用模型预测
        predictions = self.model.predict(features)
        return pd.Series(predictions, index=features.index)

    def generate_signals(self, prices, features):
        scores = self.calculate_scores(features)

        # 选择预测收益最高的股票
        signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)
        for date in signals.index:
            if date in scores.index:
                # 只买入预测收益 > threshold 的股票
                candidates = scores.loc[date][scores.loc[date] > self.config['threshold']]
                top_stocks = candidates.nlargest(self.config['top_n']).index
                signals.loc[date, top_stocks] = 1

        return signals
```

**测试完成情况** ✅：
- ✅ 单元测试：7个测试文件，108个测试用例
- ✅ 回测示例：3个完整示例（动量、均值回归、策略组合）
- ✅ 性能测试：通过（向量化计算）
- ⚠️  测试通过率：52%（需要优化，见下一节）

**后续优化**：
- 🔄 优化测试用例，提升通过率到90%+（预计2天）
- 🔄 添加更多策略示例
- 🔄 完善策略文档

---

#### 1.2 实现风险管理模块 (risk_management/)

**时间**：4天 / 32工时

**目录结构**：
```
core/src/risk_management/
├── __init__.py
├── var_calculator.py             # VaR计算器 (6h)
├── drawdown_controller.py        # 回撤控制器 (5h)
├── position_sizer.py             # 仓位计算器 (5h)
├── correlation_monitor.py        # 相关性监控 (4h)
├── risk_monitor.py               # 实时风险监控 (6h)
├── stress_test.py                # 压力测试 (4h)
└── examples/                     # 使用示例 (2h)
    └── example_risk_monitor.py
```

**核心功能**：

1. **VaR 计算器** ([var_calculator.py](core/src/risk_management/var_calculator.py:1))
```python
class VaRCalculator:
    """
    风险价值(Value at Risk)计算器

    支持三种方法：
    - historical: 历史模拟法
    - variance_covariance: 方差-协方差法
    - monte_carlo: 蒙特卡洛模拟法
    """

    def calculate_historical_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """
        历史模拟法计算VaR

        Args:
            returns: 历史收益率序列
            confidence_level: 置信水平（默认95%）

        Returns:
            VaR值（负数表示潜在损失）
        """
        return returns.quantile(1 - confidence_level)

    def calculate_portfolio_var(
        self,
        portfolio_values: pd.Series,
        confidence_level: float = 0.95,
        holding_period: int = 1
    ) -> Dict[str, float]:
        """
        计算组合VaR

        Returns:
            {
                'var_1day': 1日VaR,
                'var_5day': 5日VaR,
                'cvar': 条件VaR (CVaR/Expected Shortfall)
            }
        """
        returns = portfolio_values.pct_change().dropna()

        # 1日VaR
        var_1day = self.calculate_historical_var(returns, confidence_level)

        # N日VaR（假设收益率独立同分布）
        var_nday = var_1day * np.sqrt(holding_period)

        # CVaR（VaR之下的平均损失）
        cvar = returns[returns <= var_1day].mean()

        return {
            'var_1day': var_1day,
            f'var_{holding_period}day': var_nday,
            'cvar': cvar
        }
```

2. **回撤控制器** ([drawdown_controller.py](core/src/risk_management/drawdown_controller.py:1))
```python
class DrawdownController:
    """
    回撤控制器：监控并控制最大回撤

    功能：
    - 实时计算当前回撤
    - 触发回撤警报
    - 自动减仓/停止交易
    """

    def __init__(self, max_drawdown: float = 0.15):
        """
        Args:
            max_drawdown: 最大允许回撤（默认15%）
        """
        self.max_drawdown = max_drawdown
        self.peak_value = 0
        self.current_drawdown = 0

    def calculate_drawdown(self, portfolio_values: pd.Series) -> pd.Series:
        """计算回撤序列"""
        peak = portfolio_values.expanding().max()
        drawdown = (portfolio_values - peak) / peak
        return drawdown

    def check_drawdown_limit(self, current_value: float) -> Dict[str, any]:
        """
        检查是否触发回撤限制

        Returns:
            {
                'current_drawdown': 当前回撤,
                'is_alert': 是否警报（>最大回撤的80%）,
                'should_stop': 是否应该停止交易,
                'action': 'reduce_position' | 'stop_trading' | 'continue'
            }
        """
        # 更新峰值
        if current_value > self.peak_value:
            self.peak_value = current_value

        # 计算当前回撤
        self.current_drawdown = (current_value - self.peak_value) / self.peak_value

        # 判断是否触发警报
        is_alert = abs(self.current_drawdown) > self.max_drawdown * 0.8
        should_stop = abs(self.current_drawdown) > self.max_drawdown

        # 决定动作
        if should_stop:
            action = 'stop_trading'
        elif is_alert:
            action = 'reduce_position'
        else:
            action = 'continue'

        return {
            'current_drawdown': self.current_drawdown,
            'is_alert': is_alert,
            'should_stop': should_stop,
            'action': action,
            'recommendation': self._get_recommendation(action)
        }

    def _get_recommendation(self, action: str) -> str:
        if action == 'stop_trading':
            return '回撤已超过限制，建议立即停止交易并清仓'
        elif action == 'reduce_position':
            return '回撤接近限制，建议减仓50%降低风险'
        else:
            return '回撤在控制范围内，可以继续交易'
```

3. **仓位计算器** ([position_sizer.py](core/src/risk_management/position_sizer.py:1))
```python
class PositionSizer:
    """
    仓位计算器：根据风险计算合理的仓位大小

    支持多种方法：
    - equal_weight: 等权重
    - risk_parity: 风险平价
    - kelly: 凯利公式
    - volatility_target: 目标波动率
    """

    def calculate_kelly_size(
        self,
        win_rate: float,
        win_loss_ratio: float,
        max_position: float = 0.2
    ) -> float:
        """
        凯利公式计算仓位

        Kelly % = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio

        Args:
            win_rate: 胜率（0-1）
            win_loss_ratio: 盈亏比（平均盈利/平均亏损）
            max_position: 最大仓位限制

        Returns:
            建议仓位比例（0-1）
        """
        kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio

        # 半凯利（保守）
        kelly = kelly * 0.5

        # 限制最大仓位
        return min(max(kelly, 0), max_position)

    def calculate_risk_parity_weights(
        self,
        returns: pd.DataFrame
    ) -> pd.Series:
        """
        风险平价权重计算

        每只股票的风险贡献相等

        Args:
            returns: 股票收益率DataFrame

        Returns:
            各股票权重Series
        """
        # 计算波动率
        volatilities = returns.std()

        # 风险平价：权重与波动率成反比
        inv_vol = 1 / volatilities
        weights = inv_vol / inv_vol.sum()

        return weights
```

4. **实时风险监控** ([risk_monitor.py](core/src/risk_management/risk_monitor.py:1))
```python
class RiskMonitor:
    """
    实时风险监控器：综合监控所有风险指标

    监控内容：
    - 组合VaR
    - 最大回撤
    - 仓位集中度
    - 行业集中度
    - 相关性风险
    """

    def __init__(self, config: Dict):
        self.var_calculator = VaRCalculator()
        self.drawdown_controller = DrawdownController(
            max_drawdown=config.get('max_drawdown', 0.15)
        )
        self.alerts = []

    def monitor(
        self,
        portfolio_value: float,
        positions: Dict,
        prices: Dict
    ) -> Dict[str, any]:
        """
        执行风险监控

        Returns:
            {
                'var': VaR指标,
                'drawdown': 回撤信息,
                'concentration': 集中度信息,
                'alerts': 警报列表,
                'overall_risk_level': 'low' | 'medium' | 'high'
            }
        """
        # 1. 计算VaR（假设有历史收益率数据）
        # var_metrics = self.var_calculator.calculate_portfolio_var(...)

        # 2. 检查回撤
        drawdown_info = self.drawdown_controller.check_drawdown_limit(portfolio_value)

        # 3. 检查仓位集中度
        concentration = self._check_concentration(positions, prices, portfolio_value)

        # 4. 汇总警报
        self.alerts = []
        if drawdown_info['is_alert']:
            self.alerts.append(f"回撤警报: {drawdown_info['current_drawdown']:.2%}")

        if concentration['max_position'] > 0.3:
            self.alerts.append(f"仓位过于集中: {concentration['max_stock']} 占比 {concentration['max_position']:.2%}")

        # 5. 评估整体风险等级
        overall_risk = self._assess_overall_risk(drawdown_info, concentration)

        return {
            'drawdown': drawdown_info,
            'concentration': concentration,
            'alerts': self.alerts,
            'overall_risk_level': overall_risk,
            'timestamp': pd.Timestamp.now()
        }

    def _check_concentration(self, positions, prices, total_value):
        """检查仓位集中度"""
        if not positions:
            return {'max_position': 0, 'max_stock': None}

        position_values = {
            stock: pos['shares'] * prices.get(stock, 0)
            for stock, pos in positions.items()
        }

        max_stock = max(position_values, key=position_values.get)
        max_position = position_values[max_stock] / total_value

        return {
            'max_stock': max_stock,
            'max_position': max_position,
            'top5_concentration': sum(sorted(position_values.values(), reverse=True)[:5]) / total_value
        }

    def _assess_overall_risk(self, drawdown_info, concentration):
        """评估整体风险等级"""
        risk_score = 0

        # 回撤风险
        if abs(drawdown_info['current_drawdown']) > 0.1:
            risk_score += 2
        elif abs(drawdown_info['current_drawdown']) > 0.05:
            risk_score += 1

        # 集中度风险
        if concentration['max_position'] > 0.3:
            risk_score += 2
        elif concentration['max_position'] > 0.2:
            risk_score += 1

        # 评级
        if risk_score >= 3:
            return 'high'
        elif risk_score >= 1:
            return 'medium'
        else:
            return 'low'
```

**测试要求**：
- 单元测试覆盖率 > 80%
- 压力测试（极端市场情况）
- 性能测试（实时监控延迟 < 100ms）

---

#### 1.3 完善因子分析工具

**时间**：3天 / 24工时

**新增文件**：
```
core/src/features/
├── factor_analyzer.py            # 因子分析器 (8h)
├── ic_calculator.py              # IC计算器 (6h)
├── layering_test.py              # 分层测试 (6h)
└── decay_analyzer.py             # 衰减分析 (4h)
```

**核心功能**：

1. **IC 计算器** ([ic_calculator.py](core/src/features/ic_calculator.py:1))
```python
class ICCalculator:
    """
    信息系数(Information Coefficient)计算器

    IC = Corr(因子值, 未来收益率)

    用于评估因子的预测能力
    """

    def calculate_ic(
        self,
        factor: pd.Series,
        future_returns: pd.Series,
        method: str = 'pearson'
    ) -> float:
        """
        计算IC

        Args:
            factor: 因子值序列
            future_returns: 未来收益率序列
            method: 'pearson' | 'spearman'

        Returns:
            IC值（-1到1）
        """
        if method == 'pearson':
            return factor.corr(future_returns)
        elif method == 'spearman':
            return factor.corr(future_returns, method='spearman')

    def calculate_ic_series(
        self,
        factors: pd.DataFrame,
        prices: pd.DataFrame,
        forward_periods: int = 5
    ) -> pd.DataFrame:
        """
        计算IC时间序列

        Args:
            factors: 因子DataFrame (index=date, columns=stock_codes)
            prices: 价格DataFrame
            forward_periods: 前瞻期（天数）

        Returns:
            IC时间序列DataFrame (index=date, columns=factor_names)
        """
        # 计算未来收益率
        future_returns = prices.pct_change(forward_periods).shift(-forward_periods)

        ic_series = {}
        for date in factors.index:
            factor_values = factors.loc[date]
            return_values = future_returns.loc[date]

            # 删除NaN
            valid = factor_values.notna() & return_values.notna()

            if valid.sum() > 10:  # 至少10个有效样本
                ic = self.calculate_ic(
                    factor_values[valid],
                    return_values[valid]
                )
                ic_series[date] = ic

        return pd.Series(ic_series)

    def calculate_ic_ir(self, ic_series: pd.Series) -> Dict[str, float]:
        """
        计算IC和ICIR

        Returns:
            {
                'mean_ic': IC均值,
                'ic_std': IC标准差,
                'ic_ir': ICIR (IC均值/IC标准差),
                'ic_win_rate': IC>0的比例
            }
        """
        return {
            'mean_ic': ic_series.mean(),
            'ic_std': ic_series.std(),
            'ic_ir': ic_series.mean() / ic_series.std() if ic_series.std() > 0 else 0,
            'ic_win_rate': (ic_series > 0).mean()
        }
```

2. **分层测试** ([layering_test.py](core/src/features/layering_test.py:1))
```python
class LayeringTest:
    """
    因子分层测试

    将股票按因子值分为N层，比较各层的收益表现
    """

    def perform_layering_test(
        self,
        factor: pd.DataFrame,
        returns: pd.DataFrame,
        n_layers: int = 5
    ) -> pd.DataFrame:
        """
        执行分层测试

        Args:
            factor: 因子DataFrame
            returns: 收益率DataFrame
            n_layers: 分层数量（默认5层）

        Returns:
            各层收益统计DataFrame
        """
        layer_returns = {f'Layer_{i+1}': [] for i in range(n_layers)}

        for date in factor.index:
            if date not in returns.index:
                continue

            # 获取当期因子值和下期收益
            factor_values = factor.loc[date].dropna()
            next_returns = returns.loc[date]

            # 按因子值分层
            layers = pd.qcut(factor_values, n_layers, labels=False, duplicates='drop')

            # 计算各层平均收益
            for i in range(n_layers):
                stocks_in_layer = layers[layers == i].index
                layer_ret = next_returns[stocks_in_layer].mean()
                layer_returns[f'Layer_{i+1}'].append(layer_ret)

        # 统计各层表现
        summary = pd.DataFrame({
            'Mean_Return': {k: np.mean(v) for k, v in layer_returns.items()},
            'Std_Return': {k: np.std(v) for k, v in layer_returns.items()},
            'Sharpe': {k: np.mean(v) / np.std(v) if np.std(v) > 0 else 0
                      for k, v in layer_returns.items()}
        })

        # 添加多空组合收益（最高层 - 最低层）
        long_short = [h - l for h, l in zip(
            layer_returns[f'Layer_{n_layers}'],
            layer_returns['Layer_1']
        )]
        summary.loc['Long_Short'] = [
            np.mean(long_short),
            np.std(long_short),
            np.mean(long_short) / np.std(long_short) if np.std(long_short) > 0 else 0
        ]

        return summary
```

**测试要求**：
- 在真实数据上验证（至少3个因子）
- 生成可视化报告（IC序列图、分层收益图）

---

#### 1.4 完善数据质量检查

**时间**：2天 / 16工时

**新增文件**：
```
core/src/data/
├── data_validator.py             # 数据验证器 (5h)
├── outlier_detector.py           # 异常值检测 (5h)
├── suspend_filter.py             # 停牌过滤 (4h)
└── missing_handler.py            # 缺失值处理 (2h)
```

**核心功能**：

1. **异常值检测器** ([outlier_detector.py](core/src/data/outlier_detector.py:1))
```python
class OutlierDetector:
    """
    异常值检测器

    检测价格数据中的异常值：
    - 单日暴涨暴跌（>20%）
    - 价格突变
    - 成交量异常
    """

    def detect_price_outliers(
        self,
        df: pd.DataFrame,
        method: str = 'iqr'
    ) -> pd.DataFrame:
        """
        检测价格异常值

        Args:
            df: 价格DataFrame
            method: 'iqr' | 'zscore' | 'isolation_forest'

        Returns:
            异常标记DataFrame (True=异常)
        """
        if method == 'iqr':
            return self._detect_by_iqr(df)
        elif method == 'zscore':
            return self._detect_by_zscore(df)

    def _detect_by_iqr(self, df: pd.DataFrame) -> pd.DataFrame:
        """IQR方法检测异常值"""
        returns = df.pct_change()

        Q1 = returns.quantile(0.25)
        Q3 = returns.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - 3 * IQR
        upper_bound = Q3 + 3 * IQR

        outliers = (returns < lower_bound) | (returns > upper_bound)

        return outliers

    def filter_outliers(
        self,
        df: pd.DataFrame,
        outliers: pd.DataFrame,
        method: str = 'remove'
    ) -> pd.DataFrame:
        """
        处理异常值

        Args:
            method: 'remove' | 'winsorize' | 'interpolate'
        """
        if method == 'remove':
            return df.where(~outliers)
        elif method == 'winsorize':
            # 将异常值替换为边界值
            return df.clip(lower=df.quantile(0.01), upper=df.quantile(0.99), axis=1)
```

2. **停牌过滤器** ([suspend_filter.py](core/src/data/suspend_filter.py:1))
```python
class SuspendFilter:
    """
    停牌股票过滤器

    识别并过滤停牌股票：
    - 成交量为0
    - 连续多日价格不变
    """

    def detect_suspended_stocks(
        self,
        prices: pd.DataFrame,
        volumes: pd.DataFrame
    ) -> pd.DataFrame:
        """
        检测停牌股票

        Returns:
            停牌标记DataFrame (True=停牌)
        """
        # 方法1：成交量为0
        zero_volume = (volumes == 0) | volumes.isna()

        # 方法2：价格连续3天不变
        price_unchanged = (prices == prices.shift(1)) & \
                         (prices == prices.shift(2)) & \
                         (prices == prices.shift(3))

        # 合并
        suspended = zero_volume | price_unchanged

        return suspended

    def filter_suspended(
        self,
        df: pd.DataFrame,
        suspended: pd.DataFrame
    ) -> pd.DataFrame:
        """过滤掉停牌股票的数据"""
        return df.where(~suspended)
```

**交付物**：
- 4个新模块的代码
- 单元测试（覆盖率>80%）
- 使用示例

---

### 阶段2：功能增强（2-3周）🟡 中优先级

**目标**：提升系统性能和易用性

**工作量估算**：80-100 工时

#### 2.1 实现参数优化模块 (optimization/)

**时间**：5天 / 40工时

**目录结构**：
```
core/src/optimization/
├── __init__.py
├── grid_search.py                # 网格搜索 (8h)
├── bayesian_optimizer.py         # 贝叶斯优化 (10h)
├── walk_forward.py               # Walk-Forward优化 (10h)
├── genetic_algorithm.py          # 遗传算法 (8h)
└── examples/                     # 使用示例 (4h)
    ├── example_grid_search.py
    └── example_walk_forward.py
```

**核心功能**：

1. **网格搜索** - 遍历所有参数组合
2. **贝叶斯优化** - 智能搜索最优参数（使用 scikit-optimize）
3. **Walk-Forward 优化** - 滚动优化，避免过拟合
4. **遗传算法** - 进化算法寻优

**示例代码**：
```python
class GridSearchOptimizer:
    """网格搜索优化器"""

    def optimize(
        self,
        strategy_class,
        param_grid: Dict[str, List],
        train_data: Dict,
        validation_data: Dict,
        metric: str = 'sharpe_ratio'
    ) -> Dict:
        """
        网格搜索最优参数

        Args:
            strategy_class: 策略类
            param_grid: 参数网格，如 {'lookback': [10, 20, 30], 'top_n': [30, 50]}
            train_data: 训练数据
            validation_data: 验证数据
            metric: 优化指标

        Returns:
            {
                'best_params': 最优参数,
                'best_score': 最优得分,
                'all_results': 所有结果列表
            }
        """
        from itertools import product

        # 生成所有参数组合
        keys = param_grid.keys()
        values = param_grid.values()
        param_combinations = [dict(zip(keys, v)) for v in product(*values)]

        results = []
        for params in param_combinations:
            # 创建策略
            strategy = strategy_class('test', params)

            # 回测
            backtest_result = strategy.backtest(
                train_data['engine'],
                train_data['prices'],
                train_data['features']
            )

            # 计算指标
            score = self._calculate_metric(backtest_result, metric)

            results.append({
                'params': params,
                'score': score
            })

        # 找到最优参数
        best = max(results, key=lambda x: x['score'])

        return {
            'best_params': best['params'],
            'best_score': best['score'],
            'all_results': results
        }
```

---

#### 2.2 添加并行计算支持

**时间**：3天 / 24工时

**优化内容**：
1. 多股票并行特征计算（multiprocessing）
2. 异步数据下载（asyncio）
3. 批量模型训练（joblib）

**示例代码**：
```python
# features/parallel_calculator.py
from joblib import Parallel, delayed
from multiprocessing import cpu_count

class ParallelFeatureCalculator:
    """并行特征计算器"""

    def calculate_features_parallel(
        self,
        stock_list: List[str],
        n_jobs: int = -1
    ) -> Dict[str, pd.DataFrame]:
        """
        并行计算多只股票的特征

        Args:
            stock_list: 股票列表
            n_jobs: 并行任务数（-1=使用所有CPU核心）

        Returns:
            {stock_code: features_df}
        """
        if n_jobs == -1:
            n_jobs = cpu_count()

        # 并行计算
        results = Parallel(n_jobs=n_jobs)(
            delayed(self._calculate_single_stock)(code)
            for code in stock_list
        )

        # 组合结果
        return dict(zip(stock_list, results))

    def _calculate_single_stock(self, stock_code: str) -> pd.DataFrame:
        """计算单只股票的特征"""
        # 加载数据
        df = self.db.load_daily_data(stock_code)

        # 计算特征
        af = AlphaFactors(df)
        features = af.add_all_alpha_factors()

        return features
```

---

#### 2.3 添加性能监控和告警

**时间**：4天 / 32工时

**新增文件**：
```
core/src/monitoring/
├── __init__.py
├── performance_monitor.py        # 性能监控 (8h)
├── alert_manager.py              # 告警管理器 (8h)
├── metrics_collector.py          # 指标收集器 (8h)
└── reporters/                    # 报告生成器 (8h)
    ├── email_reporter.py
    └── dingtalk_reporter.py
```

**核心功能**：
1. 计算时间监控（装饰器）
2. 内存使用监控
3. 异常告警（钉钉/邮件）
4. 日报/周报生成

---

#### 2.4 扩展回测引擎功能

**时间**：3天 / 24工时

**新增功能**：
1. 支持做空（融券）
2. 支持期货对冲
3. 支持多种调仓频率（日/周/月）
4. 支持滑点模型优化
5. 支持交易成本分析

---

### 阶段3：生产准备（3-4周）🟢 低优先级

**目标**：实盘交易准备

**工作量估算**：100-120 工时

#### 3.1 实现实盘交易接口 (trading/)

**时间**：10天 / 80工时

**注意**：此模块需要券商授权，建议先实现模拟交易

**目录结构**：
```
core/src/trading/
├── __init__.py
├── broker_interface.py           # 券商接口基类
├── order_manager.py              # 订单管理器
├── execution_engine.py           # 执行引擎
├── trade_monitor.py              # 交易监控
├── paper_trading.py              # 模拟交易（优先实现）
└── adapters/                     # 券商适配器
    ├── __init__.py
    ├── xtp_adapter.py            # XTP接口
    └── simulator_adapter.py      # 模拟器
```

---

#### 3.2 完善文档和教程

**时间**：5天 / 40工时

**交付物**：
1. Sphinx API文档
2. Jupyter Notebook 教程（10+个）
3. 视频教程（可选）
4. FAQ文档

---

## 📝 开发规范

### 代码规范
1. **类型提示**：所有函数必须有类型提示
2. **文档字符串**：遵循 Google Style
3. **日志系统**：统一使用 Loguru
4. **异常处理**：明确的异常类型和错误信息

### 测试规范
1. **单元测试覆盖率** > 80%
2. **集成测试**：关键流程必须有集成测试
3. **性能测试**：新功能必须有性能基准

### Git规范
1. **分支策略**：feature/xxx, fix/xxx, refactor/xxx
2. **提交信息**：遵循 Conventional Commits
3. **代码审查**：所有代码必须经过Review

---

## 🎯 优先级说明

### 🔴 高优先级（必须完成）
- ~~策略层~~ ✅ 已完成
- 策略测试优化（提升通过率）
- 风险管理
- 因子分析工具

### 🟡 中优先级（建议完成）
- 参数优化
- 并行计算
- 性能监控

### 🟢 低优先级（可选）
- 实盘交易接口
- 市场中性策略
- 高级功能

---

## 📞 技术支持

如有问题，请参考：
1. [Core README](./README.md)
2. [架构分析文档](./ARCHITECTURE_ANALYSIS.md)
3. 提交 Issue 到 GitHub

---

**最后更新**：2026-01-29
**文档版本**：v1.0
**预计完成时间**：6-9周（根据优先级选择）
