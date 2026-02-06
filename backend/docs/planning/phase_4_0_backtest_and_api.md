# Phase 4.0 回测引擎与 API 文档

> **版本**: v1.0
> **日期**: 2026-02-06
> **上级文档**: [三层架构实施方案](./backtest_three_layer_architecture_implementation_plan.md)
> **当前阶段**: Phase 4.0 - 任务 4.0.5 至 4.0.6

---

## 📋 目录

- [任务 4.0.5：实现三层回测适配器](#任务-405实现三层回测适配器)
- [任务 4.0.6：创建 REST API 端点](#任务-406创建-rest-api-端点)
- [API 使用示例](#api-使用示例)
- [性能优化](#性能优化)

---

## 任务 4.0.5：实现三层回测适配器

### 目标

实现三层架构的回测适配器，支持策略组合回测。

### 工作量

**预计耗时**：4-5 天

### 架构设计

```
ThreeLayerBacktestAdapter (新增)
    ↓
ThreeLayerBacktestEngine (新增，轻量级)
    ↓
数据加载 + 回测循环 + 绩效计算
```

**设计决策**：
- 不依赖 Core 项目（Core 不支持三层架构）
- 在 Backend 实现轻量级回测引擎
- 复用现有的数据加载和绩效计算逻辑

---

### 实施详情

#### 1. ThreeLayerBacktestEngine（核心回测引擎）

**文件路径**：`backend/app/services/three_layer_backtest_engine.py`

**功能**：
- 执行三层策略的回测循环
- 管理持仓和资金
- 记录交易和净值

**完整实现**：

```python
"""
三层架构回测引擎
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

import pandas as pd
from loguru import logger

from ..strategies.three_layer.base.entry_strategy import EntryStrategy
from ..strategies.three_layer.base.exit_strategy import ExitStrategy, Position
from ..strategies.three_layer.base.stock_selector import StockSelector


@dataclass
class Trade:
    """交易记录"""

    stock_code: str
    direction: str  # 'buy' or 'sell'
    date: pd.Timestamp
    price: float
    shares: int
    amount: float
    commission: float
    tax: float  # 印花税（仅卖出）
    total_cost: float  # 总成本（含手续费）


@dataclass
class Portfolio:
    """投资组合"""

    initial_capital: float  # 初始资金
    cash: float  # 当前现金
    positions: Dict[str, Position] = field(default_factory=dict)  # 持仓
    trades: List[Trade] = field(default_factory=list)  # 交易记录
    portfolio_value_history: List[Dict] = field(default_factory=list)  # 净值历史


class ThreeLayerBacktestEngine:
    """
    三层架构回测引擎

    回测流程：
    1. 初始化投资组合
    2. 遍历交易日：
       a. 执行退出策略（每日）
       b. 执行选股（按 rebalance_freq）
       c. 执行入场策略（每日）
       d. 记录持仓和净值
    3. 计算绩效指标
    """

    def __init__(
        self,
        initial_capital: float = 1000000.0,
        commission_rate: float = 0.0003,  # 万三
        tax_rate: float = 0.001,  # 千一（仅卖出）
        slippage_rate: float = 0.0001,  # 滑点
    ):
        """
        初始化回测引擎

        参数:
            initial_capital: 初始资金
            commission_rate: 佣金率
            tax_rate: 印花税率（仅卖出）
            slippage_rate: 滑点率
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.tax_rate = tax_rate
        self.slippage_rate = slippage_rate

    def run_backtest(
        self,
        selector: StockSelector,
        entry: EntryStrategy,
        exit: ExitStrategy,
        market_data: pd.DataFrame,
        stock_data: Dict[str, pd.DataFrame],
        start_date: str,
        end_date: str,
        rebalance_freq: str = "W",
    ) -> Dict[str, Any]:
        """
        执行三层架构回测

        参数:
            selector: 选股器实例
            entry: 入场策略实例
            exit: 退出策略实例
            market_data: 全市场数据 (index=date, columns=stock_codes, values=close_price)
            stock_data: 股票详细数据 {stock_code: OHLCV DataFrame}
            start_date: 回测开始日期
            end_date: 回测结束日期
            rebalance_freq: 选股频率 ('D', 'W', 'M')

        返回:
            {
                'portfolio_value': List[Dict],  # 净值曲线
                'trades': List[Dict],            # 交易记录
                'positions': List[Dict],         # 持仓记录
                'metrics': Dict[str, float],     # 绩效指标
            }
        """
        logger.info(f"开始三层架构回测: {start_date} ~ {end_date}")

        # 初始化投资组合
        portfolio = Portfolio(
            initial_capital=self.initial_capital,
            cash=self.initial_capital,
        )

        # 获取交易日列表
        trading_dates = pd.date_range(start_date, end_date, freq="D")
        trading_dates = [d for d in trading_dates if d in market_data.index]

        # 获取选股日期列表
        rebalance_dates = pd.date_range(start_date, end_date, freq=rebalance_freq)
        rebalance_dates = [d for d in rebalance_dates if d in trading_dates]

        # 当前候选股票池
        candidate_stocks = []

        logger.info(f"交易日总数: {len(trading_dates)}")
        logger.info(f"选股日总数: {len(rebalance_dates)}")

        # 遍历交易日
        for i, date in enumerate(trading_dates):
            logger.debug(f"\n{'='*60}")
            logger.debug(f"日期: {date.strftime('%Y-%m-%d')} ({i+1}/{len(trading_dates)})")

            # Step 1: 更新持仓价格和盈亏
            self._update_positions(portfolio, stock_data, date)

            # Step 2: 执行退出策略（每日）
            exit_signals = exit.generate_exit_signals(
                positions=portfolio.positions,
                data=stock_data,
                date=date,
            )

            for stock_code in exit_signals:
                self._sell_stock(portfolio, stock_code, stock_data, date)

            # Step 3: 定期重新选股
            if date in rebalance_dates:
                logger.debug(f"执行选股（{rebalance_freq}频率）")
                candidate_stocks = selector.select(date, market_data)
                logger.debug(f"选出 {len(candidate_stocks)} 只候选股票")

            # Step 4: 执行入场策略（每日）
            if candidate_stocks:
                entry_signals = entry.generate_entry_signals(
                    stocks=candidate_stocks,
                    data=stock_data,
                    date=date,
                )

                # 执行买入
                for stock_code, weight in entry_signals.items():
                    if stock_code not in portfolio.positions:
                        self._buy_stock(
                            portfolio, stock_code, weight, stock_data, date
                        )

            # Step 5: 记录净值
            total_value = self._calculate_total_value(portfolio, stock_data, date)
            portfolio.portfolio_value_history.append(
                {
                    "date": date,
                    "total_value": total_value,
                    "cash": portfolio.cash,
                    "position_value": total_value - portfolio.cash,
                    "positions_count": len(portfolio.positions),
                }
            )

            logger.debug(f"净值: {total_value:,.2f}, 持仓: {len(portfolio.positions)}")

        logger.info(f"\n{'='*60}")
        logger.info("回测完成")
        logger.info(f"总交易次数: {len(portfolio.trades)}")
        logger.info(f"最终净值: {total_value:,.2f}")
        logger.info(
            f"总收益率: {(total_value / self.initial_capital - 1) * 100:.2f}%"
        )

        # 格式化返回结果
        return {
            "portfolio_value": portfolio.portfolio_value_history,
            "trades": [self._trade_to_dict(t) for t in portfolio.trades],
            "positions": self._get_final_positions(portfolio),
            "metrics": self._calculate_metrics(portfolio),
        }

    def _update_positions(
        self,
        portfolio: Portfolio,
        stock_data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ):
        """更新持仓的当前价格和盈亏"""
        for stock_code, position in portfolio.positions.items():
            if stock_code not in stock_data:
                continue

            df = stock_data[stock_code]
            if date not in df.index:
                continue

            current_price = df.loc[date, "close"]
            position.current_price = current_price
            position.unrealized_pnl = (
                current_price - position.entry_price
            ) * position.shares
            position.unrealized_pnl_pct = (
                current_price / position.entry_price - 1
            )

    def _sell_stock(
        self,
        portfolio: Portfolio,
        stock_code: str,
        stock_data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ):
        """卖出股票"""
        if stock_code not in portfolio.positions:
            return

        position = portfolio.positions[stock_code]

        # 获取卖出价格
        if stock_code not in stock_data or date not in stock_data[stock_code].index:
            logger.warning(f"无法获取 {stock_code} 在 {date} 的价格，跳过卖出")
            return

        sell_price = stock_data[stock_code].loc[date, "close"]
        sell_price *= 1 - self.slippage_rate  # 考虑滑点

        # 计算卖出金额
        sell_amount = sell_price * position.shares

        # 计算手续费
        commission = sell_amount * self.commission_rate
        tax = sell_amount * self.tax_rate  # 印花税（仅卖出）
        total_cost = commission + tax

        # 更新现金
        portfolio.cash += sell_amount - total_cost

        # 记录交易
        trade = Trade(
            stock_code=stock_code,
            direction="sell",
            date=date,
            price=sell_price,
            shares=position.shares,
            amount=sell_amount,
            commission=commission,
            tax=tax,
            total_cost=total_cost,
        )
        portfolio.trades.append(trade)

        # 删除持仓
        del portfolio.positions[stock_code]

        logger.debug(
            f"  卖出 {stock_code}: {position.shares} 股 @ {sell_price:.2f}"
        )

    def _buy_stock(
        self,
        portfolio: Portfolio,
        stock_code: str,
        weight: float,
        stock_data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ):
        """买入股票"""
        # 获取买入价格
        if stock_code not in stock_data or date not in stock_data[stock_code].index:
            logger.warning(f"无法获取 {stock_code} 在 {date} 的价格，跳过买入")
            return

        buy_price = stock_data[stock_code].loc[date, "close"]
        buy_price *= 1 + self.slippage_rate  # 考虑滑点

        # 计算买入金额（基于权重和可用资金）
        available_cash = portfolio.cash * 0.98  # 保留 2% 作为缓冲
        buy_amount = available_cash * weight

        # 计算买入股数（100 股为 1 手）
        shares = int(buy_amount / buy_price / 100) * 100

        if shares < 100:
            logger.debug(f"  {stock_code}: 资金不足，跳过买入")
            return

        # 计算实际买入金额
        actual_buy_amount = buy_price * shares

        # 计算手续费
        commission = actual_buy_amount * self.commission_rate
        total_cost = actual_buy_amount + commission

        # 检查资金是否充足
        if total_cost > portfolio.cash:
            logger.debug(f"  {stock_code}: 资金不足，跳过买入")
            return

        # 更新现金
        portfolio.cash -= total_cost

        # 创建持仓
        position = Position(
            stock_code=stock_code,
            entry_date=date,
            entry_price=buy_price,
            shares=shares,
            current_price=buy_price,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
        )
        portfolio.positions[stock_code] = position

        # 记录交易
        trade = Trade(
            stock_code=stock_code,
            direction="buy",
            date=date,
            price=buy_price,
            shares=shares,
            amount=actual_buy_amount,
            commission=commission,
            tax=0.0,
            total_cost=total_cost,
        )
        portfolio.trades.append(trade)

        logger.debug(f"  买入 {stock_code}: {shares} 股 @ {buy_price:.2f}")

    def _calculate_total_value(
        self,
        portfolio: Portfolio,
        stock_data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> float:
        """计算投资组合总价值"""
        total_value = portfolio.cash

        for stock_code, position in portfolio.positions.items():
            if stock_code not in stock_data or date not in stock_data[stock_code].index:
                # 使用入场价作为当前价
                total_value += position.entry_price * position.shares
            else:
                current_price = stock_data[stock_code].loc[date, "close"]
                total_value += current_price * position.shares

        return total_value

    def _calculate_metrics(self, portfolio: Portfolio) -> Dict[str, float]:
        """计算绩效指标"""
        if not portfolio.portfolio_value_history:
            return {}

        # 提取净值序列
        values = [p["total_value"] for p in portfolio.portfolio_value_history]
        dates = [p["date"] for p in portfolio.portfolio_value_history]

        # 计算收益率
        returns = pd.Series(values).pct_change().dropna()

        # 基础指标
        total_return = (values[-1] / values[0] - 1) * 100
        trading_days = len(values)
        annualized_return = (
            ((values[-1] / values[0]) ** (252 / trading_days) - 1) * 100
        )

        # 风险指标
        volatility = returns.std() * (252**0.5) * 100
        sharpe_ratio = (
            (annualized_return / 100) / (volatility / 100)
            if volatility > 0
            else 0
        )

        # 最大回撤
        cummax = pd.Series(values).cummax()
        drawdown = (pd.Series(values) - cummax) / cummax
        max_drawdown = drawdown.min() * 100

        # 交易统计
        total_trades = len(portfolio.trades)
        buy_trades = [t for t in portfolio.trades if t.direction == "buy"]
        sell_trades = [t for t in portfolio.trades if t.direction == "sell"]

        # 盈亏统计
        win_trades = 0
        total_pnl = 0

        # 匹配买卖记录计算盈亏
        buy_dict = {}
        for trade in buy_trades:
            if trade.stock_code not in buy_dict:
                buy_dict[trade.stock_code] = []
            buy_dict[trade.stock_code].append(trade)

        for sell_trade in sell_trades:
            if sell_trade.stock_code in buy_dict and buy_dict[sell_trade.stock_code]:
                buy_trade = buy_dict[sell_trade.stock_code].pop(0)
                pnl = (
                    sell_trade.price - buy_trade.price
                ) * sell_trade.shares - sell_trade.total_cost
                total_pnl += pnl
                if pnl > 0:
                    win_trades += 1

        win_rate = (win_trades / len(sell_trades) * 100) if sell_trades else 0

        return {
            "total_return": round(total_return, 2),
            "annualized_return": round(annualized_return, 2),
            "volatility": round(volatility, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "max_drawdown": round(max_drawdown, 2),
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
        }

    @staticmethod
    def _trade_to_dict(trade: Trade) -> Dict:
        """转换交易记录为字典"""
        return {
            "stock_code": trade.stock_code,
            "direction": trade.direction,
            "date": trade.date.strftime("%Y-%m-%d"),
            "price": round(trade.price, 2),
            "shares": trade.shares,
            "amount": round(trade.amount, 2),
            "commission": round(trade.commission, 2),
            "tax": round(trade.tax, 2),
            "total_cost": round(trade.total_cost, 2),
        }

    @staticmethod
    def _get_final_positions(portfolio: Portfolio) -> List[Dict]:
        """获取最终持仓"""
        positions = []
        for stock_code, position in portfolio.positions.items():
            positions.append(
                {
                    "stock_code": stock_code,
                    "entry_date": position.entry_date.strftime("%Y-%m-%d"),
                    "entry_price": round(position.entry_price, 2),
                    "shares": position.shares,
                    "current_price": round(position.current_price, 2),
                    "unrealized_pnl": round(position.unrealized_pnl, 2),
                    "unrealized_pnl_pct": round(
                        position.unrealized_pnl_pct * 100, 2
                    ),
                }
            )
        return positions
```

---

#### 2. ThreeLayerBacktestAdapter（适配器层）

**文件路径**：`backend/app/core_adapters/three_layer_backtest_adapter.py`

**功能**：
- 封装 ThreeLayerBacktestEngine
- 提供异步接口
- 处理数据加载和格式转换

**完整实现**：

```python
"""
三层架构回测适配器
"""

import asyncio
from typing import Any, Dict

import pandas as pd
from loguru import logger

from ..services.data_loader import DataLoader
from ..services.three_layer_backtest_engine import ThreeLayerBacktestEngine
from ..strategies.three_layer.base.strategy_composer import StrategyComposer


class ThreeLayerBacktestAdapter:
    """
    三层架构回测适配器

    职责：
    1. 数据加载
    2. 调用回测引擎
    3. 格式转换
    4. 缓存支持
    """

    def __init__(self):
        self.data_loader = DataLoader()
        self.backtest_engine = ThreeLayerBacktestEngine()

    async def run_backtest(
        self,
        composer: StrategyComposer,
        stock_codes: list[str],
        start_date: str,
        end_date: str,
        initial_capital: float = 1000000.0,
    ) -> Dict[str, Any]:
        """
        执行三层架构回测

        参数:
            composer: 策略组合器
            stock_codes: 股票代码列表（用于选股器的候选池）
            start_date: 回测开始日期
            end_date: 回测结束日期
            initial_capital: 初始资金

        返回:
            回测结果字典
        """
        logger.info(
            f"开始三层架构回测: {len(stock_codes)} 只股票, "
            f"{start_date} ~ {end_date}"
        )

        # 验证策略组合
        validation = composer.validate()
        if not validation["valid"]:
            raise ValueError(f"策略组合验证失败: {validation['errors']}")

        # 异步加载数据
        market_data, stock_data = await self._load_data(
            stock_codes, start_date, end_date
        )

        # 在线程池中执行回测（CPU 密集型）
        result = await asyncio.to_thread(
            self.backtest_engine.run_backtest,
            selector=composer.selector,
            entry=composer.entry,
            exit=composer.exit,
            market_data=market_data,
            stock_data=stock_data,
            start_date=start_date,
            end_date=end_date,
            rebalance_freq=composer.rebalance_freq,
        )

        logger.info("三层架构回测完成")

        return result

    async def _load_data(
        self, stock_codes: list[str], start_date: str, end_date: str
    ) -> tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        加载数据

        返回:
            (market_data, stock_data)
            - market_data: DataFrame(index=date, columns=stock_codes)
            - stock_data: {stock_code: OHLCV DataFrame}
        """
        logger.info(f"加载数据: {len(stock_codes)} 只股票")

        # 并行加载所有股票数据
        tasks = [
            self.data_loader.load_stock_data(code, start_date, end_date)
            for code in stock_codes
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理加载结果
        stock_data = {}
        for code, result in zip(stock_codes, results):
            if isinstance(result, Exception):
                logger.warning(f"加载 {code} 数据失败: {result}")
                continue
            if result is not None and not result.empty:
                stock_data[code] = result

        logger.info(f"成功加载 {len(stock_data)} 只股票数据")

        # 构建 market_data（全市场收盘价矩阵）
        market_data = pd.DataFrame(
            {code: df["close"] for code, df in stock_data.items()}
        )

        return market_data, stock_data
```

---

## 任务 4.0.6：创建 REST API 端点

### 目标

提供三层架构的 REST API 端点，供前端调用。

### 工作量

**预计耗时**：2-3 天

### API 设计

**路由前缀**：`/api/three-layer-strategy`

**端点清单**：

| 端点 | 方法 | 功能 | 优先级 |
|------|------|------|--------|
| `/selectors` | GET | 获取所有选股器列表 | P0 |
| `/entries` | GET | 获取所有入场策略列表 | P0 |
| `/exits` | GET | 获取所有退出策略列表 | P0 |
| `/metadata` | POST | 获取组合策略元数据 | P0 |
| `/validate` | POST | 验证策略组合 | P0 |
| `/backtest` | POST | 执行回测 | P0 |

---

### 实施详情

**文件路径**：`backend/app/api/endpoints/three_layer_strategy.py`

**完整实现**：

```python
"""
三层架构策略 API 端点
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from ...core_adapters.three_layer_backtest_adapter import ThreeLayerBacktestAdapter
from ...models.api_response import ApiResponse
from ...strategies.three_layer.base.strategy_composer import StrategyComposer
from ...strategies.three_layer.registry import (
    get_entry_strategy,
    get_exit_strategy,
    get_selector,
    list_entries,
    list_exits,
    list_selectors,
)

router = APIRouter(prefix="/three-layer-strategy", tags=["三层策略"])


# ==================== Pydantic 模型 ====================


class ComposedStrategyRequest(BaseModel):
    """组合策略请求"""

    selector_id: str = Field(..., description="选股器ID")
    selector_params: Dict[str, Any] = Field(default_factory=dict, description="选股器参数")
    entry_id: str = Field(..., description="入场策略ID")
    entry_params: Dict[str, Any] = Field(default_factory=dict, description="入场策略参数")
    exit_id: str = Field(..., description="退出策略ID")
    exit_params: Dict[str, Any] = Field(default_factory=dict, description="退出策略参数")
    rebalance_freq: str = Field(default="W", description="选股频率 (D/W/M)")


class BacktestRequest(BaseModel):
    """回测请求"""

    strategy: ComposedStrategyRequest = Field(..., description="策略组合")
    stock_codes: List[str] = Field(..., description="股票代码列表")
    start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    initial_capital: float = Field(default=1000000.0, description="初始资金")


# ==================== API 端点 ====================


@router.get("/selectors")
async def get_selectors():
    """
    获取所有可用选股器

    返回:
        [
            {
                "id": "momentum",
                "name": "动量选股器",
                "description": "选择近期涨幅最大的股票",
                "version": "1.0.0",
                "parameter_count": 4
            },
            ...
        ]
    """
    try:
        selectors = list_selectors()
        return ApiResponse.success(data=selectors)
    except Exception as e:
        logger.error(f"获取选股器列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entries")
async def get_entry_strategies():
    """
    获取所有可用入场策略

    返回:
        [
            {
                "id": "ma_breakout",
                "name": "均线突破入场",
                "description": "短期均线上穿长期均线时买入",
                "version": "1.0.0",
                "parameter_count": 4
            },
            ...
        ]
    """
    try:
        entries = list_entries()
        return ApiResponse.success(data=entries)
    except Exception as e:
        logger.error(f"获取入场策略列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exits")
async def get_exit_strategies():
    """
    获取所有可用退出策略

    返回:
        [
            {
                "id": "atr_stop_loss",
                "name": "ATR 动态止损",
                "description": "基于 ATR 指标设置动态止损",
                "version": "1.0.0",
                "parameter_count": 3
            },
            ...
        ]
    """
    try:
        exits = list_exits()
        return ApiResponse.success(data=exits)
    except Exception as e:
        logger.error(f"获取退出策略列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metadata")
async def get_strategy_metadata(request: ComposedStrategyRequest):
    """
    获取组合策略的完整元数据

    包含所有参数定义、默认值、取值范围等

    请求示例:
        {
            "selector_id": "momentum",
            "selector_params": {},
            "entry_id": "ma_breakout",
            "entry_params": {},
            "exit_id": "atr_stop_loss",
            "exit_params": {},
            "rebalance_freq": "W"
        }

    返回:
        {
            "selector": {
                "id": "momentum",
                "name": "动量选股器",
                "parameters": [...]
            },
            "entry": {...},
            "exit": {...},
            "rebalance_freq": "W"
        }
    """
    try:
        # 创建策略实例
        selector = get_selector(request.selector_id, request.selector_params)
        entry = get_entry_strategy(request.entry_id, request.entry_params)
        exit_strategy = get_exit_strategy(request.exit_id, request.exit_params)

        # 创建组合器
        composer = StrategyComposer(
            selector=selector,
            entry=entry,
            exit=exit_strategy,
            rebalance_freq=request.rebalance_freq,
        )

        # 获取元数据
        metadata = composer.get_metadata()

        return ApiResponse.success(data=metadata)

    except ValueError as e:
        logger.warning(f"参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取元数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_strategy(request: ComposedStrategyRequest):
    """
    验证策略组合的有效性

    返回:
        {
            "valid": true,
            "errors": []
        }

    或:
        {
            "valid": false,
            "errors": ["选股器参数错误: ...", "入场策略参数错误: ..."]
        }
    """
    try:
        # 创建策略实例
        selector = get_selector(request.selector_id, request.selector_params)
        entry = get_entry_strategy(request.entry_id, request.entry_params)
        exit_strategy = get_exit_strategy(request.exit_id, request.exit_params)

        # 创建组合器并验证
        composer = StrategyComposer(
            selector=selector,
            entry=entry,
            exit=exit_strategy,
            rebalance_freq=request.rebalance_freq,
        )

        validation_result = composer.validate()

        return ApiResponse.success(data=validation_result)

    except ValueError as e:
        # 参数错误直接返回验证失败
        return ApiResponse.success(data={"valid": False, "errors": [str(e)]})
    except Exception as e:
        logger.error(f"验证策略失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """
    执行三层架构回测

    请求示例:
        {
            "strategy": {
                "selector_id": "momentum",
                "selector_params": {"top_n": 50, "lookback_period": 20},
                "entry_id": "ma_breakout",
                "entry_params": {"short_window": 5, "long_window": 20},
                "exit_id": "atr_stop_loss",
                "exit_params": {"atr_multiplier": 2.0},
                "rebalance_freq": "W"
            },
            "stock_codes": ["600000.SH", "000001.SZ", ...],
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 1000000.0
        }

    返回:
        {
            "portfolio_value": [...],   # 净值曲线
            "trades": [...],             # 交易记录
            "positions": [...],          # 最终持仓
            "metrics": {...}             # 绩效指标
        }
    """
    try:
        logger.info(f"收到三层架构回测请求: {request.start_date} ~ {request.end_date}")

        # 创建策略实例
        selector = get_selector(
            request.strategy.selector_id, request.strategy.selector_params
        )
        entry = get_entry_strategy(
            request.strategy.entry_id, request.strategy.entry_params
        )
        exit_strategy = get_exit_strategy(
            request.strategy.exit_id, request.strategy.exit_params
        )

        # 创建组合器
        composer = StrategyComposer(
            selector=selector,
            entry=entry,
            exit=exit_strategy,
            rebalance_freq=request.strategy.rebalance_freq,
        )

        # 执行回测
        adapter = ThreeLayerBacktestAdapter()
        result = await adapter.run_backtest(
            composer=composer,
            stock_codes=request.stock_codes,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
        )

        return ApiResponse.success(data=result)

    except ValueError as e:
        logger.warning(f"参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"回测执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 策略注册表实现

**文件路径**：`backend/app/strategies/three_layer/registry.py`

```python
"""
策略注册表
管理所有三层策略的注册和实例化
"""

from typing import Any, Dict, List, Type

from .base.entry_strategy import EntryStrategy
from .base.exit_strategy import ExitStrategy
from .base.stock_selector import StockSelector
from .entries.immediate_entry import ImmediateEntry
from .entries.ma_breakout_entry import MABreakoutEntry
from .entries.rsi_oversold_entry import RSIOversoldEntry
from .exits.atr_stop_loss_exit import ATRStopLossExit
from .exits.fixed_stop_loss_exit import FixedStopLossExit
from .exits.time_based_exit import TimeBasedExit
from .selectors.external_selector import ExternalSelector
from .selectors.momentum_selector import MomentumSelector
from .selectors.value_selector import ValueSelector

# ==================== 注册表 ====================

SELECTORS: Dict[str, Type[StockSelector]] = {
    "momentum": MomentumSelector,
    "value": ValueSelector,
    "external": ExternalSelector,
}

ENTRIES: Dict[str, Type[EntryStrategy]] = {
    "ma_breakout": MABreakoutEntry,
    "rsi_oversold": RSIOversoldEntry,
    "immediate": ImmediateEntry,
}

EXITS: Dict[str, Type[ExitStrategy]] = {
    "atr_stop_loss": ATRStopLossExit,
    "fixed_stop_loss": FixedStopLossExit,
    "time_based": TimeBasedExit,
}


# ==================== 工厂方法 ====================


def get_selector(selector_id: str, params: Dict[str, Any]) -> StockSelector:
    """获取选股器实例"""
    if selector_id not in SELECTORS:
        raise ValueError(f"未知的选股器ID: {selector_id}")
    return SELECTORS[selector_id](params=params)


def get_entry_strategy(entry_id: str, params: Dict[str, Any]) -> EntryStrategy:
    """获取入场策略实例"""
    if entry_id not in ENTRIES:
        raise ValueError(f"未知的入场策略ID: {entry_id}")
    return ENTRIES[entry_id](params=params)


def get_exit_strategy(exit_id: str, params: Dict[str, Any]) -> ExitStrategy:
    """获取退出策略实例"""
    if exit_id not in EXITS:
        raise ValueError(f"未知的退出策略ID: {exit_id}")
    return EXITS[exit_id](params=params)


# ==================== 列表方法 ====================


def list_selectors() -> List[Dict[str, Any]]:
    """列出所有选股器"""
    return [
        {
            "id": selector_cls().id,
            "name": selector_cls().name,
            "description": selector_cls().description,
            "version": selector_cls().version,
            "parameter_count": len(selector_cls.get_parameters()),
        }
        for selector_cls in SELECTORS.values()
    ]


def list_entries() -> List[Dict[str, Any]]:
    """列出所有入场策略"""
    return [
        {
            "id": entry_cls().id,
            "name": entry_cls().name,
            "description": entry_cls().description,
            "version": entry_cls().version,
            "parameter_count": len(entry_cls.get_parameters()),
        }
        for entry_cls in ENTRIES.values()
    ]


def list_exits() -> List[Dict[str, Any]]:
    """列出所有退出策略"""
    return [
        {
            "id": exit_cls().id,
            "name": exit_cls().name,
            "description": exit_cls().description,
            "version": exit_cls().version,
            "parameter_count": len(exit_cls.get_parameters()),
        }
        for exit_cls in EXITS.values()
    ]
```

---

## API 使用示例

### 示例 1：获取所有可用策略

```bash
# 获取选股器列表
curl http://localhost:8000/api/three-layer-strategy/selectors

# 获取入场策略列表
curl http://localhost:8000/api/three-layer-strategy/entries

# 获取退出策略列表
curl http://localhost:8000/api/three-layer-strategy/exits
```

### 示例 2：获取策略元数据

```bash
curl -X POST http://localhost:8000/api/three-layer-strategy/metadata \
  -H "Content-Type: application/json" \
  -d '{
    "selector_id": "momentum",
    "selector_params": {},
    "entry_id": "ma_breakout",
    "entry_params": {},
    "exit_id": "atr_stop_loss",
    "exit_params": {},
    "rebalance_freq": "W"
  }'
```

### 示例 3：执行回测

```bash
curl -X POST http://localhost:8000/api/three-layer-strategy/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": {
      "selector_id": "momentum",
      "selector_params": {
        "lookback_period": 20,
        "top_n": 50,
        "filter_negative": true
      },
      "entry_id": "ma_breakout",
      "entry_params": {
        "short_window": 5,
        "long_window": 20,
        "min_breakout_pct": 0.5
      },
      "exit_id": "atr_stop_loss",
      "exit_params": {
        "atr_period": 14,
        "atr_multiplier": 2.0
      },
      "rebalance_freq": "W"
    },
    "stock_codes": ["600000.SH", "000001.SZ", "000002.SZ"],
    "start_date": "2024-01-01",
    "end_date": "2024-06-30",
    "initial_capital": 1000000.0
  }'
```

---

## 性能优化

### 优化策略

| 优化点 | 方案 | 预期效果 |
|--------|------|---------|
| **数据加载** | 并行加载多只股票数据 | 加载时间 ↓ 60% |
| **回测计算** | 使用 asyncio.to_thread() 避免阻塞 | 响应时间 ↓ 30% |
| **结果缓存** | Redis 缓存回测结果（TTL=1小时） | 重复请求命中率 50%+ |
| **选股缓存** | Redis 缓存选股器输出（TTL=1天） | 选股时间 ↓ 80% |

### 性能目标

| 指标 | 目标值 | 备注 |
|------|--------|------|
| **API 响应时间** | P95 < 5000ms | 100只股票 × 180天回测 |
| **并发支持** | 20 QPS | 限流保护 |
| **缓存命中率** | 40%+ | 相同参数回测 |

---

## 验收标准

### 任务 4.0.5 验收标准

- ✅ ThreeLayerBacktestEngine 实现完成
- ✅ 回测循环正确执行三层逻辑
- ✅ 持仓管理和资金管理正确
- ✅ 手续费和滑点计算正确
- ✅ 绩效指标计算准确
- ✅ 单元测试覆盖率 ≥ 85%

### 任务 4.0.6 验收标准

- ✅ 6 个 API 端点实现完成
- ✅ 策略注册表正确管理所有策略
- ✅ 参数验证机制完善
- ✅ 错误处理规范
- ✅ API 文档完整（Swagger）
- ✅ 集成测试通过

---

## 下一步

继续阅读：
- [Phase 4.1-4.2 实施文档](./phase_4_1_4_2_implementation.md)（策略库扩展与测试）
- [测试策略与工作量评估](./phase_4_testing_and_estimation.md)

---

**文档维护者**：开发团队
**创建日期**：2026-02-06
**最后更新**：2026-02-06
