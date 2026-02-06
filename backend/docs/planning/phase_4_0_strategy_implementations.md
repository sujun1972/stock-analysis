# Phase 4.0 策略实现文档

> **版本**: v1.0
> **日期**: 2026-02-06
> **上级文档**: [三层架构实施方案](./backtest_three_layer_architecture_implementation_plan.md)
> **当前阶段**: Phase 4.0 - 任务 4.0.3 至 4.0.4

---

## 📋 目录

- [任务 4.0.3：实现基础入场策略](#任务-403实现基础入场策略)
- [任务 4.0.4：实现基础退出策略](#任务-404实现基础退出策略)
- [策略使用示例](#策略使用示例)
- [测试计划](#测试计划)

---

## 任务 4.0.3：实现基础入场策略

### 目标

实现 3 个基础入场策略，覆盖常见的买入信号生成场景。

### 工作量

**预计耗时**：3-4 天

### 实施清单

| 策略 | 文件名 | 功能描述 | 关键参数 | 优先级 |
|------|--------|---------|---------|--------|
| **MABreakoutEntry** | `entries/ma_breakout_entry.py` | 均线突破入场 | short_window, long_window, min_breakout_pct | P0 |
| **RSIOversoldEntry** | `entries/rsi_oversold_entry.py` | RSI 超卖入场 | rsi_period, oversold_level, confirm_days | P0 |
| **ImmediateEntry** | `entries/immediate_entry.py` | 立即入场（用于测试） | weight_method | P1 |

---

### 实施详情

#### 1. MABreakoutEntry（均线突破入场策略）

**文件路径**：`backend/app/strategies/three_layer/entries/ma_breakout_entry.py`

**策略逻辑**：
1. 计算短期均线（如 5 日）和长期均线（如 20 日）
2. 当短期均线上穿长期均线时，产生买入信号
3. 可选：要求突破幅度达到一定比例（避免假突破）

**完整实现**：

```python
"""
均线突破入场策略
当短期均线上穿长期均线时买入
"""

from typing import Dict, List

import pandas as pd
from loguru import logger

from ..base.entry_strategy import EntryStrategy
from ..base.stock_selector import SelectorParameter


class MABreakoutEntry(EntryStrategy):
    """
    均线突破入场策略

    经典技术指标策略，适用于趋势市场

    策略逻辑：
    1. 计算短期均线（MA_short）和长期均线（MA_long）
    2. 检测金叉：MA_short 上穿 MA_long
    3. 可选：要求突破幅度 > min_breakout_pct（避免假突破）
    4. 对有买入信号的股票，分配等权重

    适用场景：
    - 趋势跟踪
    - 中长期交易
    - 配合动量选股器效果更佳

    注意事项：
    - 震荡市容易产生假突破
    - 建议配合 ATR 止损策略
    - 均线周期需根据市场环境调整
    """

    @property
    def id(self) -> str:
        return "ma_breakout"

    @property
    def name(self) -> str:
        return "均线突破入场"

    @property
    def description(self) -> str:
        return "短期均线上穿长期均线时买入，经典的趋势跟踪策略"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="short_window",
                label="短期均线周期",
                type="integer",
                default=5,
                min_value=2,
                max_value=60,
                step=1,
                description="短期移动平均线的窗口大小（天）",
                category="核心参数",
            ),
            SelectorParameter(
                name="long_window",
                label="长期均线周期",
                type="integer",
                default=20,
                min_value=5,
                max_value=200,
                step=5,
                description="长期移动平均线的窗口大小（天）",
                category="核心参数",
            ),
            SelectorParameter(
                name="min_breakout_pct",
                label="最小突破幅度（%）",
                type="float",
                default=0.0,
                min_value=0.0,
                max_value=5.0,
                step=0.1,
                description="短期均线必须超过长期均线至少此百分比才算有效突破（0=不限制）",
                category="高级选项",
            ),
            SelectorParameter(
                name="weight_method",
                label="权重分配方法",
                type="select",
                default="equal",
                options=[
                    {"value": "equal", "label": "等权重"},
                    {"value": "momentum", "label": "按动量加权"},
                ],
                description="如何给有买入信号的股票分配权重",
                category="高级选项",
            ),
        ]

    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """
        生成均线突破入场信号

        参数:
            stocks: 候选股票列表（来自选股器）
            data: 股票数据字典 {股票代码: OHLCV DataFrame}
            date: 当前日期

        返回:
            {股票代码: 买入权重} 字典
        """
        short_window = self.params.get("short_window", 5)
        long_window = self.params.get("long_window", 20)
        min_breakout_pct = self.params.get("min_breakout_pct", 0.0) / 100
        weight_method = self.params.get("weight_method", "equal")

        signals = {}
        momentum_values = {}

        for stock in stocks:
            if stock not in data:
                logger.warning(f"股票 {stock} 数据缺失")
                continue

            df = data[stock]

            # 检查日期是否存在
            if date not in df.index:
                continue

            # 计算均线
            ma_short = df["close"].rolling(window=short_window).mean()
            ma_long = df["close"].rolling(window=long_window).mean()

            # 获取当前和前一日的均线值
            try:
                ma_short_today = ma_short.loc[date]
                ma_long_today = ma_long.loc[date]
                ma_short_yesterday = ma_short.shift(1).loc[date]
                ma_long_yesterday = ma_long.shift(1).loc[date]
            except KeyError:
                continue

            # 检查数据有效性
            if pd.isna(ma_short_today) or pd.isna(ma_long_today):
                continue
            if pd.isna(ma_short_yesterday) or pd.isna(ma_long_yesterday):
                continue

            # 检测金叉
            golden_cross = (
                ma_short_yesterday <= ma_long_yesterday  # 昨日短期 <= 长期
                and ma_short_today > ma_long_today  # 今日短期 > 长期
            )

            if not golden_cross:
                continue

            # 检查突破幅度
            if min_breakout_pct > 0:
                breakout_pct = (ma_short_today / ma_long_today - 1)
                if breakout_pct < min_breakout_pct:
                    logger.debug(
                        f"{stock}: 突破幅度不足 "
                        f"({breakout_pct:.2%} < {min_breakout_pct:.2%})"
                    )
                    continue

            # 产生买入信号
            signals[stock] = 1.0  # 暂时赋值为 1.0

            # 如果需要按动量加权，计算动量值
            if weight_method == "momentum":
                momentum = (df["close"].loc[date] / df["close"].shift(short_window).loc[date] - 1)
                momentum_values[stock] = max(momentum, 0.01)  # 避免负值或零

        # 根据权重方法分配权重
        if not signals:
            logger.info(f"日期 {date}: ���均线突破信号")
            return {}

        if weight_method == "equal":
            # 等权重
            weight = 1.0 / len(signals)
            signals = {stock: weight for stock in signals}
        elif weight_method == "momentum":
            # 按动量加权
            total_momentum = sum(momentum_values.values())
            signals = {
                stock: momentum_values[stock] / total_momentum
                for stock in signals
            }

        logger.info(
            f"日期 {date}: 均线突破信号 {len(signals)} 个 - {list(signals.keys())}"
        )

        return signals
```

---

#### 2. RSIOversoldEntry（RSI 超卖入场策略）

**文件路径**：`backend/app/strategies/three_layer/entries/rsi_oversold_entry.py`

**策略逻辑**：
1. 计算 RSI 指标（相对强弱指数）
2. 当 RSI < 超卖阈值（如 30）时，产生买入信号
3. 可选：要求连续 N 日 RSI < 阈值（确认超卖）

**完整实现**：

```python
"""
RSI 超卖入场策略
当 RSI 指标低于超卖阈值时买入
"""

from typing import Dict, List

import pandas as pd
from loguru import logger

from ..base.entry_strategy import EntryStrategy
from ..base.stock_selector import SelectorParameter


class RSIOversoldEntry(EntryStrategy):
    """
    RSI 超卖入场策略

    基于 RSI 指标的均值回归策略

    策略逻辑：
    1. 计算 RSI 指标（默认 14 日）
    2. 当 RSI < 超卖阈值（默认 30）时，产生买入信号
    3. 可选：要求连续 N 日处于超卖状态（提高可靠性）
    4. 对有买入信号的股票，按 RSI 倒数加权（越超卖权重越高）

    适用场景：
    - 震荡市场
    - 短期反弹交易
    - 均值回归策略

    注意事项：
    - 趋势市场中 RSI 可能长期处于超卖/超买区
    - 建议配合止损策略
    - 超卖阈值需根据市场环境调整
    """

    @property
    def id(self) -> str:
        return "rsi_oversold"

    @property
    def name(self) -> str:
        return "RSI 超卖入场"

    @property
    def description(self) -> str:
        return "RSI 指标低于超卖阈值时买入，适合震荡市场的均值回归策略"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="rsi_period",
                label="RSI 计算周期",
                type="integer",
                default=14,
                min_value=5,
                max_value=50,
                step=1,
                description="RSI 指标的计算周期（天）",
                category="核心参数",
            ),
            SelectorParameter(
                name="oversold_level",
                label="超卖阈值",
                type="float",
                default=30.0,
                min_value=10.0,
                max_value=50.0,
                step=1.0,
                description="RSI 低于此值视为超卖（标准值 30）",
                category="核心参数",
            ),
            SelectorParameter(
                name="confirm_days",
                label="确认天数",
                type="integer",
                default=1,
                min_value=1,
                max_value=5,
                step=1,
                description="要求连续 N 日处于超卖状态（1=不需要确认）",
                category="高级选项",
            ),
            SelectorParameter(
                name="weight_method",
                label="权重分配方法",
                type="select",
                default="rsi_weighted",
                options=[
                    {"value": "equal", "label": "等权重"},
                    {"value": "rsi_weighted", "label": "按 RSI 倒数加权"},
                ],
                description="如何分配权重（RSI 越低权重越高）",
                category="高级选项",
            ),
        ]

    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """
        生成 RSI 超卖入场信号
        """
        rsi_period = self.params.get("rsi_period", 14)
        oversold_level = self.params.get("oversold_level", 30.0)
        confirm_days = self.params.get("confirm_days", 1)
        weight_method = self.params.get("weight_method", "rsi_weighted")

        signals = {}
        rsi_values = {}

        for stock in stocks:
            if stock not in data:
                logger.warning(f"股票 {stock} 数据缺失")
                continue

            df = data[stock]

            if date not in df.index:
                continue

            # 计算 RSI
            rsi = self._calculate_rsi(df["close"], rsi_period)

            if date not in rsi.index:
                continue

            rsi_today = rsi.loc[date]

            if pd.isna(rsi_today):
                continue

            # 检查是否处于超卖状态
            if rsi_today >= oversold_level:
                continue

            # 确认天数检查
            if confirm_days > 1:
                # 检查过去 N 日是否都处于超卖状态
                rsi_recent = rsi.loc[:date].tail(confirm_days)
                if len(rsi_recent) < confirm_days:
                    continue
                if not (rsi_recent < oversold_level).all():
                    continue

            # 产生买入信号
            signals[stock] = 1.0
            rsi_values[stock] = rsi_today

        # 权重分配
        if not signals:
            logger.info(f"日期 {date}: 无 RSI 超卖信号")
            return {}

        if weight_method == "equal":
            weight = 1.0 / len(signals)
            signals = {stock: weight for stock in signals}
        elif weight_method == "rsi_weighted":
            # RSI 越低，权重越高（使用倒数）
            rsi_reciprocals = {
                stock: 1.0 / max(rsi_values[stock], 1.0)
                for stock in signals
            }
            total = sum(rsi_reciprocals.values())
            signals = {
                stock: rsi_reciprocals[stock] / total for stock in signals
            }

        logger.info(
            f"日期 {date}: RSI 超卖信号 {len(signals)} 个 - {list(signals.keys())}"
        )

        return signals

    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        计算 RSI 指标

        参数:
            prices: 价格序列
            period: 计算周期

        返回:
            RSI 序列（0-100）
        """
        # 计算价格变动
        delta = prices.diff()

        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 计算平均上涨和下跌
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # 计算 RS 和 RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi
```

---

#### 3. ImmediateEntry（立即入场策略）

**文件路径**：`backend/app/strategies/three_layer/entries/immediate_entry.py`

**策略逻辑**：
- 对所有候选股票立即产生买入信号
- 主要用于测试选股器和退出策略
- 不做任何技术分析判断

**完整实现**：

```python
"""
立即入场策略
对所有候选股票立即产生买入信号（用于测试）
"""

from typing import Dict, List

import pandas as pd
from loguru import logger

from ..base.entry_strategy import EntryStrategy
from ..base.stock_selector import SelectorParameter


class ImmediateEntry(EntryStrategy):
    """
    立即入场策略（测试用）

    策略逻辑：
    对选股器输出的所有股票立即产生买入信号

    适用场景：
    1. 测试选股器的效果
    2. 测试退出策略的效果
    3. 评估"只要选对股票就行"的假设

    注意事项：
    - 这不是一个实际的交易策略
    - 仅用于测试和基准对比
    - 实际交易应使用有择时能力的入场策略
    """

    @property
    def id(self) -> str:
        return "immediate"

    @property
    def name(self) -> str:
        return "立即入场（测试用）"

    @property
    def description(self) -> str:
        return "对所有候选股票立即买入，用于测试选股器和退出策略的效果"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="weight_method",
                label="权重分配方法",
                type="select",
                default="equal",
                options=[
                    {"value": "equal", "label": "等权重"},
                    {"value": "market_cap", "label": "按市值加权（未实现）"},
                ],
                description="如何分配权重",
                category="核心参数",
            ),
        ]

    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """
        生成立即入场信号
        """
        weight_method = self.params.get("weight_method", "equal")

        if not stocks:
            return {}

        # 等权重分配
        if weight_method == "equal":
            weight = 1.0 / len(stocks)
            signals = {stock: weight for stock in stocks}
        else:
            # 其他方法未实现，回退到等权重
            weight = 1.0 / len(stocks)
            signals = {stock: weight for stock in stocks}

        logger.info(
            f"日期 {date}: 立即入场信号 {len(signals)} 个"
        )

        return signals
```

---

## 任务 4.0.4：实现基础退出策略

### 目标

实现 4 个基础退出策略，覆盖止损、止盈、时间管理等场景。

### 工作量

**预计耗时**：3-4 天

### 实施清单

| 策略 | 文件名 | 功能描述 | 关键参数 | 优先级 |
|------|--------|---------|---------|--------|
| **ATRStopLossExit** | `exits/atr_stop_loss_exit.py` | ATR 动态止损 | atr_period, atr_multiplier | P0 |
| **FixedStopLossExit** | `exits/fixed_stop_loss_exit.py` | 固定止损止盈 | stop_loss_pct, take_profit_pct | P0 |
| **TimeBasedExit** | `exits/time_based_exit.py` | 时间止损 | holding_period | P0 |
| **CombinedExit** | `exits/combined_exit.py` | 组合退出（OR 逻辑） | exit_strategies | P1 |

---

### 实施详情

#### 1. ATRStopLossExit（ATR 动态止损策略）

**文件路径**：`backend/app/strategies/three_layer/exits/atr_stop_loss_exit.py`

**策略逻辑**：
1. 计算 ATR（平均真实波幅）
2. 止损价 = 买入价 - ATR × 倍数
3. 当前价 < 止损价时，触发卖出

**完整实现**：

```python
"""
ATR 动态止损退出策略
基于平均真实波幅（ATR）设置动态止损
"""

from typing import Dict, List

import pandas as pd
from loguru import logger

from ..base.exit_strategy import ExitStrategy, Position
from ..base.stock_selector import SelectorParameter


class ATRStopLossExit(ExitStrategy):
    """
    ATR 动态止损退出策略

    策略逻辑：
    1. 计算 ATR（Average True Range，平均真实波幅）
    2. 止损价 = 入场价 - ATR × 倍数
    3. 当前价 < 止损价时，卖出

    优势：
    - 根据市场波动自适应调整止损幅度
    - 高波动时止损宽松，低波动时止损严格
    - 避免被正常波动震出

    适用场景：
    - 趋势跟踪策略
    - 中长期持仓
    - 波动较大的市场

    注意事项：
    - ATR 倍数越大，止损越宽松
    - 建议根据历史回测调整倍数
    - 可以结合移动止损（trailing stop）
    """

    @property
    def id(self) -> str:
        return "atr_stop_loss"

    @property
    def name(self) -> str:
        return "ATR 动态止损"

    @property
    def description(self) -> str:
        return "基于 ATR 指标设置动态止损，适应市场波动"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="atr_period",
                label="ATR 计算周期",
                type="integer",
                default=14,
                min_value=5,
                max_value=50,
                step=1,
                description="ATR 指标的计算周期（天）",
                category="核心参数",
            ),
            SelectorParameter(
                name="atr_multiplier",
                label="ATR 倍数",
                type="float",
                default=2.0,
                min_value=0.5,
                max_value=5.0,
                step=0.5,
                description="止损距离 = ATR × 倍数（倍数越大止损越宽松）",
                category="核心参数",
            ),
            SelectorParameter(
                name="use_trailing_stop",
                label="使用移动止损",
                type="boolean",
                default=False,
                description="True=止损线随价格上涨而上移, False=止损线固定",
                category="高级选项",
            ),
        ]

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> List[str]:
        """
        生成 ATR 止损退出信号
        """
        atr_period = self.params.get("atr_period", 14)
        atr_multiplier = self.params.get("atr_multiplier", 2.0)
        use_trailing_stop = self.params.get("use_trailing_stop", False)

        exit_stocks = []

        for stock_code, position in positions.items():
            if stock_code not in data:
                logger.warning(f"股票 {stock_code} 数据缺失")
                continue

            df = data[stock_code]

            if date not in df.index:
                continue

            # 计算 ATR
            atr = self._calculate_atr(df, atr_period)

            if date not in atr.index:
                continue

            atr_today = atr.loc[date]

            if pd.isna(atr_today):
                continue

            # 计算止损价
            if use_trailing_stop:
                # 移动止损：止损线随最高价上移
                highest_price = df["close"].loc[position.entry_date:date].max()
                stop_loss_price = highest_price - (atr_today * atr_multiplier)
            else:
                # 固定止损：基于入场价
                stop_loss_price = position.entry_price - (
                    atr_today * atr_multiplier
                )

            # 检查是否触发止损
            current_price = position.current_price

            if current_price < stop_loss_price:
                logger.info(
                    f"{stock_code}: ATR 止损触发 "
                    f"(当前价 {current_price:.2f} < 止损价 {stop_loss_price:.2f})"
                )
                exit_stocks.append(stock_code)

        if exit_stocks:
            logger.info(
                f"日期 {date}: ATR 止损信号 {len(exit_stocks)} 个"
            )

        return exit_stocks

    @staticmethod
    def _calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        计算 ATR (Average True Range)

        参数:
            df: OHLC 数据
            period: 计算周期

        返回:
            ATR 序列
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # 计算 True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 计算 ATR（移动平均）
        atr = tr.rolling(window=period).mean()

        return atr
```

---

#### 2. FixedStopLossExit（固定止损止盈策略）

**文件路径**：`backend/app/strategies/three_layer/exits/fixed_stop_loss_exit.py`

```python
"""
固定止损止盈退出策略
基于固定百分比设置止损和止盈
"""

from typing import Dict, List

from loguru import logger

from ..base.exit_strategy import ExitStrategy, Position
from ..base.stock_selector import SelectorParameter


class FixedStopLossExit(ExitStrategy):
    """
    固定止损止盈退出策略

    策略逻辑：
    1. 止损：亏损达到 X% 时卖出
    2. 止盈：盈利达到 Y% 时卖出

    优势：
    - 简单直观，易于理解和执行
    - 风险收益比明确
    - 适合新手交易者

    适用场景：
    - 短期交易
    - 明确的风险控制需求
    - 不想过度优化的策略

    注意事项：
    - 固定止损在高波动市场容易被打出
    - 固定止盈可能限制盈利空间
    - 建议根据回测结果调整比例
    """

    @property
    def id(self) -> str:
        return "fixed_stop_loss"

    @property
    def name(self) -> str:
        return "固定止损止盈"

    @property
    def description(self) -> str:
        return "基于固定百分比设置止损和止盈，简单直观的风控策略"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="stop_loss_pct",
                label="止损百分比（%）",
                type="float",
                default=5.0,
                min_value=1.0,
                max_value=20.0,
                step=0.5,
                description="亏损达到此百分比时卖出（如 5 表示 -5%）",
                category="核心参数",
            ),
            SelectorParameter(
                name="take_profit_pct",
                label="止盈百分比（%）",
                type="float",
                default=10.0,
                min_value=2.0,
                max_value=50.0,
                step=1.0,
                description="盈利达到此百分比时卖出（如 10 表示 +10%）",
                category="核心参数",
            ),
            SelectorParameter(
                name="enable_stop_loss",
                label="启用止损",
                type="boolean",
                default=True,
                description="是否启用止损功能",
                category="开关选项",
            ),
            SelectorParameter(
                name="enable_take_profit",
                label="启用止盈",
                type="boolean",
                default=True,
                description="是否启用止盈功能",
                category="开关选项",
            ),
        ]

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date,
    ) -> List[str]:
        """
        生成固定止损止盈退出信号
        """
        stop_loss_pct = self.params.get("stop_loss_pct", 5.0) / 100
        take_profit_pct = self.params.get("take_profit_pct", 10.0) / 100
        enable_stop_loss = self.params.get("enable_stop_loss", True)
        enable_take_profit = self.params.get("enable_take_profit", True)

        exit_stocks = []

        for stock_code, position in positions.items():
            # 计算盈亏比例
            pnl_pct = position.unrealized_pnl_pct

            # 检查止损
            if enable_stop_loss and pnl_pct <= -stop_loss_pct:
                logger.info(
                    f"{stock_code}: 固定止损触发 "
                    f"(盈亏 {pnl_pct:.2%} <= -{stop_loss_pct:.2%})"
                )
                exit_stocks.append(stock_code)
                continue

            # 检查止盈
            if enable_take_profit and pnl_pct >= take_profit_pct:
                logger.info(
                    f"{stock_code}: 固定止盈触发 "
                    f"(盈亏 {pnl_pct:.2%} >= +{take_profit_pct:.2%})"
                )
                exit_stocks.append(stock_code)
                continue

        if exit_stocks:
            logger.info(
                f"日期 {date}: 固定止损止盈信号 {len(exit_stocks)} 个"
            )

        return exit_stocks
```

---

#### 3. TimeBasedExit（时间止损策略）

**文件路径**：`backend/app/strategies/three_layer/exits/time_based_exit.py`

```python
"""
时间止损退出策略
持有达到指定天数后自动卖出
"""

from typing import Dict, List

import pandas as pd
from loguru import logger

from ..base.exit_strategy import ExitStrategy, Position
from ..base.stock_selector import SelectorParameter


class TimeBasedExit(ExitStrategy):
    """
    时间止损退出策略

    策略逻辑：
    持有达到指定天数后，无论盈亏自动卖出

    优势：
    - 避免长期套牢
    - 提高资金周转率
    - 适合短期交易策略

    适用场景：
    - 短线交易
    - 事件驱动策略
    - 配合高频选股策略

    注意事项：
    - 可能在盈利时过早退出
    - 可能在亏损时继续持有
    - 建议配合止损止盈策略使用
    """

    @property
    def id(self) -> str:
        return "time_based"

    @property
    def name(self) -> str:
        return "时间止损"

    @property
    def description(self) -> str:
        return "持有达到指定天数后自动卖出，提高资金周转率"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="holding_period",
                label="持仓期（天）",
                type="integer",
                default=5,
                min_value=1,
                max_value=60,
                step=1,
                description="持有天数达到此值后自动卖出",
                category="核心参数",
            ),
            SelectorParameter(
                name="count_trading_days",
                label="仅计算交易日",
                type="boolean",
                default=True,
                description="True=仅计算交易日, False=计算自然日",
                category="高级选项",
            ),
        ]

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> List[str]:
        """
        生成时间止损退出信号
        """
        holding_period = self.params.get("holding_period", 5)
        count_trading_days = self.params.get("count_trading_days", True)

        exit_stocks = []

        for stock_code, position in positions.items():
            if count_trading_days:
                # 计算交易日天数
                if stock_code not in data:
                    continue

                df = data[stock_code]
                trading_dates = df.loc[position.entry_date : date].index
                holding_days = len(trading_dates) - 1  # 减去入场当日
            else:
                # 计算自然日天数
                holding_days = (date - position.entry_date).days

            if holding_days >= holding_period:
                logger.info(
                    f"{stock_code}: 时间止损触发 "
                    f"(已持��� {holding_days} 天 >= {holding_period} 天)"
                )
                exit_stocks.append(stock_code)

        if exit_stocks:
            logger.info(
                f"日期 {date}: 时间止损信号 {len(exit_stocks)} 个"
            )

        return exit_stocks
```

---

#### 4. CombinedExit（组合退出策略）

**文件路径**：`backend/app/strategies/three_layer/exits/combined_exit.py`

```python
"""
组合退出策略
组合多个退出策略，任意一个触发即卖出（OR 逻辑）
"""

from typing import Dict, List

from loguru import logger

from ..base.exit_strategy import ExitStrategy, Position
from ..base.stock_selector import SelectorParameter


class CombinedExit(ExitStrategy):
    """
    组合退出策略

    策略逻辑：
    组合多个退出策略，任意一个触发即卖出（OR 逻辑）

    示例：
        combined = CombinedExit(
            exit_strategies=[
                ATRStopLossExit(params={'atr_multiplier': 2.0}),
                TimeBasedExit(params={'holding_period': 5}),
            ]
        )

    优势：
    - 多重风控保护
    - 灵活组合不同退出逻辑
    - 适应复杂市场环境

    适用场景：
    - 需要多重风控的策略
    - 长期交易策略
    - 风险厌恶型交易者

    注意事项：
    - 退出策略越多，持仓时间可能越短
    - 需要平衡风控和收益
    - 建议通过回测优化组合
    """

    def __init__(self, exit_strategies: List[ExitStrategy], params=None):
        """
        初始化组合退出策略

        参数:
            exit_strategies: 退出策略列表
            params: 参数字典（可选）
        """
        super().__init__(params)
        self.exit_strategies = exit_strategies

        if not self.exit_strategies:
            raise ValueError("exit_strategies 不能为空")

    @property
    def id(self) -> str:
        return "combined"

    @property
    def name(self) -> str:
        strategy_names = ", ".join([s.name for s in self.exit_strategies])
        return f"组合退出（{strategy_names}）"

    @property
    def description(self) -> str:
        return "组合多个退出策略，任意一个触发即卖出"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        # 组合策略的参数由子策略定义，这里返回空列表
        return []

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date,
    ) -> List[str]:
        """
        生成组合退出信号

        遍历所有子策略，收集所有退出信号（OR 逻辑）
        """
        exit_stocks = set()

        for strategy in self.exit_strategies:
            try:
                signals = strategy.generate_exit_signals(positions, data, date)
                exit_stocks.update(signals)

                if signals:
                    logger.debug(
                        f"  - {strategy.name}: {len(signals)} 个退出信号"
                    )
            except Exception as e:
                logger.error(
                    f"子策略 {strategy.name} 执行失败: {e}", exc_info=True
                )

        exit_list = list(exit_stocks)

        if exit_list:
            logger.info(
                f"日期 {date}: 组合退出信号 {len(exit_list)} 个"
            )

        return exit_list

    def get_metadata(self) -> Dict:
        """获取组合策略元数据"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "sub_strategies": [
                s.get_metadata() for s in self.exit_strategies
            ],
        }
```

---

## 策略使用示例

### 示例 1：完整的三层策略组合

```python
from backend.app.strategies.three_layer.base.strategy_composer import StrategyComposer
from backend.app.strategies.three_layer.selectors.momentum_selector import MomentumSelector
from backend.app.strategies.three_layer.entries.ma_breakout_entry import MABreakoutEntry
from backend.app.strategies.three_layer.exits.combined_exit import CombinedExit
from backend.app.strategies.three_layer.exits.atr_stop_loss_exit import ATRStopLossExit
from backend.app.strategies.three_layer.exits.time_based_exit import TimeBasedExit

# 创建策略组合
strategy = StrategyComposer(
    selector=MomentumSelector(params={
        'lookback_period': 20,
        'top_n': 50,
        'filter_negative': True
    }),
    entry=MABreakoutEntry(params={
        'short_window': 5,
        'long_window': 20,
        'min_breakout_pct': 0.5
    }),
    exit=CombinedExit(
        exit_strategies=[
            ATRStopLossExit(params={
                'atr_period': 14,
                'atr_multiplier': 2.0
            }),
            TimeBasedExit(params={
                'holding_period': 5
            })
        ]
    ),
    rebalance_freq='W'  # 每周重新选股
)

# 获取元数据
metadata = strategy.get_metadata()
print(metadata)

# 验证策略
validation = strategy.validate()
if validation['valid']:
    print("策略验证通过")
else:
    print(f"策略验证失败: {validation['errors']}")
```

### 示例 2：外部选股 + RSI 入场

```python
from backend.app.strategies.three_layer.selectors.external_selector import ExternalSelector
from backend.app.strategies.three_layer.entries.rsi_oversold_entry import RSIOversoldEntry
from backend.app.strategies.three_layer.exits.fixed_stop_loss_exit import FixedStopLossExit

# StarRanker 选股 + RSI 超卖入场 + 固定止损
strategy = StrategyComposer(
    selector=ExternalSelector(params={
        'source': 'manual',
        'manual_stocks': '600000.SH,000001.SZ,000002.SZ'
    }),
    entry=RSIOversoldEntry(params={
        'rsi_period': 14,
        'oversold_level': 30,
        'confirm_days': 2
    }),
    exit=FixedStopLossExit(params={
        'stop_loss_pct': 5.0,
        'take_profit_pct': 10.0
    }),
    rebalance_freq='D'  # 每日检查选股（外部源可能每日更新）
)
```

---

## 测试计划

### 单元测试

**测试文件位置**：`backend/tests/unit/strategies/three_layer/`

**测试覆盖**：

| 模块 | 测试文件 | 测试用例数 | 覆盖率目标 |
|------|---------|-----------|----------|
| **入场策略** | `test_ma_breakout_entry.py` | 8 | 90%+ |
|  | `test_rsi_oversold_entry.py` | 8 | 90%+ |
|  | `test_immediate_entry.py` | 4 | 90%+ |
| **退出策略** | `test_atr_stop_loss_exit.py` | 8 | 90%+ |
|  | `test_fixed_stop_loss_exit.py` | 6 | 90%+ |
|  | `test_time_based_exit.py` | 6 | 90%+ |
|  | `test_combined_exit.py` | 6 | 90%+ |
| **合计** | - | **46** | **90%+** |

**示例测试用例**（MABreakoutEntry）：

```python
"""
测试均线突破入场策略
"""

import pandas as pd
import pytest

from backend.app.strategies.three_layer.entries.ma_breakout_entry import MABreakoutEntry


def test_ma_breakout_entry_initialization():
    """测试策略初始化"""
    strategy = MABreakoutEntry(params={
        'short_window': 5,
        'long_window': 20
    })
    assert strategy.id == "ma_breakout"
    assert strategy.name == "均线突破入场"


def test_ma_breakout_entry_golden_cross():
    """测试金叉检测"""
    # 创建测试数据：模拟金叉
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    data = {
        'stock1': pd.DataFrame({
            'close': list(range(100, 80, -1)) + list(range(80, 90)),
            'open': list(range(100, 80, -1)) + list(range(80, 90)),
            'high': list(range(101, 81, -1)) + list(range(81, 91)),
            'low': list(range(99, 79, -1)) + list(range(79, 89)),
            'volume': [1000000] * 30
        }, index=dates)
    }

    strategy = MABreakoutEntry(params={
        'short_window': 5,
        'long_window': 20,
        'min_breakout_pct': 0.0
    })

    # 在金叉发生的日期检测信号
    signals = strategy.generate_entry_signals(
        stocks=['stock1'],
        data=data,
        date=pd.Timestamp('2024-01-25')
    )

    # 应该检测到金叉
    assert 'stock1' in signals
    assert signals['stock1'] > 0


def test_ma_breakout_entry_no_signal():
    """测试无信号场景"""
    # 创建测试数据：持续下跌，无金叉
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    data = {
        'stock1': pd.DataFrame({
            'close': list(range(100, 70, -1)),
            'open': list(range(100, 70, -1)),
            'high': list(range(101, 71, -1)),
            'low': list(range(99, 69, -1)),
            'volume': [1000000] * 30
        }, index=dates)
    }

    strategy = MABreakoutEntry(params={
        'short_window': 5,
        'long_window': 20
    })

    signals = strategy.generate_entry_signals(
        stocks=['stock1'],
        data=data,
        date=pd.Timestamp('2024-01-25')
    )

    # 应该无信号
    assert len(signals) == 0
```

### 集成测试

**测试重点**：
1. 策略组合器的完整流程测试
2. 多个股票同时处理的测试
3. 边界条件测试（数据缺失、参数异常等）

---

## 验收标准

### 任务 4.0.3 验收标准

- ✅ 3 个入场策略实现完成
- ✅ 所有策略通过参数验证
- ✅ RSIOversoldEntry 正确计算 RSI
- ✅ MABreakoutEntry 正确检测金叉
- ✅ 单元测试覆盖率 ≥ 90%
- ✅ 代码通过 `black` 和 `flake8` 检查

### 任务 4.0.4 验收标准

- ✅ 4 个退出策略实现完成
- ✅ ATRStopLossExit 正确计算 ATR
- ✅ CombinedExit 正确组合子策略
- ✅ FixedStopLossExit 同时支持止损和止盈
- ✅ 单元测试覆盖率 ≥ 90%
- ✅ 代码通过 `black` 和 `flake8` 检查

---

## 下一步

继续阅读：
- [Phase 4.0 回测引擎与 API 文档](./phase_4_0_backtest_and_api.md)（任务 4.0.5 - 4.0.6）
- [Phase 4.1-4.2 实施文档](./phase_4_1_4_2_implementation.md)（策略库扩展与测试）

---

**文档维护者**：开发团队
**创建日期**：2026-02-06
**最后更新**：2026-02-06
