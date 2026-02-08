# API 参考文档

**文档版本**: v5.1.0
**最后更新**: 2026-02-07

---

## 📋 目录

- [策略 API](#策略-api)
- [风控 API](#风控-api)
- [回测引擎 API](#回测引擎-api)
- [机器学习 API](#机器学习-api)
- [数据模型](#数据模型)

---

## 策略 API

### EntryStrategy

**入场策略基类**

```python
from abc import ABC, abstractmethod
from typing import Dict, List
import pandas as pd

class EntryStrategy(ABC):
    """入场策略基类"""

    @abstractmethod
    def generate_signals(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> Dict[str, Dict]:
        """
        生成入场信号

        Args:
            stock_pool: 股票池列表
            market_data: 市场数据 DataFrame
            date: 当前日期 (YYYY-MM-DD)

        Returns:
            Dict[str, Dict]: 信号字典
            {
                '600000.SH': {
                    'action': 'long',      # 'long' 或 'short'
                    'weight': 0.15         # 仓位权重 0-1
                },
                '000001.SZ': {
                    'action': 'short',
                    'weight': 0.10
                }
            }

        Notes:
            - 所有权重之和应为 1.0 (代表 100% 仓位)
            - action 只能是 'long' 或 'short'
            - 策略内部需要归一化权重
        """
        pass
```

### MomentumEntry

**动量入场策略**

```python
class MomentumEntry(EntryStrategy):
    """
    动量入场策略

    逻辑:
    - 动量 > threshold → 做多
    - 动量 < -threshold → 做空
    - 权重与动量大小成正比
    """

    def __init__(
        self,
        lookback: int = 20,
        threshold: float = 0.10
    ):
        """
        Args:
            lookback: 回看窗口期
            threshold: 动量阈值
        """
        self.lookback = lookback
        self.threshold = threshold
```

### MLEntry

**ML 入场策略**

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
        """
        Args:
            model_path: 模型文件路径
            confidence_threshold: 置信度阈值 (0-1)
            top_long: 选择前 N 只做多
            top_short: 选择前 N 只做空
        """
        self.model = TrainedModel.load(model_path)
        self.confidence_threshold = confidence_threshold
        self.top_long = top_long
        self.top_short = top_short
```

### ExitStrategy

**退出策略基类**

```python
class ExitStrategy(ABC):
    """退出策略基类"""

    @abstractmethod
    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        market_data: pd.DataFrame,
        date: str
    ) -> Dict[str, Any]:
        """
        生成退出信号

        Args:
            positions: 当前持仓字典
            market_data: 市场数据
            date: 当前日期

        Returns:
            {
                'close': ['600000.SH', '000001.SZ'],  # 需要平仓的股票
                'reverse': {                          # 需要反向开仓的股票
                    '600036.SH': {
                        'action': 'short',
                        'weight': 0.10
                    }
                }
            }

        Notes:
            - 'close': 平仓(关闭当前持仓)
            - 'reverse': 反向开仓(平掉当前仓位 + 开反向新仓位)
        """
        pass
```

### TimeBasedExit

**时间退出策略**

```python
class TimeBasedExit(ExitStrategy):
    """时间退出策略"""

    def __init__(self, max_holding_days: int = 20):
        """
        Args:
            max_holding_days: 最大持仓天数
        """
        self.max_holding_days = max_holding_days
```

---

## 风控 API

### RiskManager

**风控管理器**

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
        """
        Args:
            max_position_loss_pct: 单仓位最大亏损比例
            max_portfolio_loss_pct: 组合最大亏损比例
            max_holding_days: 最大持仓天数
            max_leverage: 最大杠杆倍数
            max_position_size: 单仓位最大权重
            max_sector_concentration: 单行业最大权重
            enable_short_constraints: 是否启用融券限制
            shortable_stocks: 可融券股票列表
        """
        pass

    def check_stop_loss(
        self,
        positions: Dict[str, Position],
        date: str
    ) -> List[str]:
        """
        检查止损条件

        Args:
            positions: 当前持仓字典
            date: 当前日期

        Returns:
            List[str]: 需要强制平仓的股票列表
        """
        pass

    def check_entry_limits(
        self,
        new_signals: Dict[str, Dict],
        current_positions: Dict[str, Position],
        portfolio_value: float,
        sector_map: Dict[str, str] = None
    ) -> Dict[str, Dict]:
        """
        检查入场限制，调整新信号的权重

        Args:
            new_signals: 新信号字典
            current_positions: 当前持仓
            portfolio_value: 组合总价值
            sector_map: 股票行业映射 (可选)

        Returns:
            Dict[str, Dict]: 调整后的信号字典
        """
        pass
```

---

## 回测引擎 API

### BacktestEngine

**回测引擎**

```python
class BacktestEngine:
    """回测引擎"""

    def __init__(
        self,
        entry_strategy: EntryStrategy,
        exit_strategy: ExitStrategy,
        risk_manager: RiskManager
    ):
        """
        Args:
            entry_strategy: 入场策略实例
            exit_strategy: 退出策略实例
            risk_manager: 风控管理器实例
        """
        self.entry_strategy = entry_strategy
        self.exit_strategy = exit_strategy
        self.risk_manager = risk_manager

    def run(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        start_date: str,
        end_date: str,
        initial_capital: float = 1000000.0,
        commission_rate: float = 0.0003,
        stamp_tax: float = 0.001,
        slippage_pct: float = 0.001
    ) -> BacktestResult:
        """
        运行回测

        Args:
            stock_pool: 股票池列表
            market_data: 市场数据 DataFrame
            start_date: 回测开始日期 (YYYY-MM-DD)
            end_date: 回测结束日期 (YYYY-MM-DD)
            initial_capital: 初始资金
            commission_rate: 佣金费率 (默认万三)
            stamp_tax: 印花税率 (默认千一)
            slippage_pct: 滑点比例 (默认 0.1%)

        Returns:
            BacktestResult: 回测结果对象
        """
        pass
```

### Portfolio

**组合管理**

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
        """
        Args:
            initial_capital: 初始资金
            commission_rate: 佣金费率
            stamp_tax: 印花税率
            slippage_pct: 滑点比例
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}

    def open_positions(
        self,
        signals: Dict[str, Dict],
        market_data: pd.DataFrame,
        date: str
    ):
        """
        开仓

        Args:
            signals: 信号字典
            market_data: 市场数据
            date: 当前日期
        """
        pass

    def close_positions(
        self,
        stocks: List[str],
        market_data: pd.DataFrame,
        date: str
    ):
        """
        平仓

        Args:
            stocks: 需要平仓的股票列表
            market_data: 市场数据
            date: 当前日期
        """
        pass

    @property
    def total_value(self) -> float:
        """组合总价值"""
        pass
```

---

## 机器学习 API

### MLStockRanker

**ML 股票评分工具**

```python
class MLStockRanker:
    """
    ML 股票评分工具 (类似 BigQuant StockRanker)
    """

    def __init__(
        self,
        model_path: str,
        feature_config: Dict = None
    ):
        """
        Args:
            model_path: 模型文件路径
            feature_config: 特征计算配置
        """
        self.model = self._load_model(model_path)
        self.feature_config = feature_config

    def rank(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        date: str,
        return_top_n: int = None
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
                }
            }
        """
        pass
```

### ModelTrainer

**模型训练器**

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
    """模型训练器"""

    def __init__(self, config: TrainingConfig):
        """
        Args:
            config: 训练配置对象
        """
        self.config = config

    def train(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame
    ) -> TrainedModel:
        """
        训练模型

        Args:
            stock_pool: 股票池列表
            market_data: 市场数据

        Returns:
            TrainedModel: 训练好的模型对象
        """
        pass
```

### TrainedModel

**训练好的模型**

```python
class TrainedModel:
    """训练好的模型"""

    def __init__(
        self,
        model,
        feature_engine: FeatureEngine,
        config: TrainingConfig,
        metrics: Dict
    ):
        """
        Args:
            model: 训练好的模型对象
            feature_engine: 特征引擎
            config: 训练配置
            metrics: 评估指标
        """
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

        Args:
            stock_codes: 股票代码列表
            market_data: 市场数据
            date: 预测日期

        Returns:
            pd.DataFrame: 预测结果
                columns = ['expected_return', 'volatility', 'confidence']
                index = stock_codes
        """
        pass

    def save(self, path: str):
        """保存模型到文件"""
        pass

    @staticmethod
    def load(path: str) -> 'TrainedModel':
        """从文件加载模型"""
        pass
```

---

## 数据模型

### Position

**持仓信息**

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

### Signal

**交易信号**

```python
@dataclass
class Signal:
    """交易信号"""
    stock_code: str                       # 股票代码
    action: Literal['long', 'short']      # 'long' 或 'short'
    weight: float                         # 仓位权重 0-1
    metadata: Dict[str, Any] = None       # 额外元数据
```

### BacktestResult

**回测结果**

```python
@dataclass
class BacktestResult:
    """回测结果"""
    # 基础信息
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float

    # 收益指标
    total_return: float                   # 总收益率
    annual_return: float                  # 年化收益率
    excess_return: float                  # 超额收益率

    # 风险指标
    volatility: float                     # 波动率
    max_drawdown: float                   # 最大回撤
    downside_risk: float                  # 下行风险

    # 风险调整收益
    sharpe_ratio: float                   # 夏普比率
    sortino_ratio: float                  # 索提诺比率
    calmar_ratio: float                   # 卡玛比率

    # 交易指标
    win_rate: float                       # 胜率
    profit_loss_ratio: float              # 盈亏比
    turnover_rate: float                  # 换手率
    total_trades: int                     # 总交易次数

    # 详细数据
    equity_curve: pd.Series               # 权益曲线
    drawdown_curve: pd.Series             # 回撤曲线
    positions_history: List[Dict]         # 持仓历史
    trades_history: List[Dict]            # 交易历史
```

---

## 使用示例

### 完整回测流程

```python
from core.strategies.entries import MomentumEntry
from core.strategies.exits import TimeBasedExit
from core.risk import RiskManager
from core.backtest import BacktestEngine

# 1. 创建策略
entry = MomentumEntry(lookback=20, threshold=0.10)
exit_strategy = TimeBasedExit(max_holding_days=20)
risk_manager = RiskManager(
    max_position_loss_pct=0.10,
    max_leverage=1.0
)

# 2. 创建回测引擎
engine = BacktestEngine(
    entry_strategy=entry,
    exit_strategy=exit_strategy,
    risk_manager=risk_manager
)

# 3. 运行回测
result = engine.run(
    stock_pool=['600000.SH', '000001.SZ'],
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31',
    initial_capital=1000000.0
)

# 4. 查看结果
print(f"总收益率: {result.total_return:.2%}")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
print(f"最大回撤: {result.max_drawdown:.2%}")
```

---

## 相关文档

- [架构详解](../architecture/overview.md)
- [机器学习系统](../ml/README.md)
- [最佳实践](../guides/best-practices.md)

---

**文档版本**: v5.1.0
**最后更新**: 2026-02-07
